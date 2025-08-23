# Transcripts

Serverless audio/video transcription pipeline using OpenAI Whisper API. Upload files to Dropbox, get transcripts automatically.

## Features
- **Webhook-based Processing**: Automatic transcription when files are uploaded
- **Large File Support**: Handles files >25MB with automatic compression
- **Multiple Formats**: Audio (mp3, wav, m4a) and video (mp4, mov, avi, webm)
- **Serverless Architecture**: Scales automatically with Google Cloud Run
- **Structured Output**: Both JSON (with timestamps) and plain text formats
- **Email Notifications**: Get email alerts when transcription jobs complete

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

# CLI tools
cd cli/
uv sync
uv run backfill.py
```

## How It Works

1. ** Upload**: Drop audio/video files into Dropbox folder
2. ** Webhook**: Dropbox notifies our webhook service instantly
3. ** Processing**: Cloud Run worker downloads, compresses if needed, and transcribes
4. ** Results**: JSON (with timestamps) and TXT files uploaded back to Dropbox
5. ** Done**: Transcripts appear in processed folder automatically

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
├── cli/                         # CLI tools
│   ├── pyproject.toml          # CLI dependencies
│   └── backfill.py             # Process existing files
├── templates/                   # Shared output templates
├── terraform/                   # Infrastructure as Code
└── tests/                       # Integration tests
```

## Deployment

### Deploy Worker Changes

1. **Build and push Docker image**:
   ```bash
   cd worker
   gcloud builds submit --tag gcr.io/YOUR_PROJECT/transcription-worker:latest
   ```

2. **Update environment variables** (if needed):
   ```bash
   gcloud run jobs update transcription-worker \
     --set-env-vars ENABLE_SMS_NOTIFICATIONS=true,NOTIFICATION_PHONE_NUMBER=+1XXXXXXXXXX \
     --region us-east1 \
     --project YOUR_PROJECT
   ```

3. **Test**: Drop a file in your Dropbox raw folder

### Deploy Webhook Changes

```bash
cd terraform
gcloud functions deploy webhook-handler \
  --source ../webhook \
  --entry-point webhook_handler \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --region us-east1
```

### Environment Variables

**Worker Job**:
- `ENABLE_SMS_NOTIFICATIONS`: Enable SMS alerts (true/false)
- `NOTIFICATION_PHONE_NUMBER`: Phone for notifications
- `TWILIO_SECRET_NAME`: Twilio credentials secret name
- `MAX_FILES`: Max files per job run

**Webhook**:
- `DROPBOX_APP_SECRET`: For webhook verification
- `WORKER_JOB_NAME`: Cloud Run job to trigger

### Monitoring

```bash
# View job runs
gcloud run jobs executions list --job transcription-worker --region us-east1

# View logs
gcloud logging read "resource.type=cloud_run_job" --limit 50
```

## Troubleshooting

### "OpenAI API key not found"
```bash
export OPENAI_API_KEY="your_key_here"
```

### "ffmpeg not found"
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```