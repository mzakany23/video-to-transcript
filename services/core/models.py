"""
Data models for the transcription service system
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class JobState(Enum):
    """Job execution states"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class FileInfo:
    """Information about a file in storage"""

    name: str
    path: str
    size: int
    modified_at: datetime
    mime_type: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def extension(self) -> str:
        """Get file extension"""
        return Path(self.name).suffix.lower()

    @property
    def size_mb(self) -> float:
        """Get size in megabytes"""
        return self.size / (1024 * 1024)


@dataclass
class DownloadResult:
    """Result of a download operation"""

    success: bool
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    download_time_seconds: Optional[float] = None
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class UploadResult:
    """Result of an upload operation"""

    success: bool
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    upload_time_seconds: Optional[float] = None
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchResult:
    """Result of a batch operation"""

    successful: list[Any] = field(default_factory=list)
    failed: list[dict[str, Any]] = field(default_factory=list)
    total_processed: int = 0

    @property
    def success_count(self) -> int:
        """Number of successful operations"""
        return len(self.successful)

    @property
    def failure_count(self) -> int:
        """Number of failed operations"""
        return len(self.failed)

    @property
    def success_rate(self) -> float:
        """Success rate as percentage"""
        if self.total_processed == 0:
            return 0.0
        return (self.success_count / self.total_processed) * 100


@dataclass
class TranscriptionOptions:
    """Options for transcription"""

    language: Optional[str] = None
    model: str = "whisper-1"
    response_format: str = "verbose_json"
    temperature: float = 0.0
    prompt: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API calls"""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class TranscriptionSegment:
    """A segment of transcribed text"""

    id: int
    start: float
    end: float
    text: str
    confidence: Optional[float] = None

    @property
    def duration(self) -> float:
        """Get segment duration in seconds"""
        return self.end - self.start


@dataclass
class TranscriptionResult:
    """Result of a transcription operation"""

    text: str
    segments: list[TranscriptionSegment]
    language: str
    duration: float
    processed_at: datetime
    model: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def word_count(self) -> int:
        """Get word count of transcription"""
        return len(self.text.split())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "text": self.text,
            "segments": [
                {
                    "id": s.id,
                    "start": s.start,
                    "end": s.end,
                    "text": s.text,
                    "confidence": s.confidence,
                }
                for s in self.segments
            ],
            "language": self.language,
            "duration": self.duration,
            "processed_at": self.processed_at.isoformat(),
            "model": self.model,
            "metadata": self.metadata,
        }


@dataclass
class ResourceRequirements:
    """Resource requirements for a job"""

    cpu: str = "1"
    memory: str = "2Gi"
    timeout_seconds: int = 3600
    environment: dict[str, str] = field(default_factory=dict)


@dataclass
class JobSpec:
    """Specification for a job to be executed"""

    job_type: str
    input_data: dict[str, Any]
    resources: ResourceRequirements = field(default_factory=ResourceRequirements)
    environment: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class JobStatus:
    """Status of a job"""

    job_id: str
    state: JobState
    progress: Optional[float] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        """Check if job is in terminal state"""
        return self.state in [JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED]

    @property
    def duration(self) -> Optional[float]:
        """Get job duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
