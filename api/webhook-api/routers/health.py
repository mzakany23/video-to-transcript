"""
Health router for Webhook API
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from typing import Dict, Any

from ..dependencies import get_service_factory, get_webhook_service

router = APIRouter()


@router.get("/health")
async def get_health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "0.1.0"
    }


@router.get("/status")
async def get_status(
    factory = Depends(get_service_factory),
    webhook_service = Depends(get_webhook_service)
) -> Dict[str, Any]:
    """Detailed service status"""
    try:
        # Get processing statistics
        stats = await webhook_service.get_processing_stats()
        
        # Get validation
        validation = factory.validate_configuration()
        
        return {
            "status": "healthy" if validation["valid"] else "degraded",
            "version": "0.1.0",
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "storage_provider": factory.settings.storage_provider,
                "job_runner": factory.settings.job_runner,
                "environment": factory.settings.environment,
            },
            "validation": validation,
            "statistics": stats
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }