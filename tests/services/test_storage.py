"""
Unit tests for storage service and providers
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import asyncio
from datetime import datetime
from pathlib import Path
import tempfile

from services.storage import StorageService
from services.storage.providers import DropboxStorageProvider
from services.core.models import FileInfo, DownloadResult, UploadResult
from services.core.exceptions import StorageException


class TestStorageService(unittest.TestCase):
    """Test StorageService functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_provider = Mock()
        self.service = StorageService(self.mock_provider)
    
    def test_initialization(self):
        """Test service initialization"""
        self.assertIsNotNone(self.service)
        self.assertEqual(self.service.provider, self.mock_provider)
    
    def test_download_file_success(self):
        """Test successful file download"""
        # Mock provider response
        self.mock_provider.download = AsyncMock(return_value=DownloadResult(
            success=True,
            local_path="/tmp/test.mp3",
            size=1024
        ))
        
        # Run async test
        async def run_test():
            result = await self.service.download_file("test.mp3")
            self.assertTrue(result.success)
            self.assertEqual(result.local_path, "/tmp/test.mp3")
            self.assertEqual(result.size, 1024)
        
        asyncio.run(run_test())
    
    def test_download_file_failure(self):
        """Test failed file download"""
        self.mock_provider.download = AsyncMock(return_value=DownloadResult(
            success=False,
            error="Network error"
        ))
        
        async def run_test():
            result = await self.service.download_file("test.mp3")
            self.assertFalse(result.success)
            self.assertEqual(result.error, "Network error")
        
        asyncio.run(run_test())
    
    def test_upload_file_success(self):
        """Test successful file upload"""
        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name
        
        try:
            self.mock_provider.upload = AsyncMock(return_value=UploadResult(
                success=True,
                storage_path="/uploaded/test.mp3",
                size=12
            ))
            
            async def run_test():
                result = await self.service.upload_file(
                    tmp_path,
                    "/uploaded/test.mp3"
                )
                self.assertTrue(result.success)
                self.assertEqual(result.storage_path, "/uploaded/test.mp3")
            
            asyncio.run(run_test())
            
        finally:
            Path(tmp_path).unlink()
    
    def test_upload_file_not_found(self):
        """Test upload with non-existent file"""
        async def run_test():
            with self.assertRaises(StorageException):
                await self.service.upload_file(
                    "/nonexistent/file.mp3",
                    "/destination/file.mp3"
                )
        
        asyncio.run(run_test())
    
    def test_list_files(self):
        """Test listing files"""
        mock_files = [
            FileInfo(
                path="/test/file1.mp3",
                name="file1.mp3",
                size=1024,
                modified=datetime.now()
            ),
            FileInfo(
                path="/test/file2.mp3",
                name="file2.mp3",
                size=2048,
                modified=datetime.now()
            )
        ]
        
        self.mock_provider.list_files = AsyncMock(return_value=mock_files)
        
        async def run_test():
            files = await self.service.list_files("/test", "*.mp3")
            self.assertEqual(len(files), 2)
            self.assertEqual(files[0].name, "file1.mp3")
            self.assertEqual(files[1].name, "file2.mp3")
        
        asyncio.run(run_test())
    
    def test_batch_download(self):
        """Test batch download functionality"""
        self.mock_provider.download = AsyncMock(side_effect=[
            DownloadResult(success=True, local_path="/tmp/file1.mp3", size=1024),
            DownloadResult(success=True, local_path="/tmp/file2.mp3", size=2048),
            DownloadResult(success=False, error="Failed")
        ])
        
        async def run_test():
            results = await self.service.batch_download(
                ["file1.mp3", "file2.mp3", "file3.mp3"],
                "/tmp"
            )
            
            self.assertEqual(len(results), 3)
            self.assertTrue(results[0].success)
            self.assertTrue(results[1].success)
            self.assertFalse(results[2].success)
        
        asyncio.run(run_test())


