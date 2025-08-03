#!/usr/bin/env python3
"""
Cloud Run Job for heavy transcription processing
Handles audio extraction, compression, and OpenAI Whisper transcription
"""

import json
import os
import tempfile
import re
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from google.cloud import secretmanager
from openai import OpenAI
import ffmpeg

# Import Dropbox handler
sys.path.append('..')
from dropbox_handler import DropboxHandler


def main():
    """Main entry point for Cloud Run Job"""
    print("🚀 Starting transcription processing job...")
    
    # Initialize processor
    processor = TranscriptionJobProcessor()
    
    # Check if triggered by webhook with specific file info
    webhook_trigger = os.environ.get('WEBHOOK_TRIGGER', 'false').lower() == 'true'
    
    if webhook_trigger:
        print("📧 Triggered by Drive webhook - processing new files")
        processor.process_new_drive_files()
    else:
        print("⏰ Scheduled/manual run - processing all pending files")
        processor.process_pending_drive_files()
    
    print("✅ Transcription job completed")


class TranscriptionJobProcessor:
    """Handles batch transcription processing for Cloud Run Jobs using Dropbox"""
    
    def __init__(self):
        """Initialize with environment variables and clients"""
        self.project_id = os.environ.get('PROJECT_ID')
        self.secret_name = os.environ.get('SECRET_NAME')
        
        # Initialize clients
        self.secret_client = secretmanager.SecretManagerServiceClient()
        
        # Get OpenAI API key from Secret Manager
        self.openai_api_key = self._get_secret(self.secret_name)
        self.openai_client = OpenAI(api_key=self.openai_api_key)
        
        # Initialize Dropbox handler
        self.dropbox_handler = DropboxHandler()
        
        # Job tracking file path
        self.job_tracking_file = Path('/tmp/processed_jobs.json')
        
        print(f"🔧 Initialized transcription processor with Dropbox")
        folder_info = self.dropbox_handler.get_folder_info()
        print(f"📁 Raw folder: {folder_info['raw_folder']}")
        print(f"📁 Processed folder: {folder_info['processed_folder']}")
    
    def process_specific_file(self):
        """Process a specific file specified by webhook (triggered by Dropbox webhook)"""
        file_path = os.environ.get('DROPBOX_FILE_PATH')
        file_name = os.environ.get('DROPBOX_FILE_NAME')
        file_id = os.environ.get('DROPBOX_FILE_ID')
        
        if not all([file_path, file_name, file_id]):
            print("⚠️ No specific file specified, falling back to batch processing")
            return self.process_pending_drive_files()
        
        print(f"🎯 Processing specific file: {file_name}")
        
        try:
            # Create file info dict
            file_info = {
                'id': file_id,
                'name': file_name,
                'path': file_path
            }
            
            # Process the file
            result = self.process_file(file_info)
            
            if result.get('success'):
                print(f"✅ Successfully processed: {file_name}")
            else:
                print(f"❌ Failed to process: {file_name} - {result.get('error')}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error processing specific file: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _get_secret(self, secret_name: str) -> str:
        """Retrieve secret from Google Secret Manager"""
        name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
        response = self.secret_client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    
    def process_new_drive_files(self):
        """Process new files in Dropbox (triggered by webhook)"""
        print("📥 Processing new files from Dropbox...")
        
        # Check if this is a specific file trigger
        if os.environ.get('DROPBOX_FILE_PATH'):
            return self.process_specific_file()
        
        # Otherwise process batch
        max_files = int(os.environ.get('MAX_FILES', '5'))  # Default 5 for webhook triggers
        self._process_drive_files(max_files=max_files)
    
    def process_pending_drive_files(self):
        """Process all pending files in Dropbox (scheduled/manual run)"""  
        print("📥 Processing all pending files from Dropbox...")
        max_files = int(os.environ.get('MAX_FILES', '10'))  # Default 10 for scheduled runs
        self._process_drive_files(max_files=max_files)
    
    def _process_drive_files(self, max_files: int = 10):
        """Core method to process files from Dropbox"""
        try:
            # Load job tracking
            processed_jobs = self._load_job_tracking()
            
            # Get audio/video files from Dropbox raw folder
            audio_video_files = self.dropbox_handler.get_audio_video_files(list(processed_jobs.keys()))
            
            if not audio_video_files:
                print("ℹ️ No audio/video files found in raw folder")
                return
            
            # Limit processing for performance
            files_to_process = audio_video_files[:max_files]
            print(f"📨 Found {len(files_to_process)} new files to process (limited to {max_files})")
            
            # Process each file
            processed_count = 0
            
            for file_info in files_to_process:
                try:
                    result = self.process_file(file_info)
                    
                    if result.get('success'):
                        print(f"✅ Successfully processed: {file_info.get('name')}")
                        processed_count += 1
                        # Mark as processed
                        processed_jobs[file_info['id']] = {
                            'name': file_info['name'],
                            'processed_at': datetime.now().isoformat(),
                            'success': True
                        }
                    else:
                        print(f"❌ Failed to process: {file_info.get('name')} - {result.get('error')}")
                        # Mark as failed
                        processed_jobs[file_info['id']] = {
                            'name': file_info['name'],
                            'processed_at': datetime.now().isoformat(),
                            'success': False,
                            'error': result.get('error')
                        }
                    
                    # Save progress after each file
                    self._save_job_tracking(processed_jobs)
                    
                except Exception as e:
                    print(f"❌ Error processing file {file_info.get('name', 'unknown')}: {str(e)}")
                    # Mark as failed
                    processed_jobs[file_info['id']] = {
                        'name': file_info.get('name', 'unknown'),
                        'processed_at': datetime.now().isoformat(),
                        'success': False,
                        'error': str(e)
                    }
                    self._save_job_tracking(processed_jobs)
            
            print(f"📊 Job completed: {processed_count}/{len(files_to_process)} files processed successfully")
            
        except Exception as e:
            print(f"❌ Error in process_drive_files: {str(e)}")
            raise
    
    def _load_job_tracking(self) -> Dict[str, Any]:
        """Load job tracking data from file"""
        try:
            if self.job_tracking_file.exists():
                with open(self.job_tracking_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"⚠️ Error loading job tracking: {str(e)}")
            return {}
    
    def _save_job_tracking(self, processed_jobs: Dict[str, Any]):
        """Save job tracking data to file"""
        try:
            self.job_tracking_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.job_tracking_file, 'w') as f:
                json.dump(processed_jobs, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error saving job tracking: {str(e)}")
    
    
    def process_file(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single file for transcription"""
        processing_start_time = datetime.now()
        
        try:
            file_id = file_info.get('id')
            file_name = file_info.get('name')
            
            print(f"🔄 Processing: {file_name}")
            
            # Download file from Dropbox to temporary storage
            file_path = file_info.get('path')
            temp_file_path = self._download_from_dropbox(file_path, file_name)
            
            if not temp_file_path:
                return {'success': False, 'error': 'Failed to download file from Drive'}
            
            # Process audio based on file type
            audio_file_path = self._prepare_audio_file(temp_file_path, file_name)
            
            if not audio_file_path:
                return {'success': False, 'error': 'Failed to prepare audio file'}
            
            # Transcribe using OpenAI Whisper
            transcript_result = self._transcribe_audio(audio_file_path)
            
            if not transcript_result.get('success'):
                return transcript_result
            
            # Upload results back to Dropbox
            upload_result = self.dropbox_handler.upload_transcript_results(
                transcript_result['transcript_data'], file_name
            )
            
            # Clean up temporary files
            if temp_file_path.exists():
                temp_file_path.unlink()
            if audio_file_path != temp_file_path and audio_file_path.exists():
                audio_file_path.unlink()
            
            return {
                'success': True,
                'file_name': file_name,
                'transcript_data': transcript_result['transcript_data'],
                'upload_result': upload_result
            }
            
        except Exception as e:
            print(f"❌ Error processing file {file_info.get('name', 'unknown')}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _download_from_dropbox(self, file_path: str, file_name: str) -> Path:
        """Download file from Dropbox to temporary location"""
        try:
            temp_file = self.dropbox_handler.download_file(file_path, file_name)
            return temp_file
        except Exception as e:
            print(f"❌ Error downloading {file_name}: {str(e)}")
            return None
    
    def _prepare_audio_file(self, input_path: Path, file_name: str) -> Path:
        """Prepare audio file - extract from video or compress audio if needed"""
        try:
            file_size = input_path.stat().st_size
            max_size = 25 * 1024 * 1024  # 25MB OpenAI limit
            
            file_extension = input_path.suffix.lower()
            is_audio_only = file_extension in ['.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg']
            
            # If it's already small audio, use as-is
            if is_audio_only and file_size <= max_size:
                print(f"✅ Audio file {file_name} is {file_size / 1024 / 1024:.1f}MB - using as-is")
                return input_path
            
            # Extract audio and/or compress
            if is_audio_only:
                print(f"🎵 Audio file {file_name} is {file_size / 1024 / 1024:.1f}MB - recompressing")
            else:
                print(f"🎬 Video file {file_name} is {file_size / 1024 / 1024:.1f}MB - extracting audio")
            
            return self._extract_and_compress_audio(input_path)
            
        except Exception as e:
            print(f"❌ Error preparing audio file: {str(e)}")
            return None
    
    def _extract_and_compress_audio(self, input_path: Path, max_size_mb: int = 24) -> Path:
        """Extract audio-only and compress aggressively"""
        try:
            audio_path = input_path.parent / f"audio_only_{input_path.stem}.mp3"
            
            print(f"🎵 Extracting and compressing audio from: {input_path.name}")
            
            # Get duration for bitrate calculation
            probe = ffmpeg.probe(str(input_path))
            duration = float(probe['format']['duration'])
            
            # Calculate aggressive bitrate for audio-only
            target_size_bits = max_size_mb * 1024 * 1024 * 8
            target_bitrate = int(target_size_bits / duration)
            target_bitrate = max(16000, min(target_bitrate, 64000))  # 16k-64k for speech
            
            print(f"🎯 Target: {target_bitrate}bps for {duration:.1f}s duration")
            
            # Extract audio-only with aggressive compression
            (
                ffmpeg
                .input(str(input_path))
                .output(
                    str(audio_path),
                    vn=None,  # No video
                    acodec='libmp3lame',
                    audio_bitrate=target_bitrate,
                    ac=1,  # Mono
                    ar=22050  # Lower sample rate
                )
                .overwrite_output()
                .run(quiet=True, capture_stdout=True, capture_stderr=True)
            )
            
            final_size = audio_path.stat().st_size
            final_size_mb = final_size / 1024 / 1024
            
            print(f"✅ Audio extracted: {final_size_mb:.1f}MB (target: {max_size_mb}MB)")
            
            return audio_path
            
        except Exception as e:
            print(f"❌ Error extracting audio: {str(e)}")
            return None
    
    def _transcribe_audio(self, audio_file_path: Path) -> Dict[str, Any]:
        """Transcribe audio file using OpenAI Whisper"""
        try:
            file_size = audio_file_path.stat().st_size
            print(f"🎙️ Transcribing audio file: {file_size / 1024 / 1024:.1f}MB")
            
            with open(audio_file_path, 'rb') as audio_file:
                transcript = self.openai_client.audio.transcriptions.create(
                    file=audio_file,
                    model='whisper-1',
                    response_format='verbose_json'
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
                
                transcript_data = {
                    'text': transcript.text,
                    'segments': segments,
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
    


def sanitize_filename(original_name: str, timestamp: datetime) -> str:
    """Create sanitized filename: YYYYMMDD:HHMM-sanitized-title.txt"""
    name_without_ext = os.path.splitext(original_name)[0]
    sanitized = name_without_ext.lower()
    sanitized = re.sub(r"[^a-z0-9\s\-]", "", sanitized)
    sanitized = re.sub(r"\s+", " ", sanitized)
    sanitized = sanitized.replace(" ", "-").strip("-")
    timestamp_str = timestamp.strftime("%Y%m%d:%H%M")
    return f"{timestamp_str}-{sanitized}.txt"


if __name__ == "__main__":
    main()