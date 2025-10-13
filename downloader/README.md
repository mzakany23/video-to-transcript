# Zoom Downloader Service

Cloud Function that receives Zoom webhook notifications, downloads MP4 recordings from Zoom cloud storage, and uploads them to Dropbox to trigger the transcription pipeline.

## Overview

This service bridges Zoom cloud recordings with the existing Dropbox-based transcription pipeline:

1. Zoom meeting ends and recording processing completes (~5-10 minutes)
2. Zoom fires `recording.completed` webhook to this service
3. Service downloads MP4 files from Zoom using OAuth
4. Service uploads files to Dropbox `/transcripts/raw` folder
5. Existing Dropbox webhook triggers transcription worker

## Architecture

- **Type**: Google Cloud Function (Gen2)
- **Runtime**: Python 3.11
- **Trigger**: HTTP webhook from Zoom
- **Security**: HMAC-SHA256 signature verification
- **Scaling**: Scales to zero (no cost when idle)

## Features

- **Zoom Webhook Handler**: Receives and validates webhook events
- **Signature Verification**: Cryptographic verification of Zoom requests
- **OAuth Authentication**: Server-to-Server OAuth for Zoom API
- **Streaming Downloads**: Efficiently handles large video files
- **Chunked Uploads**: Uploads large files to Dropbox in chunks
- **Duplicate Prevention**: Tracks processed recordings to avoid reprocessing
- **Error Tracking**: Sentry integration for monitoring
- **Progress Logging**: Detailed logging for troubleshooting

## Prerequisites

### Zoom Setup
1. Zoom Pro account or higher
2. Zoom Server-to-Server OAuth App created in [Zoom Marketplace](https://marketplace.zoom.us)
3. Required OAuth scopes:
   - `recording:read:admin` - View and download recordings
   - `user:read:admin` - Read user info
4. Webhook event subscriptions configured:
   - `recording.completed` - Triggered when recording finishes processing

### GCP Resources
- Cloud Functions Gen2 enabled
- Secret Manager for credentials
- Cloud Storage bucket for tracking processed recordings
- Service account with required permissions

### Environment Variables

Required:
- `ZOOM_ACCOUNT_ID` - Zoom account ID from OAuth app
- `ZOOM_CLIENT_ID` - Zoom client ID from OAuth app
- `ZOOM_CLIENT_SECRET` - Zoom client secret from OAuth app
- `ZOOM_WEBHOOK_SECRET` - Zoom webhook secret token
- `DROPBOX_ACCESS_TOKEN` or refresh token setup
- `DROPBOX_APP_KEY` - For OAuth refresh token flow
- `DROPBOX_APP_SECRET` - For OAuth refresh token flow
- `DROPBOX_REFRESH_TOKEN` - Long-lived refresh token
- `PROJECT_ID` - GCP project ID
- `DROPBOX_RAW_FOLDER` - Target folder in Dropbox (e.g., `/transcripts/raw`)

Optional:
- `SENTRY_DSN` - Sentry error tracking DSN
- `SENTRY_ENVIRONMENT` - Environment name (default: production)
- `VERSION` - Service version for tracking
- `GCP_REGION` - GCP region (default: us-east1)

## Installation

### Local Development

```bash
# Install dependencies
cd downloader
pip install -r requirements.txt

# Set environment variables
export ZOOM_ACCOUNT_ID="your_account_id"
export ZOOM_CLIENT_ID="your_client_id"
export ZOOM_CLIENT_SECRET="your_client_secret"
export ZOOM_WEBHOOK_SECRET="your_webhook_secret"
export DROPBOX_REFRESH_TOKEN="your_refresh_token"
export DROPBOX_APP_KEY="your_app_key"
export DROPBOX_APP_SECRET="your_app_secret"
export PROJECT_ID="your_project_id"
export DROPBOX_RAW_FOLDER="/transcripts/raw"

# Run locally with functions-framework
functions-framework --target=zoom_downloader_handler --debug
```

### Deploy with Terraform

The service is deployed automatically via Terraform. See [terraform/main.tf](../terraform/main.tf) for configuration.

```bash
cd terraform
terraform plan
terraform apply
```

## Webhook Events

### Endpoint Validation (`endpoint.url_validation`)

Zoom sends this event when you first configure the webhook endpoint:

```json
{
  "event": "endpoint.url_validation",
  "payload": {
    "plainToken": "random_string"
  }
}
```

Response:
```json
{
  "plainToken": "random_string",
  "encryptedToken": "hmac_sha256_hash"
}
```

### Recording Completed (`recording.completed`)

Zoom sends this event when a cloud recording finishes processing:

```json
{
  "event": "recording.completed",
  "payload": {
    "object": {
      "uuid": "meeting_uuid",
      "topic": "Meeting Title",
      "recording_files": [
        {
          "id": "file_id",
          "recording_start": "2024-01-15T10:30:00Z",
          "recording_end": "2024-01-15T11:30:00Z",
          "file_type": "MP4",
          "file_size": 123456789,
          "recording_type": "shared_screen_with_speaker_view",
          "download_url": "https://zoom.us/rec/download/..."
        }
      ]
    }
  }
}
```

## File Naming Convention

Downloaded files are named following this pattern:
```
YYYYMMDD-HHMMSS-meeting_topic-recording_type.mp4
```

Example:
```
20240115-103000-Weekly_Team_Standup-shared_screen_with_speaker_view.mp4
```

## Security

### Webhook Signature Verification

All incoming Zoom webhooks are verified using HMAC-SHA256:

1. Zoom sends signature in `x-zm-signature` header
2. Zoom sends timestamp in `x-zm-request-timestamp` header
3. Service reconstructs signature using webhook secret
4. Signatures must match or request is rejected

Format:
```
signature = "v0=" + HMAC-SHA256("v0:{timestamp}:{body}", webhook_secret)
```

### Credentials

All sensitive credentials are stored in GCP Secret Manager:
- Zoom OAuth credentials
- Dropbox OAuth credentials
- Webhook secrets
- API keys

Never commit credentials to version control.

## State Tracking

The service tracks processed recordings in a Cloud Storage bucket to prevent duplicate processing:

- **Bucket**: `{PROJECT_ID}-zoom-recordings`
- **File**: `processed_recordings.json`
- **Format**: JSON object mapping meeting UUIDs to processing metadata

Example:
```json
{
  "meeting_uuid_123": {
    "meeting_topic": "Weekly Team Standup",
    "processed_at": "2024-01-15T10:35:00Z",
    "files_processed": 1
  }
}
```

## Error Handling

### Zoom API Errors
- **401 Unauthorized**: OAuth token expired - automatically refreshes
- **404 Not Found**: Recording no longer available
- **429 Rate Limited**: Implements exponential backoff

### Dropbox Errors
- **401 Unauthorized**: Refresh token invalid - check credentials
- **507 Insufficient Storage**: Dropbox storage full
- **Network errors**: Retries with exponential backoff

### Storage Errors
- **Bucket not found**: Automatically creates bucket on first use
- **Permission denied**: Check service account permissions

## Monitoring

### Logs

View logs in Cloud Console:
```bash
gcloud functions logs read transcription-downloader --region=us-east1
```

### Metrics

Monitor in Cloud Console:
- Invocations per minute
- Error rate
- Execution time
- Memory usage

### Sentry

If configured, errors are automatically reported to Sentry with:
- Stack traces
- Request context
- Environment information
- User-defined tags

## Testing

### Unit Tests

```bash
cd downloader
python -m pytest tests/ -v
```

### Integration Testing

1. Record a test Zoom meeting
2. Wait for recording to process (5-10 minutes)
3. Check function logs for webhook receipt
4. Verify file appears in Dropbox
5. Verify transcription pipeline triggers

### Manual Testing with cURL

Test endpoint validation:
```bash
curl -X POST https://your-function-url.run.app \
  -H "Content-Type: application/json" \
  -H "x-zm-signature: v0=test" \
  -H "x-zm-request-timestamp: 1234567890" \
  -d '{"event":"endpoint.url_validation","payload":{"plainToken":"test"}}'
```

## Troubleshooting

### Webhook Not Receiving Events

1. Check Zoom webhook configuration is active
2. Verify webhook URL is correct
3. Check function is deployed and running
4. Verify Cloud Function has public access

### Signature Verification Failing

1. Check `ZOOM_WEBHOOK_SECRET` is correct
2. Verify timestamp is within acceptable range
3. Check request body is not modified

### Downloads Failing

1. Verify Zoom OAuth credentials are correct
2. Check OAuth scopes include `recording:read:admin`
3. Verify recording still exists in Zoom cloud
4. Check Zoom API rate limits

### Uploads to Dropbox Failing

1. Verify Dropbox credentials are correct
2. Check Dropbox folder path exists
3. Verify Dropbox has sufficient storage
4. Check network connectivity

### Already Processed Error

If recordings are incorrectly marked as processed:
1. Delete entry from `processed_recordings.json` in Cloud Storage
2. Re-trigger webhook (or wait for Zoom to retry)

## Cost Optimization

- **Cloud Function**: Scales to zero = $0 when idle
- **Invocations**: Only charged when webhook fires
- **Network**: Minimal egress costs for downloads/uploads
- **Storage**: Minimal costs for tracking data

Typical monthly cost: **< $1** for moderate usage

## Limitations

- OAuth tokens expire after 1 hour (automatically refreshed)
- Maximum file size: Limited by Cloud Function memory (default 256MB)
- Processing time: 60 second timeout (configurable)
- Zoom may resend webhooks if no response within 3 seconds

## Future Enhancements

- [ ] Support multiple Zoom accounts
- [ ] Add webhook for `recording.transcript_completed`
- [ ] Archive original recordings after processing
- [ ] Add metrics dashboard
- [ ] Support audio-only recordings (M4A)
- [ ] Implement webhook retry queue for failures
- [ ] Add admin API for reprocessing recordings

## References

- [Zoom Webhook Documentation](https://developers.zoom.us/docs/api/webhooks/)
- [Zoom Server-to-Server OAuth](https://developers.zoom.us/docs/internal-apps/create/)
- [Cloud Functions Documentation](https://cloud.google.com/functions/docs)
- [Dropbox API Documentation](https://www.dropbox.com/developers/documentation)

## Support

For issues or questions:
1. Check Cloud Function logs
2. Review Sentry error reports (if configured)
3. Check Zoom webhook event history
4. Consult main project documentation

## License

See main project [LICENSE](../LICENSE) file.
