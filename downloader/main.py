"""
Zoom Downloader Handler
Receives Zoom webhook notifications, downloads recordings, and uploads to Dropbox
"""

import json
import os
import hmac
import hashlib
import tempfile
from typing import Dict, Any, Optional
from datetime import datetime

import functions_framework
from flask import Request
import requests
import dropbox
from google.cloud import storage

# Initialize Sentry for error tracking
try:
    import sentry_sdk
    sentry_dsn = os.environ.get('SENTRY_DSN')
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=os.environ.get('SENTRY_ENVIRONMENT', 'production'),
            release=os.environ.get('VERSION', 'downloader@unknown'),
            send_default_pii=True,
            traces_sample_rate=0.1
        )
        print(f"✅ Sentry initialized - version: {os.environ.get('VERSION', 'unknown')}")
    else:
        print("ℹ️ Sentry DSN not configured, error tracking disabled")
except ImportError:
    print("⚠️ Sentry SDK not installed, error tracking disabled")
except Exception as e:
    print(f"⚠️ Failed to initialize Sentry: {e}")


@functions_framework.http
def zoom_downloader_handler(request: Request):
    """
    HTTP Cloud Function to handle Zoom webhook notifications
    Downloads recordings and uploads to Dropbox for transcription

    Args:
        request: HTTP request from Zoom webhook notifications
    """
    # Handle Zoom webhook verification (GET request with challenge)
    if request.method == 'GET':
        challenge = request.args.get('challenge')
        if challenge:
            print(f"✅ Zoom webhook verification - returning challenge")
            return challenge, 200
        else:
            print("⚠️ GET request without challenge parameter")
            return 'Bad Request', 400

    # Handle actual webhook notifications (POST requests)
    if request.method != 'POST':
        return 'Method not allowed', 405

    # SECURITY: Verify Zoom signature
    zoom_signature = request.headers.get('x-zm-signature')
    zoom_timestamp = request.headers.get('x-zm-request-timestamp')

    if not zoom_signature or not zoom_timestamp:
        print("⚠️ Missing Zoom signature or timestamp - rejecting request")
        return 'Unauthorized', 401

    # Verify the signature using Zoom webhook secret
    webhook_secret = os.environ.get('ZOOM_WEBHOOK_SECRET')
    if not webhook_secret:
        print("❌ Missing ZOOM_WEBHOOK_SECRET environment variable")
        return 'Server Error', 500

    request_body = request.get_data(as_text=True)

    # Zoom signature format: v0=<hash> where hash = HMAC-SHA256(v0:{timestamp}:{body}, secret)
    message = f"v0:{zoom_timestamp}:{request_body}"
    expected_hash = hmac.new(
        webhook_secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    expected_signature = f"v0={expected_hash}"

    if not hmac.compare_digest(zoom_signature, expected_signature):
        print("⚠️ Invalid Zoom signature - rejecting request")
        return 'Unauthorized', 401

    try:
        # Parse Zoom webhook payload
        webhook_data = request.get_json(force=True)
        event_type = webhook_data.get('event')

        print(f"📧 Zoom webhook received: {event_type}")

        # Handle endpoint validation challenge
        if event_type == 'endpoint.url_validation':
            return handle_validation_challenge(webhook_data)

        # Handle recording completed event
        if event_type == 'recording.completed':
            processor = ZoomRecordingProcessor()
            result = processor.process_recording_completed(webhook_data)

            if result['success']:
                print(f"✅ Successfully processed recording: {result.get('file_name')}")
                return 'OK', 200
            else:
                print(f"❌ Failed to process recording: {result.get('error')}")
                return 'Error', 500

        # Other events - just acknowledge
        print(f"ℹ️ Unhandled event type: {event_type}")
        return 'OK', 200

    except Exception as e:
        print(f"❌ Error in webhook handler: {str(e)}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")
        return 'Error', 500


def handle_validation_challenge(payload: Dict[str, Any]) -> tuple:
    """
    Respond to Zoom's endpoint validation challenge

    Args:
        payload: Zoom validation challenge payload

    Returns:
        JSON response with encrypted token
    """
    plain_token = payload.get('payload', {}).get('plainToken')
    webhook_secret = os.environ.get('ZOOM_WEBHOOK_SECRET')

    if not plain_token:
        print("⚠️ Missing plainToken in validation challenge")
        return {'error': 'Missing plainToken'}, 400

    # Create encrypted token response
    encrypted_token = hmac.new(
        webhook_secret.encode('utf-8'),
        plain_token.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    print(f"✅ Responding to Zoom validation challenge")

    response = {
        "plainToken": plain_token,
        "encryptedToken": encrypted_token
    }

    return response, 200


class ZoomClient:
    """Client for Zoom API authentication and operations"""

    def __init__(self):
        """Initialize Zoom client with Server-to-Server OAuth"""
        self.account_id = os.environ.get('ZOOM_ACCOUNT_ID')
        self.client_id = os.environ.get('ZOOM_CLIENT_ID')
        self.client_secret = os.environ.get('ZOOM_CLIENT_SECRET')
        self.base_url = "https://api.zoom.us/v2"
        self.access_token = None

        if not all([self.account_id, self.client_id, self.client_secret]):
            raise ValueError("Missing Zoom credentials in environment variables")

    def get_access_token(self) -> str:
        """
        Generate OAuth access token (expires after 1 hour)

        Returns:
            Access token string
        """
        print("🔑 Requesting Zoom access token...")

        url = "https://zoom.us/oauth/token"
        auth = requests.auth.HTTPBasicAuth(self.client_id, self.client_secret)
        data = {
            "grant_type": "account_credentials",
            "account_id": self.account_id
        }

        response = requests.post(url, auth=auth, data=data, timeout=30)
        response.raise_for_status()

        token_data = response.json()
        self.access_token = token_data["access_token"]

        print("✅ Successfully obtained Zoom access token")
        return self.access_token

    def list_all_recordings(self, user_id: str = "me", page_size: int = 30) -> dict:
        """
        List all cloud recordings for a user

        Args:
            user_id: User ID or 'me' for account-level recordings
            page_size: Number of recordings per page (max 300)

        Returns:
            Dictionary with recordings list
        """
        if not self.access_token:
            self.get_access_token()

        print(f"📋 Fetching all recordings for user: {user_id}")

        url = f"{self.base_url}/users/{user_id}/recordings"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        params = {"page_size": page_size}

        response = requests.get(url, headers=headers, params=params, timeout=30)

        if response.status_code != 200:
            print(f"❌ API Error Response ({response.status_code}):")
            try:
                error_data = response.json()
                print(f"   Error code: {error_data.get('code', 'N/A')}")
                print(f"   Error message: {error_data.get('message', 'N/A')}")
            except:
                print(f"   Response text: {response.text[:500]}")

        response.raise_for_status()

        data = response.json()
        print(f"✅ Found {len(data.get('meetings', []))} recordings")
        return data

    def get_meeting_recordings(self, meeting_uuid: str) -> dict:
        """
        Fetch meeting recording details from Zoom API

        Args:
            meeting_uuid: Meeting UUID from webhook

        Returns:
            Recording data with download URLs that work with OAuth Bearer token
        """
        if not self.access_token:
            self.get_access_token()

        print(f"📋 Fetching recording details from API for meeting: {meeting_uuid}")

        # URL encode the meeting UUID
        # Zoom requires double-encoding ONLY for UUIDs with '/' or '//' in them
        # For UUIDs ending in '==', single encoding is sufficient
        import urllib.parse
        if '/' in meeting_uuid:
            # Double-encode for meeting IDs with forward slashes
            encoded_uuid = urllib.parse.quote(urllib.parse.quote(meeting_uuid, safe=''), safe='')
        else:
            # Single encode for standard base64 UUIDs (with = padding)
            encoded_uuid = urllib.parse.quote(meeting_uuid, safe='')

        url = f"{self.base_url}/meetings/{encoded_uuid}/recordings"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        print("✅ Retrieved recording details from API")
        return response.json()

    def download_recording(self, download_url: str, output_path: str) -> str:
        """
        Download recording file from Zoom to local path

        Args:
            download_url: URL to download recording from
            output_path: Local file path to save recording

        Returns:
            Path to downloaded file
        """
        if not self.access_token:
            self.get_access_token()

        print(f"⬇️ Downloading recording from Zoom...")

        headers = {"Authorization": f"Bearer {self.access_token}"}

        # Stream download to handle large files
        response = requests.get(download_url, headers=headers, stream=True, timeout=300)
        response.raise_for_status()

        # Get file size if available
        total_size = int(response.headers.get('content-length', 0))
        total_size_mb = total_size / (1024 * 1024) if total_size > 0 else 0

        print(f"📦 File size: {total_size_mb:.1f} MB")

        # Write to file in chunks
        downloaded = 0
        chunk_size = 8192

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Log progress for large files
                    if total_size > 0 and downloaded % (1024 * 1024 * 10) == 0:  # Every 10MB
                        progress = (downloaded / total_size) * 100
                        print(f"📊 Download progress: {progress:.1f}%")

        downloaded_mb = downloaded / (1024 * 1024)
        print(f"✅ Downloaded {downloaded_mb:.1f} MB to {output_path}")

        return output_path


class ZoomRecordingProcessor:
    """Processes Zoom recording webhooks and uploads to Dropbox"""

    def __init__(self):
        """Initialize processor with Zoom and Dropbox clients"""
        self.zoom_client = ZoomClient()

        # Initialize Dropbox client with refresh token capability
        refresh_token = os.environ.get('DROPBOX_REFRESH_TOKEN', '').strip()
        app_key = os.environ.get('DROPBOX_APP_KEY', '').strip()
        app_secret = os.environ.get('DROPBOX_APP_SECRET', '').strip()

        if refresh_token and app_key and app_secret:
            print("🔄 Initializing Dropbox client with refresh token...")
            self.dbx = dropbox.Dropbox(
                app_key=app_key,
                app_secret=app_secret,
                oauth2_refresh_token=refresh_token
            )
        else:
            print("🔑 Falling back to Dropbox access token...")
            access_token = os.environ.get('DROPBOX_ACCESS_TOKEN', '').strip()
            if not access_token:
                raise ValueError("DROPBOX_ACCESS_TOKEN or refresh token setup required")
            self.dbx = dropbox.Dropbox(access_token)

        # Dropbox folder path
        self.dropbox_folder = os.environ.get('DROPBOX_RAW_FOLDER', '/transcripts/raw')

        # Cloud Storage for tracking processed recordings
        self.storage_client = storage.Client()
        project_id = os.environ.get('PROJECT_ID')
        self.tracking_bucket_name = f"{project_id}-zoom-recordings"
        self.tracking_blob_name = "processed_recordings.json"

    def _load_processed_recordings(self) -> Dict[str, Any]:
        """Load tracking data for processed recordings from Cloud Storage"""
        try:
            bucket = self.storage_client.bucket(self.tracking_bucket_name)
            blob = bucket.blob(self.tracking_blob_name)

            if blob.exists():
                data = blob.download_as_text()
                processed = json.loads(data)
                print(f"📥 Loaded tracking data: {len(processed)} processed recordings")
                return processed
            else:
                print("📝 No existing tracking data found")
                return {}
        except Exception as e:
            print(f"⚠️ Error loading tracking data: {str(e)}")
            return {}

    def _save_processed_recordings(self, processed: Dict[str, Any]):
        """Save tracking data for processed recordings to Cloud Storage"""
        try:
            bucket = self.storage_client.bucket(self.tracking_bucket_name)

            # Ensure bucket exists
            try:
                bucket.reload()
            except:
                print(f"📦 Creating tracking bucket: {self.tracking_bucket_name}")
                bucket = self.storage_client.create_bucket(
                    self.tracking_bucket_name,
                    location=os.environ.get('GCP_REGION', 'us-east1')
                )

            blob = bucket.blob(self.tracking_blob_name)
            data = json.dumps(processed, indent=2)
            blob.upload_from_string(data, content_type='application/json')

            print(f"💾 Saved tracking data: {len(processed)} processed recordings")
        except Exception as e:
            print(f"❌ Error saving tracking data: {str(e)}")

    def process_recording_completed(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process recording.completed webhook event

        Args:
            webhook_data: Zoom webhook payload

        Returns:
            Dictionary with processing result
        """
        try:
            payload = webhook_data.get('payload', {})
            recording_object = payload.get('object', {})

            meeting_uuid = recording_object.get('uuid')
            meeting_topic = recording_object.get('topic', 'Untitled Meeting')

            print(f"🎥 Processing recording: {meeting_topic}")
            print(f"📋 Meeting UUID: {meeting_uuid}")

            # Check if already processed
            processed_recordings = self._load_processed_recordings()
            if meeting_uuid in processed_recordings:
                print(f"⏭️ Recording already processed, skipping")
                return {'success': True, 'skipped': True, 'reason': 'already_processed'}

            # Fetch recording details from Zoom API (this gives us OAuth-compatible download URLs)
            # Unlike webhook download URLs which require short-lived download_token,
            # API download URLs work with our OAuth Bearer token
            print("🔄 Fetching recording details from Zoom API...")
            api_recording_data = self.zoom_client.get_meeting_recordings(meeting_uuid)

            # Extract recording files from API response
            recording_files = api_recording_data.get('recording_files', [])
            print(f"📁 Found {len(recording_files)} recording files from API")

            # Filter for MP4 video files only
            mp4_files = [
                f for f in recording_files
                if f.get('file_type', '').upper() == 'MP4'
            ]

            if not mp4_files:
                print("⚠️ No MP4 files found in recording")
                return {'success': False, 'error': 'No MP4 files found'}

            print(f"🎬 Found {len(mp4_files)} MP4 file(s) to process")

            # Process each MP4 file
            results = []
            for file_info in mp4_files:
                result = self._process_recording_file(
                    file_info,
                    meeting_topic,
                    meeting_uuid
                )
                results.append(result)

            # Mark as processed
            processed_recordings[meeting_uuid] = {
                'meeting_topic': meeting_topic,
                'processed_at': datetime.utcnow().isoformat(),
                'files_processed': len(results)
            }
            self._save_processed_recordings(processed_recordings)

            successful = sum(1 for r in results if r.get('success'))
            print(f"✅ Processed {successful}/{len(results)} files successfully")

            return {
                'success': successful > 0,
                'meeting_uuid': meeting_uuid,
                'meeting_topic': meeting_topic,
                'files_processed': successful,
                'total_files': len(results)
            }

        except Exception as e:
            print(f"❌ Error processing recording: {str(e)}")
            import traceback
            print(f"🔍 Traceback: {traceback.format_exc()}")
            return {'success': False, 'error': str(e)}

    def _process_recording_file(
        self,
        file_info: Dict[str, Any],
        meeting_topic: str,
        meeting_uuid: str
    ) -> Dict[str, Any]:
        """
        Download recording file from Zoom and upload to Dropbox

        Args:
            file_info: Recording file metadata from Zoom
            meeting_topic: Meeting topic/title
            meeting_uuid: Meeting unique identifier

        Returns:
            Dictionary with processing result
        """
        try:
            download_url = file_info.get('download_url')
            file_type = file_info.get('file_type')
            recording_type = file_info.get('recording_type', 'unknown')
            recording_start = file_info.get('recording_start', '')
            file_size = file_info.get('file_size', 0)
            file_size_mb = file_size / (1024 * 1024) if file_size > 0 else 0

            print(f"📹 Processing: {recording_type}.{file_type.lower()} ({file_size_mb:.1f} MB)")

            # Create filename
            # Format: YYYYMMDD-HHMMSS-meeting_topic-recording_type.mp4
            timestamp = recording_start.replace(':', '-').replace('T', '-').split('Z')[0]
            safe_topic = meeting_topic.replace('/', '_').replace(' ', '_')[:50]  # Limit length
            filename = f"{timestamp}-{safe_topic}-{recording_type}.mp4"

            print(f"📝 Target filename: {filename}")

            # Download to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                tmp_path = tmp_file.name

            try:
                # Download from Zoom
                self.zoom_client.download_recording(download_url, tmp_path)

                # Upload to Dropbox
                dropbox_path = f"{self.dropbox_folder}/{filename}"

                print(f"⬆️ Uploading to Dropbox: {dropbox_path}")

                # Use chunked upload for large files (> 10MB)
                file_size_bytes = os.path.getsize(tmp_path)

                if file_size_bytes > 10 * 1024 * 1024:  # > 10MB
                    self._upload_large_file(tmp_path, dropbox_path)
                else:
                    with open(tmp_path, 'rb') as f:
                        self.dbx.files_upload(
                            f.read(),
                            dropbox_path,
                            mode=dropbox.files.WriteMode.overwrite
                        )

                print(f"✅ Successfully uploaded to Dropbox: {dropbox_path}")

                return {
                    'success': True,
                    'file_name': filename,
                    'dropbox_path': dropbox_path,
                    'file_size_mb': file_size_mb
                }

            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        except Exception as e:
            print(f"❌ Error processing file: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _upload_large_file(self, local_path: str, dropbox_path: str):
        """
        Upload large file to Dropbox using chunked upload

        Args:
            local_path: Path to local file
            dropbox_path: Target path in Dropbox
        """
        chunk_size = 4 * 1024 * 1024  # 4MB chunks
        file_size = os.path.getsize(local_path)

        print(f"📤 Using chunked upload for large file ({file_size / (1024*1024):.1f} MB)")

        with open(local_path, 'rb') as f:
            # Start upload session
            upload_session_start_result = self.dbx.files_upload_session_start(
                f.read(chunk_size)
            )
            cursor = dropbox.files.UploadSessionCursor(
                session_id=upload_session_start_result.session_id,
                offset=f.tell()
            )
            commit = dropbox.files.CommitInfo(
                path=dropbox_path,
                mode=dropbox.files.WriteMode.overwrite
            )

            # Upload chunks
            while f.tell() < file_size:
                remaining = file_size - f.tell()
                chunk = f.read(min(chunk_size, remaining))

                if remaining <= chunk_size:
                    # Last chunk - finish session
                    self.dbx.files_upload_session_finish(
                        chunk,
                        cursor,
                        commit
                    )
                else:
                    # More chunks to come
                    self.dbx.files_upload_session_append_v2(chunk, cursor)
                    cursor.offset = f.tell()

                # Log progress
                progress = (f.tell() / file_size) * 100
                print(f"📊 Upload progress: {progress:.1f}%")


if __name__ == "__main__":
    # For local testing with functions-framework
    pass
