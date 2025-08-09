"""
Batch operations router for Orchestration API
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List

from ..dependencies import get_orchestration_service

router = APIRouter()


@router.post("/")
async def submit_batch_jobs(
    batch_request: Dict[str, Any],
    orchestration = Depends(get_orchestration_service)
):
    """Submit batch jobs"""
    try:
        jobs = batch_request.get("jobs", [])
        max_concurrent = batch_request.get("max_concurrent", 5)
        
        if not jobs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No jobs provided in batch"
            )
        
        if len(jobs) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 100 jobs per batch"
            )
        
        # Prepare files for batch processing
        files = []
        for job in jobs:
            input_data = job.get("input_data", {})
            files.append({
                "path": input_data.get("file_path", ""),
                "name": input_data.get("file_name", "unknown")
            })
        
        # Submit batch jobs
        job_ids = await orchestration.submit_batch_jobs(files, max_concurrent=max_concurrent)
        
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return {
            "batch_id": batch_id,
            "job_ids": job_ids,
            "total_jobs": len(jobs),
            "successful_submissions": len(job_ids),
            "failed_submissions": len(jobs) - len(job_ids),
            "submitted_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch submission failed: {str(e)}"
        )


@router.get("/{batch_id}")
async def get_batch_status(
    batch_id: str,
    orchestration = Depends(get_orchestration_service)
):
    """Get batch status"""
    try:
        # For now, return a mock response since we don't have persistent batch tracking
        # TODO: Implement proper batch tracking
        
        return {
            "batch_id": batch_id,
            "total_jobs": 0,
            "pending_jobs": 0,
            "running_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "cancelled_jobs": 0,
            "overall_progress": 0,
            "jobs": [],
            "message": "Batch tracking not fully implemented yet"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get batch status: {str(e)}"
        )