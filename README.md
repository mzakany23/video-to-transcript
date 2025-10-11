# Transcripts

Serverless audio/video transcription pipeline using OpenAI Whisper API. Upload files to Dropbox, get transcripts automatically.

## Features
- **Webhook-based Processing**: Automatic transcription when files are uploaded
- **Large File Support**: Handles files of ANY size with automatic chunking (splits files >20MB)
- **Smart Compression**: Targets 19MB for optimal API compatibility
- **Multiple Formats**: Audio (mp3, wav, m4a) and video (mp4, mov, avi, webm)
- **Serverless Architecture**: Scales automatically with Google Cloud Run
- **Structured Output**: Both JSON (with timestamps) and plain text formats
- **Email Notifications**: Job start, completion, and failure alerts (multiple recipients)
- **Error Tracking**: Optional Sentry integration for production monitoring

## Quick Start

1. **Deploy infrastructure**:
   ```bash
   cd terraform/
   terraform init
   terraform apply
   ```

2. **Configure environment** (set in Cloud Run):
   ```bash
   export OPENAI_API_KEY="your_api_key_here"
   export DROPBOX_APP_KEY="your_app_key"
   export DROPBOX_APP_SECRET="your_app_secret"
   ```

3. **Upload files to Dropbox** → Transcripts appear automatically!

## Development

Each service is independently managed:

```bash
# Webhook service
cd webhook/
uv sync
uv run main.py

# Worker service
cd worker/
uv sync
uv run main.py


```

## How It Works

1. **Upload**: Drop audio/video files into Dropbox folder
2. **Webhook**: Dropbox notifies our webhook service instantly
3. **Processing**: Cloud Run worker downloads, compresses if needed, and transcribes
4. **Results**: JSON (with timestamps) and TXT files uploaded back to Dropbox
5. **Done**: Transcripts appear in processed folder automatically

## Architecture

```
Dropbox/
├── raw/           # Upload files here
└── processed/     # Transcripts appear here
```

**Services:**
- **Webhook Service**: Receives Dropbox notifications → triggers jobs
- **Worker Service**: Downloads files → transcribes → uploads results
- **Shared Library**: Common code used by both services

## Output Files

For each input file `meeting.mp4`, you get:
- `meeting.json` - Full transcript data with timestamps and metadata
- `meeting.txt` - Clean text transcript

## Supported File Formats

- **Audio**: `.mp3`, `.wav`, `.m4a`, `.aac`, `.ogg`, `.flac`, `.mpga`, `.oga`
- **Video**: `.mp4`, `.mov`, `.avi`, `.webm`, `.mpeg`

## Project Structure

**Monorepo** - Each service is independently deployable:

```
transcripts/
├── webhook/                     # Webhook service
│   ├── pyproject.toml          # Lightweight dependencies
│   └── main.py                 # Receives notifications
├── worker/                      # Worker service
│   ├── pyproject.toml          # Full transcription dependencies
│   ├── src/transcripts/        # Core transcription logic
│   ├── main.py                 # Processes files
│   └── Dockerfile              # Container image

├── terraform/                   # Infrastructure as Code
└── tests/                       # Integration tests
```

## Deployment

**Important**: All deployment is managed through Terraform. Do NOT use individual gcloud commands - they will be overwritten.

### Initial Setup (One Time)

1. **Configure Docker for Google Container Registry**:
   ```bash
   gcloud auth configure-docker
   ```

2. **Edit Terraform variables**:
   ```bash
   cd terraform
   # Edit terraform.tfvars with your credentials
   # (See terraform/README.md for details)
   ```

### Deploy Worker Changes

When you modify worker code (main.py, notifications, chunking, etc.):

1. **Build and push Docker image**:
   ```bash
   cd worker
   docker buildx build --platform linux/amd64 \
     -t gcr.io/jos-transcripts/transcription-worker:latest \
     . --push
   ```

2. **Update Cloud Run Job** (optional, only if Terraform config changed):
   ```bash
   cd ../terraform
   terraform apply
   ```

3. **Force new job execution** (to test immediately):
   ```bash
   gcloud run jobs execute transcription-worker \
     --region us-east1 \
     --project jos-transcripts
   ```

### Deploy Webhook Changes

When you modify webhook code:

1. **Apply Terraform** (auto-zips and deploys webhook):
   ```bash
   cd terraform
   terraform apply
   ```

   Terraform will:
   - Automatically zip webhook/ directory
   - Upload to GCS bucket
   - Deploy/update Cloud Function

