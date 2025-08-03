"""
Dropbox handler for transcription pipeline
Handles all Dropbox operations with clean interface
"""

import json
import tempfile
import requests
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

try:
    import dropbox
    from dropbox.exceptions import AuthError, ApiError
except ImportError:
    raise ImportError("Dropbox SDK not installed. Run: uv add dropbox")

from ..config import Config


class DropboxHandler:
    """Handles Dropbox operations for the transcription pipeline"""
    
    def __init__(self, access_token: Optional[str] = None):
        """Initialize Dropbox handler with access token"""
        self.access_token = access_token or Config.DROPBOX_ACCESS_TOKEN
        if not self.access_token:
            raise ValueError("Dropbox access token is required")
        
        try:
            self.dbx = dropbox.Dropbox(self.access_token)
            # Test connection
            self.account = self.dbx.users_get_current_account()
            print(f"✅ Connected to Dropbox: {self.account.name.display_name}")
        except AuthError as e:
            raise Exception(f"Dropbox authentication failed: {e}")
        
        # Ensure folder structure exists
        self._setup_folder_structure()
    
    
    def _setup_folder_structure(self):
        """Create folder structure if it doesn't exist (within scoped folder)"""
        folders_to_create = [Config.RAW_FOLDER, Config.PROCESSED_FOLDER]
        
        for folder_path in folders_to_create:
            try:
                self.dbx.files_create_folder_v2(folder_path)
                print(f"✅ Created folder: {folder_path}")
            except ApiError as e:
                if e.error.is_path() and e.error.get_path().is_conflict():
                    # Folder already exists
                    print(f"ℹ️ Folder already exists: {folder_path}")
                else:
                    print(f"⚠️ Error creating folder {folder_path}: {e}")
    
    def get_audio_video_files(self, processed_jobs: List[str] = None) -> List[Dict[str, Any]]:
        """Get list of audio/video files in raw folder that haven't been processed"""
        processed_jobs = processed_jobs or []
        
        try:
            result = self.dbx.files_list_folder(Config.RAW_FOLDER)
            files = result.entries
            
            # Get additional pages if they exist
            while result.has_more:
                result = self.dbx.files_list_folder_continue(result.cursor)
                files.extend(result.entries)
            
            audio_video_files = []
            
            for file_entry in files:
                if not hasattr(file_entry, 'path_display'):
                    continue
                
                file_name = file_entry.name
                file_path = file_entry.path_display
                
                # Check if it's a supported audio/video format
                if Config.is_supported_format(file_name):
                    # Create unique ID from path for tracking
                    file_id = file_path.replace('/', '_').replace(' ', '_')
                    
                    # Check if already processed
                    if file_id not in processed_jobs:
                        file_info = {
                            'id': file_id,
                            'name': file_name,
                            'path': file_path,
                            'size': getattr(file_entry, 'size', 0),
                            'modified': getattr(file_entry, 'client_modified', None),
                            'dropbox_entry': file_entry
                        }
                        audio_video_files.append(file_info)
            
            # Sort by modification time (oldest first for processing)
            audio_video_files.sort(key=lambda x: x.get('modified') or datetime.min)
            
            print(f"📁 Found {len(audio_video_files)} new audio/video files in raw folder")
            return audio_video_files
            
        except Exception as e:
            print(f"❌ Error getting audio/video files: {e}")
            return []
    
    def download_file(self, file_path: str, file_name: str) -> Optional[Path]:
        """Download file from Dropbox to temporary location"""
        try:
            # Create temporary file
            temp_dir = Path(tempfile.mkdtemp())
            temp_file = temp_dir / f"temp_{file_name}"
            
            # Download file from Dropbox
            metadata, response = self.dbx.files_download(file_path)
            
            with open(temp_file, 'wb') as f:
                f.write(response.content)
            
            file_size_mb = temp_file.stat().st_size / (1024 * 1024)
            print(f"✅ Downloaded: {file_name} ({file_size_mb:.1f}MB)")
            return temp_file
            
        except Exception as e:
            print(f"❌ Error downloading {file_name}: {e}")
            return None
    
    def upload_transcript_results(self, transcript_data: Dict, original_file_name: str) -> Dict[str, Any]:
        """Upload transcript results (JSON and TXT) to processed folder"""
        base_name = Path(original_file_name).stem
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results = {}
        
        try:
            # Upload JSON file with detailed transcript data
            json_filename = f"{timestamp}_{base_name}_transcript.json"
            json_content = json.dumps({
                **transcript_data,
                'original_file': original_file_name,
                'processed_at': timestamp,
                'status': 'completed'
            }, indent=2, ensure_ascii=False)
            
            json_path = f"{Config.PROCESSED_FOLDER}/{json_filename}"
            
            self.dbx.files_upload(
                json_content.encode('utf-8'),
                json_path,
                mode=dropbox.files.WriteMode.overwrite
            )
            
            results['json_file_path'] = json_path
            results['json_filename'] = json_filename
            print(f"✅ Uploaded JSON: {json_filename}")
            
            # Upload TXT file with readable transcript
            txt_filename = f"{timestamp}_{base_name}_transcript.txt"
            txt_content = self._format_transcript_text(transcript_data, original_file_name, timestamp)
            
            txt_path = f"{Config.PROCESSED_FOLDER}/{txt_filename}"
            
            self.dbx.files_upload(
                txt_content.encode('utf-8'),
                txt_path,
                mode=dropbox.files.WriteMode.overwrite
            )
            
            results['txt_file_path'] = txt_path
            results['txt_filename'] = txt_filename
            print(f"✅ Uploaded TXT: {txt_filename}")
            
            # Create shareable links for easy access
            try:
                json_link = self.dbx.sharing_create_shared_link(json_path)
                txt_link = self.dbx.sharing_create_shared_link(txt_path)
                
                results['json_share_url'] = json_link.url
                results['txt_share_url'] = txt_link.url
                print(f"🔗 Created shareable links")
                
            except Exception as e:
                print(f"⚠️ Could not create shareable links: {e}")
            
            print(f"📁 Results uploaded to: {Config.PROCESSED_FOLDER}")
            return results
            
        except Exception as e:
            print(f"❌ Error uploading transcript results: {e}")
            return {'error': str(e)}
    
    def _format_transcript_text(self, transcript_data: Dict, original_file_name: str, timestamp: str) -> str:
        """Format transcript data into readable text"""
        content = f"""Transcription Results
===================
Original File: {original_file_name}
Processed: {timestamp}
Language: {transcript_data.get('language', 'unknown')}
Duration: {transcript_data.get('duration', 0)} seconds

{transcript_data.get('text', '')}

--- Detailed Segments ---
"""
        
        # Add segments with timestamps
        for segment in transcript_data.get('segments', []):
            start = segment.get('start', 0)
            end = segment.get('end', 0)
            text = segment.get('text', '')
            content += f"[{start:.1f}s - {end:.1f}s]: {text}\n"
        
        return content
    
    def get_folder_info(self) -> Dict[str, str]:
        """Get folder information for user reference"""
        return {
            'scoped_folder': 'jos-transcripts',
            'raw_folder': f"jos-transcripts{Config.RAW_FOLDER}",
            'processed_folder': f"jos-transcripts{Config.PROCESSED_FOLDER}",
            'account': self.account.name.display_name,
            'email': self.account.email
        }
    
    def is_audio_video_file(self, file_path: str) -> bool:
        """Check if file is supported audio/video format"""
        return Config.is_supported_format(file_path)