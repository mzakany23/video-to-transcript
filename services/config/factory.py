"""
Service factory for creating configured service instances
"""

from typing import Optional, Type, Any
import logging

from .settings import Settings, ProviderConfig
from ..core.interfaces import StorageProvider, TranscriptionProvider, JobRunner
from ..core.exceptions import ServiceException
from ..core.logging import get_logger

# Import all providers
from ..storage.providers.dropbox import DropboxStorageProvider
from ..storage.providers.gcs import GCSStorageProvider
from ..storage.providers.local import LocalStorageProvider

from ..transcription.providers.openai import OpenAITranscriptionProvider

from ..orchestration.runners.cloudrun import CloudRunJobRunner
from ..orchestration.runners.local import LocalJobRunner

logger = get_logger(__name__)


class ServiceFactory:
    """
    Factory for creating configured service instances
    """
    
    # Registry of available providers
    STORAGE_PROVIDERS = {
        "dropbox": DropboxStorageProvider,
        "gcs": GCSStorageProvider,
        "local": LocalStorageProvider,
    }
    
    TRANSCRIPTION_PROVIDERS = {
        "openai": OpenAITranscriptionProvider,
    }
    
    JOB_RUNNERS = {
        "cloudrun": CloudRunJobRunner,
        "local": LocalJobRunner,
    }
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize service factory
        
        Args:
            settings: Configuration settings, uses environment if None
        """
        self.settings = settings or Settings.from_env()
        logger.info(f"ServiceFactory initialized with {len(self.get_available_providers())} providers")
    
    def create_storage_provider(self, provider_name: Optional[str] = None) -> StorageProvider:
        """
        Create a storage provider instance
        
        Args:
            provider_name: Provider name, uses default from settings if None
            
        Returns:
            Configured StorageProvider instance
        """
        provider_name = provider_name or self.settings.storage_provider
        
        if provider_name not in self.STORAGE_PROVIDERS:
            available = ", ".join(self.STORAGE_PROVIDERS.keys())
            raise ServiceException(f"Unknown storage provider: {provider_name}. Available: {available}")
        
        config = self.settings.get_storage_config(provider_name)
        if not config.enabled:
            raise ServiceException(f"Storage provider '{provider_name}' is disabled")
        
        provider_class = self.STORAGE_PROVIDERS[provider_name]
        
        try:
            # Create provider instance with configuration
            if provider_name == "dropbox":
                # Dropbox provider constructor takes dropbox_client, raw_folder, processed_folder
                return provider_class(
                    dropbox_client=None,  # Let it create its own client
                    raw_folder=config.get("raw_folder", "/transcripts/raw"),
                    processed_folder=config.get("processed_folder", "/transcripts/processed"),
                )
            elif provider_name == "gcs":
                return provider_class(
                    project_id=config.get("project_id"),
                    bucket_name=config.get("bucket_name"),
                    credentials_path=config.get("credentials_path"),
                )
            elif provider_name == "local":
                return provider_class(
                    base_path=config.get("base_path"),
                )
            else:
                # Generic instantiation
                return provider_class(**config.config)
                
        except Exception as e:
            logger.error(f"Failed to create storage provider '{provider_name}': {str(e)}")
            raise ServiceException(f"Storage provider creation failed: {str(e)}")
    
    def create_transcription_provider(self, provider_name: Optional[str] = None) -> TranscriptionProvider:
        """
        Create a transcription provider instance
        
        Args:
            provider_name: Provider name, uses default from settings if None
            
        Returns:
            Configured TranscriptionProvider instance
        """
        provider_name = provider_name or self.settings.transcription_provider
        
        if provider_name not in self.TRANSCRIPTION_PROVIDERS:
            available = ", ".join(self.TRANSCRIPTION_PROVIDERS.keys())
            raise ServiceException(f"Unknown transcription provider: {provider_name}. Available: {available}")
        
        config = self.settings.get_transcription_config(provider_name)
        if not config.enabled:
            raise ServiceException(f"Transcription provider '{provider_name}' is disabled")
        
        provider_class = self.TRANSCRIPTION_PROVIDERS[provider_name]
        
        try:
            # Create provider instance with configuration
            if provider_name == "openai":
                # OpenAI provider constructor only takes api_key
                return provider_class(
                    api_key=config.get("api_key"),
                )
            else:
                # Generic instantiation
                return provider_class(**config.config)
                
        except Exception as e:
            logger.error(f"Failed to create transcription provider '{provider_name}': {str(e)}")
            raise ServiceException(f"Transcription provider creation failed: {str(e)}")
    
    def create_job_runner(self, runner_name: Optional[str] = None) -> JobRunner:
        """
        Create a job runner instance
        
        Args:
            runner_name: Runner name, uses default from settings if None
            
        Returns:
            Configured JobRunner instance
        """
        runner_name = runner_name or self.settings.job_runner
        
        if runner_name not in self.JOB_RUNNERS:
            available = ", ".join(self.JOB_RUNNERS.keys())
            raise ServiceException(f"Unknown job runner: {runner_name}. Available: {available}")
        
        config = self.settings.get_job_runner_config(runner_name)
        if not config.enabled:
            raise ServiceException(f"Job runner '{runner_name}' is disabled")
        
        runner_class = self.JOB_RUNNERS[runner_name]
        
        try:
            # Create runner instance with configuration
            if runner_name == "cloudrun":
                return runner_class(
                    project_id=config.get("project_id"),
                    region=config.get("region", "us-east1"),
                    job_name=config.get("job_name", "transcription-worker"),
                )
            elif runner_name == "local":
                return runner_class(
                    work_dir=config.get("work_dir", "./.local_jobs"),
                )
            else:
                # Generic instantiation
                return runner_class(**config.config)
                
        except Exception as e:
            logger.error(f"Failed to create job runner '{runner_name}': {str(e)}")
            raise ServiceException(f"Job runner creation failed: {str(e)}")
    
    def create_orchestration_service(
        self,
        job_runner_name: Optional[str] = None
    ):
        """
        Create an orchestration service with configured job runner
        
        Args:
            job_runner_name: Job runner name, uses default from settings if None
            
        Returns:
            Configured OrchestrationService instance
        """
        from ..orchestration.service import OrchestrationService
        
        job_runner = self.create_job_runner(job_runner_name)
        return OrchestrationService(job_runner)
    
    def create_storage_service(
        self,
        provider_name: Optional[str] = None
    ):
        """
        Create a storage service with configured provider
        
        Args:
            provider_name: Storage provider name, uses default from settings if None
            
        Returns:
            Configured StorageService instance
        """
        from ..storage.service import StorageService
        
        provider = self.create_storage_provider(provider_name)
        return StorageService(provider)
    
    def create_transcription_service(
        self,
        transcription_provider_name: Optional[str] = None,
        storage_provider_name: Optional[str] = None
    ):
        """
        Create a transcription service with configured providers
        
        Args:
            transcription_provider_name: Transcription provider name
            storage_provider_name: Storage provider name
            
        Returns:
            Configured TranscriptionService instance
        """
        from ..transcription.service import TranscriptionService
        
        transcription_provider = self.create_transcription_provider(transcription_provider_name)
        storage_provider = self.create_storage_provider(storage_provider_name)
        
        return TranscriptionService(transcription_provider, storage_provider)
    
    def get_available_providers(self) -> dict:
        """
        Get information about all available providers
        
        Returns:
            Dictionary with provider information
        """
        return {
            "storage": {
                "available": list(self.STORAGE_PROVIDERS.keys()),
                "default": self.settings.storage_provider,
                "enabled": list(self.settings.get_enabled_providers("storage").keys())
            },
            "transcription": {
                "available": list(self.TRANSCRIPTION_PROVIDERS.keys()),
                "default": self.settings.transcription_provider,
                "enabled": list(self.settings.get_enabled_providers("transcription").keys())
            },
            "job_runner": {
                "available": list(self.JOB_RUNNERS.keys()),
                "default": self.settings.job_runner,
                "enabled": list(self.settings.get_enabled_providers("job_runner").keys())
            }
        }
    
    def validate_configuration(self) -> dict:
        """
        Validate current configuration and return status
        
        Returns:
            Dictionary with validation results
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "provider_status": {}
        }
        
        # Check each provider type
        for provider_type in ["storage", "transcription", "job_runner"]:
            try:
                if provider_type == "storage":
                    provider = self.create_storage_provider()
                    results["provider_status"]["storage"] = {
                        "name": self.settings.storage_provider,
                        "status": "valid"
                    }
                elif provider_type == "transcription":
                    provider = self.create_transcription_provider()
                    results["provider_status"]["transcription"] = {
                        "name": self.settings.transcription_provider,
                        "status": "valid"
                    }
                elif provider_type == "job_runner":
                    provider = self.create_job_runner()
                    results["provider_status"]["job_runner"] = {
                        "name": self.settings.job_runner,
                        "status": "valid"
                    }
                    
            except ServiceException as e:
                results["valid"] = False
                results["errors"].append(f"{provider_type}: {str(e)}")
                results["provider_status"][provider_type] = {
                    "name": getattr(self.settings, f"{provider_type}_provider", "unknown"),
                    "status": "error",
                    "error": str(e)
                }
            except Exception as e:
                results["valid"] = False
                results["errors"].append(f"{provider_type}: Unexpected error - {str(e)}")
                results["provider_status"][provider_type] = {
                    "name": getattr(self.settings, f"{provider_type}_provider", "unknown"),
                    "status": "error",
                    "error": str(e)
                }
        
        # Check for missing configuration
        enabled_providers = {
            "storage": self.settings.get_enabled_providers("storage"),
            "transcription": self.settings.get_enabled_providers("transcription"),
            "job_runner": self.settings.get_enabled_providers("job_runner"),
        }
        
        for provider_type, providers in enabled_providers.items():
            if not providers:
                results["warnings"].append(f"No enabled {provider_type} providers")
        
        return results
    
    @classmethod
    def register_storage_provider(cls, name: str, provider_class: Type[StorageProvider]):
        """
        Register a new storage provider
        
        Args:
            name: Provider name
            provider_class: Provider class
        """
        cls.STORAGE_PROVIDERS[name] = provider_class
        logger.info(f"Registered storage provider: {name}")
    
    @classmethod
    def register_transcription_provider(cls, name: str, provider_class: Type[TranscriptionProvider]):
        """
        Register a new transcription provider
        
        Args:
            name: Provider name
            provider_class: Provider class
        """
        cls.TRANSCRIPTION_PROVIDERS[name] = provider_class
        logger.info(f"Registered transcription provider: {name}")
    
    @classmethod
    def register_job_runner(cls, name: str, runner_class: Type[JobRunner]):
        """
        Register a new job runner
        
        Args:
            name: Runner name
            runner_class: Runner class
        """
        cls.JOB_RUNNERS[name] = runner_class
        logger.info(f"Registered job runner: {name}")