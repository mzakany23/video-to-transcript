"""
Transcripts - Dropbox-based transcription pipeline
"""

__version__ = "2.0.0"
__author__ = "Transcription Pipeline"

from .core.audio_processor import AudioProcessor
from .core.dropbox_handler import DropboxHandler
from .core.transcription import TranscriptionService

__all__ = ["DropboxHandler", "TranscriptionService", "AudioProcessor"]
