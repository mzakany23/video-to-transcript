# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development
```bash
# Install dependencies
uv sync

# Run tests
uv run pytest tests/ -v

# Run transcription on Google Drive files
uv run python transcribe_drive.py

# Show current status of processed jobs
uv run python transcribe_drive.py --status

# Process specific number of files
uv run python transcribe_drive.py --max-files 5

# Set up Google Drive credentials (OAuth)
uv run python setup_google_credentials.py
```

### Terraform (Infrastructure)
```bash
# Navigate to terraform directory
cd terraform/

# Initialize Terraform
terraform init

# Plan infrastructure changes
terraform plan

# Apply infrastructure (creates service account)
terraform apply

# Navigate back to project root
cd ..
```

## Architecture

This is a **transcription pipeline** that processes audio/video files using the OpenAI Whisper API with Google Drive integration.

### Core Components

1. **transcribe_drive.py** - Main entry point for Google Drive integration
   - Monitors shared Google Drive folder for new audio/video files
   - Handles large file compression using ffmpeg (>25MB limit)
   - Job tracking to prevent reprocessing
   - Automatically uploads results back to Google Drive

2. **google_drive_handler.py** - Google Drive API wrapper
   - Supports both OAuth (credentials.json) and service account authentication
   - Manages folder structure creation (`raw/` and `processed/` folders)
   - Handles file uploads/downloads and metadata operations

3. **transcribe.py** - Legacy local file processing (for backward compatibility)

4. **terraform/** - Infrastructure as Code for GCP service account
   - Creates service account with Drive API permissions
   - Generates service-account.json for automated authentication
   - Enables required APIs (Drive, IAM)

### Authentication Flow

The system supports two authentication methods:
1. **Service Account** (recommended for automation) - Uses `service-account.json`
2. **OAuth** (fallback) - Uses `credentials.json` and `token.json`

The Google Drive handler tries service account first, then falls back to OAuth if the service account file is not found.

### Data Flow

1. Team uploads files to Google Drive `raw/` folder
2. System detects new files and downloads them temporarily
3. Large files (>25MB) are compressed using ffmpeg
4. Files are transcribed using OpenAI Whisper API
5. Results (JSON with timestamps + plain text) are uploaded to `processed/` folder
6. Job tracking prevents duplicate processing

### File Structure

- `conversation/` - Temporary files and job tracking (gitignored)
- `data/` - Local data storage (if needed)
- `tests/` - Test suite
- `terraform/` - Infrastructure configuration

### Dependencies

Uses `uv` for Python dependency management. Key dependencies:
- OpenAI API client for Whisper transcription
- Google API clients for Drive integration
- ffmpeg-python for audio/video processing
- pytest for testing

### Environment Variables

- `OPENAI_API_KEY` - Required for Whisper API access