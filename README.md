# Transcripts

[![Deploy Terraform](https://github.com/mzakany23/video-to-transcript/actions/workflows/deploy-terraform.yml/badge.svg)](https://github.com/mzakany23/video-to-transcript/actions/workflows/deploy-terraform.yml)
[![Deploy Worker](https://github.com/mzakany23/video-to-transcript/actions/workflows/deploy-worker.yml/badge.svg)](https://github.com/mzakany23/video-to-transcript/actions/workflows/deploy-worker.yml)
[![PR Checks](https://github.com/mzakany23/video-to-transcript/actions/workflows/pr-checks.yml/badge.svg)](https://github.com/mzakany23/video-to-transcript/actions/workflows/pr-checks.yml)
[![Worker Release](https://img.shields.io/github/v/release/mzakany23/video-to-transcript?filter=worker-*&label=worker)](https://github.com/mzakany23/video-to-transcript/releases?q=worker)
[![Webhook Release](https://img.shields.io/github/v/release/mzakany23/video-to-transcript?filter=webhook-*&label=webhook)](https://github.com/mzakany23/video-to-transcript/releases?q=webhook)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Serverless audio/video transcription pipeline using OpenAI Whisper API. Upload files to Dropbox, get transcripts automatically.

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Development](#development)
- [Versioning](#versioning)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Output Files](#output-files)
- [Supported File Formats](#supported-file-formats)
- [Project Structure](#project-structure)
- [Deployment](#deployment)
  - [CI/CD Pipeline (Recommended)](#cicd-pipeline-recommended)
  - [Making a New Deployment](#making-a-new-deployment)
  - [Manual Deployment (Alternative)](#manual-deployment-alternative)
  - [Environment Variables](#environment-variables)
  - [Optional: Sentry Error Tracking](#optional-sentry-error-tracking)
  - [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features
- **AI-Powered Topic Summarization**: Automatic topic identification with timestamps, key points, and action items
- **Enhanced Timestamps**: Human-readable `HH:MM:SS` format throughout all outputs
- **Webhook-based Processing**: Automatic transcription when files are uploaded
- **Large File Support**: Handles files of ANY size with automatic chunking (splits files >20MB)
- **Smart Compression**: Targets 19MB for optimal API compatibility
- **Multiple Formats**: Audio (mp3, wav, m4a) and video (mp4, mov, avi, webm)
- **Serverless Architecture**: Scales automatically with Google Cloud Run
- **Structured Output**: JSON (with topic analysis), summary documents, and plain text
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

## Versioning

This project uses **independent semantic versioning** for webhook and worker services:

- **Webhook versions**: `webhook-v1.2.0`, `webhook-v1.3.0`, etc.
- **Worker versions**: `worker-v1.1.0`, `worker-v1.2.0`, etc.

**Version control:**
- Each service has its own `CHANGELOG.md` in its directory ([webhook/CHANGELOG.md](webhook/CHANGELOG.md), [worker/CHANGELOG.md](worker/CHANGELOG.md))
- Git tags follow the pattern `{service}-v{semver}` (e.g., `webhook-v1.2.0`)
- **Smart deployments**: Services only rebuild/redeploy when their CHANGELOG version changes
- Pipeline checks if git tag exists for CHANGELOG version - skips build if already deployed
- Version numbers are set in [terraform/terraform.tfvars](terraform/terraform.tfvars) (`webhook_version`, `worker_image_version`)

**CHANGELOG-driven deployments:**
The CI/CD pipeline automatically:
1. Extracts version from each service's `CHANGELOG.md` (first `## [X.Y.Z]` line)
2. Checks if git tag `{service}-vX.Y.Z` already exists
3. Skips build/deploy if tag exists (prevents unnecessary rebuilds)
4. Creates git tag automatically after successful deployment
5. Updates version in terraform.tfvars to match deployed version

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
- `meeting_SUMMARY.txt` - **NEW!** Executive summary with topics, timestamps, key points, and action items
- `meeting_SUMMARY.md` - **NEW!** Markdown version with formatting
- `meeting.json` - Full transcript data with timestamps, segments, and topic analysis
- `meeting.txt` - Clean text transcript with human-readable timestamps (`HH:MM:SS`)

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

### CI/CD Pipeline (Recommended)

This project includes GitHub Actions workflows for automated deployment:

**Automatic Deployments:**
- **Worker changes** (`worker/`) → Auto-build and deploy Docker image
- **Webhook changes** (`webhook/`) → Auto-deploy via Terraform
- **Infrastructure changes** (`terraform/`) → Auto-apply Terraform
- **PR checks** → Validate code, Terraform, and Docker builds

**Setup (One-time):**

1. **Configure Workload Identity Federation** (no service account keys needed!):
   ```bash
   # Edit .github/setup-workload-identity.sh and update GITHUB_REPO
   vim .github/setup-workload-identity.sh

   # Run setup script
   ./.github/setup-workload-identity.sh
   ```

2. **Add GitHub Secrets** (from script output):
   - Go to: `https://github.com/YOUR_USERNAME/transcripts/settings/secrets/actions`
   - Add: `WIF_PROVIDER` (Workload Identity Provider path)
   - Add: `WIF_SERVICE_ACCOUNT` (Service account email)

3. **Push to main** → Automatic deployment!

**Detailed CI/CD documentation:** See [.github/CICD.md](.github/CICD.md)

### Making a New Deployment

To deploy new changes to webhook or worker services:

**Step 1: Update the CHANGELOG**

Edit the appropriate service's CHANGELOG ([webhook/CHANGELOG.md](webhook/CHANGELOG.md) or [worker/CHANGELOG.md](worker/CHANGELOG.md)):

```markdown
## [1.3.0] - 2025-10-12

### Added
- New feature description

### Fixed
- Bug fix description

### Changed
- Change description
```

**Important**:
- Use semantic versioning (MAJOR.MINOR.PATCH)
- Follow [Keep a Changelog](https://keepachangelog.com/) format
- The **first** `## [X.Y.Z]` line determines the version to deploy

**Step 2: Update terraform.tfvars**

Update the version in [terraform/terraform.tfvars](terraform/terraform.tfvars):

```hcl
# Service versions (bump these to trigger deployments)
webhook_version        = "v1.3.0"   # Match CHANGELOG version
worker_image_version   = "v1.2.0"   # Match CHANGELOG version
```

**Step 3: Commit and push**

```bash
git add webhook/CHANGELOG.md terraform/terraform.tfvars  # (or worker/CHANGELOG.md)
git commit -m "Release webhook v1.3.0: Add new feature"
git push origin main
```

**What happens automatically:**

1. GitHub Actions workflow triggers on push to main
2. Pipeline extracts version from CHANGELOG
3. Checks if git tag `webhook-v1.3.0` exists
   - **If tag exists**: Skips build/deploy (already deployed)
   - **If tag doesn't exist**: Builds and deploys
4. On successful deployment:
   - Creates git tag `webhook-v1.3.0` with CHANGELOG notes
   - Pushes tag to repository

**Verification:**

```bash
# Check workflow status
gh run list --limit 5

# View recent tags
git fetch --tags
git tag -l "webhook-*" --sort=-version:refname | head -5
git tag -l "worker-*" --sort=-version:refname | head -5

# Check deployed versions
gcloud run jobs describe transcription-worker --region us-east1 --format='get(template.template.containers[0].image)'
gcloud functions describe dropbox-webhook --region us-east1 --gen2 --format='get(labels.version)'
```

### Manual Deployment (Alternative)

If you prefer manual deployment or need to deploy locally:

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
- `OPENAI_SUMMARIZATION_MODEL`: AI model for topic summarization (default: `gpt-4o-mini`)
  - Options: `gpt-4o-mini` (recommended, ~$0.01-0.03 per 30-min transcript)
  - Options: `gpt-4o` (higher quality, ~$0.05-0.15 per 30-min transcript)
  - Options: `gpt-4-turbo` (legacy, ~$0.10-0.30 per 30-min transcript)
- `ENABLE_TOPIC_SUMMARIZATION`: Enable AI-powered topic analysis (default: `true`)
  - Set to `false` to disable topic summarization and save on API costs
- `ENABLE_EMAIL_NOTIFICATIONS`: Enable email alerts (default: `false`)
- `NOTIFICATION_EMAIL`: Comma-separated list of email recipients
- `GMAIL_SECRET_NAME`: Gmail credentials secret name
- `MAX_FILES`: Max files per job run (default: `10`)
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
3. You should see messages like: `File is large, using chunked transcription`

### View detailed error logs
```bash
# Recent errors only
gcloud logging read "resource.type=cloud_run_job AND severity>=ERROR" --limit 50 --project jos-transcripts

# Specific execution
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=transcription-worker" --limit 200 --project jos-transcripts

# Real-time streaming
gcloud logging tail "resource.type=cloud_run_job" --project jos-transcripts
```

## Contributing

We welcome contributions! Whether you're fixing bugs, adding features, or improving documentation, your help is appreciated.

**Getting Started:**
- Read the [Contributing Guide](CONTRIBUTING.md) for development setup, testing, and submission guidelines
- Check out [open issues](https://github.com/mzakany23/video-to-transcript/issues) for tasks to work on
- Fork the repo and create a feature branch
- Write tests for your changes
- Submit a pull request

**Quick Development Setup:**
```bash
# Fork and clone the repo
git clone https://github.com/YOUR_USERNAME/transcripts.git
cd transcripts

# Set up worker
cd worker/
uv sync
source .venv/bin/activate

# Run tests
make test
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for complete details on:
- Development environment setup
- Running tests locally
- Code style guidelines
- Pull request process
- Project architecture

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**TL;DR:** You can use, modify, and distribute this software freely, even for commercial purposes. Just include the original copyright notice.