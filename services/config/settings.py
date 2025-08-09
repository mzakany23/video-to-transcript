"""
Configuration settings for services
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
import json
import logging

from ..core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ProviderConfig:
    """Configuration for a service provider"""
    provider_type: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with default"""
        return self.config.get(key, default)


@dataclass 
class Settings:
    """
    Central configuration for all services
    """
    
    # Storage settings
    storage_provider: str = "dropbox"
    storage_configs: Dict[str, ProviderConfig] = field(default_factory=dict)
    
    # Transcription settings  
    transcription_provider: str = "openai"
    transcription_configs: Dict[str, ProviderConfig] = field(default_factory=dict)
    
    # Job runner settings
    job_runner: str = "cloudrun"
    job_runner_configs: Dict[str, ProviderConfig] = field(default_factory=dict)
    
    # Notification settings
    notification_provider: str = "email"
    notification_configs: Dict[str, ProviderConfig] = field(default_factory=dict)
    
    # General settings
    environment: str = "production"
    log_level: str = "INFO"
    log_format: str = "json"
    service_name: str = "transcription-service"
    
    def __post_init__(self):
        """Initialize default configurations"""
        if not self.storage_configs:
            self.storage_configs = self._get_default_storage_configs()
        
        if not self.transcription_configs:
            self.transcription_configs = self._get_default_transcription_configs()
            
        if not self.job_runner_configs:
            self.job_runner_configs = self._get_default_job_runner_configs()
            
        if not self.notification_configs:
            self.notification_configs = self._get_default_notification_configs()
    
    def _get_default_storage_configs(self) -> Dict[str, ProviderConfig]:
        """Get default storage provider configurations"""
        return {
            "dropbox": ProviderConfig(
                provider_type="dropbox",
                enabled=True,
                config={
                    "app_key": os.environ.get("DROPBOX_APP_KEY"),
                    "app_secret": os.environ.get("DROPBOX_APP_SECRET"),
                    "refresh_token": os.environ.get("DROPBOX_REFRESH_TOKEN"),
                }
            ),
            "gcs": ProviderConfig(
                provider_type="gcs",
                enabled=bool(os.environ.get("GCS_BUCKET")),
                config={
                    "project_id": os.environ.get("PROJECT_ID"),
                    "bucket_name": os.environ.get("GCS_BUCKET"),
                    "credentials_path": os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
                }
            ),
            "local": ProviderConfig(
                provider_type="local",
                enabled=True,
                config={
                    "base_path": os.environ.get("LOCAL_STORAGE_PATH", "./local_storage"),
                }
            )
        }
    
    def _get_default_transcription_configs(self) -> Dict[str, ProviderConfig]:
        """Get default transcription provider configurations"""
        return {
            "openai": ProviderConfig(
                provider_type="openai",
                enabled=bool(os.environ.get("OPENAI_API_KEY")),
                config={
                    "api_key": os.environ.get("OPENAI_API_KEY"),
                    "model": os.environ.get("WHISPER_MODEL", "whisper-1"),
                    "max_file_size": int(os.environ.get("MAX_FILE_SIZE", "25000000")),
                    "supported_formats": [
                        "mp3", "mp4", "mpeg", "mpga", "m4a", 
                        "wav", "webm", "ogg", "flac"
                    ],
                }
            )
        }
    
    def _get_default_job_runner_configs(self) -> Dict[str, ProviderConfig]:
        """Get default job runner configurations"""
        return {
            "cloudrun": ProviderConfig(
                provider_type="cloudrun",
                enabled=bool(os.environ.get("PROJECT_ID")),
                config={
                    "project_id": os.environ.get("PROJECT_ID"),
                    "region": os.environ.get("GCP_REGION", "us-east1"),
                    "job_name": os.environ.get("WORKER_JOB_NAME", "transcription-worker"),
                }
            ),
            "local": ProviderConfig(
                provider_type="local", 
                enabled=True,
                config={
                    "work_dir": os.environ.get("LOCAL_JOB_DIR", "./.local_jobs"),
                }
            )
        }
    
    def _get_default_notification_configs(self) -> Dict[str, ProviderConfig]:
        """Get default notification provider configurations"""
        return {
            "email": ProviderConfig(
                provider_type="email",
                enabled=bool(os.environ.get("EMAIL_USER")),
                config={
                    "smtp_server": os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
                    "smtp_port": int(os.environ.get("SMTP_PORT", "587")),
                    "email_user": os.environ.get("EMAIL_USER"),
                    "email_password": os.environ.get("EMAIL_PASSWORD"),
                    "recipients": os.environ.get("EMAIL_RECIPIENTS", "").split(",") if os.environ.get("EMAIL_RECIPIENTS") else [],
                }
            )
        }
    
    def get_storage_config(self, provider: Optional[str] = None) -> ProviderConfig:
        """
        Get storage provider configuration
        
        Args:
            provider: Provider name, uses default if None
            
        Returns:
            ProviderConfig for the storage provider
        """
        provider_name = provider or self.storage_provider
        if provider_name not in self.storage_configs:
            raise ValueError(f"Unknown storage provider: {provider_name}")
        return self.storage_configs[provider_name]
    
    def get_transcription_config(self, provider: Optional[str] = None) -> ProviderConfig:
        """
        Get transcription provider configuration
        
        Args:
            provider: Provider name, uses default if None
            
        Returns:
            ProviderConfig for the transcription provider
        """
        provider_name = provider or self.transcription_provider
        if provider_name not in self.transcription_configs:
            raise ValueError(f"Unknown transcription provider: {provider_name}")
        return self.transcription_configs[provider_name]
    
    def get_job_runner_config(self, provider: Optional[str] = None) -> ProviderConfig:
        """
        Get job runner configuration
        
        Args:
            provider: Provider name, uses default if None
            
        Returns:
            ProviderConfig for the job runner
        """
        provider_name = provider or self.job_runner
        if provider_name not in self.job_runner_configs:
            raise ValueError(f"Unknown job runner: {provider_name}")
        return self.job_runner_configs[provider_name]
    
    def get_notification_config(self, provider: Optional[str] = None) -> ProviderConfig:
        """
        Get notification provider configuration
        
        Args:
            provider: Provider name, uses default if None
            
        Returns:
            ProviderConfig for the notification provider
        """
        provider_name = provider or self.notification_provider
        if provider_name not in self.notification_configs:
            raise ValueError(f"Unknown notification provider: {provider_name}")
        return self.notification_configs[provider_name]
    
    @classmethod
    def from_env(cls) -> 'Settings':
        """
        Create settings from environment variables
        
        Returns:
            Settings instance configured from environment
        """
        return cls(
            # Provider selections
            storage_provider=os.environ.get("STORAGE_PROVIDER", "dropbox"),
            transcription_provider=os.environ.get("TRANSCRIPTION_PROVIDER", "openai"),
            job_runner=os.environ.get("JOB_RUNNER", "cloudrun"),
            notification_provider=os.environ.get("NOTIFICATION_PROVIDER", "email"),
            
            # General settings
            environment=os.environ.get("ENVIRONMENT", "production"),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
            log_format=os.environ.get("LOG_FORMAT", "json"),
            service_name=os.environ.get("SERVICE_NAME", "transcription-service"),
        )
    
    @classmethod
    def from_file(cls, config_path: str) -> 'Settings':
        """
        Load settings from JSON configuration file
        
        Args:
            config_path: Path to JSON configuration file
            
        Returns:
            Settings instance
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            # Convert provider configs from dict to ProviderConfig objects
            for provider_type in ['storage_configs', 'transcription_configs', 'job_runner_configs', 'notification_configs']:
                if provider_type in config_data:
                    provider_configs = {}
                    for name, config in config_data[provider_type].items():
                        provider_configs[name] = ProviderConfig(
                            provider_type=config.get('provider_type', name),
                            enabled=config.get('enabled', True),
                            config=config.get('config', {})
                        )
                    config_data[provider_type] = provider_configs
            
            return cls(**config_data)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise ValueError(f"Error loading configuration: {e}")
    
    def to_file(self, config_path: str):
        """
        Save settings to JSON configuration file
        
        Args:
            config_path: Path to save configuration file
        """
        config_data = {
            # Provider selections
            "storage_provider": self.storage_provider,
            "transcription_provider": self.transcription_provider,
            "job_runner": self.job_runner,
            "notification_provider": self.notification_provider,
            
            # General settings
            "environment": self.environment,
            "log_level": self.log_level,
            "log_format": self.log_format,
            "service_name": self.service_name,
            
            # Provider configurations
            "storage_configs": {
                name: {
                    "provider_type": config.provider_type,
                    "enabled": config.enabled,
                    "config": config.config
                }
                for name, config in self.storage_configs.items()
            },
            "transcription_configs": {
                name: {
                    "provider_type": config.provider_type,
                    "enabled": config.enabled,
                    "config": config.config
                }
                for name, config in self.transcription_configs.items()
            },
            "job_runner_configs": {
                name: {
                    "provider_type": config.provider_type,
                    "enabled": config.enabled,
                    "config": config.config
                }
                for name, config in self.job_runner_configs.items()
            },
            "notification_configs": {
                name: {
                    "provider_type": config.provider_type,
                    "enabled": config.enabled,
                    "config": config.config
                }
                for name, config in self.notification_configs.items()
            }
        }
        
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        logger.info(f"Configuration saved to: {config_path}")
    
    def is_provider_enabled(self, provider_type: str, provider_name: str) -> bool:
        """
        Check if a provider is enabled
        
        Args:
            provider_type: Type of provider (storage, transcription, etc.)
            provider_name: Name of the provider
            
        Returns:
            True if provider is enabled
        """
        configs_map = {
            "storage": self.storage_configs,
            "transcription": self.transcription_configs,
            "job_runner": self.job_runner_configs,
            "notification": self.notification_configs,
        }
        
        if provider_type not in configs_map:
            return False
        
        provider_config = configs_map[provider_type].get(provider_name)
        return provider_config.enabled if provider_config else False
    
    def get_enabled_providers(self, provider_type: str) -> Dict[str, ProviderConfig]:
        """
        Get all enabled providers of a given type
        
        Args:
            provider_type: Type of provider
            
        Returns:
            Dictionary of enabled provider configurations
        """
        configs_map = {
            "storage": self.storage_configs,
            "transcription": self.transcription_configs, 
            "job_runner": self.job_runner_configs,
            "notification": self.notification_configs,
        }
        
        if provider_type not in configs_map:
            return {}
        
        return {
            name: config 
            for name, config in configs_map[provider_type].items()
            if config.enabled
        }