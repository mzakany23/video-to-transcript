# Dropbox Webhook Handler

Lightweight webhook service that receives Dropbox file change notifications and triggers transcription worker jobs. Deployed as a Google Cloud Function (Gen2).

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Dropbox app credentials (app key, app secret, refresh token)
- GCP project with Cloud Run and Cloud Functions enabled

### Setup

```bash
# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate

# Create .env file with required variables
cat > .env << EOF
DROPBOX_APP_KEY=your_app_key
DROPBOX_APP_SECRET=your_app_secret
DROPBOX_REFRESH_TOKEN=your_refresh_token
DROPBOX_RAW_FOLDER=/transcripts/raw
DROPBOX_PROCESSED_FOLDER=/transcripts/processed
WORKER_JOB_NAME=transcription-worker
PROJECT_ID=your-gcp-project-id
REGION=us-east1
EOF
```

### Run Locally

```bash
# Run with Functions Framework
functions-framework --target=webhook_handler --debug

# Test with curl (GET - verification)
curl "http://localhost:8080/?challenge=test123"

# Test with curl (POST - webhook)
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -H "X-Dropbox-Signature: test" \
  -d '{"list_folder":{"accounts":["test"]}}'
```

### Testing

```bash
# Run tests
make test

# Run with pytest directly
python -m pytest tests/ -v
```

## How It Works

1. **Dropbox Setup**: Register webhook URL with Dropbox app
2. **File Change**: User uploads file to Dropbox raw folder
3. **Notification**: Dropbox sends webhook notification to Cloud Function
4. **Verification**: Function verifies HMAC signature from Dropbox
5. **Discovery**: Lists changed files in monitored folder
6. **Filtering**: Identifies audio/video files to process
7. **Job Trigger**: Launches Cloud Run worker job with file metadata
8. **Response**: Returns 200 OK to Dropbox

## Security Features

- **HMAC Signature Verification**: Validates all webhook requests using Dropbox app secret
- **Early Request Rejection**: Invalid requests rejected before processing
- **No Authentication Required**: Public endpoint secured via HMAC (industry standard for webhooks)
- **Rate Limiting**: Dropbox implements automatic rate limiting
- **Billing Protection**: Early validation prevents unauthorized job triggers

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DROPBOX_APP_KEY` | Dropbox app key | - |
| `DROPBOX_APP_SECRET` | Dropbox app secret (for HMAC) | **Required** |
| `DROPBOX_REFRESH_TOKEN` | OAuth refresh token | - |
| `DROPBOX_RAW_FOLDER` | Folder to watch for new files | `/transcripts/raw` |
| `DROPBOX_PROCESSED_FOLDER` | Folder for output files | `/transcripts/processed` |
| `WORKER_JOB_NAME` | Cloud Run job to trigger | `transcription-worker` |
| `PROJECT_ID` | GCP project ID | - |
| `REGION` | GCP region | `us-east1` |
| `TARGET_FILE_SIZE_MB` | Target compression size | `19` |
| `SENTRY_DSN` | Sentry error tracking DSN | - |
| `SENTRY_ENVIRONMENT` | Sentry environment name | `production` |
| `VERSION` | Service version | - |

## Project Structure

```
webhook/
├── main.py              # Webhook handler (Cloud Function entry point)
├── tests/              # Test suite
│   └── test_webhook.py
├── Dockerfile          # Container definition (optional)
├── Makefile           # Test commands
└── CHANGELOG.md       # Version history
```

## Supported File Formats

The webhook triggers jobs for these file extensions:
- **Audio**: `.mp3`, `.wav`, `.m4a`, `.aac`, `.ogg`, `.flac`, `.mpga`, `.oga`
- **Video**: `.mp4`, `.mov`, `.avi`, `.webm`, `.mpeg`

## Deployment

This service is deployed as a Google Cloud Function (Gen2). See the main [README](../README.md) for deployment instructions.

**Quick deployment:**
```bash
cd ../terraform/
terraform apply
```

Terraform automatically:
- Zips the webhook directory
- Uploads to GCS bucket
- Deploys/updates Cloud Function
- Configures environment variables
- Sets up IAM permissions

## Dropbox Webhook Setup

### 1. Register Webhook URL

In your Dropbox app console:
1. Go to Settings → Webhooks
2. Add your Cloud Function URL:
   ```
   https://REGION-PROJECT_ID.cloudfunctions.net/dropbox-webhook
   ```
3. Dropbox will send a verification request (GET with `challenge` parameter)
4. Function responds with challenge to complete registration

### 2. Configure App Permissions

Required Dropbox permissions:
- `files.metadata.read` - List files and folders
- `files.content.read` - Read file contents
- `files.content.write` - Upload transcripts

### 3. Generate Refresh Token

```bash
# Use Dropbox OAuth flow to get refresh token
# See: https://www.dropbox.com/developers/documentation/http/documentation#authorization
```

## Monitoring

### View Logs

```bash
# Recent logs
gcloud functions logs read dropbox-webhook --region us-east1 --limit 50

