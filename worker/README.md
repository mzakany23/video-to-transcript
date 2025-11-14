# Transcription Worker

The worker service handles audio/video file processing, transcription via OpenAI Whisper API, AI-powered topic analysis, and result delivery.

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- ffmpeg (`brew install ffmpeg` on macOS)
- OpenAI API key
- Dropbox access token

### Setup

```bash
# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate

# Create .env file with required variables
cat > .env << EOF
OPENAI_API_KEY=your_openai_api_key_here
DROPBOX_ACCESS_TOKEN=your_dropbox_token
DROPBOX_RAW_FOLDER=/transcripts/raw
DROPBOX_PROCESSED_FOLDER=/transcripts/processed
PROJECT_ID=your-gcp-project-id
ENABLE_TOPIC_SUMMARIZATION=true
OPENAI_SUMMARIZATION_MODEL=gpt-4o-mini
EOF
```

### Run Locally

```bash
# Run worker directly
python main.py

# Or use uv
uv run main.py
```

### Testing

```bash
# Run unit tests (fast)
make test

# Run integration tests (requires API keys)
make test-integration

# Run all tests
make test-all

# Run with coverage
python -m pytest tests/ --cov=src/transcripts --cov-report=term-missing
```

## Features

- **Multi-Provider LLM Support**: Use OpenAI, Anthropic Claude, or 100+ models via LiteLLM
- **AI Topic Summarization**: Automatic topic detection with configurable models (default: GPT-5)
- **Audio Chunking**: Handles files of ANY size (splits files >20MB)
- **Smart Compression**: Targets 19MB for optimal API compatibility
- **Enhanced Timestamps**: Human-readable `HH:MM:SS` format
- **Multiple Output Formats**: JSON (with topic analysis), summary docs, plain text
- **Email Notifications**: Job start, completion, and failure alerts
- **Error Tracking**: Sentry integration for production monitoring

## Output Files

For each input file `interview.mp4`, generates:
- `interview_SUMMARY.txt` - Executive summary with topics and timestamps
- `interview_SUMMARY.md` - Markdown version with formatting
- `interview.json` - Full transcript with timestamps and topic analysis
- `interview.txt` - Clean text transcript with human-readable timestamps

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key (required for Whisper + GPT models) | - |
| `OPENAI_SUMMARIZATION_MODEL` | Model for analysis (e.g., `gpt-5`, `gpt-4o`, `claude-3-5-sonnet-20241022`) | `gpt-5` |
| `ANTHROPIC_API_KEY` | Anthropic API key (required only for Claude models) | - |
| `ENABLE_TOPIC_SUMMARIZATION` | Enable AI topic analysis | `true` |
| `DROPBOX_ACCESS_TOKEN` | Dropbox access token | - |
| `DROPBOX_RAW_FOLDER` | Folder to watch for new files | `/transcripts/raw` |
| `DROPBOX_PROCESSED_FOLDER` | Folder for output files | `/transcripts/processed` |
| `PROJECT_ID` | GCP project ID for Secret Manager | - |
| `ENABLE_EMAIL_NOTIFICATIONS` | Enable email alerts | `false` |
| `DEVELOPER_EMAILS` | Comma-separated developer emails (receives debug emails) | - |
| `USER_EMAILS` | Comma-separated user emails (receives summary emails only) | - |
| `MAX_FILES` | Max files to process per run | `10` |
| `SENTRY_DSN` | Sentry error tracking DSN | - |
| `SENTRY_ENVIRONMENT` | Sentry environment name | - |

## LLM Model Selection