### Deploy Everything (Full Stack)

When you change infrastructure, secrets, or environment variables:

1. **Build worker image** (if worker code changed):
   ```bash
   cd worker
   docker buildx build --platform linux/amd64 \
     -t gcr.io/jos-transcripts/transcription-worker:latest \
     . --push
   ```

2. **Apply Terraform**:
   ```bash
   cd terraform
   terraform apply
   ```

### Quick Deployment Commands

```bash
# Full deployment (from project root)
cd worker && docker buildx build --platform linux/amd64 -t gcr.io/jos-transcripts/transcription-worker:latest . --push && cd ../terraform && terraform apply

# Webhook only
cd terraform && terraform apply

# Test worker immediately
gcloud run jobs execute transcription-worker --region us-east1 --project jos-transcripts
```

### Environment Variables

**Worker Job**:
- `ENABLE_EMAIL_NOTIFICATIONS`: Enable email alerts (true/false)
- `NOTIFICATION_EMAIL`: Comma-separated list of email recipients
- `GMAIL_SECRET_NAME`: Gmail credentials secret name
- `MAX_FILES`: Max files per job run
- `SENTRY_DSN`: Sentry error tracking DSN (optional)
- `SENTRY_ENVIRONMENT`: Environment name for Sentry (optional)

**Webhook**:
- `DROPBOX_APP_SECRET`: For webhook verification
- `DROPBOX_REFRESH_TOKEN`: OAuth refresh token for Dropbox
- `DROPBOX_APP_KEY`: Dropbox app key
- `WORKER_JOB_NAME`: Cloud Run job to trigger

### Optional: Sentry Error Tracking

To enable error tracking and monitoring:

1. **Sign up for Sentry**: https://sentry.io (free tier available)

2. **Create a Python project** and copy your DSN

3. **Add to terraform/main.tf** (around line 273, in worker env vars):
   ```hcl
   env {
     name  = "SENTRY_DSN"
     value = "https://your-dsn@sentry.io/project-id"
   }

   env {
     name  = "SENTRY_ENVIRONMENT"
     value = "production"
   }
   ```

4. **Deploy**: `cd terraform && terraform apply`

Sentry will automatically capture:
- All unhandled exceptions
- Performance metrics (10% sample rate)
- Breadcrumbs for debugging
- Release tracking

### Monitoring

```bash
# View job runs
gcloud run jobs executions list --job transcription-worker --region us-east1

# View logs
gcloud logging read "resource.type=cloud_run_job" --limit 50
```

## Troubleshooting

### "OpenAI API key not found"
Check that the secret exists in Secret Manager:
```bash
gcloud secrets list --project jos-transcripts
gcloud secrets versions access latest --secret openai-api-key --project jos-transcripts
```

### "ffmpeg not found"
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

### "Error code: 413 - Maximum content size limit exceeded"
This means the file is too large for the OpenAI API (>25MB). The fixes in v1.1.0+ handle this automatically:
- Files compress to 19MB target (with safety margin)
- Files >20MB are automatically chunked into smaller pieces
- **Solution**: Deploy the latest worker image with chunking support

### "Recipient email was refused by the server"
This was a bug where multiple email recipients weren't parsed correctly.
- **Fixed in v1.1.0+**: Emails now properly split on commas
- **Solution**: Deploy the latest worker image

### Email notifications not arriving
1. **Check Gmail app password** is correct in terraform.tfvars
2. **Verify email notifications are enabled**:
   ```bash
   gcloud run jobs describe transcription-worker --region us-east1 | grep ENABLE_EMAIL
   ```
3. **Check spam folder** for first email
4. **View logs** for SMTP errors:
   ```bash
   gcloud logging read "resource.type=cloud_run_job" --limit 50 | grep "email"
   ```

### Large files failing to transcribe
For files >25MB (like 40MB+ interviews):
1. **Ensure you're running v1.1.0+** with chunking support
2. **Check logs** to see if chunking is triggered:
   ```bash
   gcloud logging read "resource.type=cloud_run_job" --limit 100 | grep "chunk"
   ```
3. You should see messages like: `📦 File is large, using chunked transcription`

### View detailed error logs
```bash
# Recent errors only
gcloud logging read "resource.type=cloud_run_job AND severity>=ERROR" --limit 50 --project jos-transcripts

# Specific execution
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=transcription-worker" --limit 200 --project jos-transcripts

# Real-time streaming
gcloud logging tail "resource.type=cloud_run_job" --project jos-transcripts
```