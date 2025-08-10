"""
Transcription service using OpenAI Whisper API
"""

from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
except ImportError:
    raise ImportError("OpenAI SDK not installed. Run: uv add openai")

from ..config import Config


class TranscriptionService:
    """Handles audio transcription using OpenAI Whisper"""

    def __init__(self, api_key: str = None):
        """Initialize transcription service"""
        self.api_key = api_key or Config.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.client = OpenAI(api_key=self.api_key)
        print("✅ OpenAI transcription service initialized")

    def transcribe_audio(self, audio_file_path: Path) -> dict[str, Any]:
        """Transcribe audio file using OpenAI Whisper"""
        try:
            file_size = audio_file_path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)

            print(f"🎙️ Transcribing audio file: {file_size_mb:.1f}MB")

            # Check file size limit
            if file_size_mb > Config.MAX_FILE_SIZE_MB:
                return {
                    "success": False,
                    "error": f"File too large: {file_size_mb:.1f}MB > {Config.MAX_FILE_SIZE_MB}MB limit",
                }

            with open(audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    file=audio_file, model=Config.OPENAI_MODEL, response_format="verbose_json"
                )

                # Process segments
                segments = getattr(transcript, "segments", [])
                if segments:
                    segments = [
                        {
                            "id": getattr(segment, "id", i),
                            "start": getattr(segment, "start", 0),
                            "end": getattr(segment, "end", 0),
                            "text": getattr(segment, "text", ""),
                        }
                        for i, segment in enumerate(segments)
                    ]

                transcript_data = {
                    "text": transcript.text,
                    "segments": segments,
                    "language": getattr(transcript, "language", "unknown"),
                    "duration": getattr(transcript, "duration", 0),
                    "processed_at": datetime.now().isoformat(),
                    "model": Config.OPENAI_MODEL,
                }

                print(f"✅ Transcription completed: {len(transcript.text)} characters")
                return {"success": True, "transcript_data": transcript_data}

        except Exception as e:
            print(f"❌ Error transcribing audio: {str(e)}")
            return {"success": False, "error": str(e)}
