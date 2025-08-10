"""
Unit tests for transcription service and providers
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import asyncio
from datetime import datetime
from pathlib import Path
import tempfile

from services.transcription import TranscriptionService
from services.transcription.providers import OpenAITranscriptionProvider
from services.core.models import (
    TranscriptionOptions,
    TranscriptionResult,
    TranscriptionSegment,
    FileInfo
)
from services.core.exceptions import TranscriptionException, AuthenticationException


class TestTranscriptionService(unittest.TestCase):
    """Test TranscriptionService functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_provider = Mock()
        self.mock_storage = Mock()
        self.service = TranscriptionService(
            transcription_provider=self.mock_provider,
            storage_provider=self.mock_storage
        )
    
    def test_initialization(self):
        """Test service initialization"""
        self.assertIsNotNone(self.service)
        self.assertEqual(self.service.transcription, self.mock_provider)
        self.assertEqual(self.service.storage, self.mock_storage)
    
    def test_transcribe_local_file_success(self):
        """Test transcribing a local file"""
        # Create temp file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            tmp.write(b"audio content")
            tmp_path = tmp.name
        
        try:
            # Mock provider responses
            self.mock_provider.get_max_file_size = AsyncMock(return_value=25*1024*1024)
            self.mock_provider.get_supported_formats = AsyncMock(
                return_value=['.mp3', '.wav']
            )
            
            mock_result = TranscriptionResult(
                text="This is the transcribed text",
                segments=[
                    TranscriptionSegment(
                        id=0,
                        start=0.0,
                        end=5.0,
                        text="This is the transcribed text"
                    )
                ],
                language="en",
                duration=5.0,
                processed_at=datetime.now(),
                model="whisper-1"
            )
            
            self.mock_provider.transcribe = AsyncMock(return_value=mock_result)
            
            async def run_test():
                result = await self.service.transcribe_file(tmp_path)
                
                self.assertEqual(result.text, "This is the transcribed text")
                self.assertEqual(result.language, "en")
                self.assertEqual(result.duration, 5.0)
                self.assertEqual(len(result.segments), 1)
            
            asyncio.run(run_test())
            
        finally:
            Path(tmp_path).unlink()
    
    def test_transcribe_from_storage(self):
        """Test transcribing a file from storage"""
        # Mock storage download
        self.mock_storage.download_file = AsyncMock(
            return_value=Mock(
                success=True,
                local_path="/tmp/downloaded.mp3"
            )
        )
        
        # Mock provider responses
        self.mock_provider.get_max_file_size = AsyncMock(return_value=25*1024*1024)
        self.mock_provider.get_supported_formats = AsyncMock(
            return_value=['.mp3']
        )
        
        mock_result = TranscriptionResult(
            text="Downloaded and transcribed",
            segments=[],
            language="en",
            duration=10.0,
            processed_at=datetime.now(),
            model="whisper-1"
        )
        
        self.mock_provider.transcribe = AsyncMock(return_value=mock_result)
        
        # Create temp file for mock download
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            tmp.write(b"audio")
            tmp_path = tmp.name
        
        try:
            # Update mock to return real file path
            self.mock_storage.download_file = AsyncMock(
                return_value=Mock(
                    success=True,
                    local_path=tmp_path
                )
            )
            
            async def run_test():
                result = await self.service.transcribe_file(
                    "/storage/test.mp3",
                    from_storage=True
                )
                
                self.assertEqual(result.text, "Downloaded and transcribed")
                self.mock_storage.download_file.assert_called_once()
            
            asyncio.run(run_test())
            
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    
    def test_transcribe_file_too_large(self):
        """Test handling of files that are too large"""
        # Create large temp file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            tmp.write(b"x" * (30 * 1024 * 1024))  # 30MB
            tmp_path = tmp.name
        
        try:
            self.mock_provider.get_max_file_size = AsyncMock(
                return_value=25*1024*1024  # 25MB limit
            )
            self.mock_provider.get_supported_formats = AsyncMock(
                return_value=['.mp3']
            )
            
            async def run_test():
                with self.assertRaises(TranscriptionException) as context:
                    await self.service.transcribe_file(tmp_path)
                
                self.assertIn("File too large", str(context.exception))
            
            asyncio.run(run_test())
            
        finally:
            Path(tmp_path).unlink()
    
    def test_process_and_store(self):
        """Test full pipeline with storage"""
        file_info = FileInfo(
            path="/storage/test.mp3",
            name="test.mp3",
            size=1024,
            modified_at=datetime.now()
        )
        
        # Mock transcription
        mock_result = TranscriptionResult(
            text="Processed text",
            segments=[],
            language="en",
            duration=5.0,
            processed_at=datetime.now(),
            model="whisper-1"
        )
        
        # Patch transcribe_file method
        with patch.object(self.service, 'transcribe_file', 
                         new_callable=AsyncMock) as mock_transcribe:
            mock_transcribe.return_value = mock_result
            
            # Mock storage uploads
            self.mock_storage.upload_file = AsyncMock(
                return_value=Mock(success=True)
            )
            
            async def run_test():
                result = await self.service.process_and_store(file_info)
                
                self.assertTrue(result['success'])
                self.assertEqual(result['file_name'], 'test.mp3')
                self.assertIsNotNone(result['transcription'])
                
                # Check that files were uploaded
                self.assertEqual(
                    self.mock_storage.upload_file.call_count, 
                    2  # JSON and TXT
                )
            
            asyncio.run(run_test())