class TestDropboxStorageProvider(unittest.TestCase):
    """Test DropboxStorageProvider functionality"""
    
    @patch('services.storage.providers.dropbox.dropbox')
    def setUp(self, mock_dropbox_module):
        """Set up test fixtures"""
        self.mock_client = Mock()
        self.provider = DropboxStorageProvider(
            dropbox_client=self.mock_client,
            raw_folder="/test/raw",
            processed_folder="/test/processed"
        )
    
    def test_initialization(self):
        """Test provider initialization"""
        self.assertIsNotNone(self.provider)
        self.assertEqual(self.provider.raw_folder, "/test/raw")
        self.assertEqual(self.provider.processed_folder, "/test/processed")
    
    @patch('services.storage.providers.dropbox.executor')
    def test_download_success(self, mock_executor):
        """Test successful download from Dropbox"""
        # Mock Dropbox response
        mock_response = Mock()
        mock_response.content = b"file content"
        mock_metadata = Mock()
        mock_metadata.id = "test_id"
        mock_metadata.rev = "test_rev"
        mock_metadata.server_modified = datetime.now()
        
        self.mock_client.files_download.return_value = (mock_metadata, mock_response)
        
        # Mock executor to run synchronously
        mock_executor.submit = Mock(side_effect=lambda fn, *args: Mock(
            result=lambda: fn(*args)
        ))
        
        async def run_test():
            with tempfile.TemporaryDirectory() as tmpdir:
                dest_path = f"{tmpdir}/test.mp3"
                
                # Patch the executor in the provider
                with patch.object(self.provider, '_run_sync') as mock_run:
                    # Make it run the coroutine directly
                    mock_run.return_value = DownloadResult(
                        success=True,
                        local_path=dest_path,
                        size=12
                    )
                    
                    result = await self.provider.download("/test.mp3", dest_path)
                    
                    self.assertTrue(result.success)
                    self.assertEqual(result.local_path, dest_path)
        
        asyncio.run(run_test())
    
    def test_list_files(self):
        """Test listing files in Dropbox"""
        # Mock Dropbox list response
        mock_entry1 = Mock()
        mock_entry1.name = "file1.mp3"
        mock_entry1.path_display = "/test/raw/file1.mp3"
        mock_entry1.size = 1024
        mock_entry1.server_modified = datetime.now()
        mock_entry1.id = "id1"
        mock_entry1.rev = "rev1"
        mock_entry1.is_deleted = False
        
        mock_entry2 = Mock()
        mock_entry2.name = "file2.mp4"
        mock_entry2.path_display = "/test/raw/file2.mp4"
        mock_entry2.size = 2048
        mock_entry2.server_modified = datetime.now()
        mock_entry2.id = "id2"
        mock_entry2.rev = "rev2"
        mock_entry2.is_deleted = False
        
        mock_result = Mock()
        mock_result.entries = [mock_entry1, mock_entry2]
        mock_result.has_more = False
        
        self.mock_client.files_list_folder.return_value = mock_result
        
        async def run_test():
            # Patch executor to run synchronously
            with patch('services.storage.providers.dropbox.executor'):
                with patch.object(self.provider, '_run_sync') as mock_run:
                    mock_run.return_value = [
                        FileInfo(
                            path="/test/raw/file1.mp3",
                            name="file1.mp3",
                            size=1024,
                            modified=datetime.now()
                        ),
                        FileInfo(
                            path="/test/raw/file2.mp4",
                            name="file2.mp4",
                            size=2048,
                            modified=datetime.now()
                        )
                    ]
                    
                    files = await self.provider.list_files("/test/raw")
                    
                    self.assertEqual(len(files), 2)
                    self.assertEqual(files[0].name, "file1.mp3")
                    self.assertEqual(files[1].name, "file2.mp4")
        
        asyncio.run(run_test())


class TestStorageProviderContract(unittest.TestCase):
    """Contract tests to ensure all providers implement the interface correctly"""
    
    def test_dropbox_provider_implements_interface(self):
        """Test that DropboxStorageProvider implements all required methods"""
        from services.core.interfaces import StorageProvider
        
        # Check that DropboxStorageProvider is a subclass
        self.assertTrue(issubclass(DropboxStorageProvider, StorageProvider))
        
        # Check all required methods exist
        required_methods = [
            'download', 'upload', 'list_files', 'delete', 'exists'
        ]
        
        for method_name in required_methods:
            self.assertTrue(
                hasattr(DropboxStorageProvider, method_name),
                f"DropboxStorageProvider missing method: {method_name}"
            )


if __name__ == '__main__':
    unittest.main()