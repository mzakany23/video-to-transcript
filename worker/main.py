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
import time

from google.cloud import secretmanager, storage
from openai import OpenAI
import ffmpeg

# Import from our src package
sys.path.append('src')
from transcripts.core.dropbox_handler import DropboxHandler
from transcripts.core.notifications import EmailNotificationService
from transcripts.core.audio_chunker import AudioChunker

# Initialize Sentry for error tracking
try:
    import sentry_sdk
    sentry_dsn = os.environ.get('SENTRY_DSN')
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
            environment=os.environ.get('SENTRY_ENVIRONMENT', 'production'),
            release=os.environ.get('SENTRY_RELEASE', 'transcripts-worker@1.1.0')
        )
        print("✅ Sentry error tracking initialized")
    else:
        print("ℹ️ Sentry DSN not configured, error tracking disabled")
except ImportError:
    print("⚠️ Sentry SDK not installed, error tracking disabled")
except Exception as e:
    print(f"⚠️ Failed to initialize Sentry: {e}")


def main():
    """Main entry point for Cloud Run Job"""
    print("🚀 Starting transcription processing job...")
    
    # Initialize processor
    processor = TranscriptionJobProcessor()
    
    # Check if processing a single specific file
    single_file_mode = os.environ.get('PROCESS_SINGLE_FILE', 'false').lower() == 'true'
    
    if single_file_mode:
        target_file_path = os.environ.get('TARGET_FILE_PATH')
        target_file_name = os.environ.get('TARGET_FILE_NAME')
        
        if target_file_path and target_file_name:
            print(f"🎯 Processing single file: {target_file_name}")
            processor.process_single_file(target_file_path, target_file_name)
        else:
            print("❌ Single file mode enabled but missing TARGET_FILE_PATH or TARGET_FILE_NAME")
            return
    else:
        # Legacy mode - process all pending files
        print("⏰ Processing all pending files")
        processor.process_pending_files()
    
    print("✅ Transcription job completed")


