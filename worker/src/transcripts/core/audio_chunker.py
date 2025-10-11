"""
Audio chunking utilities for handling files too large for OpenAI Whisper API
Splits large audio files into manageable chunks, transcribes each, and merges results
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
import math

try:
    import ffmpeg
except ImportError:
    raise ImportError("FFmpeg-python not installed. Run: uv add ffmpeg-python")

from ..config import Config


class AudioChunker:
    """Handles splitting and merging of large audio files"""

    # Maximum safe file size for Whisper API (with safety margin)
    MAX_CHUNK_SIZE_MB = 19  # OpenAI limit is 25MB, we target 19MB to be safe

    @staticmethod
    def should_chunk_file(file_path: Path) -> bool:
        """
        Determine if a file needs to be chunked based on size

        Args:
            file_path: Path to the audio file

        Returns:
            bool: True if file should be chunked
        """
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        # Chunk if file is over 20MB (compressed files might still be too large)
        return file_size_mb > 20

    @staticmethod
    def get_audio_duration(file_path: Path) -> float:
        """
        Get the duration of an audio file in seconds

        Args:
            file_path: Path to the audio file

        Returns:
            float: Duration in seconds
        """
        try:
            probe = ffmpeg.probe(str(file_path))
            return float(probe['format']['duration'])
        except Exception as e:
            print(f"❌ Error getting audio duration: {e}")
            return 0

    @staticmethod
    def split_audio_into_chunks(input_path: Path, chunk_duration_minutes: int = 10) -> List[Path]:
        """
        Split audio file into time-based chunks

        Args:
            input_path: Path to the input audio file
            chunk_duration_minutes: Duration of each chunk in minutes (default 10 minutes)

        Returns:
            List of paths to chunk files
        """
        try:
            # Get total duration
            total_duration = AudioChunker.get_audio_duration(input_path)
            if total_duration == 0:
                print("❌ Could not determine audio duration")
                return []

            chunk_duration_seconds = chunk_duration_minutes * 60
            num_chunks = math.ceil(total_duration / chunk_duration_seconds)

            print(f"🔪 Splitting {input_path.name} into {num_chunks} chunks ({chunk_duration_minutes}min each)")
            print(f"   Total duration: {total_duration/60:.1f} minutes")

            chunk_paths = []
            for i in range(num_chunks):
                start_time = i * chunk_duration_seconds
                chunk_path = input_path.parent / f"chunk_{i:03d}_{input_path.stem}.mp3"

                # Extract chunk with high-quality compression for speech
                (
                    ffmpeg
                    .input(str(input_path), ss=start_time, t=chunk_duration_seconds)
                    .output(
                        str(chunk_path),
                        acodec='libmp3lame',
                        audio_bitrate='32k',  # 32kbps is good for speech
                        ac=1,  # Mono
                        ar=22050  # Lower sample rate for speech
                    )
                    .overwrite_output()
                    .run(quiet=True, capture_stdout=True, capture_stderr=True)
                )

                chunk_size_mb = chunk_path.stat().st_size / (1024 * 1024)
                print(f"   ✅ Chunk {i+1}/{num_chunks}: {chunk_size_mb:.1f}MB")

                # Verify chunk is under limit
                if chunk_size_mb > AudioChunker.MAX_CHUNK_SIZE_MB:
                    print(f"   ⚠️ Warning: Chunk {i+1} is {chunk_size_mb:.1f}MB, may need further splitting")

                chunk_paths.append(chunk_path)

            return chunk_paths

        except Exception as e:
            print(f"❌ Error splitting audio into chunks: {e}")
            return []

    @staticmethod
    def merge_transcriptions(chunk_transcripts: List[Dict[str, Any]], original_filename: str) -> Dict[str, Any]:
        """
        Merge multiple chunk transcriptions into a single transcript

        Args:
            chunk_transcripts: List of transcript dictionaries from each chunk
            original_filename: Original filename for metadata

        Returns:
            Merged transcript dictionary
        """
        try:
            if not chunk_transcripts:
                return {'text': '', 'segments': [], 'language': 'unknown', 'duration': 0}

            # Merge text
            merged_text = ' '.join([t.get('text', '') for t in chunk_transcripts])

            # Merge segments with adjusted timestamps
            merged_segments = []
            cumulative_duration = 0

            for chunk_idx, transcript in enumerate(chunk_transcripts):
                chunk_segments = transcript.get('segments', [])
                chunk_duration = transcript.get('duration', 0)

                for segment in chunk_segments:
                    adjusted_segment = {
                        'id': len(merged_segments),
                        'start': segment.get('start', 0) + cumulative_duration,
                        'end': segment.get('end', 0) + cumulative_duration,
                        'text': segment.get('text', '')
                    }
                    merged_segments.append(adjusted_segment)

                cumulative_duration += chunk_duration

            # Use language from first chunk (should be consistent)
            language = chunk_transcripts[0].get('language', 'unknown')

            merged_transcript = {
                'text': merged_text,
                'segments': merged_segments,
                'language': language,
                'duration': cumulative_duration,
                'processed_at': chunk_transcripts[0].get('processed_at', ''),
                'model': 'whisper-1',
                'chunked': True,
                'num_chunks': len(chunk_transcripts)
            }

            print(f"✅ Merged {len(chunk_transcripts)} chunk transcriptions")
            print(f"   Total duration: {cumulative_duration/60:.1f} minutes")
            print(f"   Total segments: {len(merged_segments)}")
            print(f"   Total text length: {len(merged_text)} characters")

            return merged_transcript

        except Exception as e:
            print(f"❌ Error merging transcriptions: {e}")
            return {'text': '', 'segments': [], 'language': 'unknown', 'duration': 0}

    @staticmethod
    def cleanup_chunks(chunk_paths: List[Path]):
        """
        Delete temporary chunk files

        Args:
            chunk_paths: List of paths to chunk files to delete
        """
        for chunk_path in chunk_paths:
            try:
                if chunk_path.exists():
                    chunk_path.unlink()
                    print(f"🗑️ Deleted chunk: {chunk_path.name}")
            except Exception as e:
                print(f"⚠️ Could not delete chunk {chunk_path.name}: {e}")
