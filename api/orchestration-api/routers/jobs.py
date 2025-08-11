"""
Jobs router for Orchestration API
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, Any, Optional, List

from ..dependencies import get_orchestration_service

router = APIRouter()


@router.post("/")
async def submit_job(
    job_request: Dict[str, Any],
    orchestration = Depends(get_orchestration_service)
):
    """Submit a new job"""
    try:
        # Extract job parameters
        job_type = job_request.get("job_type", "transcription")
        input_data = job_request.get("input_data", {})
        environment = job_request.get("environment", {})
        
        # Submit job using orchestration service
        job_id = await orchestration.submit_transcription_job(
            file_path=input_data.get("file_path", ""),
            file_name=input_data.get("file_name", "unknown"),
            environment=environment
        )
        
        return {
            "job_id": job_id,
            "status": "pending",
            "submitted_at": datetime.now().isoformat(),
            "runner": orchestration.job_runner.__class__.__name__
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Job submission failed: {str(e)}"
        )


@router.get("/")
async def list_jobs(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    orchestration = Depends(get_orchestration_service)
):
    """List jobs"""
    try:
        # Get active jobs
        jobs = await orchestration.list_active_jobs()
        
        # Convert to API format
        job_list = []
        for job in jobs:
            job_info = {
                "job_id": job.job_id,
                "status": job.state.value,
                "created_at": job.started_at.isoformat() if job.started_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "runner": orchestration.job_runner.__class__.__name__,
                "metadata": job.metadata
            }
            job_list.append(job_info)
        
        # Apply filtering
        if status_filter:
            job_list = [job for job in job_list if job["status"] == status_filter]
        
        return {
            "jobs": job_list[:limit],
            "total": len(job_list),
            "limit": limit,
            "has_more": len(job_list) > limit
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}"
        )


@router.get("/{job_id}")
async def get_job(job_id: str, orchestration = Depends(get_orchestration_service)):
    """Get job details"""
    try:
        status = await orchestration.get_job_status(job_id)
        
        return {
            "job_id": job_id,
            "status": status.state.value,
            "created_at": status.started_at.isoformat() if status.started_at else None,
            "started_at": status.started_at.isoformat() if status.started_at else None,
            "completed_at": status.completed_at.isoformat() if status.completed_at else None,
            "runner": orchestration.job_runner.__class__.__name__,
            "metadata": status.metadata,
            "is_terminal": status.is_terminal
        }
        
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job: {str(e)}"
        )


@router.delete("/{job_id}")
async def cancel_job(job_id: str, orchestration = Depends(get_orchestration_service)):
    """Cancel a job"""
    try:
        success = await orchestration.cancel_job(job_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Job cannot be cancelled"
            )
        
        return {
            "job_id": job_id,
            "status": "cancelled",
            "cancelled_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {str(e)}"
        )


@router.get("/{job_id}/logs")
async def get_job_logs(
    job_id: str,
    lines: int = Query(default=100, ge=1, le=1000),
    orchestration = Depends(get_orchestration_service)
):
    """Get job logs"""
    try:
        logs = await orchestration.get_job_logs(job_id, lines=lines)
        
        return {
            "job_id": job_id,
            "logs": logs,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job logs: {str(e)}"
        )