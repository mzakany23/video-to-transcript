"""
OpenAI Whisper implementation of TranscriptionProvider
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ...core.interfaces import TranscriptionProvider
from ...core.models import (
    TranscriptionOptions,
    TranscriptionResult,
    TranscriptionSegment,
)
from ...core.exceptions import TranscriptionException, AuthenticationException

logger = logging.getLogger(__name__)

# Thread pool for blocking I/O operations
executor = ThreadPoolExecutor(max_workers=3)


class OpenAITranscriptionProvider(TranscriptionProvider):
    """
    OpenAI Whisper implementation of transcription provider
    """
    
    # OpenAI limits
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB
    SUPPORTED_FORMATS = [
        '.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', 
        '.webm', '.aac', '.oga', '.ogg', '.flac'
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI transcription provider
        
        Args:
            api_key: OpenAI API key (will read from env if not provided)
        """
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        
        if not self.api_key:
            raise AuthenticationException(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable"
            )
        
        # Initialize OpenAI client
        self._initialize_client()
        
        logger.info("Initialized OpenAITranscriptionProvider")
    
    def _initialize_client(self):
        """Initialize OpenAI client"""
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
            logger.info("OpenAI client initialized successfully")
        except ImportError:
            raise TranscriptionException(
                "OpenAI package not installed. Run: pip install openai"
            )
        except Exception as e:
            raise AuthenticationException(f"Failed to initialize OpenAI client: {str(e)}")
    
    async def transcribe(
        self,
        audio_path: str,
        options: Optional[TranscriptionOptions] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio file using OpenAI Whisper
        
        Args:
            audio_path: Path to audio file
            options: Transcription options
            
        Returns:
            TranscriptionResult
        """
        def _transcribe():
            try:
                # Check file exists
                audio_file_path = Path(audio_path)
                if not audio_file_path.exists():
                    raise TranscriptionException(f"Audio file not found: {audio_path}")
                
                # Check file size
                file_size = audio_file_path.stat().st_size
                if file_size > self.MAX_FILE_SIZE:
                    file_size_mb = file_size / (1024 * 1024)
                    max_size_mb = self.MAX_FILE_SIZE / (1024 * 1024)
                    raise TranscriptionException(
                        f"File too large: {file_size_mb:.1f}MB > {max_size_mb:.1f}MB"
                    )
                
                # Prepare options
                if options:
                    api_options = options.to_dict()
                else:
                    api_options = TranscriptionOptions().to_dict()
                
                # Ensure verbose_json for segments
                api_options['response_format'] = 'verbose_json'
                
                logger.info(
                    f"Transcribing {audio_path} "
                    f"({file_size / 1024 / 1024:.1f}MB) "
                    f"with model {api_options.get('model', 'whisper-1')}"
                )
                
                # Call OpenAI API
                with open(audio_file_path, 'rb') as audio_file:
                    transcript = self.client.audio.transcriptions.create(
                        file=audio_file,
                        model=api_options.get('model', 'whisper-1'),
                        response_format='verbose_json',
                        language=api_options.get('language'),
                        prompt=api_options.get('prompt'),
                        temperature=api_options.get('temperature', 0.0)
                    )
                
                # Process segments
                segments = []
                if hasattr(transcript, 'segments') and transcript.segments:
                    for i, segment in enumerate(transcript.segments):
                        segments.append(TranscriptionSegment(
                            id=getattr(segment, 'id', i),
                            start=getattr(segment, 'start', 0.0),
                            end=getattr(segment, 'end', 0.0),
                            text=getattr(segment, 'text', ''),
                            confidence=None  # OpenAI doesn't provide confidence
                        ))
                
                # Create result
                result = TranscriptionResult(
                    text=transcript.text,
                    segments=segments,
                    language=getattr(transcript, 'language', 'unknown'),
                    duration=getattr(transcript, 'duration', 0.0),
                    processed_at=datetime.now(),
                    model=api_options.get('model', 'whisper-1'),
                    metadata={
                        'file_path': audio_path,
                        'file_size': file_size
                    }
                )
                
                logger.info(
                    f"Transcription completed: {result.word_count} words, "
                    f"{result.duration:.1f}s duration, "
                    f"language: {result.language}"
                )
                
                return result
                
            except Exception as e:
                logger.error(f"Transcription failed for {audio_path}: {str(e)}")
                if "API" in str(e) or "authentication" in str(e).lower():
                    raise AuthenticationException(f"OpenAI API error: {str(e)}")
                raise TranscriptionException(f"Transcription failed: {str(e)}")
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, _transcribe)
    
    async def get_supported_formats(self) -> List[str]:
        """
        Get list of supported audio formats
        
        Returns:
            List of file extensions
        """
        return self.SUPPORTED_FORMATS.copy()
    
    async def get_max_file_size(self) -> int:
        """
        Get maximum supported file size in bytes
        
        Returns:
            Maximum file size in bytes
        """
        return self.MAX_FILE_SIZE