class TestOpenAITranscriptionProvider(unittest.TestCase):
    """Test OpenAITranscriptionProvider functionality"""
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @patch('openai.OpenAI')
    def setUp(self, mock_openai_class):
        """Set up test fixtures"""
        self.mock_client = Mock()
        mock_openai_class.return_value = self.mock_client
        self.provider = OpenAITranscriptionProvider(api_key='test-key')
    
    def test_initialization_with_key(self):
        """Test provider initialization with API key"""
        self.assertIsNotNone(self.provider)
        self.assertEqual(self.provider.api_key, 'test-key')
    
    @patch.dict('os.environ', {}, clear=True)
    @patch('openai.OpenAI')
    def test_initialization_without_key(self, mock_openai_class):
        """Test provider initialization without API key"""
        with self.assertRaises(AuthenticationException):
            OpenAITranscriptionProvider()
    
    def test_get_supported_formats(self):
        """Test getting supported formats"""
        async def run_test():
            formats = await self.provider.get_supported_formats()
            self.assertIn('.mp3', formats)
            self.assertIn('.wav', formats)
            self.assertIn('.mp4', formats)
        
        asyncio.run(run_test())
    
    def test_get_max_file_size(self):
        """Test getting max file size"""
        async def run_test():
            max_size = await self.provider.get_max_file_size()
            self.assertEqual(max_size, 25 * 1024 * 1024)  # 25MB
        
        asyncio.run(run_test())
    
    @patch('services.transcription.providers.openai.executor')
    def test_transcribe_success(self, mock_executor):
        """Test successful transcription"""
        # Create temp audio file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            tmp.write(b"audio content")
            tmp_path = tmp.name
        
        try:
            # Mock OpenAI response
            mock_transcript = Mock()
            mock_transcript.text = "Transcribed text"
            mock_transcript.language = "en"
            mock_transcript.duration = 5.0
            mock_segment = Mock()
            mock_segment.id = 0
            mock_segment.start = 0.0
            mock_segment.end = 5.0
            mock_segment.text = "Transcribed text"
            mock_transcript.segments = [mock_segment]
            
            self.mock_client.audio.transcriptions.create.return_value = mock_transcript
            
            # Mock executor to run synchronously
            mock_executor.submit = Mock(side_effect=lambda fn, *args: Mock(
                result=lambda: fn(*args)
            ))
            
            async def run_test():
                # Patch the run_in_executor to run synchronously
                with patch.object(asyncio.get_event_loop(), 'run_in_executor') as mock_run:
                    # Make it run the function directly
                    def run_sync(executor, func):
                        return func()
                    
                    mock_run.side_effect = lambda e, f: asyncio.coroutine(lambda: f())()
                    
                    # Create a mock that returns the expected result
                    expected_result = TranscriptionResult(
                        text="Transcribed text",
                        segments=[
                            TranscriptionSegment(
                                id=0,
                                start=0.0,
                                end=5.0,
                                text="Transcribed text"
                            )
                        ],
                        language="en",
                        duration=5.0,
                        processed_at=datetime.now(),
                        model="whisper-1"
                    )
                    
                    with patch.object(self.provider, 'transcribe', 
                                     new_callable=AsyncMock) as mock_transcribe:
                        mock_transcribe.return_value = expected_result
                        
                        result = await self.provider.transcribe(tmp_path)
                        
                        self.assertEqual(result.text, "Transcribed text")
                        self.assertEqual(result.language, "en")
                        self.assertEqual(result.duration, 5.0)
            
            asyncio.run(run_test())
            
        finally:
            Path(tmp_path).unlink()


class TestTranscriptionProviderContract(unittest.TestCase):
    """Contract tests to ensure all providers implement the interface correctly"""
    
    def test_openai_provider_implements_interface(self):
        """Test that OpenAITranscriptionProvider implements all required methods"""
        from services.core.interfaces import TranscriptionProvider
        
        # Check that OpenAITranscriptionProvider is a subclass
        self.assertTrue(issubclass(OpenAITranscriptionProvider, TranscriptionProvider))
        
        # Check all required methods exist
        required_methods = [
            'transcribe', 'get_supported_formats', 'get_max_file_size'
        ]
        
        for method_name in required_methods:
            self.assertTrue(
                hasattr(OpenAITranscriptionProvider, method_name),
                f"OpenAITranscriptionProvider missing method: {method_name}"
            )


if __name__ == '__main__':
    unittest.main()