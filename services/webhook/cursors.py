"""
Cursor management for webhook processing
"""

import json
from typing import Dict, Optional
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..core.interfaces import StorageProvider
from ..core.exceptions import ServiceException
from ..core.logging import get_logger

logger = get_logger(__name__)

# Thread pool for blocking operations
executor = ThreadPoolExecutor(max_workers=2)


class CursorManager:
    """
    Manages cursors for tracking changes in external services
    """
    
    def __init__(
        self,
        storage_provider: StorageProvider,
        cursor_file_path: str = "webhook_cursors.json"
    ):
        """
        Initialize cursor manager
        
        Args:
            storage_provider: Storage provider for persisting cursors
            cursor_file_path: Path to cursor storage file
        """
        self.storage = storage_provider
        self.cursor_file_path = cursor_file_path
        self._cursors_cache: Optional[Dict[str, str]] = None
        
        logger.info(f"Initialized CursorManager with storage: {type(storage_provider).__name__}")
    
    async def get_cursor(self, path: str) -> Optional[str]:
        """
        Get cursor for a specific path
        
        Args:
            path: Path to get cursor for
            
        Returns:
            Cursor string or None if not found
        """
        try:
            cursors = await self._load_cursors()
            cursor = cursors.get(path)
            
            if cursor:
                logger.debug(f"Retrieved cursor for {path}: {cursor[:20]}...")
            else:
                logger.debug(f"No cursor found for {path}")
                
            return cursor
            
        except Exception as e:
            logger.error(f"Error getting cursor for {path}: {str(e)}")
            return None
    
    async def set_cursor(self, path: str, cursor: str):
        """
        Set cursor for a specific path
        
        Args:
            path: Path to set cursor for
            cursor: Cursor string to store
        """
        try:
            cursors = await self._load_cursors()
            cursors[path] = cursor
            cursors['_last_updated'] = datetime.now().isoformat()
            
            await self._save_cursors(cursors)
            
            logger.debug(f"Set cursor for {path}: {cursor[:20]}...")
            
        except Exception as e:
            logger.error(f"Error setting cursor for {path}: {str(e)}")
            raise ServiceException(f"Failed to set cursor: {str(e)}")
    
    async def update_cursors(self, cursor_updates: Dict[str, str]):
        """
        Update multiple cursors atomically
        
        Args:
            cursor_updates: Dictionary of path -> cursor mappings
        """
        try:
            cursors = await self._load_cursors()
            cursors.update(cursor_updates)
            cursors['_last_updated'] = datetime.now().isoformat()
            
            await self._save_cursors(cursors)
            
            logger.info(f"Updated {len(cursor_updates)} cursors")
            
        except Exception as e:
            logger.error(f"Error updating cursors: {str(e)}")
            raise ServiceException(f"Failed to update cursors: {str(e)}")
    
    async def list_cursors(self) -> Dict[str, str]:
        """
        List all stored cursors
        
        Returns:
            Dictionary of path -> cursor mappings
        """
        try:
            cursors = await self._load_cursors()
            # Filter out metadata
            return {k: v for k, v in cursors.items() if not k.startswith('_')}
            
        except Exception as e:
            logger.error(f"Error listing cursors: {str(e)}")
            return {}
    
    async def delete_cursor(self, path: str) -> bool:
        """
        Delete cursor for a specific path
        
        Args:
            path: Path to delete cursor for
            
        Returns:
            True if cursor was deleted
        """
        try:
            cursors = await self._load_cursors()
            
            if path in cursors:
                del cursors[path]
                cursors['_last_updated'] = datetime.now().isoformat()
                await self._save_cursors(cursors)
                
                logger.info(f"Deleted cursor for {path}")
                return True
            else:
                logger.debug(f"No cursor to delete for {path}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting cursor for {path}: {str(e)}")
            return False
    
    async def reset_all_cursors(self):
        """
        Reset all cursors (delete all stored cursors)
        """
        try:
            empty_cursors = {
                '_reset_at': datetime.now().isoformat()
            }
            await self._save_cursors(empty_cursors)
            
            # Clear cache
            self._cursors_cache = None
            
            logger.warning("All cursors have been reset")
            
        except Exception as e:
            logger.error(f"Error resetting cursors: {str(e)}")
            raise ServiceException(f"Failed to reset cursors: {str(e)}")
    
    async def get_cursor_info(self) -> Dict[str, any]:
        """
        Get information about cursor storage
        
        Returns:
            Dictionary with cursor information
        """
        try:
            cursors = await self._load_cursors()
            
            # Filter out metadata for counting
            cursor_count = sum(1 for k in cursors.keys() if not k.startswith('_'))
            
            return {
                "cursor_count": cursor_count,
                "paths": [k for k in cursors.keys() if not k.startswith('_')],
                "last_updated": cursors.get('_last_updated'),
                "reset_at": cursors.get('_reset_at'),
                "storage_provider": type(self.storage).__name__,
                "cursor_file": self.cursor_file_path
            }
            
        except Exception as e:
            logger.error(f"Error getting cursor info: {str(e)}")
            return {
                "error": str(e),
                "storage_provider": type(self.storage).__name__,
                "cursor_file": self.cursor_file_path
            }
    
    async def _load_cursors(self) -> Dict[str, str]:
        """
        Load cursors from storage
        
        Returns:
            Dictionary of cursors
        """
        # Use cache if available
        if self._cursors_cache is not None:
            return self._cursors_cache.copy()
        
        def _load():
            try:
                # Check if cursor file exists
                if not asyncio.run(self.storage.exists(self.cursor_file_path)):
                    logger.debug("No existing cursor file found")
                    return {}
                
                # Download cursor file to temporary location
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp_file:
                    temp_path = temp_file.name
                
                # Download the file
                result = asyncio.run(self.storage.download(self.cursor_file_path, temp_path))
                
                if not result.success:
                    logger.warning(f"Failed to download cursor file: {result.error}")
                    return {}
                
                # Read and parse JSON
                with open(temp_path, 'r') as f:
                    cursors = json.load(f)
                
                # Clean up temp file
                import os
                os.unlink(temp_path)
                
                logger.debug(f"Loaded {len(cursors)} cursors from storage")
                return cursors
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in cursor file: {e}")
                return {}
            except Exception as e:
                logger.error(f"Error loading cursors: {str(e)}")
                return {}
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        cursors = await loop.run_in_executor(executor, _load)
        
        # Cache the result
        self._cursors_cache = cursors.copy()
        return cursors
    
    async def _save_cursors(self, cursors: Dict[str, str]):
        """
        Save cursors to storage
        
        Args:
            cursors: Dictionary of cursors to save
        """
        def _save():
            try:
                # Create temporary file with cursor data
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                    json.dump(cursors, temp_file, indent=2)
                    temp_path = temp_file.name
                
                # Upload to storage
                result = asyncio.run(self.storage.upload(temp_path, self.cursor_file_path))
                
                # Clean up temp file
                import os
                os.unlink(temp_path)
                
                if not result.success:
                    raise ServiceException(f"Failed to upload cursor file: {result.error}")
                
                logger.debug(f"Saved {len(cursors)} cursors to storage")
                
            except Exception as e:
                logger.error(f"Error saving cursors: {str(e)}")
                raise
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(executor, _save)
        
        # Update cache
        self._cursors_cache = cursors.copy()