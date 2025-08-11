"""
Admin router for Webhook API
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any

from ..dependencies import get_service_factory, get_webhook_service

router = APIRouter()


@router.post("/validate")
async def validate_configuration(factory = Depends(get_service_factory)):
    """Validate webhook service configuration"""
    try:
        validation = factory.validate_configuration()
        
        return {
            "valid": validation["valid"],
            "errors": validation.get("errors", []),
            "warnings": validation.get("warnings", []),
            "provider_status": validation.get("provider_status", {}),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Configuration validation failed: {str(e)}"
        )


@router.post("/reset")
async def reset_webhook_state(
    reset_data: Dict[str, Any],
    webhook_service = Depends(get_webhook_service)
):
    """Reset webhook processing state"""
    try:
        if not reset_data.get("confirm", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Confirmation required to reset webhook state"
            )
        
        reset_cursors = reset_data.get("reset_cursors", True)
        reset_tracking = reset_data.get("reset_tracking", True)
        
        result = await webhook_service.reset_processing_state(confirm=True)
        
        return {
            "success": result["success"],
            "message": result["message"],
            "cursors_reset": reset_cursors,
            "tracking_reset": reset_tracking,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset webhook state: {str(e)}"
        )


@router.get("/statistics")
async def get_webhook_statistics(webhook_service = Depends(get_webhook_service)):
    """Get detailed webhook statistics"""
    try:
        stats = await webhook_service.get_processing_stats()
        
        return {
            **stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


@router.post("/cleanup")
async def cleanup_old_records(
    cleanup_data: Dict[str, Any],
    webhook_service = Depends(get_webhook_service)
):
    """Clean up old processing records"""
    try:
        days_old = cleanup_data.get("days_old", 30)
        dry_run = cleanup_data.get("dry_run", False)
        
        # For now, just return what would be done
        # TODO: Implement actual cleanup in job tracker
        
        return {
            "success": True,
            "message": f"Would clean up records older than {days_old} days",
            "records_would_remove": 0,  # TODO: Calculate actual number
            "dry_run": dry_run,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cleanup failed: {str(e)}"
        )