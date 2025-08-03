#!/usr/bin/env python3
"""
Backfill transcription job - processes all files in Google Drive raw folder
Outputs both JSON (with timestamps) and TXT files organized in subdirectories
"""

import os
import json
import tempfile
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from openai import OpenAI
import ffmpeg
import io


class BackfillProcessor:
    """Processes all files in Google Drive raw folder for backfill transcription"""
    
    def __init__(self):
        """Initialize with Google Drive and OpenAI clients"""
        # Initialize Google Drive service
        self.drive_service = self._initialize_drive_service()
        
        # Initialize OpenAI client
        openai_api_key = os.environ.get('OPENAI_API_KEY')
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.openai_client = OpenAI(api_key=openai_api_key)
        
        # Folder IDs (from actual deployment)
        self.raw_folder_id = "1YX5nM-gUFIaxTm9wlXdb1rSPwcZIbT4R"  # Has the 3 test files
        self.processed_folder_id = "1FPgSS1TgqaUbnwtXLhov1MJ3aUxS5LQg"
        
        print(f"🔧 Backfill processor initialized")
        print(f"📁 Raw folder: https://drive.google.com/drive/folders/{self.raw_folder_id}")
        print(f"📁 Processed folder: https://drive.google.com/drive/folders/{self.processed_folder_id}")
    
    def _initialize_drive_service(self):
        """Initialize Google Drive service using service account"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                'service-account.json',
                scopes=['https://www.googleapis.com/auth/drive']
            )
            
            return build('drive', 'v3', credentials=credentials)
            
        except Exception as e:
            print(f"❌ Error initializing Drive service: {str(e)}")
            raise
    
    def get_audio_video_files(self) -> List[Dict[str, Any]]:
        """Get all audio/video files from Google Drive raw folder"""
        try:
            # Define audio/video MIME types and extensions
            audio_video_types = [
                'video/mp4', 'video/avi', 'video/mov', 'video/wmv', 'video/flv',
                'video/webm', 'video/mkv', 'video/m4v', 'video/3gp', 'video/quicktime',
                'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/aac', 'audio/ogg',
                'audio/flac', 'audio/m4a', 'audio/wma', 'audio/opus'
            ]
            
            # Query for files in raw folder
            query = f"'{self.raw_folder_id}' in parents and trashed=false"
            
            results = self.drive_service.files().list(
                q=query,
                fields='files(id,name,mimeType,size,createdTime)',
                orderBy='createdTime desc'
            ).execute()
            
            files = results.get('files', [])
            
            # Filter for audio/video files
            audio_video_files = []
            for file_info in files:
                mime_type = file_info.get('mimeType', '')
                name = file_info.get('name', '')
                
                # Check by MIME type or file extension
                is_audio_video = (
                    mime_type in audio_video_types or
                    any(name.lower().endswith(ext) for ext in [
                        '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv',
                        '.m4v', '.3gp', '.mp3', '.wav', '.aac', '.ogg', '.flac',
                        '.m4a', '.wma', '.opus'
                    ])
                )
                
                if is_audio_video:
                    audio_video_files.append(file_info)
            
            # Sort by file size (smallest first for easier testing)
            audio_video_files.sort(key=lambda x: int(x.get('size', 0)))
            
            print(f"📁 Found {len(audio_video_files)} audio/video files in raw folder")
            return audio_video_files
            
        except Exception as e:
            print(f"❌ Error getting audio/video files: {str(e)}")
            return []
    
    def download_from_drive(self, file_id: str, file_name: str) -> Path:
        """Download file from Google Drive to temporary location"""
        try:
            request = self.drive_service.files().get_media(fileId=file_id)
            
            # Create temporary file
            temp_dir = Path(tempfile.mkdtemp())
            temp_file = temp_dir / f"temp_{file_name}"
            
            with open(temp_file, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
            
            print(f"✅ Downloaded: {file_name}")
            return temp_file
            
        except Exception as e:
            print(f"❌ Error downloading {file_name}: {str(e)}")
            return None
    
    def compress_audio(self, input_path: Path, max_size_mb: int = 24) -> Path:
        """Compress audio file using ffmpeg if too large"""
        try:
            file_size_mb = input_path.stat().st_size / (1024 * 1024)
            
            if file_size_mb <= max_size_mb:
                print(f"📁 File size ({file_size_mb:.1f}MB) is acceptable, no compression needed")
                return input_path
            
            compressed_path = input_path.parent / f"compressed_{input_path.name}"
            
            # Get file duration
            probe = ffmpeg.probe(str(input_path))
            duration = float(probe['format']['duration'])
            
            # Calculate target bitrate
            target_size_bits = max_size_mb * 1024 * 1024 * 8
            target_bitrate = int(target_size_bits / duration)
            target_bitrate = max(32000, min(target_bitrate, 128000))  # 32k to 128k
            
            print(f"🔄 Compressing {file_size_mb:.1f}MB file to ~{max_size_mb}MB...")
            
            # Compress audio
            (
                ffmpeg
                .input(str(input_path))
                .output(str(compressed_path), acodec='libmp3lame', audio_bitrate=target_bitrate)
                .overwrite_output()
                .run(quiet=True)
            )
            
            compressed_size_mb = compressed_path.stat().st_size / (1024 * 1024)
            print(f"✅ Compressed: {file_size_mb:.1f}MB -> {compressed_size_mb:.1f}MB")
            return compressed_path
            
        except Exception as e:
            print(f"❌ Error compressing {input_path.name}: {str(e)}")
            return input_path  # Return original if compression fails
    
    def transcribe_audio(self, audio_file_path: Path) -> Dict[str, Any]:
        """Transcribe audio file using OpenAI Whisper"""
        try:
            print(f"🎤 Transcribing: {audio_file_path.name}")
            
            with open(audio_file_path, 'rb') as audio_file:
                transcript = self.openai_client.audio.transcriptions.create(
                    file=audio_file,
                    model='whisper-1',
                    response_format='verbose_json',
                    timestamp_granularities=['word', 'segment']
                )
                
                # Process segments
                segments = getattr(transcript, 'segments', [])
                if segments:
                    segments = [
                        {
                            'id': getattr(segment, 'id', i),
                            'start': getattr(segment, 'start', 0),
                            'end': getattr(segment, 'end', 0),
                            'text': getattr(segment, 'text', ''),
                        }
                        for i, segment in enumerate(segments)
                    ]
                
                # Process words if available
                words = getattr(transcript, 'words', [])
                if words:
                    words = [
                        {
                            'start': getattr(word, 'start', 0),
                            'end': getattr(word, 'end', 0),
                            'word': getattr(word, 'word', ''),
                        }
                        for word in words
                    ]
                
                transcript_data = {
                    'text': transcript.text,
                    'segments': segments,
                    'words': words,
                    'language': getattr(transcript, 'language', 'unknown'),
                    'duration': getattr(transcript, 'duration', 0),
                    'processed_at': datetime.now().isoformat(),
                    'model': 'whisper-1'
                }
                
                print(f"✅ Transcription completed: {len(transcript.text)} characters")
                return {'success': True, 'transcript_data': transcript_data}
                
        except Exception as e:
            print(f"❌ Error transcribing audio: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def create_output_folder(self, file_name: str) -> str:
        """Create a subdirectory in processed folder for the transcription files"""
        try:
            # Sanitize filename for folder name
            base_name = os.path.splitext(file_name)[0]
            sanitized_name = "".join(c for c in base_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            folder_name = f"{datetime.now().strftime('%Y%m%d_%H%M')}_{sanitized_name}"
            
            # Create folder in Google Drive
            folder_metadata = {
                'name': folder_name,
                'parents': [self.processed_folder_id],
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            folder = self.drive_service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')
            
            print(f"📁 Created output folder: {folder_name}")
            return folder_id
            
        except Exception as e:
            print(f"❌ Error creating output folder: {str(e)}")
            return self.processed_folder_id  # Fall back to root processed folder
    
    def upload_results(self, transcript_data: Dict, original_file_name: str, output_folder_id: str):
        """Upload both JSON and TXT files to Google Drive"""
        try:
            base_name = os.path.splitext(original_file_name)[0]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            
            # Upload JSON file with full transcript data
            json_filename = f"{timestamp}_{base_name}_transcript.json"
            json_content = json.dumps(transcript_data, indent=2, ensure_ascii=False)
            
            json_metadata = {
                'name': json_filename,
                'parents': [output_folder_id]
            }
            
            json_media = MediaIoBaseUpload(
                io.BytesIO(json_content.encode('utf-8')),
                mimetype='application/json'
            )
            
            json_file = self.drive_service.files().create(
                body=json_metadata,
                media_body=json_media,
                fields='id'
            ).execute()
            
            # Upload TXT file with plain text
            txt_filename = f"{timestamp}_{base_name}_transcript.txt"
            txt_content = transcript_data.get('text', '')
            
            txt_metadata = {
                'name': txt_filename,
                'parents': [output_folder_id]
            }
            
            txt_media = MediaIoBaseUpload(
                io.BytesIO(txt_content.encode('utf-8')),
                mimetype='text/plain'
            )
            
            txt_file = self.drive_service.files().create(
                body=txt_metadata,
                media_body=txt_media,
                fields='id'
            ).execute()
            
            print(f"✅ Uploaded results:")
            print(f"   📄 JSON: {json_filename}")
            print(f"   📝 TXT: {txt_filename}")
            
            return {
                'json_file_id': json_file.get('id'),
                'txt_file_id': txt_file.get('id'),
                'json_filename': json_filename,
                'txt_filename': txt_filename
            }
            
        except Exception as e:
            print(f"❌ Error uploading results: {str(e)}")
            return {'error': str(e)}
    
    def process_all_files(self, max_files: int = None):
        """Process all audio/video files in the raw folder"""
        print(f"🚀 Starting backfill transcription job...")
        
        # Get all audio/video files
        files_to_process = self.get_audio_video_files()
        
        if not files_to_process:
            print("ℹ️ No audio/video files found to process")
            return
        
        if max_files:
            files_to_process = files_to_process[:max_files]
            print(f"📊 Processing {len(files_to_process)} files (limited to {max_files})")
        else:
            print(f"📊 Processing {len(files_to_process)} files")
        
        successful = 0
        failed = 0
        
        for i, file_info in enumerate(files_to_process, 1):
            file_name = file_info.get('name')
            file_id = file_info.get('id')
            
            print(f"\n🔄 [{i}/{len(files_to_process)}] Processing: {file_name}")
            
            try:
                # Download file
                temp_file = self.download_from_drive(file_id, file_name)
                if not temp_file:
                    failed += 1
                    continue
                
                # Compress if needed
                processed_file = self.compress_audio(temp_file)
                
                # Transcribe
                result = self.transcribe_audio(processed_file)
                
                if result.get('success'):
                    # Create output folder
                    output_folder_id = self.create_output_folder(file_name)
                    
                    # Upload results
                    upload_result = self.upload_results(
                        result['transcript_data'], 
                        file_name, 
                        output_folder_id
                    )
                    
                    if 'error' not in upload_result:
                        successful += 1
                        print(f"✅ [{i}/{len(files_to_process)}] Completed: {file_name}")
                    else:
                        failed += 1
                        print(f"❌ [{i}/{len(files_to_process)}] Upload failed: {file_name}")
                else:
                    failed += 1
                    print(f"❌ [{i}/{len(files_to_process)}] Transcription failed: {file_name}")
                
                # Clean up temporary files
                if temp_file and temp_file.exists():
                    temp_file.unlink()
                if processed_file != temp_file and processed_file.exists():
                    processed_file.unlink()
                    
            except Exception as e:
                failed += 1
                print(f"❌ [{i}/{len(files_to_process)}] Error processing {file_name}: {str(e)}")
        
        print(f"\n📊 Backfill job completed:")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📁 Results in: https://drive.google.com/drive/folders/{self.processed_folder_id}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Backfill transcription of Google Drive files')
    parser.add_argument('--max-files', type=int, help='Maximum number of files to process')
    parser.add_argument('--dry-run', action='store_true', help='List files without processing')
    
    args = parser.parse_args()
    
    try:
        processor = BackfillProcessor()
        
        if args.dry_run:
            files = processor.get_audio_video_files()
            print(f"\n📋 Files that would be processed:")
            for i, file_info in enumerate(files, 1):
                size_mb = int(file_info.get('size', 0)) / (1024 * 1024)
                print(f"   {i}. {file_info.get('name')} ({size_mb:.1f}MB)")
        else:
            processor.process_all_files(max_files=args.max_files)
            
    except KeyboardInterrupt:
        print("\n⚠️ Job interrupted by user")
    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main()