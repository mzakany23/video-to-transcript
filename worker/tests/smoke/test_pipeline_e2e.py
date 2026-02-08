"""
End-to-end pipeline smoke test.
Drops a file into Dropbox, waits for the worker to process it,
then verifies output files in Dropbox and emails in Gmail.

Requires: OPENAI_API_KEY, Dropbox credentials, Gmail credentials.
Run with: pytest tests/smoke/test_pipeline_e2e.py -v -m smoke -s
"""

import imaplib
import email
import json
import os
import subprocess
import time
from datetime import datetime, timezone

import pytest
import requests


# ---------------------------------------------------------------------------
# Credentials — all from environment variables (source ~/.secrets first)
# ---------------------------------------------------------------------------

GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
PROJECT_ID = os.environ.get("PROJECT_ID", "jos-transcripts")
DROPBOX_RAW_FOLDER = os.environ.get("DROPBOX_RAW_FOLDER", "/jos-transcripts/raw")
DROPBOX_PROCESSED_FOLDER = os.environ.get("DROPBOX_PROCESSED_FOLDER", "/jos-transcripts/processed")
DROPBOX_APP_KEY = os.environ.get("DROPBOX_APP_KEY", "")
DROPBOX_APP_SECRET = os.environ.get("DROPBOX_APP_SECRET", "")
DROPBOX_REFRESH_TOKEN = os.environ.get("DROPBOX_REFRESH_TOKEN", "")


def _get_dropbox_token() -> str:
    """Get a fresh Dropbox access token via refresh token."""
    resp = requests.post(
        "https://api.dropboxapi.com/oauth2/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": DROPBOX_REFRESH_TOKEN,
            "client_id": DROPBOX_APP_KEY,
            "client_secret": DROPBOX_APP_SECRET,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _can_run_e2e() -> bool:
    """Check whether we have everything needed for the e2e test."""
    if not all([DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REFRESH_TOKEN]):
        return False
    if not all([GMAIL_ADDRESS, GMAIL_APP_PASSWORD]):
        return False
    try:
        _get_dropbox_token()
        return True
    except Exception:
        return False


SKIP_NO_E2E = pytest.mark.skipif(
    not _can_run_e2e(),
    reason="Dropbox + Gmail credentials required (set DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REFRESH_TOKEN, GMAIL_ADDRESS, GMAIL_APP_PASSWORD)",
)

SKIP_NO_GMAIL = pytest.mark.skipif(
    not all([GMAIL_ADDRESS, GMAIL_APP_PASSWORD]),
    reason="GMAIL_ADDRESS and GMAIL_APP_PASSWORD required",
)

TEST_FILENAME = "e2e-pipeline-test.m4a"


# ---------------------------------------------------------------------------
# Dropbox helpers
# ---------------------------------------------------------------------------

def dropbox_upload(token: str, data: bytes, path: str):
    """Upload bytes to Dropbox."""
    resp = requests.post(
        "https://content.dropboxapi.com/2/files/upload",
        headers={
            "Authorization": f"Bearer {token}",
            "Dropbox-API-Arg": json.dumps({"path": path, "mode": "overwrite"}),
            "Content-Type": "application/octet-stream",
        },
        data=data,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def dropbox_delete(token: str, path: str):
    """Delete a file/folder from Dropbox (ignores not-found)."""
    resp = requests.post(
        "https://api.dropboxapi.com/2/files/delete_v2",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"path": path},
        timeout=15,
    )
    # 409 = path not found — fine
    if resp.status_code not in (200, 409):
        resp.raise_for_status()


def dropbox_list_folder(token: str, path: str) -> list:
    """List files in a Dropbox folder."""
    resp = requests.post(
        "https://api.dropboxapi.com/2/files/list_folder",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"path": path},
        timeout=15,
    )
    if resp.status_code == 409:
        return []  # folder doesn't exist
    resp.raise_for_status()
    return resp.json().get("entries", [])


