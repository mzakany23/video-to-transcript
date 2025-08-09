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

```bash
# Set up development environment
make setup

# Run tests
make test

# Build containers
make build

# Deploy to GCP (set PROJECT_ID first)
export PROJECT_ID=your-project-id
make deploy-gcp
```

**Traditional deployment:**
1. Deploy infrastructure: `cd terraform/ && terraform apply`
2. Configure environment variables in Cloud Run
3. Upload files to Dropbox → Transcripts appear automatically!

## Development

```bash
# Set up environment
make setup
source .venv/bin/activate

# Run tests
make test

# Format code
make format

# Run linting  
make lint

# Local testing
make run-worker    # Test worker locally
make run-webhook   # Test webhook locally
```

**Legacy service management** (still supported):
```bash
# Individual services
cd webhook/ && uv sync && uv run main.py
cd worker/ && uv sync && uv run main.py
```

## How It Works

1. **📤 Upload**: Drop audio/video files into Dropbox folder
2. **🔔 Webhook**: Dropbox notifies our webhook service instantly  
3. **⚡ Processing**: Cloud Run worker downloads, compresses if needed, and transcribes
4. **📥 Results**: JSON (with timestamps) and TXT files uploaded back to Dropbox
5. **✅ Done**: Transcripts appear in processed folder automatically

## Architecture

```
📁 Dropbox/
├── 📁 raw/           # 👥 Upload files here
└── 📁 processed/     # 🤖 Transcripts appear here
```

**Services:**
- **Webhook Service**: Receives Dropbox notifications → triggers jobs
- **Worker Service**: Downloads files → transcribes → uploads results  
- **Shared Library**: Modular services with pluggable providers

## Available Commands

```bash
make help                # Show all available commands
make setup              # Set up development environment
make test               # Run tests with coverage
make build              # Build Docker containers
make test-containers    # Test container builds
make deploy-gcp         # Deploy to Google Cloud Platform
make deploy-aws         # Deploy to AWS (coming Phase 3)
make deploy-azure       # Deploy to Azure (coming Phase 3)
make clean              # Clean up Docker resources
```

## Output Files

For each input file `meeting.mp4`, you get:
- `meeting.json` - Full transcript data with timestamps and metadata
- `meeting.txt` - Clean text transcript

## Supported File Formats

- **Audio**: `.mp3`, `.wav`, `.m4a`, `.aac`, `.ogg`, `.flac`, `.mpga`, `.oga`
- **Video**: `.mp4`, `.mov`, `.avi`, `.webm`, `.mpeg`

## Project Structure

**Monorepo** with modular architecture:

```
transcripts/
├── Dockerfile                   # Multi-stage build for all services
├── Makefile                     # Build, test, and deployment commands
├── services/                    # 🔧 Modular services library
│   ├── core/                   # Interfaces, models, logging
│   ├── storage/                # Storage providers (Dropbox, GCS, etc.)
│   └── transcription/          # Transcription providers (OpenAI, local)
├── webhook/                     # 🔔 Webhook service
├── worker/                      # ⚙️  Worker service  
├── terraform/                   # 🏗️  Infrastructure as Code
├── tests/                       # 🧪 Unit and integration tests
└── requirements/                # 📦 Dependency management

## Deployment

### Modern Deployment (Recommended)

```bash
# Set your GCP project
export PROJECT_ID=your-gcp-project

# Deploy to Google Cloud Platform  
make deploy-gcp

# Deploy to other clouds (when available)
make deploy-aws        # Coming in Phase 3
make deploy-azure      # Coming in Phase 3

# Or step by step
make build              # Build containers
make push-gcp          # Push to Google Container Registry
```

### Legacy Deployment (Still supported)

```bash
# Build and push worker
cd worker
gcloud builds submit --tag gcr.io/YOUR_PROJECT/transcription-worker:latest

# Deploy webhook
cd terraform  
gcloud functions deploy webhook-handler --source ../webhook
```

## Migration Status

- ✅ **Phase 1**: Architecture & API boundaries defined  
- ✅ **Phase 2**: Core services extracted with feature flags
- 🔄 **Phase 3**: Infrastructure abstraction (next)
- ⏳ **Phase 4**: FastAPI service wrappers
- ⏳ **Phase 5**: Full migration & cleanup

## Feature Flags

Set `USE_NEW_SERVICES=true` to enable the new modular architecture.

### Environment Variables

**Worker Job**:
- `USE_NEW_SERVICES`: Enable new modular services (true/false)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `LOG_FORMAT`: Log format ('text' for dev, 'json' for prod)
- `MAX_FILES`: Max files per job run

**Webhook**:
- `DROPBOX_APP_SECRET`: For webhook verification
- `WORKER_JOB_NAME`: Cloud Run job to trigger

## Documentation

- [`docs/deployment.md`](docs/deployment.md) - Deployment guide
- [`docs/logging.md`](docs/logging.md) - Logging strategy  
- [`conversation/docs/`](conversation/docs/) - Architecture decisions

For detailed migration progress, see [`conversation/docs/2.md`](conversation/docs/2.md).

### Monitoring

```bash
# Show project info
make info

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