class TranscriptionJobProcessor:
    """Handles transcription processing for Cloud Run Jobs using Dropbox"""
    
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
        
        # Initialize email notification service
        self.notification_service = EmailNotificationService(self.project_id)
        
        # Initialize Cloud Storage for job tracking persistence
        self.storage_client = storage.Client()
        self.bucket_name = f"{self.project_id}-job-tracking"
        self.job_tracking_blob_name = "processed_jobs.json"
        
        # Job tracking file path (local cache)
        self.job_tracking_file = Path('/tmp/processed_jobs.json')
        
        print(f"🔧 Initialized transcription processor with Dropbox")
        folder_info = self.dropbox_handler.get_folder_info()
        print(f"📁 Raw folder: {folder_info['raw_folder']}")
        print(f"📁 Processed folder: {folder_info['processed_folder']}")
    
    def _get_secret(self, secret_name: str) -> str:
        """Retrieve secret from Google Secret Manager"""
        name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
        response = self.secret_client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    
    def process_webhook_trigger(self):
        """Process files triggered by Dropbox webhook"""
        print("📥 Processing webhook trigger from Dropbox...")
        
        # Get webhook data from environment
        webhook_data_str = os.environ.get('DROPBOX_WEBHOOK_DATA')
        if webhook_data_str:
            print("📊 Processing webhook data")
            # For now, just process batch - webhook tells us something changed
            # In future, could parse specific changed files
        
        # Process recent files (webhook indicates changes)
        max_files = int(os.environ.get('MAX_FILES', '5'))  # Default 5 for webhook triggers
        self._process_dropbox_files(max_files=max_files)
    
    def process_pending_files(self):
        """Process all pending files in Dropbox (scheduled/manual run)"""  
        print("📥 Processing all pending files from Dropbox...")
        max_files = int(os.environ.get('MAX_FILES', '10'))  # Default 10 for scheduled runs
        self._process_dropbox_files(max_files=max_files)
    
    def process_single_file(self, file_path: str, file_name: str):
        """Process a single specific file"""
        print(f"🎯 Processing single file: {file_name} at {file_path}")
        job_start_time = time.time()
        failed_files = []

        try:
            # Create file info structure
            file_info = {
                'id': file_path.replace('/', '_').replace(' ', '_'),
                'name': file_name,
                'path': file_path,
                'size': 0,  # Will be determined during download
                'modified': datetime.now().isoformat()
            }

            # Send job start notification (get file size from env if available)
            file_size_mb = float(os.environ.get('TARGET_FILE_SIZE_MB', '0'))
            self.notification_service.send_job_start({
                'file_name': file_name,
                'file_size_mb': file_size_mb
            })

            # Process the file
            result = self.process_file(file_info)
            
            if result.get('success'):
                print(f"✅ Successfully processed: {file_name}")
                processed_count = 1
            else:
                print(f"❌ Failed to process: {file_name} - {result.get('error')}")
                failed_files.append(file_name)
                processed_count = 0
            
            # Calculate job duration
            job_duration = time.time() - job_start_time
            
            # Send email notification for single file processing
            job_summary = {
                'processed_count': processed_count,
                'total_count': 1,
                'duration': job_duration,
                'failed_files': failed_files
            }
            self.notification_service.send_job_completion(job_summary)
                
        except Exception as e:
            print(f"❌ Error processing single file {file_name}: {str(e)}")
            # Send error notification
            self.notification_service.send_job_error(f"Single file processing failed for {file_name}: {str(e)}")
            raise
    
    def _process_dropbox_files(self, max_files: int = 10):
        """Core method to process files from Dropbox"""
        job_start_time = time.time()
        failed_files = []
        
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
                        failed_files.append(file_info.get('name', 'unknown'))
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
                    failed_files.append(file_info.get('name', 'unknown'))
                    # Mark as failed
                    processed_jobs[file_info['id']] = {
                        'name': file_info.get('name', 'unknown'),
                        'processed_at': datetime.now().isoformat(),
                        'success': False,
                        'error': str(e)
                    }
                    self._save_job_tracking(processed_jobs)
            
            # Calculate job duration
            job_duration = time.time() - job_start_time
            
            print(f"📊 Job completed: {processed_count}/{len(files_to_process)} files processed successfully")
            
            # Send email notification if any files were processed
            if len(files_to_process) > 0:
                job_summary = {
                    'processed_count': processed_count,
                    'total_count': len(files_to_process),
                    'duration': job_duration,
                    'failed_files': failed_files
                }
                self.notification_service.send_job_completion(job_summary)
            
        except Exception as e:
            print(f"❌ Error in _process_dropbox_files: {str(e)}")
            # Send error notification
            self.notification_service.send_job_error(f"Job failed: {str(e)}")
            raise
    
    def _load_job_tracking(self) -> Dict[str, Any]:
        """Load job tracking data from Cloud Storage"""
        try:
            # Try to load from Cloud Storage first
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(self.job_tracking_blob_name)
            
            if blob.exists():
                job_data = blob.download_as_text()
                processed_jobs = json.loads(job_data)
                print(f"📥 Loaded job tracking from Cloud Storage: {len(processed_jobs)} processed files")
                
                # Cache locally for faster access during this run
                self.job_tracking_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.job_tracking_file, 'w') as f:
                    json.dump(processed_jobs, f, indent=2)
                
                return processed_jobs
            else:
                print("📝 No existing job tracking found, starting fresh")
                return {}
                
        except Exception as e:
            print(f"⚠️ Error loading job tracking from Cloud Storage: {str(e)}")
            # Fallback to local file if it exists
            try:
                if self.job_tracking_file.exists():
                    with open(self.job_tracking_file, 'r') as f:
                        return json.load(f)
            except Exception as local_e:
                print(f"⚠️ Error loading local job tracking: {str(local_e)}")
            return {}
    
    def _save_job_tracking(self, processed_jobs: Dict[str, Any]):
        """Save job tracking data to Cloud Storage"""
        try:
            # Save to Cloud Storage for persistence
            print(f"💾 Saving job tracking to Cloud Storage...")
            
            # Ensure bucket exists
            bucket = self.storage_client.bucket(self.bucket_name)
            try:
                bucket.reload()
                print(f"✅ Bucket exists: {self.bucket_name}")
            except Exception as reload_error:
                # Create bucket if it doesn't exist
                print(f"📦 Creating job tracking bucket: {self.bucket_name}")
                try:
                    bucket = self.storage_client.create_bucket(self.bucket_name, location="us-east1")
                    print(f"✅ Successfully created bucket: {self.bucket_name}")
                except Exception as create_error:
                    print(f"❌ Bucket creation failed: {str(create_error)}")
                    # Fall back to local storage only
                    self._save_job_tracking_local(processed_jobs)
                    return
            
            # Save to Cloud Storage
            blob = bucket.blob(self.job_tracking_blob_name)
            job_data = json.dumps(processed_jobs, indent=2)
            blob.upload_from_string(job_data, content_type='application/json')
            print(f"✅ Saved job tracking to Cloud Storage: {len(processed_jobs)} files")
            
            # Also save locally for faster access during this run
            self._save_job_tracking_local(processed_jobs)
            
        except Exception as e:
            print(f"❌ Error saving job tracking to Cloud Storage: {str(e)}")
            # Fall back to local storage only
            self._save_job_tracking_local(processed_jobs)
    
    def _save_job_tracking_local(self, processed_jobs: Dict[str, Any]):
        """Save job tracking data to local file (backup/cache)"""
        try:
            self.job_tracking_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.job_tracking_file, 'w') as f:
                json.dump(processed_jobs, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error saving local job tracking: {str(e)}")
    
    
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
                return {'success': False, 'error': 'Failed to download file from Dropbox'}
            
            # Process audio based on file type
            audio_file_path = self._prepare_audio_file(temp_file_path, file_name)

            if not audio_file_path:
                return {'success': False, 'error': 'Failed to prepare audio file'}

            # Check if file needs chunking
            if AudioChunker.should_chunk_file(audio_file_path):
                print(f"📦 File is large, using chunked transcription")
                transcript_result = self._transcribe_audio_chunked(audio_file_path)
            else:
                # Transcribe using OpenAI Whisper (single file)
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

    def _transcribe_audio_chunked(self, audio_file_path: Path) -> Dict[str, Any]:
        """Transcribe large audio file by splitting into chunks"""
        try:
            print(f"📦 Starting chunked transcription for {audio_file_path.name}")

            # Split audio into chunks
            chunk_paths = AudioChunker.split_audio_into_chunks(audio_file_path, chunk_duration_minutes=10)

            if not chunk_paths:
                return {'success': False, 'error': 'Failed to split audio into chunks'}

            # Transcribe each chunk
            chunk_transcripts = []
            for i, chunk_path in enumerate(chunk_paths):
                print(f"🎙️ Transcribing chunk {i+1}/{len(chunk_paths)}")

                # Transcribe this chunk
                with open(chunk_path, 'rb') as audio_file:
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
                                'id': getattr(segment, 'id', j),
                                'start': getattr(segment, 'start', 0),
                                'end': getattr(segment, 'end', 0),
                                'text': getattr(segment, 'text', ''),
                            }
                            for j, segment in enumerate(segments)
                        ]

                    chunk_transcript = {
                        'text': transcript.text,
                        'segments': segments,
                        'language': getattr(transcript, 'language', 'unknown'),
                        'duration': getattr(transcript, 'duration', 0),
                        'processed_at': datetime.now().isoformat(),
                        'model': 'whisper-1'
                    }

                    chunk_transcripts.append(chunk_transcript)
                    print(f"✅ Chunk {i+1} completed: {len(transcript.text)} characters")

            # Merge all chunk transcriptions
            merged_transcript = AudioChunker.merge_transcriptions(
                chunk_transcripts,
                audio_file_path.name
            )

            # Cleanup temporary chunk files
            AudioChunker.cleanup_chunks(chunk_paths)

            print(f"✅ Chunked transcription completed: {len(merged_transcript.get('text', ''))} total characters")
            return {'success': True, 'transcript_data': merged_transcript}

        except Exception as e:
            print(f"❌ Error in chunked transcription: {str(e)}")
            # Cleanup on error
            try:
                if 'chunk_paths' in locals():
                    AudioChunker.cleanup_chunks(chunk_paths)
            except:
                pass
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