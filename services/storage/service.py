"""
High-level storage service that orchestrates storage operations
"""

import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from ..core.interfaces import StorageProvider
from ..core.models import FileInfo, DownloadResult, UploadResult
from ..core.exceptions import StorageException

logger = logging.getLogger(__name__)


class StorageService:
    """
    High-level storage service that works with any storage provider
    """
    
    def __init__(self, provider: StorageProvider):
        """
        Initialize storage service with a provider
        
        Args:
            provider: Storage provider implementation
        """
        self.provider = provider
        logger.info(f"Initialized StorageService with {provider.__class__.__name__}")
    
    async def download_file(
        self,
        source_path: str,
        destination_path: Optional[str] = None
    ) -> DownloadResult:
        """
        Download a file from storage
        
        Args:
            source_path: Path in storage system
            destination_path: Local path (auto-generated if not provided)
            
        Returns:
            DownloadResult with file information
        """
        try:
            if destination_path is None:
                # Generate temp path
                import tempfile
                temp_dir = Path(tempfile.mkdtemp())
                file_name = Path(source_path).name
                destination_path = str(temp_dir / file_name)
            
            logger.info(f"Downloading {source_path} to {destination_path}")
            result = await self.provider.download(source_path, destination_path)
            
            if result.success:
                logger.info(f"Successfully downloaded {source_path}")
            else:
                logger.error(f"Failed to download {source_path}: {result.error}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error downloading {source_path}: {str(e)}")
            raise StorageException(f"Download failed: {str(e)}")
    
    async def upload_file(
        self,
        source_path: str,
        destination_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UploadResult:
        """
        Upload a file to storage
        
        Args:
            source_path: Local file path
            destination_path: Destination in storage
            metadata: Optional metadata
            
        Returns:
            UploadResult with upload information
        """
        try:
            # Verify source exists
            source = Path(source_path)
            if not source.exists():
                raise StorageException(f"Source file not found: {source_path}")
            
            logger.info(f"Uploading {source_path} to {destination_path}")
            result = await self.provider.upload(source_path, destination_path, metadata)
            
            if result.success:
                logger.info(f"Successfully uploaded to {destination_path}")
            else:
                logger.error(f"Failed to upload {source_path}: {result.error}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error uploading {source_path}: {str(e)}")
            raise StorageException(f"Upload failed: {str(e)}")
    
    async def list_files(
        self,
        path: str,
        pattern: str = "*",
        recursive: bool = False
    ) -> List[FileInfo]:
        """
        List files in storage
        
        Args:
            path: Storage path
            pattern: File pattern to match
            recursive: Whether to list recursively
            
        Returns:
            List of FileInfo objects
        """
        try:
            logger.info(f"Listing files in {path} with pattern {pattern}")
            files = await self.provider.list_files(path, pattern, recursive)
            logger.info(f"Found {len(files)} files")
            return files
            
        except Exception as e:
            logger.error(f"Error listing files in {path}: {str(e)}")
            raise StorageException(f"List files failed: {str(e)}")
    
    async def file_exists(self, path: str) -> bool:
        """
        Check if a file exists
        
        Args:
            path: Storage path
            
        Returns:
            True if exists
        """
        try:
            return await self.provider.exists(path)
        except Exception as e:
            logger.error(f"Error checking existence of {path}: {str(e)}")
            raise StorageException(f"Existence check failed: {str(e)}")
    
    async def delete_file(self, path: str) -> bool:
        """
        Delete a file from storage
        
        Args:
            path: Storage path
            
        Returns:
            True if deleted successfully
        """
        try:
            logger.info(f"Deleting {path}")
            result = await self.provider.delete(path)
            
            if result:
                logger.info(f"Successfully deleted {path}")
            else:
                logger.warning(f"Failed to delete {path}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error deleting {path}: {str(e)}")
            raise StorageException(f"Delete failed: {str(e)}")
    
    async def batch_download(
        self,
        file_paths: List[str],
        destination_dir: str
    ) -> List[DownloadResult]:
        """
        Download multiple files in parallel
        
        Args:
            file_paths: List of storage paths
            destination_dir: Local directory for downloads
            
        Returns:
            List of DownloadResult objects
        """
        dest_path = Path(destination_dir)
        dest_path.mkdir(parents=True, exist_ok=True)
        
        tasks = []
        for file_path in file_paths:
            file_name = Path(file_path).name
            dest_file = str(dest_path / file_name)
            tasks.append(self.download_file(file_path, dest_file))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to failed results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    DownloadResult(
                        success=False,
                        error=str(result)
                    )
                )
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def batch_upload(
        self,
        files: List[tuple[str, str]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[UploadResult]:
        """
        Upload multiple files in parallel
        
        Args:
            files: List of (source_path, destination_path) tuples
            metadata: Optional metadata for all files
            
        Returns:
            List of UploadResult objects
        """
        tasks = []
        for source_path, dest_path in files:
            tasks.append(self.upload_file(source_path, dest_path, metadata))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to failed results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    UploadResult(
                        success=False,
                        error=str(result)
                    )
                )
            else:
                processed_results.append(result)
        
        return processed_results