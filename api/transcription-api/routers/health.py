"""
Health router for Transcription API
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from ..models import HealthStatus
from ..dependencies import get_service_factory

router = APIRouter()


@router.get("/health", response_model=HealthStatus)
async def get_health():
    """
    Health check endpoint
    
    Returns basic health status of the transcription service
    """
    return HealthStatus(
        status="healthy",
        timestamp=datetime.now(),
        version="0.1.0"
    )


@router.get("/status")
async def get_status(factory: ServiceFactory = Depends(get_service_factory)) -> Dict[str, Any]:
    """
    Detailed service status
    
    Returns comprehensive information about service configuration and providers
    """
    try:
        # Get factory validation
        validation = factory.validate_configuration()
        
        # Get available providers
        providers = factory.get_available_providers()
        
        return {
            "status": "healthy" if validation["valid"] else "unhealthy",
            "version": "0.1.0",
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "transcription_provider": factory.settings.transcription_provider,
                "storage_provider": factory.settings.storage_provider,
                "job_runner": factory.settings.job_runner,
                "environment": factory.settings.environment,
            },
            "validation": validation,
            "providers": providers,
            "statistics": {
                "active_jobs": 0,  # TODO: Get from orchestration service
                "supported_formats": [".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".flac"]
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service status check failed: {str(e)}"
        )