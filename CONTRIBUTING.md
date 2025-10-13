# Contributing to Transcripts

Thank you for your interest in contributing to this project! This guide will help you get started with development, testing, and submitting changes.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Running Tests](#running-tests)
- [Project Structure](#project-structure)
- [Making Changes](#making-changes)
- [Submitting Pull Requests](#submitting-pull-requests)
- [Code Style](#code-style)
- [Deployment](#deployment)

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Docker (for building worker images)
- ffmpeg (for audio processing)
- Google Cloud CLI (for deployments)
- Terraform (for infrastructure changes)

### Installing Prerequisites

```bash
# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install ffmpeg
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Install Google Cloud CLI
# https://cloud.google.com/sdk/docs/install

# Install Terraform
# https://developer.hashicorp.com/terraform/install
```

## Development Setup

### 1. Fork and Clone

```bash
git clone https://github.com/YOUR_USERNAME/transcripts.git
cd transcripts
```

### 2. Set Up Worker Service

```bash
cd worker/

# Create virtual environment and install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

### 3. Set Up Webhook Service

```bash
cd webhook/

# Create virtual environment and install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate
```

### 4. Configure Environment Variables

Create a `.env` file in the worker directory for local testing:

```bash
# worker/.env
OPENAI_API_KEY=your_openai_api_key_here
DROPBOX_ACCESS_TOKEN=your_dropbox_token_here
DROPBOX_RAW_FOLDER=/transcripts/raw
DROPBOX_PROCESSED_FOLDER=/transcripts/processed
PROJECT_ID=your-gcp-project-id
ENABLE_TOPIC_SUMMARIZATION=true
OPENAI_SUMMARIZATION_MODEL=gpt-4o-mini
```

## Running Tests

This project uses pytest for testing. Tests are organized into unit and integration tests.

### Quick Test Commands

```bash
cd worker/

# Run only unit tests (fast, no external dependencies)
make test

# Run integration tests (requires OpenAI API key and test audio files)
make test-integration

# Run all tests
make test-all

# Run tests with coverage
python -m pytest tests/ --cov=src/transcripts --cov-report=term-missing
```

### Understanding the Test Structure

```
worker/tests/
├── unit/                   # Fast tests, no external dependencies
│   ├── test_config.py
│   ├── test_timestamp_formatter.py
│   └── ...
└── integration/            # Slower tests, require API keys
    ├── test_topic_summarization_e2e.py
    └── ...
```

### Writing Tests

- **Unit tests**: Test individual functions/classes in isolation
- **Integration tests**: Test full workflows with real APIs (mark with `@pytest.mark.integration`)
- Place test files in the appropriate directory
- Name test files with `test_` prefix
- Use descriptive test function names

Example:

```python
import pytest

def test_format_timestamp_zero_seconds():
    """Test timestamp formatting for zero seconds"""
    from transcripts.utils.timestamp_formatter import format_timestamp
    assert format_timestamp(0) == "00:00"

@pytest.mark.integration
def test_full_transcription_pipeline():
    """Test complete transcription workflow"""
    # Integration test code here
```

## Project Structure

This is a monorepo with independent services:

```
transcripts/
├── worker/                      # Worker service (transcription processing)
│   ├── src/transcripts/         # Core library
│   │   ├── config.py           # Configuration management
│   │   ├── core/               # Core business logic
│   │   │   ├── audio_chunker.py
│   │   │   ├── dropbox_handler.py
│   │   │   ├── topic_analyzer.py
│   │   │   └── transcription.py
│   │   └── utils/              # Utility functions
│   │       └── timestamp_formatter.py
│   ├── tests/                  # Test suite
│   │   ├── unit/
│   │   └── integration/
│   ├── main.py                 # Worker entry point
│   ├── Makefile               # Test commands
│   ├── CHANGELOG.md           # Version history
│   └── pyproject.toml         # Dependencies
│
├── webhook/                    # Webhook service (Dropbox notifications)
│   ├── main.py                # Webhook entry point
│   ├── CHANGELOG.md           # Version history
│   └── pyproject.toml         # Dependencies
│
├── terraform/                  # Infrastructure as Code
│   ├── main.tf                # GCP resources
│   ├── terraform.tfvars       # Configuration
│   └── README.md
│
└── .github/
    └── workflows/             # CI/CD pipelines
        ├── deploy-worker.yml
        ├── deploy-webhook.yml
        └── pr-checks.yml
```

### Key Components

- **Worker**: Handles file download, audio chunking, transcription, topic analysis, and result upload
- **Webhook**: Receives Dropbox notifications and triggers worker jobs
- **Shared Logic**: Configuration and utilities in `worker/src/transcripts/`

## Making Changes

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Your Changes

- Write clean, readable code
- Add tests for new functionality
- Update documentation if needed
- Follow existing code style

### 3. Run Tests Locally

```bash
cd worker/
make test        # Run unit tests
make test-all    # Run all tests (if you have API keys)
```

### 4. Update CHANGELOG

If your change affects users, update the appropriate CHANGELOG:

```bash
# For worker changes
vim worker/CHANGELOG.md

# For webhook changes
vim webhook/CHANGELOG.md
```

Follow [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
## [Unreleased]

### Added
- New feature description

### Fixed
- Bug fix description

### Changed
- Change description
```

## Submitting Pull Requests

### 1. Commit Your Changes

```bash
git add .
git commit -m "feat: Add feature description"
# or
git commit -m "fix: Fix bug description"
```

**Commit message conventions:**
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `test:` Test additions/changes
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

### 2. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 3. Open a Pull Request

1. Go to the [original repository](https://github.com/mzakany23/video-to-transcript)
2. Click "New Pull Request"
3. Select your fork and branch
4. Fill in the PR template:
   - **Description**: What does this PR do?
   - **Testing**: How did you test it?
   - **Related Issues**: Link any related issues

### 4. PR Checklist

Before submitting, ensure:

- [ ] Tests pass locally (`make test`)
- [ ] Code follows project style
- [ ] Documentation is updated
- [ ] CHANGELOG is updated (if applicable)
- [ ] PR description is clear and complete

### 5. Code Review Process

- Maintainers will review your PR
- Address any feedback or requested changes
- Once approved, your PR will be merged

## Code Style

### Python Style

- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints where possible
- Write descriptive variable and function names
- Add docstrings to classes and functions

Example:

```python
from typing import Dict, List

def format_timestamp(seconds: float) -> str:
    """
    Convert seconds to HH:MM:SS or MM:SS format.

    Args:
        seconds: Number of seconds (float or int)

    Returns:
        Formatted timestamp string

    Examples:
        >>> format_timestamp(90)
        '01:30'
        >>> format_timestamp(3665)
        '01:01:05'
    """
    total_seconds = int(round(seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    if hours == 0:
        return f"{minutes:02d}:{secs:02d}"
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
```

### Linting

The project uses ruff for linting (optional but recommended):

```bash
pip install ruff
ruff check worker/
ruff check webhook/
```

## Deployment

### Local Testing

Test worker locally without deploying:

```bash
cd worker/
source .venv/bin/activate
python main.py
```

### CI/CD Pipeline

The project uses GitHub Actions for automated deployment. When you open a PR:

1. **PR Checks** run automatically:
   - Python linting with ruff
   - Dockerfile validation with hadolint
   - Terraform validation
   - Docker build test

2. **After merge to main**:
   - Services automatically deploy if CHANGELOG version changed
   - Docker images are built and pushed
   - Terraform applies infrastructure changes
   - Git tags are created automatically

### Manual Deployment (Maintainers)

If you have access to the GCP project:

```bash
# Build and push worker image
cd worker/
docker buildx build --platform linux/amd64 \
  -t gcr.io/jos-transcripts/transcription-worker:latest \
  . --push

# Deploy with Terraform
cd ../terraform/
terraform init
terraform apply
```

See [README.md](README.md) for detailed deployment instructions.

## Need Help?

- **Questions**: Open a [GitHub Discussion](https://github.com/mzakany23/video-to-transcript/discussions)
- **Bugs**: Open a [GitHub Issue](https://github.com/mzakany23/video-to-transcript/issues)
- **Security**: See [SECURITY.md](SECURITY.md) for reporting vulnerabilities

## License

By contributing, you agree that your contributions will be licensed under the same [MIT License](LICENSE) that covers this project.

## Thank You!

Your contributions make this project better for everyone. Thank you for taking the time to contribute!
