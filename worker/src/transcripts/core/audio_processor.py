"""
Audio processing utilities for transcription pipeline
Handles audio extraction and compression using FFmpeg
"""

from pathlib import Path
from typing import Optional

try:
    import ffmpeg
except ImportError:
    raise ImportError("FFmpeg-python not installed. Run: uv add ffmpeg-python")

from ..config import Config


class AudioProcessor:
    """Handles audio processing and compression"""
    
    @staticmethod
    def prepare_audio_file(input_path: Path, file_name: str) -> Optional[Path]:
        """Prepare audio file - extract from video or compress audio if needed"""
        try:
            file_size = input_path.stat().st_size
            max_size = Config.MAX_FILE_SIZE_MB * 1024 * 1024  # Convert to bytes
            
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
            
            return AudioProcessor._extract_and_compress_audio(input_path)
            
        except Exception as e:
            print(f"❌ Error preparing audio file: {str(e)}")
            return None
    
    @staticmethod
    def _extract_and_compress_audio(input_path: Path, max_size_mb: int = 24) -> Optional[Path]:
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