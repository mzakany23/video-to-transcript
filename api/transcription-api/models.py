"""
Pydantic models for Transcription API
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field


# Enums
class JobState(str, Enum):
    """Job execution states"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Core Models
class HealthStatus(BaseModel):
    """Health status model"""
    status: str = Field(description="Service health status")
    timestamp: datetime = Field(description="Status check timestamp")
    version: str = Field(description="Service version")


class TranscriptionOptions(BaseModel):
    """Options for transcription"""
    language: Optional[str] = Field(None, description="Language code (e.g., 'en', 'es')")
    model: str = Field(default="whisper-1", description="Transcription model to use")
    response_format: str = Field(default="json", description="Response format")
    temperature: float = Field(default=0.0, ge=0, le=1, description="Temperature for transcription")
    prompt: Optional[str] = Field(None, description="Optional prompt to guide transcription")


class TranscriptionSegment(BaseModel):
    """A segment of transcribed text"""
    id: int = Field(description="Segment ID")
    start: float = Field(description="Segment start time in seconds")
    end: float = Field(description="Segment end time in seconds")
    text: str = Field(description="Segment text")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Confidence score")


class TranscriptionResult(BaseModel):
    """Result of a transcription operation"""
    text: str = Field(description="Full transcription text")
    segments: List[TranscriptionSegment] = Field(description="Transcription segments")
    language: str = Field(description="Detected language")
    duration: float = Field(description="Audio duration in seconds")
    model: str = Field(description="Model used for transcription")
    processed_at: datetime = Field(description="Processing timestamp")


class JobResponse(BaseModel):
    """Response when submitting a job"""
    job_id: str = Field(description="Unique job identifier")
    status: JobState = Field(description="Job status")
    created_at: datetime = Field(description="Job creation timestamp")
    estimated_duration: Optional[float] = Field(None, description="Estimated processing time in seconds")


class JobStatus(BaseModel):
    """Job status information"""
    job_id: str = Field(description="Job identifier")
    status: JobState = Field(description="Current job status")
    progress: Optional[float] = Field(None, ge=0, le=100, description="Job progress percentage")
    created_at: datetime = Field(description="Job creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    result: Optional[TranscriptionResult] = Field(None, description="Transcription result")
    error: Optional[str] = Field(None, description="Error message if job failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class JobLogs(BaseModel):
    """Job execution logs"""
    job_id: str = Field(description="Job identifier")
    logs: List[str] = Field(description="Log lines")
    timestamp: datetime = Field(description="Logs retrieved timestamp")


class BatchJobResponse(BaseModel):
    """Response when submitting batch jobs"""
    batch_id: str = Field(description="Batch identifier")
    job_ids: List[str] = Field(description="Individual job identifiers")
    total_jobs: int = Field(description="Total number of jobs")
    successful_submissions: int = Field(description="Number of successful submissions")
    failed_submissions: int = Field(description="Number of failed submissions")
    created_at: datetime = Field(description="Batch creation timestamp")


class TranscribeUrlRequest(BaseModel):
    """Request to transcribe from URL"""
    url: str = Field(description="URL of audio file to transcribe")
    options: Optional[TranscriptionOptions] = Field(None, description="Transcription options")


class ProviderInfo(BaseModel):
    """Information about a provider"""
    id: str = Field(description="Provider identifier")
    name: str = Field(description="Provider name")
    description: str = Field(description="Provider description")
    enabled: bool = Field(description="Whether provider is enabled")
    available: bool = Field(description="Whether provider is available")
    supported_formats: List[str] = Field(description="Supported file formats")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="Provider configuration")


class Error(BaseModel):
    """Error response model"""
    error: str = Field(description="Error message")
    code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(description="Error timestamp")