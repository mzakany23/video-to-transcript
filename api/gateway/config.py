"""
Gateway configuration
"""

from pydantic import BaseSettings
from typing import Dict, Any

class GatewaySettings(BaseSettings):
    """Gateway configuration settings"""
    
    # Gateway settings
    gateway_host: str = "0.0.0.0"
    gateway_port: int = 8000
    
    # Service URLs
    transcription_service_url: str = "http://localhost:8001"
    webhook_service_url: str = "http://localhost:8002" 
    orchestration_service_url: str = "http://localhost:8003"
    
    # Health check settings
    health_check_timeout: float = 5.0
    service_timeout: float = 30.0
    
    # CORS settings
    cors_origins: list = ["*"]
    cors_credentials: bool = True
    cors_methods: list = ["*"]
    cors_headers: list = ["*"]
    
    class Config:
        env_file = ".env"
        env_prefix = "GATEWAY_"

def get_service_config(settings: GatewaySettings) -> Dict[str, Dict[str, Any]]:
    """Get service configuration from settings"""
    return {
        "transcription": {
            "name": "Transcription API",
            "url": settings.transcription_service_url,
            "health_path": "/health",
            "prefix": "/api/v1/transcription"
        },
        "webhook": {
            "name": "Webhook API",
            "url": settings.webhook_service_url,
            "health_path": "/health", 
            "prefix": "/api/v1/webhook"
        },
        "orchestration": {
            "name": "Orchestration API",
            "url": settings.orchestration_service_url,
            "health_path": "/health",
            "prefix": "/api/v1/orchestration"
        }
    }