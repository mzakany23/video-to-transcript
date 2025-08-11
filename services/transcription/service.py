"""
High-level transcription service that orchestrates transcription operations
"""

import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ..core.exceptions import TranscriptionError
from ..core.interfaces import StorageProvider, TranscriptionProvider
from ..core.models import (
    FileInfo,
    TranscriptionOptions,
    TranscriptionResult,
)

logger = logging.getLogger(__name__)


class TranscriptionService:
    """
    High-level transcription service that works with any transcription provider
    """

    def __init__(
        self,
        transcription_provider: TranscriptionProvider,
        storage_provider: Optional[StorageProvider] = None,
        audio_processor: Optional[Any] = None,
    ):
        """
        Initialize transcription service

        Args:
            transcription_provider: Provider for transcription
            storage_provider: Optional storage provider for file operations
            audio_processor: Optional audio processor for format conversion
        """
        self.transcription = transcription_provider
        self.storage = storage_provider
        self.audio_processor = audio_processor

        logger.info(
            f"Initialized TranscriptionService with {transcription_provider.__class__.__name__}"
        )

    async def transcribe_file(
        self,
        file_path: str,
        options: Optional[TranscriptionOptions] = None,
        from_storage: bool = False,
    ) -> TranscriptionResult:
        """
        Transcribe an audio/video file

        Args:
            file_path: Path to file (local or in storage)
            options: Transcription options
            from_storage: Whether file is in storage (requires storage_provider)

        Returns:
            TranscriptionResult
        """
        local_path = file_path
        temp_file = None

        try:
            # Download from storage if needed
            if from_storage:
                if not self.storage:
                    raise TranscriptionError("Storage provider required for from_storage=True")

                logger.info(f"Downloading file from storage: {file_path}")
                download_result = await self.storage.download_file(file_path)

                if not download_result.success:
                    raise TranscriptionError(f"Failed to download file: {download_result.error}")

                local_path = download_result.local_path
                temp_file = local_path

            # Check file size
            file_size = Path(local_path).stat().st_size
            max_size = await self.transcription.get_max_file_size()

            if file_size > max_size:
                file_size_mb = file_size / (1024 * 1024)
                max_size_mb = max_size / (1024 * 1024)

                # Try to process audio if processor available
                if self.audio_processor:
                    logger.info(
                        f"File too large ({file_size_mb:.1f}MB > {max_size_mb:.1f}MB), "
                        "attempting audio processing"
                    )
                    processed_path = await self._process_audio(local_path)
                    if processed_path:
                        local_path = processed_path
                        if temp_file:
                            # Clean up original temp file
                            Path(temp_file).unlink(missing_ok=True)
                        temp_file = processed_path
                else:
                    raise TranscriptionError(
                        f"File too large: {file_size_mb:.1f}MB > {max_size_mb:.1f}MB limit"
                    )

            # Check format support
            file_extension = Path(local_path).suffix.lower()
            supported_formats = await self.transcription.get_supported_formats()

            if file_extension not in supported_formats:
                if self.audio_processor:
                    logger.info(f"Unsupported format {file_extension}, converting...")
                    processed_path = await self._process_audio(local_path)
                    if processed_path:
                        local_path = processed_path
                        if temp_file:
                            Path(temp_file).unlink(missing_ok=True)
                        temp_file = processed_path
                else:
                    raise TranscriptionError(
                        f"Unsupported format: {file_extension}. Supported: {supported_formats}"
                    )

            # Perform transcription
            logger.info(f"Transcribing file: {local_path}")
            result = await self.transcription.transcribe(local_path, options)

            logger.info(
                f"Transcription completed: {result.word_count} words, "
                f"{result.duration:.1f}s duration"
            )

            return result

        finally:
            # Clean up temp files
            if temp_file and Path(temp_file).exists():
                try:
                    Path(temp_file).unlink()
                    logger.debug(f"Cleaned up temp file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file: {e}")

    async def transcribe_batch(
        self,
        file_paths: list[str],
        options: Optional[TranscriptionOptions] = None,
        from_storage: bool = False,
    ) -> list[tuple[str, TranscriptionResult]]:
        """
        Transcribe multiple files

        Args:
            file_paths: List of file paths
            options: Transcription options
            from_storage: Whether files are in storage

        Returns:
            List of (file_path, TranscriptionResult) tuples
        """
        results = []

        for file_path in file_paths:
            try:
                result = await self.transcribe_file(file_path, options, from_storage)
                results.append((file_path, result))

            except Exception as e:
                logger.error(f"Failed to transcribe {file_path}: {str(e)}")
                # Create error result
                error_result = TranscriptionResult(
                    text="",
                    segments=[],
                    language="unknown",
                    duration=0.0,
                    processed_at=datetime.now(),
                    model="error",
                    metadata={"error": str(e)},
                )
                results.append((file_path, error_result))

        return results

    async def process_and_store(
        self, file_info: FileInfo, options: Optional[TranscriptionOptions] = None
    ) -> dict[str, Any]:
        """
        Full pipeline: download, transcribe, and store results

        Args:
            file_info: File information
            options: Transcription options

        Returns:
            Dictionary with processing results
        """
        if not self.storage:
            raise TranscriptionError("Storage provider required for process_and_store")

        try:
            # Transcribe file
            result = await self.transcribe_file(file_info.path, options, from_storage=True)

            # Prepare results for storage
            result_data = result.to_dict()
            result_data["original_file"] = file_info.name
            result_data["file_size"] = file_info.size

            # Save results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = Path(file_info.name).stem

            # Save JSON result
            json_content = self._format_json_result(result_data)
            json_path = f"processed/{timestamp}_{base_name}.json"
            json_temp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
            json_temp.write(json_content)
            json_temp.close()

            json_upload = await self.storage.upload_file(json_temp.name, json_path)
            Path(json_temp.name).unlink()

            # Save text result
            txt_content = self._format_text_result(result, file_info)
            txt_path = f"processed/{timestamp}_{base_name}.txt"
            txt_temp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
            txt_temp.write(txt_content)
            txt_temp.close()

            txt_upload = await self.storage.upload_file(txt_temp.name, txt_path)
            Path(txt_temp.name).unlink()

            return {
                "success": True,
                "file_name": file_info.name,
                "transcription": result,
                "outputs": {
                    "json": json_path if json_upload.success else None,
                    "text": txt_path if txt_upload.success else None,
                },
            }

        except Exception as e:
            logger.error(f"Failed to process and store {file_info.name}: {str(e)}")
            return {"success": False, "file_name": file_info.name, "error": str(e)}

    async def _process_audio(self, input_path: str) -> Optional[str]:
        """
        Process audio file (extract/compress)

        Args:
            input_path: Path to input file

        Returns:
            Path to processed file or None
        """
        if not self.audio_processor:
            return None

        try:
            # Use the audio processor if available
            # This would integrate with the existing audio_processor module
            output_path = await self.audio_processor.process(input_path)
            return output_path

        except Exception as e:
            logger.error(f"Audio processing failed: {str(e)}")
            return None

    def _format_json_result(self, result_data: dict[str, Any]) -> str:
        """Format result as JSON string"""
        import json

        return json.dumps(result_data, indent=2, ensure_ascii=False)

    def _format_text_result(self, result: TranscriptionResult, file_info: FileInfo) -> str:
        """Format result as human-readable text"""
        content = f"""Transcription Results
====================
Original File: {file_info.name}
File Size: {file_info.size_mb:.1f} MB
Processed: {result.processed_at.isoformat()}
Language: {result.language}
Duration: {result.duration:.1f} seconds
Model: {result.model}
Word Count: {result.word_count}

TRANSCRIPT
----------
{result.text}

DETAILED SEGMENTS
-----------------
"""

        for segment in result.segments:
            content += f"[{segment.start:.1f}s - {segment.end:.1f}s]: {segment.text}\n"

        return content
