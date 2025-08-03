"""
Transcripts - Dropbox-based transcription pipeline
"""

__version__ = "2.0.0"
__author__ = "Transcription Pipeline"

from .core.dropbox_handler import DropboxHandler
from .core.transcription import TranscriptionService
from .core.audio_processor import AudioProcessor

__all__ = ["DropboxHandler", "TranscriptionService", "AudioProcessor"]