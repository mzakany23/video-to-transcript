"""
Job tracking for webhook processing
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..core.interfaces import StorageProvider
from ..core.exceptions import ServiceException
from ..core.logging import get_logger

logger = get_logger(__name__)

# Thread pool for blocking operations
executor = ThreadPoolExecutor(max_workers=2)


class JobTracker:
    """
    Tracks processed jobs to prevent duplicate processing
    """
    
    def __init__(
        self,
        storage_provider: StorageProvider,
        tracking_file_path: str = "processed_jobs.json"
    ):
        """
        Initialize job tracker
        
        Args:
            storage_provider: Storage provider for persisting job data
            tracking_file_path: Path to job tracking file
        """
        self.storage = storage_provider
        self.tracking_file_path = tracking_file_path
        self._jobs_cache: Optional[Dict[str, Dict[str, Any]]] = None
        
        logger.info(f"Initialized JobTracker with storage: {type(storage_provider).__name__}")
    
    async def is_processed(self, file_id: str) -> bool:
        """
        Check if a file has been processed
        
        Args:
            file_id: Unique identifier for the file
            
        Returns:
            True if file has been processed
        """
        try:
            jobs = await self._load_jobs()
            is_processed = file_id in jobs
            
            logger.debug(f"File {file_id} processed status: {is_processed}")
            return is_processed
            
        except Exception as e:
            logger.error(f"Error checking if {file_id} is processed: {str(e)}")
            return False
    
    async def mark_processed(
        self,
        file_id: str,
        job_id: Optional[str] = None,
        file_info: Optional[Dict[str, Any]] = None
    ):
        """
        Mark a file as processed
        
        Args:
            file_id: Unique identifier for the file
            job_id: Job ID that processed this file
            file_info: Additional file information
        """
        try:
            jobs = await self._load_jobs()
            
            job_record = {
                "processed_at": datetime.now().isoformat(),
                "job_id": job_id,
                "file_info": file_info or {}
            }
            
            jobs[file_id] = job_record
            await self._save_jobs(jobs)
            
            logger.info(f"Marked file {file_id} as processed (job: {job_id})")
            
        except Exception as e:
            logger.error(f"Error marking {file_id} as processed: {str(e)}")
            raise ServiceException(f"Failed to mark file as processed: {str(e)}")
    
    async def get_job_record(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job record for a file
        
        Args:
            file_id: Unique identifier for the file
            
        Returns:
            Job record dictionary or None if not found
        """
        try:
            jobs = await self._load_jobs()
            return jobs.get(file_id)
            
        except Exception as e:
            logger.error(f"Error getting job record for {file_id}: {str(e)}")
            return None
    
    async def list_processed_files(
        self,
        limit: Optional[int] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        List processed files
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            Dictionary of file_id -> job_record
        """
        try:
            jobs = await self._load_jobs()
            
            # Sort by processed_at timestamp (most recent first)
            sorted_items = sorted(
                jobs.items(),
                key=lambda x: x[1].get('processed_at', ''),
                reverse=True
            )
            
            if limit:
                sorted_items = sorted_items[:limit]
            
            return dict(sorted_items)
            
        except Exception as e:
            logger.error(f"Error listing processed files: {str(e)}")
            return {}
    
    async def get_processed_count(self) -> int:
        """
        Get count of processed files
        
        Returns:
            Number of processed files
        """
        try:
            jobs = await self._load_jobs()
            count = len(jobs)
            
            logger.debug(f"Total processed files: {count}")
            return count
            
        except Exception as e:
            logger.error(f"Error getting processed count: {str(e)}")
            return 0
    
    async def remove_processed_record(self, file_id: str) -> bool:
        """
        Remove a processed file record
        
        Args:
            file_id: Unique identifier for the file
            
        Returns:
            True if record was removed
        """
        try:
            jobs = await self._load_jobs()
            
            if file_id in jobs:
                del jobs[file_id]
                await self._save_jobs(jobs)
                
                logger.info(f"Removed processed record for {file_id}")
                return True
            else:
                logger.debug(f"No processed record to remove for {file_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error removing processed record for {file_id}: {str(e)}")
            return False
    
    async def reset_tracking(self):
        """
        Reset all job tracking (remove all processed records)
        """
        try:
            empty_jobs = {
                '_reset_at': datetime.now().isoformat()
            }
            await self._save_jobs(empty_jobs)
            
            # Clear cache
            self._jobs_cache = None
            
            logger.warning("All job tracking has been reset")
            
        except Exception as e:
            logger.error(f"Error resetting job tracking: {str(e)}")
            raise ServiceException(f"Failed to reset job tracking: {str(e)}")
    
    async def cleanup_old_records(self, days_old: int = 30):
        """
        Clean up old processed records
        
        Args:
            days_old: Remove records older than this many days
        """
        try:
            from datetime import timedelta
            
            jobs = await self._load_jobs()
            cutoff_date = datetime.now() - timedelta(days=days_old)
            cutoff_iso = cutoff_date.isoformat()
            
            # Filter out old records
            cleaned_jobs = {}
            removed_count = 0
            
            for file_id, job_record in jobs.items():
                if file_id.startswith('_'):
                    # Keep metadata
                    cleaned_jobs[file_id] = job_record
                    continue
                
                processed_at = job_record.get('processed_at', '')
                if processed_at >= cutoff_iso:
                    cleaned_jobs[file_id] = job_record
                else:
                    removed_count += 1
            
            if removed_count > 0:
                cleaned_jobs['_last_cleanup'] = datetime.now().isoformat()
                await self._save_jobs(cleaned_jobs)
                
                logger.info(f"Cleaned up {removed_count} old job records (older than {days_old} days)")
            else:
                logger.debug(f"No old records to clean up")
            
        except Exception as e:
            logger.error(f"Error cleaning up old records: {str(e)}")
            raise ServiceException(f"Failed to cleanup old records: {str(e)}")
    
    async def get_tracking_info(self) -> Dict[str, Any]:
        """
        Get information about job tracking
        
        Returns:
            Dictionary with tracking information
        """
        try:
            jobs = await self._load_jobs()
            
            # Filter out metadata for counting
            job_count = sum(1 for k in jobs.keys() if not k.startswith('_'))
            
            return {
                "processed_count": job_count,
                "last_cleanup": jobs.get('_last_cleanup'),
                "reset_at": jobs.get('_reset_at'),
                "storage_provider": type(self.storage).__name__,
                "tracking_file": self.tracking_file_path
            }
            
        except Exception as e:
            logger.error(f"Error getting tracking info: {str(e)}")
            return {
                "error": str(e),
                "storage_provider": type(self.storage).__name__,
                "tracking_file": self.tracking_file_path
            }
    
    async def _load_jobs(self) -> Dict[str, Dict[str, Any]]:
        """
        Load job records from storage
        
        Returns:
            Dictionary of job records
        """
        # Use cache if available
        if self._jobs_cache is not None:
            return self._jobs_cache.copy()
        
        def _load():
            try:
                # Check if tracking file exists
                if not asyncio.run(self.storage.exists(self.tracking_file_path)):
                    logger.debug("No existing job tracking file found")
                    return {}
                
                # Download tracking file to temporary location
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp_file:
                    temp_path = temp_file.name
                
                # Download the file
                result = asyncio.run(self.storage.download(self.tracking_file_path, temp_path))
                
                if not result.success:
                    logger.warning(f"Failed to download job tracking file: {result.error}")
                    return {}
                
                # Read and parse JSON
                with open(temp_path, 'r') as f:
                    jobs = json.load(f)
                
                # Clean up temp file
                import os
                os.unlink(temp_path)
                
                logger.debug(f"Loaded {len(jobs)} job records from storage")
                return jobs
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in job tracking file: {e}")
                return {}
            except Exception as e:
                logger.error(f"Error loading job records: {str(e)}")
                return {}
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        jobs = await loop.run_in_executor(executor, _load)
        
        # Cache the result
        self._jobs_cache = jobs.copy()
        return jobs
    
    async def _save_jobs(self, jobs: Dict[str, Dict[str, Any]]):
        """
        Save job records to storage
        
        Args:
            jobs: Dictionary of job records to save
        """
        def _save():
            try:
                # Create temporary file with job data
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                    json.dump(jobs, temp_file, indent=2)
                    temp_path = temp_file.name
                
                # Upload to storage
                result = asyncio.run(self.storage.upload(temp_path, self.tracking_file_path))
                
                # Clean up temp file
                import os
                os.unlink(temp_path)
                
                if not result.success:
                    raise ServiceException(f"Failed to upload job tracking file: {result.error}")
                
                logger.debug(f"Saved {len(jobs)} job records to storage")
                
            except Exception as e:
                logger.error(f"Error saving job records: {str(e)}")
                raise
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(executor, _save)
        
        # Update cache
        self._jobs_cache = jobs.copy()