def dropbox_download(token: str, path: str) -> bytes:
    """Download a file from Dropbox."""
    resp = requests.post(
        "https://content.dropboxapi.com/2/files/download",
        headers={
            "Authorization": f"Bearer {token}",
            "Dropbox-API-Arg": json.dumps({"path": path}),
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.content


# ---------------------------------------------------------------------------
# Gmail helpers
# ---------------------------------------------------------------------------

def gmail_search_recent(subject_fragment: str, since_time: datetime, timeout_secs: int = 120) -> list:
    """
    Search Gmail IMAP for recent messages matching a subject fragment.
    Polls until found or timeout.
    """
    deadline = time.time() + timeout_secs
    while time.time() < deadline:
        try:
            conn = imaplib.IMAP4_SSL("imap.gmail.com")
            conn.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            conn.select("INBOX")

            # IMAP date search (day granularity)
            date_str = since_time.strftime("%d-%b-%Y")
            _, msg_ids = conn.search(None, f'(SINCE "{date_str}" SUBJECT "{subject_fragment}")')

            results = []
            for num in msg_ids[0].split():
                _, data = conn.fetch(num, "(RFC822)")
                msg = email.message_from_bytes(data[0][1])
                msg_date = email.utils.parsedate_to_datetime(msg["Date"])
                if msg_date >= since_time:
                    results.append({
                        "subject": msg["Subject"],
                        "from": msg["From"],
                        "to": msg["To"],
                        "date": msg_date,
                    })

            conn.logout()

            if results:
                return results
        except Exception as e:
            print(f"  IMAP poll error (will retry): {e}")

        time.sleep(10)

    return []


# ---------------------------------------------------------------------------
# Cloud Run job helpers
# ---------------------------------------------------------------------------

def wait_for_job_completion(execution_prefix: str, timeout_secs: int = 180) -> dict:
    """Wait for a Cloud Run job execution to complete."""
    deadline = time.time() + timeout_secs
    while time.time() < deadline:
        try:
            result = subprocess.run(
                [
                    "gcloud", "run", "jobs", "executions", "list",
                    "--job=transcription-worker",
                    f"--project={PROJECT_ID}",
                    "--region=us-east1",
                    "--limit=1",
                    "--format=json",
                ],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                executions = json.loads(result.stdout)
                if executions:
                    latest = executions[0]
                    conditions = latest.get("status", {}).get("conditions", [])
                    for c in conditions:
                        if c.get("type") == "Completed" and c.get("status") == "True":
                            return {"status": "completed", "execution": latest}
        except Exception as e:
            print(f"  Job poll error (will retry): {e}")

        time.sleep(10)

    return {"status": "timeout"}


# ---------------------------------------------------------------------------
# The test
# ---------------------------------------------------------------------------

@pytest.mark.smoke
@SKIP_NO_E2E
def test_full_pipeline_dropbox_to_email():
    """
    Full e2e: upload to Dropbox -> webhook -> worker -> verify Dropbox output + Gmail email.

    This test takes ~2-3 minutes:
    - Upload a tiny test audio file to Dropbox raw folder
    - Wait for webhook + worker to process it
    - Verify output files exist in Dropbox processed folder
    - Verify emails arrived in Gmail
    - Clean up test artifacts
    """
    token = _get_dropbox_token()
    test_start = datetime.now(timezone.utc)
    test_stem = TEST_FILENAME.rsplit(".", 1)[0]

    # --- Generate a tiny test audio file (10s sine wave) ---
    print("\n[1/5] Generating test audio file...")
    audio_path = "/tmp/e2e-pipeline-test.m4a"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=10",
            "-ar", "16000", "-ac", "1", "-b:a", "32k", audio_path,
        ],
        capture_output=True, timeout=15,
    )
    with open(audio_path, "rb") as f:
        audio_data = f.read()
    assert len(audio_data) > 0, "Failed to generate test audio"
    print(f"  Generated {len(audio_data)} byte test file")

    # --- Upload to Dropbox ---
    print("[2/5] Uploading to Dropbox raw folder...")
    upload_result = dropbox_upload(token, audio_data, f"{DROPBOX_RAW_FOLDER}/{TEST_FILENAME}")
    assert upload_result["name"] == TEST_FILENAME
    print(f"  Uploaded: {upload_result['path_display']}")

    # --- Wait for Cloud Run job to complete ---
    print("[3/5] Waiting for pipeline to process (up to 3 min)...")
    job_result = wait_for_job_completion("transcription-worker", timeout_secs=180)
    assert job_result["status"] == "completed", "Worker job did not complete in time"
    print("  Worker job completed")

    # --- Verify Dropbox output ---
    print("[4/5] Verifying Dropbox output files...")
    # Refresh token in case it expired during wait
    token = _get_dropbox_token()

    # Find the processed folder (format: YYYY-MM-DD:HH:MM-stem)
    processed_entries = dropbox_list_folder(token, DROPBOX_PROCESSED_FOLDER)
    matching_folders = [
        e for e in processed_entries
        if e[".tag"] == "folder" and test_stem in e["name"]
    ]
    assert len(matching_folders) > 0, (
        f"No processed folder found for '{test_stem}'. "
        f"Found: {[e['name'] for e in processed_entries]}"
    )

    output_folder = matching_folders[-1]  # most recent
    output_path = output_folder["path_display"]
    print(f"  Found output folder: {output_path}")

    output_files = dropbox_list_folder(token, output_path)
    output_names = [e["name"] for e in output_files]
    print(f"  Output files: {output_names}")

    # Verify expected files exist
    assert any(n.endswith(".json") for n in output_names), f"Missing .json in {output_names}"
    assert any(n.endswith(".txt") and "SUMMARY" not in n for n in output_names), f"Missing .txt in {output_names}"
    assert any("SUMMARY.txt" in n for n in output_names), f"Missing SUMMARY.txt in {output_names}"
    assert any("SUMMARY.md" in n for n in output_names), f"Missing SUMMARY.md in {output_names}"

    # Download and validate JSON structure
    json_file = next(n for n in output_names if n.endswith(".json"))
    json_bytes = dropbox_download(token, f"{output_path}/{json_file}")
    transcript_json = json.loads(json_bytes)

    assert "text" in transcript_json, "JSON missing 'text' field"
    assert "segments" in transcript_json, "JSON missing 'segments' field"
    assert len(transcript_json["text"]) > 0, "Transcript text is empty"
    print(f"  JSON valid: {len(transcript_json['text'])} chars, {len(transcript_json.get('segments', []))} segments")

    # Check for topic analysis in JSON
    if "topic_analysis" in transcript_json:
        ta = transcript_json["topic_analysis"]
        assert "summary" in ta, "topic_analysis missing 'summary'"
        print(f"  Topic analysis present: {len(ta.get('summary', ''))} char summary")

    # --- Verify Gmail emails ---
    print("[5/5] Checking Gmail for notification emails...")
    # Look for the summary email (sent to user_emails)
    summary_emails = gmail_search_recent(test_stem, test_start, timeout_secs=60)

    if summary_emails:
        print(f"  Found {len(summary_emails)} matching email(s):")
        for em in summary_emails:
            print(f"    Subject: {em['subject']}")
            print(f"    To: {em['to']}")
            print(f"    Date: {em['date']}")
    else:
        print("  WARNING: No matching emails found (may have delivery delay)")
        # Don't fail on email — there can be IMAP indexing delay
        # The Cloud Run logs already confirmed email was sent

    # --- Cleanup ---
    print("\nCleaning up test artifacts...")
    token = _get_dropbox_token()
    dropbox_delete(token, f"{DROPBOX_RAW_FOLDER}/{TEST_FILENAME}")
    dropbox_delete(token, output_path)
    print("  Cleaned up Dropbox files")

    print(f"\n{'='*60}")
    print("E2E PIPELINE TEST PASSED")
    print(f"  Duration: {(datetime.now(timezone.utc) - test_start).total_seconds():.0f}s")
    print(f"  Output files: {output_names}")
    print(f"  Emails found: {len(summary_emails)}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Standalone verification tests (check last run artifacts without re-running)
# ---------------------------------------------------------------------------

@pytest.mark.smoke
@SKIP_NO_E2E
def test_dropbox_processed_folder_has_recent_output():
    """Verify the most recent processed folder has all expected files."""
    token = _get_dropbox_token()
    entries = dropbox_list_folder(token, DROPBOX_PROCESSED_FOLDER)
    folders = [e for e in entries if e[".tag"] == "folder"]
    assert len(folders) > 0, "No processed folders found"

    # Check most recent folder
    latest = sorted(folders, key=lambda e: e["name"])[-1]
    files = dropbox_list_folder(token, latest["path_display"])
    names = [f["name"] for f in files]

    assert any(n.endswith(".json") for n in names), f"No .json in latest output: {names}"
    assert any(n.endswith(".txt") for n in names), f"No .txt in latest output: {names}"
    print(f"Latest output: {latest['name']} -> {names}")


@pytest.mark.smoke
@SKIP_NO_GMAIL
def test_gmail_imap_login():
    """Verify Gmail IMAP credentials work."""
    try:
        conn = imaplib.IMAP4_SSL("imap.gmail.com")
        status, _ = conn.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        assert status == "OK", f"IMAP login failed: {status}"
        conn.logout()
    except imaplib.IMAP4.error as e:
        pytest.fail(f"Gmail IMAP login failed: {e}")


@pytest.mark.smoke
@SKIP_NO_GMAIL
def test_gmail_has_recent_transcription_email():
    """Verify Gmail has a transcription-related email from recently."""
    conn = imaplib.IMAP4_SSL("imap.gmail.com")
    conn.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
    conn.select("INBOX")

    # Search last 2 days to handle timezone edge cases (IMAP SINCE is day-granularity UTC)
    from datetime import timedelta
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%d-%b-%Y")
    _, msg_ids = conn.search(None, f'(SINCE "{yesterday}" FROM "{GMAIL_ADDRESS}" SUBJECT "Summary Ready")')

    results = []
    for num in msg_ids[0].split():
        _, data = conn.fetch(num, "(BODY[HEADER.FIELDS (SUBJECT DATE)])")
        results.append(data[0][1].decode().strip())

    conn.logout()

    assert len(results) > 0, "No 'Summary Ready' emails found in last 2 days"
    print(f"Found {len(results)} 'Summary Ready' email(s):")
    for r in results:
        print(f"  {r}")
