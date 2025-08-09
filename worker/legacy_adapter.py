"""
Legacy adapter to bridge old code with new services
Allows gradual migration without breaking existing functionality
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add services to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.storage import StorageService, DropboxStorageProvider
from services.transcription import TranscriptionService, OpenAITranscriptionProvider
from services.core.models import FileInfo, TranscriptionOptions
from services.core.logging import configure_logging, get_logger

# Configure logging for services
configure_logging(
    level=os.environ.get('LOG_LEVEL', 'INFO'),
    format_type=os.environ.get('LOG_FORMAT', 'text'),
    service_name='transcription-worker'
)

logger = get_logger(__name__)


class LegacyTranscriptionAdapter:
    """
    Adapter that provides the same interface as TranscriptionJobProcessor
    but uses new modular services underneath
    """
    
    def __init__(self):
        """Initialize adapter with new services"""
        logger.info("Initializing LegacyTranscriptionAdapter with new services")
        
        # Get configuration from environment (same as old code)
        self.project_id = os.environ.get('PROJECT_ID')
        self.secret_name = os.environ.get('SECRET_NAME')
        
        # Initialize new services
        self._initialize_services()
        
        # Compatibility attributes for old code
        self.job_tracking_file = Path('/tmp/processed_jobs.json')
        
        logger.info("LegacyTranscriptionAdapter initialized successfully")
    
    def _initialize_services(self):
        """Initialize new modular services"""
        try:
            # Initialize storage service with Dropbox
            dropbox_provider = DropboxStorageProvider(
                raw_folder=os.environ.get('DROPBOX_RAW_FOLDER', '/transcripts/raw'),
                processed_folder=os.environ.get('DROPBOX_PROCESSED_FOLDER', '/transcripts/processed')
            )
            self.storage_service = StorageService(dropbox_provider)
            self.dropbox_provider = dropbox_provider  # Keep reference for compatibility
            
            # Initialize transcription service with OpenAI
            # Get OpenAI key from environment or secret manager
            openai_key = os.environ.get('OPENAI_API_KEY')
            if not openai_key and self.secret_name:
                openai_key = self._get_secret(self.secret_name)
            
            openai_provider = OpenAITranscriptionProvider(api_key=openai_key)
            self.transcription_service = TranscriptionService(
                transcription_provider=openai_provider,
                storage_provider=self.storage_service
            )
            
            logger.info("Services initialized: Storage (Dropbox), Transcription (OpenAI)")
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {str(e)}")
            raise
    
    def _get_secret(self, secret_name: str) -> str:
        """Get secret from Google Secret Manager (compatibility method)"""
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.error(f"Failed to get secret {secret_name}: {str(e)}")
            raise
    
    def process_file(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single file (compatibility method)
        Matches the signature of the original TranscriptionJobProcessor.process_file
        
        Args:
            file_info: Dictionary with file information (old format)
            
        Returns:
            Dictionary with processing results (old format)
        """
        try:
            # Convert old file_info format to new FileInfo model
            file_model = FileInfo(
                path=file_info.get('path'),
                name=file_info.get('name'),
                size=file_info.get('size', 0),
                modified=file_info.get('modified', datetime.now())
            )
            
            # Run async method in sync context (for compatibility)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    self._process_file_async(file_model)
                )
            finally:
                loop.close()
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing file {file_info.get('name', 'unknown')}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def _process_file_async(self, file_info: FileInfo) -> Dict[str, Any]:
        """
        Async file processing using new services
        
        Args:
            file_info: FileInfo model
            
        Returns:
            Processing result dictionary (old format for compatibility)
        """
        try:
            logger.info(f"Processing file: {file_info.name}")
            
            # Use new transcription service
            result = await self.transcription_service.process_and_store(file_info)
            
            if result['success']:
                # Convert new format to old format for compatibility
                return {
                    'success': True,
                    'file_name': file_info.name,
                    'transcript_data': result['transcription'].to_dict(),
                    'upload_result': {
                        'json_file_path': result['outputs'].get('json'),
                        'txt_file_path': result['outputs'].get('text')
                    }
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error')
                }
                
        except Exception as e:
            logger.error(f"Error in async processing: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def process_pending_files(self):
        """
        Process all pending files (compatibility method)
        Matches the original TranscriptionJobProcessor.process_pending_files
        """
        max_files = int(os.environ.get('MAX_FILES', '10'))
        self._process_dropbox_files(max_files=max_files)
    
    def process_single_file(self, file_path: str, file_name: str):
        """
        Process a single specific file (compatibility method)
        Matches the original TranscriptionJobProcessor.process_single_file
        """
        logger.info(f"Processing single file: {file_name} at {file_path}")
        
        file_info = {
            'id': file_path.replace('/', '_').replace(' ', '_'),
            'name': file_name,
            'path': file_path,
            'size': 0,
            'modified': datetime.now().isoformat()
        }
        
        result = self.process_file(file_info)
        
        if result.get('success'):
            logger.info(f"Successfully processed: {file_name}")
        else:
            logger.error(f"Failed to process: {file_name} - {result.get('error')}")
    
    def _process_dropbox_files(self, max_files: int = 10):
        """
        Process files from Dropbox (compatibility method)
        """
        try:
            # Load job tracking
            processed_jobs = self._load_job_tracking()
            
            # Get files using new storage service
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                files = loop.run_until_complete(
                    self.storage_service.list_files(
                        self.dropbox_provider.raw_folder,
                        pattern="*"
                    )
                )
            finally:
                loop.close()
            
            # Filter to audio/video files
            audio_video_files = []
            supported_formats = {
                '.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm',
                '.aac', '.oga', '.ogg', '.flac', '.mov', '.avi', '.mkv'
            }
            
            for file_info in files:
                if file_info.extension in supported_formats:
                    file_id = file_info.path.replace('/', '_').replace(' ', '_')
                    if file_id not in processed_jobs:
                        audio_video_files.append({
                            'id': file_id,
                            'name': file_info.name,
                            'path': file_info.path,
                            'size': file_info.size,
                            'modified': file_info.modified
                        })
            
            # Process files (limited by max_files)
            files_to_process = audio_video_files[:max_files]
            logger.info(f"Found {len(files_to_process)} files to process")
            
            processed_count = 0
            for file_info in files_to_process:
                result = self.process_file(file_info)
                
                if result.get('success'):
                    processed_count += 1
                    processed_jobs[file_info['id']] = {
                        'name': file_info['name'],
                        'processed_at': datetime.now().isoformat(),
                        'success': True
                    }
                else:
                    processed_jobs[file_info['id']] = {
                        'name': file_info['name'],
                        'processed_at': datetime.now().isoformat(),
                        'success': False,
                        'error': result.get('error')
                    }
                
                # Save progress
                self._save_job_tracking(processed_jobs)
            
            logger.info(f"Processed {processed_count}/{len(files_to_process)} files successfully")
            
        except Exception as e:
            logger.error(f"Error processing Dropbox files: {str(e)}")
            raise
    
    def _load_job_tracking(self) -> Dict[str, Any]:
        """Load job tracking (compatibility method)"""
        try:
            if self.job_tracking_file.exists():
                with open(self.job_tracking_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load job tracking: {str(e)}")
        return {}
    
    def _save_job_tracking(self, processed_jobs: Dict[str, Any]):
        """Save job tracking (compatibility method)"""
        try:
            self.job_tracking_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.job_tracking_file, 'w') as f:
                json.dump(processed_jobs, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save job tracking: {str(e)}")
    
    def get_folder_info(self) -> Dict[str, str]:
        """Get folder information (compatibility method)"""
        return {
            'raw_folder': self.dropbox_provider.raw_folder,
            'processed_folder': self.dropbox_provider.processed_folder
        }