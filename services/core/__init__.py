"""
Core interfaces and models for the transcription service system
"""

from .interfaces import (
    StorageProvider,
    TranscriptionProvider,
    JobRunner,
    NotificationProvider,
)

from .models import (
    FileInfo,
    TranscriptionOptions,
    TranscriptionResult,
    TranscriptionSegment,
    JobSpec,
    JobState,
    JobStatus,
    DownloadResult,
    UploadResult,
)

from .exceptions import (
    ServiceException,
    StorageException,
    TranscriptionException,
    JobException,
    NotificationException,
)

from .logging import configure_logging, get_logger

__all__ = [
    # Interfaces
    "StorageProvider",
    "TranscriptionProvider", 
    "JobRunner",
    "NotificationProvider",
    # Models
    "FileInfo",
    "TranscriptionOptions",
    "TranscriptionResult",
    "TranscriptionSegment",
    "JobSpec",
    "JobState",
    "JobStatus",
    "DownloadResult",
    "UploadResult",
    # Exceptions
    "ServiceException",
    "StorageException",
    "TranscriptionException",
    "JobException",
    "NotificationException",
    # Logging
    "configure_logging",
    "get_logger",
]