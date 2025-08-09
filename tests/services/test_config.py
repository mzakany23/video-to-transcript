"""
Unit tests for configuration system
"""

import os
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add project root to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from services.config.settings import Settings, ProviderConfig
from services.config.factory import ServiceFactory
from services.core.exceptions import ServiceException


class TestProviderConfig(unittest.TestCase):
    """Test ProviderConfig class"""
    
    def test_provider_config_creation(self):
        """Test creating a ProviderConfig"""
        config = ProviderConfig(
            provider_type="test",
            enabled=True,
            config={"key": "value"}
        )
        
        self.assertEqual(config.provider_type, "test")
        self.assertTrue(config.enabled)
        self.assertEqual(config.get("key"), "value")
        self.assertEqual(config.get("nonexistent", "default"), "default")
    
    def test_provider_config_defaults(self):
        """Test ProviderConfig with defaults"""
        config = ProviderConfig(provider_type="test")
        
        self.assertEqual(config.provider_type, "test")
        self.assertTrue(config.enabled)
        self.assertEqual(config.config, {})


class TestSettings(unittest.TestCase):
    """Test Settings class"""
    
    def test_settings_creation(self):
        """Test creating Settings with defaults"""
        settings = Settings()
        
        self.assertEqual(settings.storage_provider, "dropbox")
        self.assertEqual(settings.transcription_provider, "openai")
        self.assertEqual(settings.job_runner, "cloudrun")
        self.assertEqual(settings.environment, "production")
        
        # Check that default configs were created
        self.assertIn("dropbox", settings.storage_configs)
        self.assertIn("openai", settings.transcription_configs)
        self.assertIn("cloudrun", settings.job_runner_configs)
    
    @patch.dict(os.environ, {
        'STORAGE_PROVIDER': 'gcs',
        'TRANSCRIPTION_PROVIDER': 'openai',
        'JOB_RUNNER': 'local',
        'ENVIRONMENT': 'development',
        'LOG_LEVEL': 'DEBUG'
    })
    def test_settings_from_env(self):
        """Test creating Settings from environment variables"""
        settings = Settings.from_env()
        
        self.assertEqual(settings.storage_provider, "gcs")
        self.assertEqual(settings.transcription_provider, "openai")
        self.assertEqual(settings.job_runner, "local")
        self.assertEqual(settings.environment, "development")
        self.assertEqual(settings.log_level, "DEBUG")
    
    def test_settings_file_operations(self):
        """Test saving and loading Settings from file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_path = f.name
        
        try:
            # Create settings and save to file
            original_settings = Settings(
                storage_provider="local",
                transcription_provider="openai",
                job_runner="local",
                environment="test"
            )
            original_settings.to_file(config_path)
            
            # Load settings from file
            loaded_settings = Settings.from_file(config_path)
            
            # Verify settings match
            self.assertEqual(loaded_settings.storage_provider, "local")
            self.assertEqual(loaded_settings.transcription_provider, "openai")
            self.assertEqual(loaded_settings.job_runner, "local")
            self.assertEqual(loaded_settings.environment, "test")
            
        finally:
            os.unlink(config_path)
    
    def test_settings_file_not_found(self):
        """Test loading from non-existent file"""
        with self.assertRaises(FileNotFoundError):
            Settings.from_file("/nonexistent/config.json")
    
    def test_get_provider_configs(self):
        """Test getting provider configurations"""
        settings = Settings()
        
        # Test storage config
        storage_config = settings.get_storage_config("dropbox")
        self.assertEqual(storage_config.provider_type, "dropbox")
        
        # Test transcription config
        transcription_config = settings.get_transcription_config("openai")
        self.assertEqual(transcription_config.provider_type, "openai")
        
        # Test job runner config
        job_runner_config = settings.get_job_runner_config("cloudrun")
        self.assertEqual(job_runner_config.provider_type, "cloudrun")
        
        # Test unknown provider
        with self.assertRaises(ValueError):
            settings.get_storage_config("unknown")
    
    def test_provider_enabled_status(self):
        """Test checking if providers are enabled"""
        settings = Settings()
        
        # Test enabled provider
        self.assertTrue(settings.is_provider_enabled("storage", "local"))
        
        # Disable a provider and test
        settings.storage_configs["local"].enabled = False
        self.assertFalse(settings.is_provider_enabled("storage", "local"))
        
        # Test unknown provider type
        self.assertFalse(settings.is_provider_enabled("unknown_type", "provider"))
    
    def test_get_enabled_providers(self):
        """Test getting enabled providers"""
        settings = Settings()
        
        # Get enabled storage providers
        enabled_storage = settings.get_enabled_providers("storage")
        self.assertIn("local", enabled_storage)
        
        # Disable a provider
        settings.storage_configs["local"].enabled = False
        enabled_storage = settings.get_enabled_providers("storage")
        self.assertNotIn("local", enabled_storage)
        
        # Test unknown provider type
        enabled_unknown = settings.get_enabled_providers("unknown_type")
        self.assertEqual(enabled_unknown, {})


class TestServiceFactory(unittest.TestCase):
    """Test ServiceFactory class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.settings = Settings(
            storage_provider="local",
            transcription_provider="openai", 
            job_runner="local",
            environment="test"
        )
        
        # Mock the configurations to avoid real API calls
        self.settings.storage_configs["local"].config.update({
            "base_path": "/tmp/test_storage"
        })
        self.settings.transcription_configs["openai"].config.update({
            "api_key": "test_key",
            "model": "whisper-1"
        })
        self.settings.job_runner_configs["local"].config.update({
            "work_dir": "/tmp/test_jobs"
        })
        
        self.factory = ServiceFactory(self.settings)
    
    def test_factory_initialization(self):
        """Test ServiceFactory initialization"""
        self.assertEqual(self.factory.settings.storage_provider, "local")
        
        available_providers = self.factory.get_available_providers()
        self.assertIn("storage", available_providers)
        self.assertIn("transcription", available_providers)
        self.assertIn("job_runner", available_providers)
    
    def test_create_storage_provider(self):
        """Test creating storage providers"""
        # Test local storage provider
        provider = self.factory.create_storage_provider("local")
        self.assertIsNotNone(provider)
        
        # Test unknown provider
        with self.assertRaises(ServiceException):
            self.factory.create_storage_provider("unknown")
        
        # Test disabled provider
        self.settings.storage_configs["local"].enabled = False
        with self.assertRaises(ServiceException):
            self.factory.create_storage_provider("local")
    
    @patch('services.transcription.providers.openai.OpenAITranscriptionProvider')
    def test_create_transcription_provider(self, mock_provider):
        """Test creating transcription providers"""
        mock_instance = MagicMock()
        mock_provider.return_value = mock_instance
        
        provider = self.factory.create_transcription_provider("openai")
        self.assertEqual(provider, mock_instance)
        
        # Verify provider was called with correct config
        mock_provider.assert_called_once_with(
            api_key="test_key",
            model="whisper-1",
            max_file_size=25000000,
            supported_formats=["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm", "ogg", "flac"]
        )
    
    def test_create_job_runner(self):
        """Test creating job runners"""
        runner = self.factory.create_job_runner("local")
        self.assertIsNotNone(runner)
        
        # Test unknown runner
        with self.assertRaises(ServiceException):
            self.factory.create_job_runner("unknown")
    
    def test_create_orchestration_service(self):
        """Test creating orchestration service"""
        orchestration = self.factory.create_orchestration_service("local")
        self.assertIsNotNone(orchestration)
    
    def test_create_storage_service(self):
        """Test creating storage service"""
        storage_service = self.factory.create_storage_service("local")
        self.assertIsNotNone(storage_service)
    
    @patch('services.transcription.providers.openai.OpenAITranscriptionProvider')
    def test_create_transcription_service(self, mock_provider):
        """Test creating transcription service"""
        mock_instance = MagicMock()
        mock_provider.return_value = mock_instance
        
        transcription_service = self.factory.create_transcription_service()
        self.assertIsNotNone(transcription_service)
    
    def test_get_available_providers(self):
        """Test getting available providers information"""
        providers = self.factory.get_available_providers()
        
        # Check structure
        self.assertIn("storage", providers)
        self.assertIn("transcription", providers)
        self.assertIn("job_runner", providers)
        
        # Check storage providers
        storage_info = providers["storage"]
        self.assertIn("local", storage_info["available"])
        self.assertIn("dropbox", storage_info["available"])
        self.assertIn("gcs", storage_info["available"])
        self.assertEqual(storage_info["default"], "local")
    
    @patch('services.transcription.providers.openai.OpenAITranscriptionProvider')
    def test_validate_configuration(self, mock_provider):
        """Test configuration validation"""
        mock_instance = MagicMock()
        mock_provider.return_value = mock_instance
        
        results = self.factory.validate_configuration()
        
        self.assertIn("valid", results)
        self.assertIn("errors", results)
        self.assertIn("warnings", results)
        self.assertIn("provider_status", results)
        
        # Should be valid with our test configuration
        if not results["valid"]:
            print("Validation errors:", results["errors"])
    
    def test_register_custom_provider(self):
        """Test registering custom providers"""
        # Create mock provider class
        class MockStorageProvider:
            def __init__(self, **kwargs):
                pass
        
        # Register it
        ServiceFactory.register_storage_provider("mock", MockStorageProvider)
        
        # Verify it's available
        self.assertIn("mock", ServiceFactory.STORAGE_PROVIDERS)
    
    def test_configuration_validation_errors(self):
        """Test configuration validation with errors"""
        # Create settings with missing required config
        bad_settings = Settings()
        bad_settings.storage_configs["dropbox"].config = {}  # Missing required keys
        
        factory = ServiceFactory(bad_settings)
        results = factory.validate_configuration()
        
        # Should have errors for missing configuration
        self.assertFalse(results["valid"])
        self.assertTrue(len(results["errors"]) > 0)


if __name__ == '__main__':
    unittest.main()