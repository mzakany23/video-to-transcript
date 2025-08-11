"""
Tracking router for Webhook API
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, Any, Optional

from ..dependencies import get_job_tracker

router = APIRouter()


@router.get("/")
async def get_tracking_info(job_tracker = Depends(get_job_tracker)):
    """Get job tracking information"""
    try:
        info = await job_tracker.get_tracking_info()
        return info
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tracking info: {str(e)}"
        )


@router.get("/processed")
async def list_processed_files(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    job_tracker = Depends(get_job_tracker)
):
    """List processed files"""
    try:
        processed_files = await job_tracker.list_processed_files(limit=limit)
        
        # Simple pagination
        files_list = list(processed_files.items())
        total = len(files_list)
        paginated = files_list[offset:offset + limit]
        
        return {
            "files": [
                {
                    "file_id": file_id,
                    **record
                }
                for file_id, record in paginated
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list processed files: {str(e)}"
        )


@router.get("/processed/{file_id}")
async def is_file_processed(file_id: str, job_tracker = Depends(get_job_tracker)):
    """Check if file is processed"""
    try:
        is_processed = await job_tracker.is_processed(file_id)
        record = None
        
        if is_processed:
            record = await job_tracker.get_job_record(file_id)
        
        return {
            "file_id": file_id,
            "is_processed": is_processed,
            "processed_at": record.get("processed_at") if record else None,
            "job_id": record.get("job_id") if record else None,
            "file_info": record.get("file_info") if record else None
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check file status: {str(e)}"
        )


@router.post("/processed/{file_id}")
async def mark_file_processed(
    file_id: str,
    mark_data: Dict[str, Any],
    job_tracker = Depends(get_job_tracker)
):
    """Mark file as processed"""
    try:
        await job_tracker.mark_processed(
            file_id=file_id,
            job_id=mark_data.get("job_id"),
            file_info=mark_data.get("file_info", {})
        )
        
        return {
            "file_id": file_id,
            "marked_processed": True,
            "job_id": mark_data.get("job_id")
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark file as processed: {str(e)}"
        )


@router.delete("/processed")
async def reset_job_tracking(
    confirm_data: Dict[str, bool],
    job_tracker = Depends(get_job_tracker)
):
    """Reset all job tracking"""
    try:
        if not confirm_data.get("confirm", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Confirmation required to reset tracking"
            )
        
        await job_tracker.reset_tracking()
        
        return {
            "reset": True,
            "message": "Job tracking reset successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset tracking: {str(e)}"
        )