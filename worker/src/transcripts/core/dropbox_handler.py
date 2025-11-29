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
from .dropbox_auth import DropboxAuthManager
from ..utils.timestamp_formatter import format_timestamp, format_duration, format_timestamp_range
from .topic_analyzer import TopicAnalyzer
from .summary_formatter import SummaryFormatter


class DropboxHandler:
    """Handles Dropbox operations for the transcription pipeline"""
    
    def __init__(self, project_id: str = None, openai_api_key: str = None):
        """Initialize Dropbox handler with automated token management"""
        self.project_id = project_id or Config.PROJECT_ID
        if not self.project_id:
            raise ValueError("Project ID is required for Dropbox authentication")

        # Store OpenAI API key for topic summarization
        self.openai_api_key = openai_api_key or Config.OPENAI_API_KEY
            
        # Initialize automated auth manager
        self.auth_manager = DropboxAuthManager(self.project_id)
        
        # Get authenticated Dropbox client
        try:
            self.dbx = self.auth_manager.get_dropbox_client()
            self.account = self.dbx.users_get_current_account()
            print(f"✅ Dropbox handler initialized: {self.account.name.display_name}")
        except Exception as e:
            raise Exception(f"Failed to initialize Dropbox handler: {e}")
        
        # Ensure folder structure exists
        self._setup_folder_structure()
    
    def _ensure_valid_client(self):
        """Ensure we have a valid Dropbox client, refresh if needed"""
        try:
            # Test current client
            self.dbx.users_get_current_account()
        except AuthError as e:
            if "expired" in str(e).lower():
                print("🔄 Token expired, getting fresh client...")
                self.dbx = self.auth_manager.get_dropbox_client()
            else:
                raise
    
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
            print(f"🔍 Searching for files in: {Config.RAW_FOLDER}")
            result = self.dbx.files_list_folder(Config.RAW_FOLDER)
            files = result.entries
            
            print(f"📋 Found {len(files)} total entries in folder")
            
            # Get additional pages if they exist
            while result.has_more:
                result = self.dbx.files_list_folder_continue(result.cursor)
                files.extend(result.entries)
            
            audio_video_files = []
            
            for file_entry in files:
                print(f"🔍 Checking entry: {getattr(file_entry, 'name', 'NO_NAME')} (type: {type(file_entry).__name__})")
                
                if not hasattr(file_entry, 'path_display'):
                    print(f"  ❌ No path_display attribute")
                    continue
                
                file_name = file_entry.name
                file_path = file_entry.path_display
                print(f"  📄 File: {file_name} at {file_path}")
                
                # Check if it's a supported audio/video format
                is_supported = Config.is_supported_format(file_name)
                print(f"  🎵 Is supported format? {is_supported}")
                
                if is_supported:
                    # Create unique ID from path for tracking
                    file_id = file_path.replace('/', '_').replace(' ', '_')
                    
                    # Check if already processed
                    already_processed = file_id in processed_jobs
                    print(f"  ♻️ Already processed? {already_processed} (file_id: {file_id})")
                    
                    if not already_processed:
                        file_info = {
                            'id': file_id,
                            'name': file_name,
                            'path': file_path,
                            'size': getattr(file_entry, 'size', 0),
                            'modified': getattr(file_entry, 'client_modified', None),
                            'dropbox_entry': file_entry
                        }
                        audio_video_files.append(file_info)
                        print(f"  ✅ Added to processing queue")
            
            # Sort by modification time (oldest first for processing)
            audio_video_files.sort(key=lambda x: x.get('modified') or datetime.min)
            
            print(f"📁 Found {len(audio_video_files)} new audio/video files in raw folder")
            return audio_video_files
            
        except Exception as e:
            print(f"❌ Error getting audio/video files: {e}")
            return []
    
    def download_file(self, file_path: str, file_name: str) -> Optional[Path]:
        """Download file from Dropbox to temporary location using streaming to handle large files"""
        try:
            # Create temporary file
            temp_dir = Path(tempfile.mkdtemp())
            temp_file = temp_dir / f"temp_{file_name}"

            # Download file from Dropbox with streaming
            metadata, response = self.dbx.files_download(file_path)

            # Stream download in chunks to avoid loading entire file into memory
            chunk_size = 4 * 1024 * 1024  # 4MB chunks
            downloaded = 0
            file_size = metadata.size

            print(f"📥 Downloading {file_name} ({file_size / (1024 * 1024):.1f} MB)...")

            with open(temp_file, 'wb') as f:
                # Dropbox SDK returns response.content as bytes, but we can iterate
                # For very large files, we need to use the raw attribute if available
                if hasattr(response, 'raw'):
                    # Stream from raw response
                    while True:
                        chunk = response.raw.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Log progress every 100MB
                        if downloaded % (100 * 1024 * 1024) == 0:
                            progress = (downloaded / file_size) * 100 if file_size > 0 else 0
                            print(f"  📊 Progress: {progress:.1f}% ({downloaded / (1024 * 1024):.1f} MB)")
                else:
                    # Fallback: write content directly (for smaller files or if raw not available)
                    # Note: This loads into memory but is kept as fallback
                    f.write(response.content)

            file_size_mb = temp_file.stat().st_size / (1024 * 1024)
            print(f"✅ Downloaded: {file_name} ({file_size_mb:.1f}MB)")
            return temp_file

        except Exception as e:
            print(f"❌ Error downloading {file_name}: {e}")
            return None
    
    def upload_transcript_results(self, transcript_data: Dict, original_file_name: str) -> Dict[str, Any]:
        """Upload transcript results with timestamp and filename-based folder structure"""
        base_name = Path(original_file_name).stem
        now = datetime.now()
        timestamp = now.strftime('%Y-%m-%d:%H:%M')  # e.g., "2025-08-04:15:30"
        # Sanitize filename for folder name (remove special chars)
        safe_filename = "".join(c for c in base_name if c.isalnum() or c in ('-', '_')).strip()
        folder_name = f"{timestamp}-{safe_filename}"  # e.g., "2025-08-04:15:30-audio_file"
        results = {}

        try:
            # Create timestamp+filename folder: processed/2025-08-04:15:30-audio_file/
            processing_folder = f"{Config.PROCESSED_FOLDER}/{folder_name}"

            # Ensure folder exists
            self._ensure_folder_exists(processing_folder)

            # Generate topic analysis if enabled
            topic_analysis = None
            if Config.ENABLE_TOPIC_SUMMARIZATION:
                try:
                    print("🔍 Generating topic analysis...")
                    # Use the OpenAI API key passed to DropboxHandler
                    analyzer = TopicAnalyzer(api_key=self.openai_api_key)
                    topic_analysis = analyzer.analyze_transcript(transcript_data)
                    print(f"✅ Topic analysis complete: {topic_analysis.get('metadata', {}).get('total_topics', 0)} topics")
                except Exception as e:
                    print(f"⚠️ Topic analysis failed (continuing without it): {e}")
                    topic_analysis = None

            # Upload JSON file with simple naming (include topic analysis if available)
            json_filename = f"{base_name}.json"
            json_data = {
                **transcript_data,
                'original_file': original_file_name,
                'processed_at': now.isoformat(),
                'status': 'completed'
            }

            # Add topic analysis to JSON if available
            if topic_analysis:
                json_data['topic_analysis'] = topic_analysis

            json_content = json.dumps(json_data, indent=2, ensure_ascii=False)

            json_path = f"{processing_folder}/{json_filename}"

            self.dbx.files_upload(
                json_content.encode('utf-8'),
                json_path,
                mode=dropbox.files.WriteMode.overwrite
            )

            results['json_file_path'] = json_path
            results['json_filename'] = json_filename
            print(f"✅ Uploaded JSON: {json_filename}")

            # Upload SUMMARY file if topic analysis is available
            # Check for 'summary' (new Instagram-focused format) or 'topics' (legacy format)
            if topic_analysis and (topic_analysis.get('summary') or topic_analysis.get('topics')):
                summary_filename = f"{base_name}_SUMMARY.txt"
                summary_content = SummaryFormatter.format_summary_text(
                    transcript_data, topic_analysis, original_file_name
                )

                summary_path = f"{processing_folder}/{summary_filename}"

                self.dbx.files_upload(
                    summary_content.encode('utf-8'),
                    summary_path,
                    mode=dropbox.files.WriteMode.overwrite
                )

                results['summary_file_path'] = summary_path
                results['summary_filename'] = summary_filename
                print(f"✅ Uploaded SUMMARY: {summary_filename}")

                # Also upload markdown version
                summary_md_filename = f"{base_name}_SUMMARY.md"
                summary_md_content = SummaryFormatter.format_summary_markdown(
                    transcript_data, topic_analysis, original_file_name
                )

                summary_md_path = f"{processing_folder}/{summary_md_filename}"

                self.dbx.files_upload(
                    summary_md_content.encode('utf-8'),
                    summary_md_path,
                    mode=dropbox.files.WriteMode.overwrite
                )

                results['summary_md_file_path'] = summary_md_path
                results['summary_md_filename'] = summary_md_filename
                print(f"✅ Uploaded SUMMARY (Markdown): {summary_md_filename}")

            # Upload TXT file with simple naming
            txt_filename = f"{base_name}.txt"
            txt_content = self._format_transcript_text(transcript_data, original_file_name, now.isoformat())

            txt_path = f"{processing_folder}/{txt_filename}"

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

                # Add summary links if available
                if 'summary_file_path' in results:
                    try:
                        summary_link = self.dbx.sharing_create_shared_link(results['summary_file_path'])
                        results['summary_share_url'] = summary_link.url
                    except:
                        pass

                print(f"🔗 Created shareable links")

            except Exception as e:
                print(f"⚠️ Could not create shareable links: {e}")

            # Add topic analysis to results for email notifications
            if topic_analysis:
                results['topic_analysis'] = topic_analysis

            print(f"📁 Results uploaded to: {processing_folder}")
            return results

        except Exception as e:
            print(f"❌ Error uploading transcript results: {e}")
            return {'error': str(e)}
    
    def _format_transcript_text(self, transcript_data: Dict, original_file_name: str, timestamp: str) -> str:
        """Format transcript data into readable text with human-readable timestamps"""
        duration_seconds = transcript_data.get('duration', 0)
        duration_formatted = format_duration(duration_seconds)

        content = f"""Transcription Results
===================
Original File: {original_file_name}
Processed: {timestamp}
Language: {transcript_data.get('language', 'unknown')}
Duration: {duration_formatted} ({format_timestamp(duration_seconds)})

FULL TRANSCRIPT
===============

"""

        # Add full text with paragraph breaks for better readability
        full_text = transcript_data.get('text', '')
        content += full_text + "\n\n"

        # Add detailed segments with formatted timestamps
        content += """--- DETAILED SEGMENTS ---

"""

        for segment in transcript_data.get('segments', []):
            start = segment.get('start', 0)
            end = segment.get('end', 0)
            text = segment.get('text', '').strip()

            # Use the new timestamp range formatter
            timestamp_range = format_timestamp_range(start, end)
            content += f"{timestamp_range} {text}\n"

        return content
    
    def get_folder_info(self) -> Dict[str, str]:
        """Get folder information for user reference"""
        # Extract base folder from the raw folder path
        base_folder = Config.RAW_FOLDER.split('/')[1] if Config.RAW_FOLDER.startswith('/') and len(Config.RAW_FOLDER.split('/')) > 1 else 'transcripts'
        return {
            'scoped_folder': base_folder,
            'raw_folder': Config.RAW_FOLDER,
            'processed_folder': Config.PROCESSED_FOLDER,
            'account': self.account.name.display_name,
            'email': self.account.email
        }
    
    def is_audio_video_file(self, file_path: str) -> bool:
        """Check if file is supported audio/video format"""
        return Config.is_supported_format(file_path)
    
    def _ensure_folder_exists(self, folder_path: str):
        """Ensure a folder exists in Dropbox, create if it doesn't"""
        try:
            self.dbx.files_create_folder_v2(folder_path)
            print(f"✅ Created folder: {folder_path}")
        except ApiError as e:
            if e.error.is_path() and e.error.get_path().is_conflict():
                # Folder already exists
                pass
            else:
                print(f"⚠️ Error creating folder {folder_path}: {e}")