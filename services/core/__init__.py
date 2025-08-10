"""
Core interfaces and models for the transcription service system
"""

from .exceptions import (
    AuthenticationError,
    ConfigurationError,
    JobError,
    NotificationError,
    ServiceError,
    StorageError,
    TranscriptionError,
)
from .interfaces import (
    JobRunner,
    NotificationProvider,
    StorageProvider,
    TranscriptionProvider,
)
from .logging import configure_logging, get_logger
from .models import (
    DownloadResult,
    FileInfo,
    JobSpec,
    JobState,
    JobStatus,
    TranscriptionOptions,
    TranscriptionResult,
    TranscriptionSegment,
    UploadResult,
)

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
    "ServiceError",
    "StorageError",
    "TranscriptionError",
    "JobError",
    "NotificationError",
    "ConfigurationError",
    "AuthenticationError",
    # Logging
    "configure_logging",
    "get_logger",
]
