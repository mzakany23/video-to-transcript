"""
Dropbox implementation of StorageProvider
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ...core.interfaces import StorageProvider
from ...core.models import FileInfo, DownloadResult, UploadResult
from ...core.exceptions import StorageException, AuthenticationException

logger = logging.getLogger(__name__)

# Thread pool for blocking I/O operations
executor = ThreadPoolExecutor(max_workers=5)


class DropboxStorageProvider(StorageProvider):
    """
    Dropbox implementation of storage provider
    Uses existing Dropbox client from worker implementation
    """
    
    def __init__(
        self,
        dropbox_client=None,
        raw_folder: str = "/transcripts/raw",
        processed_folder: str = "/transcripts/processed"
    ):
        """
        Initialize Dropbox storage provider
        
        Args:
            dropbox_client: Dropbox client instance (will create if None)
            raw_folder: Path to raw files folder
            processed_folder: Path to processed files folder
        """
        self.raw_folder = raw_folder
        self.processed_folder = processed_folder
        
        if dropbox_client:
            self.dbx = dropbox_client
        else:
            # Initialize from environment
            self._initialize_client()
        
        logger.info(f"Initialized DropboxStorageProvider")
        logger.info(f"Raw folder: {self.raw_folder}")
        logger.info(f"Processed folder: {self.processed_folder}")
    
    def _initialize_client(self):
        """Initialize Dropbox client from environment variables"""
        try:
            import dropbox
            
            # Try refresh token first (preferred)
            refresh_token = os.environ.get('DROPBOX_REFRESH_TOKEN', '').strip()
            app_key = os.environ.get('DROPBOX_APP_KEY', '').strip()
            app_secret = os.environ.get('DROPBOX_APP_SECRET', '').strip()
            
            if refresh_token and app_key and app_secret:
                logger.info("Initializing Dropbox with refresh token")
                self.dbx = dropbox.Dropbox(
                    app_key=app_key,
                    app_secret=app_secret,
                    oauth2_refresh_token=refresh_token
                )
            else:
                # Fall back to access token
                access_token = os.environ.get('DROPBOX_ACCESS_TOKEN', '').strip()
                if not access_token:
                    raise AuthenticationException(
                        "No Dropbox credentials found. Set DROPBOX_REFRESH_TOKEN or DROPBOX_ACCESS_TOKEN"
                    )
                logger.info("Initializing Dropbox with access token")
                self.dbx = dropbox.Dropbox(access_token)
            
            # Test connection
            account = self.dbx.users_get_current_account()
            logger.info(f"Connected to Dropbox as: {account.name.display_name}")
            
        except Exception as e:
            raise AuthenticationException(f"Failed to initialize Dropbox client: {str(e)}")
    
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
        Download file from Dropbox
        
        Args:
            source_path: Path in Dropbox
            destination_path: Local filesystem path
            
        Returns:
            DownloadResult
        """
        def _download():
            try:
                # Ensure source path starts with /
                if not source_path.startswith('/'):
                    full_path = f"/{source_path}"
                else:
                    full_path = source_path
                
                # Download from Dropbox
                metadata, response = self.dbx.files_download(full_path)
                
                # Write to local file
                Path(destination_path).parent.mkdir(parents=True, exist_ok=True)
                with open(destination_path, 'wb') as f:
                    f.write(response.content)
                
                file_size = len(response.content)
                logger.info(f"Downloaded {full_path} ({file_size} bytes) to {destination_path}")
                
                return DownloadResult(
                    success=True,
                    local_path=destination_path,
                    size=file_size,
                    metadata={
                        "dropbox_id": metadata.id,
                        "rev": metadata.rev,
                        "modified": metadata.server_modified.isoformat()
                    }
                )
                
            except Exception as e:
                logger.error(f"Download failed for {source_path}: {str(e)}")
                return DownloadResult(
                    success=False,
                    error=str(e)
                )
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, _download)
    
    async def upload(
        self,
        source_path: str,
        destination_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UploadResult:
        """
        Upload file to Dropbox
        
        Args:
            source_path: Local filesystem path
            destination_path: Path in Dropbox
            metadata: Optional metadata
            
        Returns:
            UploadResult
        """
        def _upload():
            try:
                import dropbox
                
                # Ensure destination path starts with /
                if not destination_path.startswith('/'):
                    full_path = f"/{destination_path}"
                else:
                    full_path = destination_path
                
                # Read local file
                with open(source_path, 'rb') as f:
                    data = f.read()
                
                file_size = len(data)
                
                # Upload to Dropbox
                result = self.dbx.files_upload(
                    data,
                    full_path,
                    mode=dropbox.files.WriteMode.overwrite
                )
                
                logger.info(f"Uploaded {source_path} ({file_size} bytes) to {full_path}")
                
                return UploadResult(
                    success=True,
                    storage_path=full_path,
                    size=file_size,
                    metadata={
                        "dropbox_id": result.id,
                        "rev": result.rev,
                        "modified": result.server_modified.isoformat()
                    }
                )
                
            except Exception as e:
                logger.error(f"Upload failed for {source_path}: {str(e)}")
                return UploadResult(
                    success=False,
                    error=str(e)
                )
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, _upload)
    
    async def list_files(
        self,
        path: str,
        pattern: str = "*",
        recursive: bool = False
    ) -> List[FileInfo]:
        """
        List files in Dropbox folder
        
        Args:
            path: Dropbox folder path
            pattern: File pattern (glob-style)
            recursive: Whether to list recursively
            
        Returns:
            List of FileInfo objects
        """
        def _list():
            try:
                import fnmatch
                
                # Ensure path starts with /
                if not path.startswith('/'):
                    full_path = f"/{path}"
                else:
                    full_path = path
                
                files = []
                result = self.dbx.files_list_folder(full_path, recursive=recursive)
                
                while True:
                    for entry in result.entries:
                        # Skip folders unless listing recursively
                        if hasattr(entry, 'is_deleted') and entry.is_deleted:
                            continue
                        
                        if not hasattr(entry, 'size'):  # It's a folder
                            continue
                        
                        # Check pattern match
                        if pattern != "*" and not fnmatch.fnmatch(entry.name, pattern):
                            continue
                        
                        files.append(FileInfo(
                            path=entry.path_display,
                            name=entry.name,
                            size=entry.size,
                            modified=entry.server_modified,
                            metadata={
                                "dropbox_id": entry.id,
                                "rev": entry.rev
                            }
                        ))
                    
                    if not result.has_more:
                        break
                    
                    result = self.dbx.files_list_folder_continue(result.cursor)
                
                logger.info(f"Listed {len(files)} files in {full_path}")
                return files
                
            except Exception as e:
                logger.error(f"List files failed for {path}: {str(e)}")
                raise StorageException(f"Failed to list files: {str(e)}")
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, _list)
    
    async def delete(self, path: str) -> bool:
        """
        Delete file from Dropbox
        
        Args:
            path: Dropbox file path
            
        Returns:
            True if successful
        """
        def _delete():
            try:
                # Ensure path starts with /
                if not path.startswith('/'):
                    full_path = f"/{path}"
                else:
                    full_path = path
                
                self.dbx.files_delete_v2(full_path)
                logger.info(f"Deleted {full_path}")
                return True
                
            except Exception as e:
                logger.error(f"Delete failed for {path}: {str(e)}")
                return False
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, _delete)
    
    async def exists(self, path: str) -> bool:
        """
        Check if file exists in Dropbox
        
        Args:
            path: Dropbox file path
            
        Returns:
            True if exists
        """
        def _exists():
            try:
                # Ensure path starts with /
                if not path.startswith('/'):
                    full_path = f"/{path}"
                else:
                    full_path = path
                
                self.dbx.files_get_metadata(full_path)
                return True
                
            except Exception as e:
                # File doesn't exist or other error
                return False
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, _exists)
    
    async def create_folder(self, path: str) -> bool:
        """
        Create folder in Dropbox
        
        Args:
            path: Folder path
            
        Returns:
            True if created or already exists
        """
        def _create_folder():
            try:
                # Ensure path starts with /
                if not path.startswith('/'):
                    full_path = f"/{path}"
                else:
                    full_path = path
                
                self.dbx.files_create_folder_v2(full_path)
                logger.info(f"Created folder {full_path}")
                return True
                
            except Exception as e:
                if "conflict" in str(e).lower():
                    # Folder already exists
                    return True
                logger.error(f"Create folder failed for {path}: {str(e)}")
                return False
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, _create_folder)