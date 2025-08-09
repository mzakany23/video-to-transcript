"""
Runners router for Orchestration API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from ..dependencies import get_service_factory, get_orchestration_service

router = APIRouter()


@router.get("/")
async def list_runners(factory = Depends(get_service_factory)):
    """List available job runners"""
    try:
        providers = factory.get_available_providers()
        
        job_runners = []
        for runner_name in providers.get("job_runner", {}).get("available", []):
            enabled = runner_name in providers.get("job_runner", {}).get("enabled", [])
            
            runner_info = {
                "id": runner_name,
                "name": runner_name.title(),
                "type": runner_name,
                "enabled": enabled,
                "available": True  # TODO: Check actual availability
            }
            job_runners.append(runner_info)
        
        current_runner = factory.settings.job_runner
        
        return {
            "runners": job_runners,
            "current_runner": current_runner
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list runners: {str(e)}"
        )


@router.get("/current")
async def get_current_runner(orchestration = Depends(get_orchestration_service)):
    """Get current runner information"""
    try:
        runner_info = orchestration.get_runner_info()
        
        return {
            "id": runner_info["runner_type"].lower().replace("jobrunner", ""),
            "name": runner_info["runner_type"],
            "type": runner_info["runner_type"],
            "active_jobs": runner_info["active_jobs"],
            "capabilities": runner_info["capabilities"]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get current runner: {str(e)}"
        )


@router.post("/{runner_id}/validate")
async def validate_runner(
    runner_id: str,
    factory = Depends(get_service_factory)
):
    """Validate runner configuration"""
    try:
        validation = factory.validate_configuration()
        
        # Find runner in validation results
        runner_status = None
        for provider_type, status_info in validation.get("provider_status", {}).items():
            if provider_type == "job_runner" and status_info.get("name") == runner_id:
                runner_status = status_info
                break
        
        if not runner_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Runner {runner_id} not found"
            )
        
        return {
            "runner_id": runner_id,
            "valid": runner_status.get("status") == "valid",
            "available": runner_status.get("status") == "valid",
            "message": runner_status.get("error", "Runner is valid and available"),
            "tested_at": f"{__import__('datetime').datetime.now().isoformat()}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate runner: {str(e)}"
        )