# Real-time streaming
gcloud functions logs tail dropbox-webhook --region us-east1

# Errors only
gcloud functions logs read dropbox-webhook --region us-east1 \
  --filter "severity>=ERROR" --limit 50
```

### Key Log Messages

- `✅ Dropbox webhook verification` - Initial setup successful
- `📧 Dropbox notification: N account(s)` - Webhook received
- `📁 Found N changed files` - Files detected
- `🎬 Processing file: filename.mp4` - File being processed
- `🚀 Triggered job for: filename.mp4` - Worker job launched
- `⚠️ Invalid Dropbox signature` - Security rejection

## Troubleshooting

### Webhook verification failing

**Symptom**: Dropbox can't verify webhook URL

**Solutions**:
- Check Cloud Function is deployed: `gcloud functions list --region us-east1`
- Verify function allows unauthenticated access
- Test GET request manually:
  ```bash
  curl "https://REGION-PROJECT_ID.cloudfunctions.net/dropbox-webhook?challenge=test"
  ```

### "Invalid Dropbox signature" errors

**Symptom**: All webhook requests rejected with 401

**Solutions**:
- Verify `DROPBOX_APP_SECRET` matches Dropbox app console
- Check secret is properly configured in Cloud Function
- Ensure secret has no extra whitespace or quotes

### Worker jobs not triggering

**Symptom**: Webhook receives notifications but worker doesn't run

**Solutions**:
- Check worker job exists: `gcloud run jobs list --region us-east1`
- Verify `WORKER_JOB_NAME` environment variable
- Check IAM permissions for job triggering
- View logs for job trigger errors

### Files not being processed

**Symptom**: Files uploaded but no transcripts generated

**Solutions**:
- Verify files are in correct folder (`DROPBOX_RAW_FOLDER`)
- Check file extensions are supported
- Ensure files are fully uploaded (not partial)
- Check worker logs for processing errors

### High costs / billing spikes

**Symptom**: Unexpected Cloud Function invocations

**Solutions**:
- HMAC signature verification prevents unauthorized requests
- Check logs for rejected requests
- Verify Dropbox app credentials are not leaked
- Contact Dropbox support if webhook flooding occurs

## Cost Estimates

**Cloud Function invocations**:
- Free tier: 2M invocations/month
- After free tier: $0.40 per million
- Typical usage: ~1 invocation per file upload
- Monthly cost for 100 files: **FREE**

**Outbound data**:
- Minimal (only API calls to trigger jobs)
- Typically < $0.01/month

## Local Development

### Using Functions Framework

```bash
# Install Functions Framework
pip install functions-framework

# Run locally
functions-framework --target=webhook_handler --debug --port=8080

# Test verification (GET)
curl "http://localhost:8080/?challenge=test123"
# Should return: test123

# Test webhook (POST) - will fail HMAC check locally
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{"list_folder":{"accounts":["test"]}}'
```

### Testing HMAC Signatures

For local testing with valid signatures:

```python
import hmac
import hashlib
import json

app_secret = "your_app_secret"
body = json.dumps({"list_folder": {"accounts": ["test"]}})
signature = hmac.new(
    app_secret.encode('utf-8'),
    body.encode('utf-8'),
    hashlib.sha256
).hexdigest()

print(f"X-Dropbox-Signature: {signature}")
```

## Contributing

See the main [CONTRIBUTING.md](../CONTRIBUTING.md) for development guidelines.

## Version History

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

**Current version:** v1.2.2

## License

MIT License - see [LICENSE](../LICENSE) for details.
