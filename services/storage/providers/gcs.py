"""
Google Cloud Storage implementation of StorageProvider
"""

import os
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import logging

from ...core.interfaces import StorageProvider
from ...core.models import FileInfo, DownloadResult, UploadResult, BatchResult
from ...core.exceptions import StorageException, AuthenticationException
from ...core.logging import get_logger

logger = get_logger(__name__)

# Thread pool for blocking GCS API calls
executor = ThreadPoolExecutor(max_workers=3)


class GCSStorageProvider(StorageProvider):
    """
    Google Cloud Storage implementation of storage provider
    """
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        bucket_name: Optional[str] = None,
        credentials_path: Optional[str] = None
    ):
        """
        Initialize GCS storage provider
        
        Args:
            project_id: GCP project ID
            bucket_name: GCS bucket name
            credentials_path: Path to service account JSON file
        """
        self.project_id = project_id or os.environ.get('PROJECT_ID')
        self.bucket_name = bucket_name or os.environ.get('GCS_BUCKET')
        self.credentials_path = credentials_path or os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        
        if not self.bucket_name:
            raise StorageException("GCS_BUCKET is required for GCS storage")
        
        # Initialize GCS client
        self._initialize_client()
        
        logger.info(f"Initialized GCSStorageProvider: {self.project_id}/{self.bucket_name}")
    
    def _initialize_client(self):
        """Initialize Google Cloud Storage client"""
        try:
            from google.cloud import storage
            
            if self.credentials_path and os.path.exists(self.credentials_path):
                self.client = storage.Client.from_service_account_json(self.credentials_path)
            else:
                # Use default credentials (ADC)
                self.client = storage.Client(project=self.project_id)
            
            self.bucket = self.client.bucket(self.bucket_name)
            logger.info("GCS client initialized successfully")
            
        except ImportError:
            raise StorageException(
                "Google Cloud Storage library not installed. Run: pip install google-cloud-storage"
            )
        except Exception as e:
            raise AuthenticationException(f"Failed to initialize GCS client: {str(e)}")
    
    def _run_sync(self, coro):
        """Run async coroutine in thread pool"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    async def download(self, source_path: str, destination_path: str) -> DownloadResult:
        """
        Download file from GCS
        
        Args:
            source_path: GCS object path
            destination_path: Local file path
            
        Returns:
            DownloadResult with metadata
        """
        def _download():
            try:
                # Ensure destination directory exists
                os.makedirs(os.path.dirname(destination_path), exist_ok=True)
                
                # Get blob
                blob = self.bucket.blob(source_path)
                
                # Check if blob exists
                if not blob.exists():
                    raise StorageException(f"File not found in GCS: {source_path}")
                
                # Download file
                start_time = datetime.now()
                blob.download_to_filename(destination_path)
                download_time = (datetime.now() - start_time).total_seconds()
                
                # Get file info
                file_size = os.path.getsize(destination_path)
                
                logger.info(f"Downloaded from GCS: {source_path} -> {destination_path} ({file_size} bytes)")
                
                return DownloadResult(
                    success=True,
                    file_path=destination_path,
                    file_size=file_size,
                    download_time_seconds=download_time,
                    metadata={
                        "source_path": source_path,
                        "bucket": self.bucket_name,
                        "content_type": blob.content_type,
                        "etag": blob.etag,
                        "generation": blob.generation
                    }
                )
                
            except Exception as e:
                error_msg = f"GCS download failed: {str(e)}"
                logger.error(error_msg)
                return DownloadResult(
                    success=False,
                    error=error_msg,
                    metadata={"source_path": source_path}
                )
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, _download)
    
    async def upload(self, source_path: str, destination_path: str) -> UploadResult:
        """
        Upload file to GCS
        
        Args:
            source_path: Local file path
            destination_path: GCS object path
            
        Returns:
            UploadResult with metadata
        """
        def _upload():
            try:
                if not os.path.exists(source_path):
                    raise StorageException(f"Source file not found: {source_path}")
                
                # Get blob
                blob = self.bucket.blob(destination_path)
                
                # Upload file
                start_time = datetime.now()
                blob.upload_from_filename(source_path)
                upload_time = (datetime.now() - start_time).total_seconds()
                
                # Get file info
                file_size = os.path.getsize(source_path)
                
                logger.info(f"Uploaded to GCS: {source_path} -> {destination_path} ({file_size} bytes)")
                
                return UploadResult(
                    success=True,
                    file_path=destination_path,
                    file_size=file_size,
                    upload_time_seconds=upload_time,
                    metadata={
                        "source_path": source_path,
                        "bucket": self.bucket_name,
                        "content_type": blob.content_type,
                        "etag": blob.etag,
                        "generation": blob.generation
                    }
                )
                
            except Exception as e:
                error_msg = f"GCS upload failed: {str(e)}"
                logger.error(error_msg)
                return UploadResult(
                    success=False,
                    error=error_msg,
                    metadata={"source_path": source_path}
                )
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, _upload)
    
    async def list_files(
        self,
        prefix: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[FileInfo]:
        """
        List files in GCS bucket
        
        Args:
            prefix: Object prefix to filter by
            limit: Maximum number of files to return
            
        Returns:
            List of FileInfo objects
        """
        def _list():
            try:
                blobs = self.bucket.list_blobs(prefix=prefix, max_results=limit)
                
                file_infos = []
                for blob in blobs:
                    file_info = FileInfo(
                        name=blob.name,
                        path=f"gs://{self.bucket_name}/{blob.name}",
                        size=blob.size or 0,
                        modified_at=blob.time_created,
                        metadata={
                            "bucket": self.bucket_name,
                            "content_type": blob.content_type,
                            "etag": blob.etag,
                            "generation": blob.generation,
                            "storage_class": blob.storage_class
                        }
                    )
                    file_infos.append(file_info)
                
                logger.info(f"Listed {len(file_infos)} files from GCS bucket: {self.bucket_name}")
                return file_infos
                
            except Exception as e:
                logger.error(f"GCS file listing failed: {str(e)}")
                raise StorageException(f"Failed to list files: {str(e)}")
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, _list)
    
    async def delete(self, file_path: str) -> bool:
        """
        Delete file from GCS
        
        Args:
            file_path: GCS object path
            
        Returns:
            True if deleted successfully
        """
        def _delete():
            try:
                blob = self.bucket.blob(file_path)
                
                if not blob.exists():
                    logger.warning(f"File not found for deletion: {file_path}")
                    return False
                
                blob.delete()
                logger.info(f"Deleted from GCS: {file_path}")
                return True
                
            except Exception as e:
                logger.error(f"GCS deletion failed for {file_path}: {str(e)}")
                return False
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, _delete)
    
    async def exists(self, file_path: str) -> bool:
        """
        Check if file exists in GCS
        
        Args:
            file_path: GCS object path
            
        Returns:
            True if file exists
        """
        def _exists():
            try:
                blob = self.bucket.blob(file_path)
                return blob.exists()
            except Exception as e:
                logger.error(f"GCS existence check failed for {file_path}: {str(e)}")
                return False
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, _exists)
    
    async def get_file_info(self, file_path: str) -> Optional[FileInfo]:
        """
        Get detailed information about a file
        
        Args:
            file_path: GCS object path
            
        Returns:
            FileInfo object or None if not found
        """
        def _get_info():
            try:
                blob = self.bucket.blob(file_path)
                
                if not blob.exists():
                    return None
                
                # Reload to get all metadata
                blob.reload()
                
                return FileInfo(
                    name=blob.name,
                    path=f"gs://{self.bucket_name}/{blob.name}",
                    size=blob.size or 0,
                    modified_at=blob.time_created,
                    metadata={
                        "bucket": self.bucket_name,
                        "content_type": blob.content_type,
                        "etag": blob.etag,
                        "generation": blob.generation,
                        "storage_class": blob.storage_class,
                        "cache_control": blob.cache_control,
                        "content_disposition": blob.content_disposition,
                        "content_encoding": blob.content_encoding,
                        "content_language": blob.content_language,
                        "custom_metadata": dict(blob.metadata) if blob.metadata else {}
                    }
                )
                
            except Exception as e:
                logger.error(f"GCS file info failed for {file_path}: {str(e)}")
                return None
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, _get_info)
    
    async def download_batch(
        self,
        file_paths: List[str],
        destination_dir: str,
        max_concurrent: int = 5
    ) -> BatchResult:
        """
        Download multiple files concurrently
        
        Args:
            file_paths: List of GCS object paths
            destination_dir: Local directory for downloads
            max_concurrent: Maximum concurrent downloads
            
        Returns:
            BatchResult with individual results
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def download_single(file_path: str):
            async with semaphore:
                dest_path = os.path.join(destination_dir, os.path.basename(file_path))
                return await self.download(file_path, dest_path)
        
        # Execute downloads concurrently
        tasks = [download_single(fp) for fp in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful = []
        failed = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed.append({
                    "file_path": file_paths[i],
                    "error": str(result)
                })
            elif result.success:
                successful.append(result)
            else:
                failed.append({
                    "file_path": file_paths[i],
                    "error": result.error
                })
        
        logger.info(f"GCS batch download: {len(successful)} successful, {len(failed)} failed")
        
        return BatchResult(
            successful=successful,
            failed=failed,
            total_processed=len(file_paths)
        )