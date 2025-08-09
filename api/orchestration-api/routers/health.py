"""
Health router for Orchestration API
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from typing import Dict, Any

from ..dependencies import get_service_factory, get_orchestration_service

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
    orchestration = Depends(get_orchestration_service)
) -> Dict[str, Any]:
    """Detailed service status"""
    try:
        # Get runner info
        runner_info = orchestration.get_runner_info()
        
        # Get validation
        validation = factory.validate_configuration()
        
        return {
            "status": "healthy" if validation["valid"] else "degraded",
            "version": "0.1.0", 
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "job_runner": factory.settings.job_runner,
                "storage_provider": factory.settings.storage_provider,
                "environment": factory.settings.environment,
            },
            "validation": validation,
            "runner_info": runner_info,
            "statistics": {
                "active_jobs": runner_info.get("active_jobs", 0),
                "runner_capabilities": runner_info.get("capabilities", {})
            }
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }