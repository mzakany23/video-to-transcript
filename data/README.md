# Data Directory

This directory contains transient storage used by the transcription services during development and testing.

## Structure

- `dev_jobs/` - Development job artifacts and logs
- `dev_storage/` - Development file storage
- `fastapi_jobs/` - FastAPI service job data
- `fastapi_storage/` - FastAPI service file storage
- `webhook_jobs/` - Webhook-triggered job data
- `webhook_storage/` - Webhook storage including cursors and processed job tracking

## Usage

These directories are automatically created and managed by the services. They contain:
- Temporary files during processing
- Job metadata and status
- Cursor tracking for webhooks
- Development artifacts

## Cleanup

This data can be safely removed during development:

```bash
# Clean all transient data
rm -rf data/*/

# Or clean specific service data
rm -rf data/webhook_storage/*
rm -rf data/dev_jobs/*
```

## Production

In production environments, these would typically be replaced with:
- Cloud storage (GCS, S3, Azure Blob)
- Persistent databases
- External job queues