# Transcripts with OpenAI Whisper API

Transcribe audio and video files using the OpenAI Whisper API with Google Drive integration.

## Phase 1: Local Google Drive Integration ✅

### Features
- **Google Drive Integration**: Automatically monitors shared Google Drive folder
- **Large File Support**: Automatic compression for files >25MB using ffmpeg
- **Job Tracking**: Prevents reprocessing of already transcribed files
- **Multiple Formats**: Supports mp3, mp4, wav, mov, avi, webm, and more
- **Cloud Storage**: Results automatically uploaded to Google Drive

### Setup

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Set up Google Drive API credentials**:
   ```bash
   uv run python setup_google_credentials.py
   ```
   Follow the instructions to download `credentials.json` from Google Cloud Console.

3. **Set your OpenAI API key**:
   ```bash
   export OPENAI_API_KEY="your_api_key_here"
   ```

### Usage

#### Google Drive Transcription (Recommended)
```bash
# Process all new files in Google Drive
uv run python transcribe_drive.py

# Show current status
uv run python transcribe_drive.py --status

# Process specific number of files
uv run python transcribe_drive.py --max-files 5

# Specify language
uv run python transcribe_drive.py --language en
```

#### Local Transcription (Legacy)
```bash
# Process files in data/raw/
uv run python transcribe.py

# Process specific file
uv run python transcribe.py --file path/to/audio.mp3
```

## Google Drive Folder Structure

The system automatically creates this structure in your Google Drive:

```
📁 Transcription Pipeline/
├── 📁 raw/           # 👥 Team drops files here
└── 📁 processed/     # 🤖 Transcripts appear here automatically
```

## How It Works

1. **📤 Upload**: Team members drag audio/video files to the `raw/` folder
2. **🔍 Detection**: System monitors for new files automatically
3. **⚡ Processing**: Large files are compressed, then transcribed with Whisper
4. **📥 Results**: JSON (with timestamps) and TXT files appear in `processed/`
5. **✅ Tracking**: Prevents duplicate processing of the same files

## Output Files

For each input file `meeting.mp4`, you get:
- `meeting.json` - Full transcript data with timestamps and metadata
- `meeting.txt` - Clean text transcript

## Supported File Formats

- **Audio**: `.mp3`, `.wav`, `.m4a`, `.aac`, `.ogg`, `.flac`, `.mpga`, `.oga`
- **Video**: `.mp4`, `.mov`, `.avi`, `.webm`, `.mpeg`

## Development

### Run Tests
```bash
uv run pytest tests/ -v
```

### Project Structure
```
transcripts/
├── transcribe_drive.py          # 🚀 Main Google Drive integration
├── google_drive_handler.py      # 🔧 Google Drive API wrapper
├── setup_google_credentials.py  # ⚙️  Credential setup helper
├── transcribe.py                # 📁 Legacy local file processing
├── tests/                       # 🧪 Test suite
├── conversation/                # 🗂️  Temp files (gitignored)
└── data/                        # 📂 Local data (if needed)
    ├── raw/
    └── processed/
```

## Troubleshooting

### "credentials.json not found"
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create/select project → Enable Google Drive API
3. Credentials → Create OAuth client ID (Desktop application)
4. Download and save as `credentials.json` in project root

### "OpenAI API key not found"
```bash
export OPENAI_API_KEY="your_key_here"
# Or add to .env file
```

### "ffmpeg not found"
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

## Next Phases

- **Phase 2**: Cloud Infrastructure (Terraform + GCP)
- **Phase 3**: Serverless Event Processing
- **Phase 4**: CI/CD Pipeline (GitHub Actions)
- **Phase 5**: Production Monitoring

---

✨ **Ready for production!** The system now handles shared Google Drive folders with automatic processing and team collaboration.