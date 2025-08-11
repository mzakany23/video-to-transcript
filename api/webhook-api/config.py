"""
Configuration for Webhook API
"""

from pydantic import BaseSettings


class APISettings(BaseSettings):
    """API configuration settings"""
    
    # Server configuration
    service_name: str = "webhook_api"
    host: str = "0.0.0.0"
    port: int = 8002
    debug: bool = False
    
    # Logging
    log_level: str = "INFO"
    
    # CORS
    cors_origins: list = ["*"]
    
    # Security
    secret_key: str = "webhook-api-secret-key"
    
    # Webhook settings
    default_storage_provider: str = "gcs"  # Use GCS for cursor/tracking storage
    default_job_runner: str = "cloudrun"
    
    # File processing
    supported_formats: list = [".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".flac", ".mov", ".avi"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


def get_settings() -> APISettings:
    """Get settings instance"""
    return APISettings()