#!/usr/bin/env python3
"""
Transcription script using OpenAI Whisper API
Processes audio/video files from data/raw/ and saves transcripts to data/processed/
Handles large files by extracting and compressing audio.
"""

import os
import sys
import argparse
from pathlib import Path
import json
import tempfile
import shutil
from typing import List, Optional
from dotenv import load_dotenv
from openai import OpenAI
import ffmpeg

# Load environment variables
load_dotenv()

class TranscriptionProcessor:
    """Handles transcription of audio/video files using OpenAI Whisper API"""

    # Supported file formats for Whisper API
    SUPPORTED_FORMATS = {
        '.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm',
        '.aac', '.oga', '.ogg', '.flac', '.mov', '.avi'
    }

    # OpenAI Whisper API file size limit (25MB)
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB in bytes

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenAI API key"""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")

        self.client = OpenAI(api_key=self.api_key)
        self.raw_dir = Path('data/raw')
        self.processed_dir = Path('data/processed')

        # Ensure directories exist
        self.processed_dir.mkdir(parents=True, exist_ok=True)

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

    def get_audio_files(self) -> List[Path]:
        """Get all supported audio/video files from raw directory"""
        files = []
        if not self.raw_dir.exists():
            print(f"Warning: {self.raw_dir} does not exist")
            return files

        for file_path in self.raw_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_FORMATS:
                files.append(file_path)

        return sorted(files)

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

    def transcribe_file(self, file_path: Path, language: Optional[str] = None) -> dict:
        """Transcribe a single audio/video file"""
        print(f"Transcribing: {file_path.name}")

        # Check file size
        file_size = file_path.stat().st_size
        compressed_file = None

        try:
            # If file is too large, try to compress it
            if file_size > self.MAX_FILE_SIZE:
                print(f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds 25MB limit")
                compressed_file = self._compress_audio(file_path)

                if compressed_file and compressed_file.exists():
                    file_to_process = compressed_file
                    compressed_size = compressed_file.stat().st_size
                    print(f"Using compressed file ({compressed_size / 1024 / 1024:.1f}MB)")

                    if compressed_size > self.MAX_FILE_SIZE:
                        return {
                            'success': False,
                            'error': f'File too large even after compression ({compressed_size / 1024 / 1024:.1f}MB > 25MB)',
                            'source_file': str(file_path),
                        }
                else:
                    return {
                        'success': False,
                        'error': 'File too large and compression failed',
                        'source_file': str(file_path),
                    }
            else:
                file_to_process = file_path

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
                    'source_file': str(file_path),
                    'compressed': compressed_file is not None,
                }

                if compressed_file:
                    result['compression_note'] = 'File was compressed to meet API size limits'

                return result

        except Exception as e:
            print(f"Error transcribing {file_path.name}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'source_file': str(file_path),
            }

        finally:
            # Clean up compressed file
            if compressed_file and compressed_file.exists():
                try:
                    shutil.rmtree(compressed_file.parent)
                except:
                    pass

    def save_transcript(self, transcript_data: dict, source_file: Path, output_format: str = 'json'):
        """Save transcript to processed directory"""
        # Create output filename
        relative_path = source_file.relative_to(self.raw_dir)
        output_file = self.processed_dir / relative_path.with_suffix('')

        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if output_format == 'json':
            json_file = output_file.with_suffix('.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(transcript_data, f, indent=2, ensure_ascii=False)
            print(f"Saved transcript: {json_file}")

        if output_format in ['txt', 'both'] or output_format == 'json':
            txt_file = output_file.with_suffix('.txt')
            with open(txt_file, 'w', encoding='utf-8') as f:
                if transcript_data.get('success'):
                    f.write(transcript_data['text'])
                    if transcript_data.get('compressed'):
                        f.write('\n\n[Note: Audio was compressed to meet API size limits]')
                else:
                    f.write(f"Transcription failed: {transcript_data.get('error', 'Unknown error')}")
            print(f"Saved text: {txt_file}")

    def process_all_files(self, language: Optional[str] = None, output_format: str = 'json'):
        """Process all audio/video files in the raw directory"""
        files = self.get_audio_files()

        if not files:
            print("No audio/video files found in data/raw/")
            return

        print(f"Found {len(files)} file(s) to process")

        success_count = 0
        for file_path in files:
            # Check if already processed
            relative_path = file_path.relative_to(self.raw_dir)
            json_output = self.processed_dir / relative_path.with_suffix('.json')

            if json_output.exists():
                print(f"Skipping {file_path.name} (already processed)")
                continue

            transcript_data = self.transcribe_file(file_path, language)
            self.save_transcript(transcript_data, file_path, output_format)

            if transcript_data.get('success'):
                success_count += 1

        print(f"\nCompleted! Successfully transcribed {success_count}/{len(files)} files")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Transcribe audio/video files using OpenAI Whisper API')
    parser.add_argument('--file', '-f', type=str, help='Specific file to transcribe (optional)')
    parser.add_argument('--language', '-l', type=str, help='Language code (e.g., en, es, fr)')
    parser.add_argument('--format', '-o', choices=['json', 'txt', 'both'], default='json',
                        help='Output format (default: json)')

    args = parser.parse_args()

    try:
        processor = TranscriptionProcessor()

        if args.file:
            # Process specific file
            file_path = Path(args.file)
            if not file_path.exists():
                print(f"Error: File {file_path} not found")
                sys.exit(1)

            transcript_data = processor.transcribe_file(file_path, args.language)
            processor.save_transcript(transcript_data, file_path, args.format)
        else:
            # Process all files
            processor.process_all_files(args.language, args.format)

    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()