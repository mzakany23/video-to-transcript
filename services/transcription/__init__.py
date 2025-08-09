"""
Transcription service with pluggable providers
"""

from .service import TranscriptionService
from .providers.openai import OpenAITranscriptionProvider

__all__ = [
    "TranscriptionService",
    "OpenAITranscriptionProvider",
]