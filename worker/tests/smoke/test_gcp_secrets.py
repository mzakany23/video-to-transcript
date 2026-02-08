"""
Smoke tests for GCP Secret Manager.
Validates that deployed secrets are accessible and have expected format.
Requires gcloud auth — skips gracefully if not available.
"""

import subprocess
import pytest


def gcloud_available():
    """Check if gcloud CLI is authenticated and accessible."""
    try:
        result = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


SKIP_NO_GCLOUD = pytest.mark.skipif(
    not gcloud_available(),
    reason="gcloud auth required",
)

PROJECT_ID = "jos-transcripts"


def read_secret(secret_name: str) -> str:
    """Read latest version of a secret from GCP Secret Manager."""
    result = subprocess.run(
        [
            "gcloud", "secrets", "versions", "access", "latest",
            f"--secret={secret_name}",
            f"--project={PROJECT_ID}",
        ],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to read secret {secret_name}: {result.stderr}")
    return result.stdout.strip()


@pytest.mark.smoke
@SKIP_NO_GCLOUD
def test_openai_secret_in_gcp():
    """Verify openai-api-key secret is accessible and has expected prefix."""
    value = read_secret("openai-api-key")
    assert value.startswith("sk-proj-"), (
        f"OpenAI key has unexpected prefix: {value[:10]}..."
    )


@pytest.mark.smoke
@SKIP_NO_GCLOUD
def test_anthropic_secret_in_gcp():
    """Verify anthropic-api-key secret is accessible and has expected prefix."""
    value = read_secret("anthropic-api-key")
    assert value.startswith("sk-ant-"), (
        f"Anthropic key has unexpected prefix: {value[:10]}..."
    )
