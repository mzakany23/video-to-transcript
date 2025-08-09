"""
Abstract interfaces for all service providers
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path
from .models import (
    FileInfo, 
    DownloadResult, 
    UploadResult,
    TranscriptionOptions,
    TranscriptionResult,
    JobSpec,
    JobStatus,
    JobState,
)


class StorageProvider(ABC):
    """Abstract interface for storage providers"""
    
    @abstractmethod
    async def download(self, source_path: str, destination_path: str) -> DownloadResult:
        """
        Download a file from storage to local filesystem
        
        Args:
            source_path: Path in storage system
            destination_path: Local filesystem path
            
        Returns:
            DownloadResult with success status and metadata
        """
        pass
    
    @abstractmethod
    async def upload(
        self, 
        source_path: str, 
        destination_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UploadResult:
        """
        Upload a file from local filesystem to storage
        
        Args:
            source_path: Local filesystem path
            destination_path: Path in storage system
            metadata: Optional metadata to attach
            
        Returns:
            UploadResult with success status and storage path
        """
        pass
    
    @abstractmethod
    async def list_files(
        self, 
        path: str, 
        pattern: str = "*",
        recursive: bool = False
    ) -> List[FileInfo]:
        """
        List files in storage path
        
        Args:
            path: Storage path to list
            pattern: File pattern to match (glob-style)
            recursive: Whether to list recursively
            
        Returns:
            List of FileInfo objects
        """
        pass
    
    @abstractmethod
    async def delete(self, path: str) -> bool:
        """
        Delete a file from storage
        
        Args:
            path: Storage path to delete
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def exists(self, path: str) -> bool:
        """
        Check if a file exists in storage
        
        Args:
            path: Storage path to check
            
        Returns:
            True if exists, False otherwise
        """
        pass


class TranscriptionProvider(ABC):
    """Abstract interface for transcription providers"""
    
    @abstractmethod
    async def transcribe(
        self,
        audio_path: str,
        options: Optional[TranscriptionOptions] = None
    ) -> TranscriptionResult:
        """
        Transcribe an audio file
        
        Args:
            audio_path: Path to audio file
            options: Transcription options
            
        Returns:
            TranscriptionResult with text and metadata
        """
        pass
    
    @abstractmethod
    async def get_supported_formats(self) -> List[str]:
        """
        Get list of supported audio formats
        
        Returns:
            List of file extensions (e.g., ['.mp3', '.wav'])
        """
        pass
    
    @abstractmethod
    async def get_max_file_size(self) -> int:
        """
        Get maximum supported file size in bytes
        
        Returns:
            Maximum file size in bytes
        """
        pass


class JobRunner(ABC):
    """Abstract interface for job execution"""
    
    @abstractmethod
    async def submit_job(self, spec: JobSpec) -> str:
        """
        Submit a job for execution
        
        Args:
            spec: Job specification
            
        Returns:
            Job ID for tracking
        """
        pass
    
    @abstractmethod
    async def get_status(self, job_id: str) -> JobStatus:
        """
        Get status of a running job
        
        Args:
            job_id: Job identifier
            
        Returns:
            JobStatus with current state and metadata
        """
        pass
    
    @abstractmethod
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if cancelled successfully
        """
        pass
    
    @abstractmethod
    async def list_jobs(
        self,
        state: Optional[JobState] = None,
        limit: int = 100
    ) -> List[JobStatus]:
        """
        List jobs with optional filtering
        
        Args:
            state: Filter by job state
            limit: Maximum number of jobs to return
            
        Returns:
            List of JobStatus objects
        """
        pass


class NotificationProvider(ABC):
    """Abstract interface for notification providers"""
    
    @abstractmethod
    async def send_notification(
        self,
        subject: str,
        body: str,
        recipients: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a notification
        
        Args:
            subject: Notification subject
            body: Notification body
            recipients: List of recipient identifiers
            metadata: Optional metadata
            
        Returns:
            True if sent successfully
        """
        pass
    
    @abstractmethod
    async def send_job_completion(
        self,
        job_summary: Dict[str, Any]
    ) -> bool:
        """
        Send job completion notification
        
        Args:
            job_summary: Summary of completed job
            
        Returns:
            True if sent successfully
        """
        pass
    
    @abstractmethod
    async def send_error(
        self,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send error notification
        
        Args:
            error_message: Error message
            error_details: Optional error details
            
        Returns:
            True if sent successfully
        """
        pass