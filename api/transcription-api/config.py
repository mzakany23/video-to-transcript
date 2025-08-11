"""
Configuration for Transcription API
"""

import os
from pydantic import BaseSettings


class APISettings(BaseSettings):
    """API configuration settings"""
    
    # Server configuration
    service_name: str = "transcription_api"
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = False
    
    # Logging
    log_level: str = "INFO"
    
    # CORS
    cors_origins: list = ["*"]
    
    # Security
    secret_key: str = "transcription-api-secret-key"
    
    # File upload limits
    max_file_size: int = 25 * 1024 * 1024  # 25MB
    allowed_extensions: list = [".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".flac"]
    
    # Transcription settings
    default_transcription_provider: str = "openai"
    default_storage_provider: str = "local"
    default_job_runner: str = "local"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


def get_settings() -> APISettings:
    """Get settings instance"""
    return APISettings()