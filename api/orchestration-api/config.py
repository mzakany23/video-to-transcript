"""
Configuration for Orchestration API
"""

from pydantic import BaseSettings


class APISettings(BaseSettings):
    """API configuration settings"""
    
    # Server configuration
    service_name: str = "orchestration_api"
    host: str = "0.0.0.0"
    port: int = 8003
    debug: bool = False
    
    # Logging
    log_level: str = "INFO"
    
    # CORS
    cors_origins: list = ["*"]
    
    # Security
    secret_key: str = "orchestration-api-secret-key"
    
    # Orchestration settings
    default_job_runner: str = "cloudrun"
    default_storage_provider: str = "gcs"
    
    # Job limits
    max_concurrent_jobs: int = 10
    max_batch_size: int = 100
    default_timeout: int = 3600
    
    class Config:
        env_file = ".env"
        case_sensitive = False


def get_settings() -> APISettings:
    """Get settings instance"""
    return APISettings()