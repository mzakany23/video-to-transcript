"""
Transcription service with pluggable providers
"""

from .providers.openai import OpenAITranscriptionProvider
from .service import TranscriptionService

__all__ = [
    "TranscriptionService",
    "OpenAITranscriptionProvider",
]
