"""
Dropbox webhook handler
"""

import os
import hmac
import hashlib
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ...core.exceptions import ServiceException, AuthenticationException
from ...core.logging import get_logger
from ..cursors import CursorManager
from ..tracking import JobTracker

logger = get_logger(__name__)

# Thread pool for blocking Dropbox API calls
executor = ThreadPoolExecutor(max_workers=2)


class DropboxWebhookHandler:
    """
    Handler for Dropbox webhook notifications
    """
    
    def __init__(
        self,
        cursor_manager: CursorManager,
        job_tracker: JobTracker,
        supported_formats: Optional[Set[str]] = None,
        raw_folder: Optional[str] = None
    ):
        """
        Initialize Dropbox webhook handler
        
        Args:
            cursor_manager: Manager for Dropbox cursors
            job_tracker: Tracker for processed jobs
            supported_formats: Set of supported file extensions
            raw_folder: Dropbox folder to monitor
        """
        self.cursor_manager = cursor_manager
        self.job_tracker = job_tracker
        self.supported_formats = supported_formats or {
            '.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm',
            '.aac', '.oga', '.ogg', '.flac', '.mov', '.avi', '.mkv',
            '.wmv', '.flv', '.3gp'
        }
        self.raw_folder = raw_folder or os.environ.get('DROPBOX_RAW_FOLDER', '/transcripts/raw')
        
        # Initialize Dropbox client
        self._dropbox_client = None
        self._initialize_dropbox()
        
        logger.info(f"Initialized DropboxWebhookHandler for folder: {self.raw_folder}")
    
    def _initialize_dropbox(self):
        """Initialize Dropbox client"""
        try:
            import dropbox
            
            refresh_token = os.environ.get('DROPBOX_REFRESH_TOKEN', '').strip()
            app_key = os.environ.get('DROPBOX_APP_KEY', '').strip()
            app_secret = os.environ.get('DROPBOX_APP_SECRET', '').strip()
            
            if refresh_token and app_key and app_secret:
                logger.info("Initializing Dropbox client with refresh token")
                self._dropbox_client = dropbox.Dropbox(
                    app_key=app_key,
                    app_secret=app_secret,
                    oauth2_refresh_token=refresh_token
                )
            else:
                logger.info("Fallback to access token for Dropbox client")
                access_token = os.environ.get('DROPBOX_ACCESS_TOKEN', '').strip()
                if not access_token:
                    raise AuthenticationException(
                        "DROPBOX_ACCESS_TOKEN or refresh token setup required"
                    )
                self._dropbox_client = dropbox.Dropbox(access_token)
            
            logger.info("Dropbox client initialized successfully")
            
        except ImportError:
            raise ServiceException(
                "Dropbox library not installed. Run: pip install dropbox"
            )
        except Exception as e:
            raise AuthenticationException(f"Failed to initialize Dropbox client: {str(e)}")
    
    def verify_webhook_signature(self, signature: str, body: bytes) -> bool:
        """
        Verify Dropbox webhook signature
        
        Args:
            signature: X-Dropbox-Signature header value
            body: Raw request body bytes
            
        Returns:
            True if signature is valid
        """
        try:
            app_secret = os.environ.get('DROPBOX_APP_SECRET')
            if not app_secret:
                logger.error("Missing DROPBOX_APP_SECRET environment variable")
                return False
            
            expected_signature = hmac.new(
                app_secret.encode('utf-8'),
                body,
                hashlib.sha256
            ).hexdigest()
            
            is_valid = hmac.compare_digest(signature, expected_signature)
            
            if not is_valid:
                logger.warning("Invalid Dropbox webhook signature")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {str(e)}")
            return False
    
    async def get_changed_files(self, webhook_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get files that have changed based on webhook notification
        
        Args:
            webhook_data: Dropbox webhook payload
            
        Returns:
            List of changed file information
        """
        try:
            # Validate webhook data structure
            if not webhook_data or 'list_folder' not in webhook_data:
                logger.warning("Invalid Dropbox webhook payload structure")
                return []
            
            accounts = webhook_data.get('list_folder', {}).get('accounts', [])
            if not accounts:
                logger.info("No accounts in webhook notification")
                return []
            
            logger.info(f"Processing Dropbox notification for {len(accounts)} account(s)")
            
            # Get changed files using cursor API
            changed_files = await self._get_changed_files_with_cursor()
            
            logger.info(f"Found {len(changed_files)} changed files")
            return changed_files
            
        except Exception as e:
            logger.error(f"Error getting changed files: {str(e)}")
            return []
    
    async def _get_changed_files_with_cursor(self) -> List[Dict[str, Any]]:
        """
        Get changed files using Dropbox cursor API
        
        Returns:
            List of changed file information
        """
        def _get_changes():
            try:
                import dropbox
                
                # Get or initialize cursor
                cursor = asyncio.run(self.cursor_manager.get_cursor(self.raw_folder))
                
                if cursor is None:
                    # First time - get initial cursor
                    logger.info("Getting initial cursor for raw folder")
                    result = self._dropbox_client.files_list_folder(self.raw_folder)
                    cursor = result.cursor
                    
                    # Save cursor for next time
                    asyncio.run(self.cursor_manager.set_cursor(self.raw_folder, cursor))
                    
                    # On first run, don't process existing files to prevent flood
                    logger.info("Initial cursor set - skipping existing files")
                    return []
                
                # Get changes since last cursor
                logger.info("Checking for changes since last cursor")
                try:
                    result = self._dropbox_client.files_list_folder_continue(cursor)
                except dropbox.exceptions.ApiError as e:
                    if 'reset' in str(e).lower():
                        logger.warning("Cursor expired, getting fresh cursor")
                        result = self._dropbox_client.files_list_folder(self.raw_folder)
                        # Save new cursor and skip processing on reset
                        asyncio.run(self.cursor_manager.set_cursor(self.raw_folder, result.cursor))
                        return []
                    else:
                        raise
                
                # Update cursor for next time
                asyncio.run(self.cursor_manager.set_cursor(self.raw_folder, result.cursor))
                
                # Process changes
                changed_files = []
                for entry in result.entries:
                    logger.debug(f"Change detected: {getattr(entry, 'name', 'NO_NAME')} "
                                f"(type: {type(entry).__name__})")
                    
                    # Skip deleted files
                    if isinstance(entry, dropbox.files.DeletedMetadata):
                        logger.debug("Skipping deleted file")
                        continue
                    
                    # Only process files in our raw folder
                    if not hasattr(entry, 'path_display') or not entry.path_display.startswith(self.raw_folder):
                        logger.debug("Skipping file outside raw folder")
                        continue
                    
                    file_name = entry.name
                    file_extension = os.path.splitext(file_name)[1].lower()
                    
                    # Check if it's a supported format
                    if file_extension in self.supported_formats:
                        logger.info(f"New supported file: {file_name}")
                        file_info = {
                            'name': file_name,
                            'path': entry.path_display,
                            'size': getattr(entry, 'size', 0),
                            'modified': getattr(entry, 'client_modified', datetime.now()).isoformat()
                        }
                        changed_files.append(file_info)
                    else:
                        logger.debug(f"Skipping unsupported format: {file_extension}")
                
                return changed_files
                
            except Exception as e:
                logger.error(f"Error getting changed files with cursor: {str(e)}")
                # Fallback to full scan on error
                return self._fallback_get_audio_files()
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, _get_changes)
    
    def _fallback_get_audio_files(self) -> List[Dict[str, Any]]:
        """
        Fallback method - scan all files (use only on error)
        
        Returns:
            List of audio/video files
        """
        try:
            logger.warning("Using fallback method - scanning all files")
            result = self._dropbox_client.files_list_folder(self.raw_folder)
            files = result.entries
            
            audio_files = []
            for file_entry in files:
                if not hasattr(file_entry, 'path_display'):
                    continue
                
                file_name = file_entry.name
                file_extension = os.path.splitext(file_name)[1].lower()
                
                if file_extension in self.supported_formats:
                    file_info = {
                        'name': file_name,
                        'path': file_entry.path_display,
                        'size': getattr(file_entry, 'size', 0),
                        'modified': getattr(file_entry, 'client_modified', datetime.now()).isoformat()
                    }
                    audio_files.append(file_info)
            
            logger.info(f"Fallback scan found {len(audio_files)} supported files")
            return audio_files
            
        except Exception as e:
            logger.error(f"Error in fallback method: {str(e)}")
            return []
    
    async def reset_cursors(self):
        """
        Reset Dropbox cursors (force fresh scan on next webhook)
        """
        try:
            await self.cursor_manager.delete_cursor(self.raw_folder)
            logger.info("Dropbox cursors have been reset")
            
        except Exception as e:
            logger.error(f"Error resetting Dropbox cursors: {str(e)}")
            raise ServiceException(f"Failed to reset cursors: {str(e)}")
    
    def get_handler_info(self) -> Dict[str, Any]:
        """
        Get information about this webhook handler
        
        Returns:
            Dictionary with handler information
        """
        return {
            "handler_type": "dropbox",
            "raw_folder": self.raw_folder,
            "supported_formats": list(self.supported_formats),
            "dropbox_client": self._dropbox_client is not None
        }