The worker uses [LiteLLM](https://github.com/BerriAI/litellm) for multi-provider LLM support. You can easily switch between different models and providers.

### Using OpenAI Models (Default)

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_SUMMARIZATION_MODEL="gpt-5"  # default
```

**Available OpenAI models:**
- `gpt-5` (default) - Superior reasoning, 100% accurate timestamps
- `gpt-4o` - Fast and capable
- `gpt-4o-mini` - Cost-effective

### Using Anthropic Claude Models

```bash
export OPENAI_API_KEY="sk-..."  # Still needed for Whisper transcription
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_SUMMARIZATION_MODEL="claude-3-5-sonnet-20241022"
```

**Available Claude models:**
- `claude-3-5-sonnet-20241022` - Latest, excellent for analysis
- `claude-3-opus-20240229` - Most intelligent (slower/expensive)
- `claude-3-sonnet-20240229` - Balanced performance
- `claude-3-haiku-20240307` - Fast and cost-effective

### Using Other Providers

LiteLLM supports 100+ providers. See [docs](https://docs.litellm.ai/docs/providers) for full list.

**Examples:**
```bash
# Cohere
export COHERE_API_KEY="..."
export OPENAI_SUMMARIZATION_MODEL="command-r-plus"

# Mistral
export MISTRAL_API_KEY="..."
export OPENAI_SUMMARIZATION_MODEL="mistral-large-latest"
```

### Testing Different Models

Compare models before committing to production:

```bash
cd worker  # Run from worker directory

# Test with GPT-5 (default)
uv run python scripts/generate_summary_email.py \
  ../conversation/features/better-summaries/data/episode-4.json \
  -o test-output/gpt5.html

# Test with Claude 3.5 Sonnet
export ANTHROPIC_API_KEY="sk-ant-..."
uv run python scripts/generate_summary_email.py \
  ../conversation/features/better-summaries/data/episode-4.json \
  -o test-output/claude-sonnet.html \
  -m claude-3-5-sonnet-20241022

# Test with GPT-4o
uv run python scripts/generate_summary_email.py \
  ../conversation/features/better-summaries/data/episode-4.json \
  -o test-output/gpt4o.html \
  -m gpt-4o

# Compare multiple models at once
for model in gpt-5 gpt-4o claude-3-5-sonnet-20241022; do
  uv run python scripts/generate_summary_email.py input.json \
    -o test-output/${model}.html -m $model
done

# Open all results for comparison
open test-output/*.html
```

### Model Selection Tips

**Use GPT-5 when:**
- You need superior reasoning and deep analysis
- You want 100% accurate timestamps
- Quality is more important than cost

**Use Claude 3.5 Sonnet when:**
- You want excellent analysis with different perspective
- You need strong reasoning at competitive pricing
- You want to compare outputs between providers

**Use GPT-4o-mini or Claude Haiku when:**
- You need fast, cost-effective processing
- Content is straightforward
- Processing high volumes

## Project Structure

```
worker/
├── src/transcripts/           # Core library
│   ├── config.py             # Configuration management
│   ├── core/                 # Core business logic
│   │   ├── audio_chunker.py  # Large file chunking
│   │   ├── dropbox_handler.py # Dropbox integration
│   │   ├── topic_analyzer.py  # AI topic analysis
│   │   ├── transcription.py   # Whisper API integration
│   │   └── summary_formatter.py # Output formatting
│   └── utils/                # Utilities
│       └── timestamp_formatter.py # Timestamp formatting
├── tests/
│   ├── unit/                 # Unit tests (no external deps)
│   └── integration/          # Integration tests (with APIs)
├── main.py                   # Worker entry point
├── Dockerfile               # Container definition
├── Makefile                 # Test commands
└── CHANGELOG.md             # Version history
```

## How It Works

1. **File Discovery**: Scans Dropbox raw folder for new audio/video files
2. **Download**: Downloads file to temporary storage
3. **Processing**:
   - Compresses file if needed (target: 19MB)
   - Splits into chunks if >20MB (10-minute segments)
   - Transcribes each chunk via OpenAI Whisper API
   - Merges segments with adjusted timestamps
4. **AI Analysis**: Analyzes transcript to identify topics, key points, and action items
5. **Output Generation**:
   - Creates JSON with full data and topic analysis
   - Generates summary documents (TXT and MD)
   - Formats clean text transcript
6. **Upload**: Uploads all output files to Dropbox processed folder
7. **Notification**: Sends email notification on completion/failure

## Cost Estimates

**Transcription** (OpenAI Whisper API):
- $0.006 per minute of audio
- Example: 30-minute file = ~$0.18

**Topic Summarization** (varies by model):
- GPT-5: ~$0.05-0.15 per 30-minute transcript (higher quality)
- GPT-4o: ~$0.03-0.08 per 30-minute transcript
- GPT-4o-mini: ~$0.01-0.03 per 30-minute transcript (most cost-effective)
- Claude 3.5 Sonnet: ~$0.04-0.10 per 30-minute transcript
- Can be disabled via `ENABLE_TOPIC_SUMMARIZATION=false`

## Deployment

This service is deployed as a Google Cloud Run Job. See the main [README](../README.md) for deployment instructions.

**Quick deployment:**
```bash
# Build Docker image
docker buildx build --platform linux/amd64 \
  -t gcr.io/YOUR_PROJECT/transcription-worker:latest \
  . --push

# Deploy via Terraform
cd ../terraform/
terraform apply
```

## Troubleshooting

### "OpenAI API key not found"
- Check `.env` file has `OPENAI_API_KEY` set
- For GCP: Verify secret exists in Secret Manager

### "ffmpeg not found"
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

### "Error code: 413 - Maximum content size limit exceeded"
- Ensure you're running v1.1.0+ with chunking support
- Files >20MB are automatically chunked

### Test failures
- Unit tests should run without API keys
- Integration tests require valid `OPENAI_API_KEY`
- Check `.env` file is properly configured

## Contributing

See the main [CONTRIBUTING.md](../CONTRIBUTING.md) for development guidelines.

## Version History

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

**Current version:** v1.2.1

## License

MIT License - see [LICENSE](../LICENSE) for details.
