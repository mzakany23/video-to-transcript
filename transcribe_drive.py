#!/usr/bin/env python3
"""
Google Drive-enabled transcription script using OpenAI Whisper API
Monitors Google Drive folder and processes new audio/video files automatically
"""

import os
import sys
import argparse
import json
from pathlib import Path
import tempfile
import shutil
from typing import List, Optional, Dict
from dotenv import load_dotenv
from openai import OpenAI
import ffmpeg

from google_drive_handler import GoogleDriveHandler

# Load environment variables
load_dotenv()


class DriveTranscriptionProcessor:
    """Handles transcription of audio/video files from Google Drive using OpenAI Whisper API"""

    # OpenAI Whisper API file size limit (25MB)
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB in bytes

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenAI API key and Google Drive handler"""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")

        self.client = OpenAI(api_key=self.api_key)
        self.drive_handler = GoogleDriveHandler()

        # Set up folder structure
        self.folder_info = self.drive_handler.setup_folder_structure()

        # Job tracking
        self.jobs_file = Path('conversation/processed_jobs.json')
        self.jobs_file.parent.mkdir(exist_ok=True)
        self.processed_jobs = self._load_processed_jobs()

        # Check if ffmpeg is available
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """Check if ffmpeg is available"""
        try:
            ffmpeg.probe('test')
        except ffmpeg.Error:
            pass  # This is expected for a non-existent file
        except FileNotFoundError:
            print("Warning: ffmpeg not found. Large file processing will be limited.")
            print("Install ffmpeg: brew install ffmpeg (macOS) or apt install ffmpeg (Ubuntu)")

    def _load_processed_jobs(self) -> Dict[str, Dict]:
        """Load the list of already processed files"""
        if self.jobs_file.exists():
            try:
                with open(self.jobs_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return {}

    def _save_processed_jobs(self):
        """Save the list of processed files"""
        with open(self.jobs_file, 'w') as f:
            json.dump(self.processed_jobs, f, indent=2)

    def _compress_audio(self, input_path: Path, max_size_mb: int = 24) -> Optional[Path]:
        """Compress audio/video file to meet size requirements"""
        try:
            # Create temporary file for compressed audio
            temp_dir = Path(tempfile.mkdtemp())
            compressed_path = temp_dir / f"compressed_{input_path.stem}.mp3"

            print(f"Compressing {input_path.name} to meet 25MB limit...")

            # Get file info
            probe = ffmpeg.probe(str(input_path))
            duration = float(probe['format']['duration'])

            # Calculate target bitrate to stay under size limit
            target_size_bits = max_size_mb * 1024 * 1024 * 8  # Convert MB to bits
            target_bitrate = int(target_size_bits / duration)

            # Cap bitrate between reasonable limits
            target_bitrate = max(32000, min(target_bitrate, 128000))  # 32k to 128k

            # Extract and compress audio
            (
                ffmpeg
                .input(str(input_path))
                .output(str(compressed_path),
                       acodec='mp3',
                       audio_bitrate=target_bitrate,
                       ac=1,  # Mono
                       ar=22050)  # Lower sample rate
                .overwrite_output()
                .run(quiet=True)
            )

            # Check if compressed file meets size requirement
            if compressed_path.stat().st_size > self.MAX_FILE_SIZE:
                print(f"Warning: Compressed file still too large. Trying lower quality...")
                # Try even more aggressive compression
                compressed_path2 = temp_dir / f"compressed2_{input_path.stem}.mp3"
                (
                    ffmpeg
                    .input(str(input_path))
                    .output(str(compressed_path2),
                           acodec='mp3',
                           audio_bitrate=24000,  # Very low bitrate
                           ac=1,  # Mono
                           ar=16000)  # Even lower sample rate
                    .overwrite_output()
                    .run(quiet=True)
                )

                if compressed_path2.exists():
                    compressed_path.unlink()
                    compressed_path = compressed_path2

            return compressed_path

        except Exception as e:
            print(f"Error compressing audio: {e}")
            return None

    def transcribe_file(self, file_info: Dict, temp_file_path: Path, language: Optional[str] = None) -> Dict:
        """Transcribe a single audio/video file"""
        file_name = file_info['name']
        print(f"Transcribing: {file_name}")

        # Check file size
        file_size = temp_file_path.stat().st_size
        compressed_file = None

        try:
            # If file is too large, try to compress it
            if file_size > self.MAX_FILE_SIZE:
                print(f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds 25MB limit")
                compressed_file = self._compress_audio(temp_file_path)

                if compressed_file and compressed_file.exists():
                    file_to_process = compressed_file
                    compressed_size = compressed_file.stat().st_size
                    print(f"Using compressed file ({compressed_size / 1024 / 1024:.1f}MB)")

                    if compressed_size > self.MAX_FILE_SIZE:
                        return {
                            'success': False,
                            'error': f'File too large even after compression ({compressed_size / 1024 / 1024:.1f}MB > 25MB)',
                            'source_file': file_name,
                            'drive_file_id': file_info['id'],
                        }
                else:
                    return {
                        'success': False,
                        'error': 'File too large and compression failed',
                        'source_file': file_name,
                        'drive_file_id': file_info['id'],
                    }
            else:
                file_to_process = temp_file_path

            with open(file_to_process, 'rb') as audio_file:
                # Call Whisper API
                transcript_params = {
                    'file': audio_file,
                    'model': 'whisper-1',
                    'response_format': 'verbose_json',  # Get detailed response with timestamps
                }

                if language:
                    transcript_params['language'] = language

                transcript = self.client.audio.transcriptions.create(**transcript_params)

                # Convert segments to JSON-serializable format
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

                result = {
                    'success': True,
                    'text': transcript.text,
                    'segments': segments,
                    'language': getattr(transcript, 'language', language),
                    'duration': getattr(transcript, 'duration', None),
                    'source_file': file_name,
                    'drive_file_id': file_info['id'],
                    'compressed': compressed_file is not None,
                    'processed_at': json.loads(json.dumps(None))  # Will be set by caller
                }

                if compressed_file:
                    result['compression_note'] = 'File was compressed to meet API size limits'

                return result

        except Exception as e:
            print(f"Error transcribing {file_name}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'source_file': file_name,
                'drive_file_id': file_info['id'],
            }

        finally:
            # Clean up compressed file
            if compressed_file and compressed_file.exists():
                try:
                    shutil.rmtree(compressed_file.parent)
                except:
                    pass

    def process_new_files(self, language: Optional[str] = None, max_files: Optional[int] = None):
        """Process all new audio/video files in the Google Drive raw folder"""
        # Get list of processed file IDs
        processed_file_ids = list(self.processed_jobs.keys())

        # Get new files from Drive
        new_files = self.drive_handler.get_new_files_in_raw(processed_file_ids)

        if not new_files:
            print("No new audio/video files found in Google Drive raw folder")
            return

        print(f"Found {len(new_files)} new file(s) to process")

        if max_files:
            new_files = new_files[:max_files]
            print(f"Processing first {len(new_files)} file(s)")

        success_count = 0
        for file_info in new_files:
            file_id = file_info['id']
            file_name = file_info['name']

            print(f"\n🔄 Processing: {file_name}")

            # Download file to temporary location
            temp_file = Path(f"conversation/temp_{file_name}")

            try:
                if self.drive_handler.download_file(file_id, temp_file):
                    # Transcribe the file
                    transcript_data = self.transcribe_file(file_info, temp_file, language)

                    # Add processing timestamp
                    from datetime import datetime
                    transcript_data['processed_at'] = datetime.now().isoformat()

                    if transcript_data.get('success'):
                        # Upload results to Google Drive
                        upload_results = self.drive_handler.upload_transcript_results(
                            transcript_data, file_name
                        )

                        # Record successful job
                        self.processed_jobs[file_id] = {
                            'file_name': file_name,
                            'processed_at': transcript_data['processed_at'],
                            'json_file_id': upload_results.get('json_file_id'),
                            'txt_file_id': upload_results.get('txt_file_id'),
                            'success': True
                        }

                        success_count += 1
                        print(f"✅ Successfully processed: {file_name}")
                    else:
                        # Record failed job
                        self.processed_jobs[file_id] = {
                            'file_name': file_name,
                            'processed_at': transcript_data.get('processed_at'),
                            'error': transcript_data.get('error'),
                            'success': False
                        }
                        print(f"❌ Failed to process: {file_name}")

            except Exception as e:
                print(f"❌ Error processing {file_name}: {e}")
                # Record failed job
                from datetime import datetime
                self.processed_jobs[file_id] = {
                    'file_name': file_name,
                    'processed_at': datetime.now().isoformat(),
                    'error': str(e),
                    'success': False
                }

            finally:
                # Clean up temp file
                if temp_file.exists():
                    temp_file.unlink()

                # Save job tracking after each file
                self._save_processed_jobs()

        print(f"\n🏁 Processing complete! Successfully transcribed {success_count}/{len(new_files)} files")

        # Show folder links
        print(f"\n📁 Check results:")
        print(f"   Processed folder: {self.folder_info['processed_folder_url']}")

    def show_status(self):
        """Show current status and statistics"""
        print("📊 Transcription Pipeline Status")
        print("=" * 40)

        # Folder info
        print(f"📁 Raw folder: {self.folder_info['raw_folder_url']}")
        print(f"📁 Processed folder: {self.folder_info['processed_folder_url']}")

        # Job statistics
        total_jobs = len(self.processed_jobs)
        successful_jobs = sum(1 for job in self.processed_jobs.values() if job.get('success'))
        failed_jobs = total_jobs - successful_jobs

        print(f"\n📈 Statistics:")
        print(f"   Total files processed: {total_jobs}")
        print(f"   Successful: {successful_jobs}")
        print(f"   Failed: {failed_jobs}")

        # Recent jobs
        if self.processed_jobs:
            print(f"\n📋 Recent jobs:")
            recent_jobs = sorted(
                self.processed_jobs.items(),
                key=lambda x: x[1].get('processed_at', ''),
                reverse=True
            )[:5]

            for file_id, job in recent_jobs:
                status = "✅" if job.get('success') else "❌"
                print(f"   {status} {job['file_name']} - {job.get('processed_at', 'unknown')}")

        # Check for new files
        processed_file_ids = list(self.processed_jobs.keys())
        new_files = self.drive_handler.get_new_files_in_raw(processed_file_ids)
        if new_files:
            print(f"\n🆕 {len(new_files)} new file(s) waiting to be processed:")
            for file in new_files[:3]:  # Show first 3
                print(f"   📄 {file['name']}")
            if len(new_files) > 3:
                print(f"   ... and {len(new_files) - 3} more")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Transcribe audio/video files from Google Drive using OpenAI Whisper API')
    parser.add_argument('--language', '-l', type=str, help='Language code (e.g., en, es, fr)')
    parser.add_argument('--max-files', '-m', type=int, help='Maximum number of files to process')
    parser.add_argument('--status', '-s', action='store_true', help='Show status and exit')

    args = parser.parse_args()

    try:
        processor = DriveTranscriptionProcessor()

        if args.status:
            processor.show_status()
        else:
            processor.process_new_files(args.language, args.max_files)

    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()