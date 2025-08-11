"""
Jobs router for Transcription API
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import PlainTextResponse
from typing import Optional, List

from ..models import JobStatus, JobLogs, JobState
from ..dependencies import get_orchestration_service

router = APIRouter()


@router.get("/{job_id}", response_model=JobStatus)
async def get_job_status(
    job_id: str,
    orchestration = Depends(get_orchestration_service)
):
    """
    Get job status and details
    
    Retrieve the current status, progress, and result of a transcription job
    """
    try:
        status_info = await orchestration.get_job_status(job_id)
        
        # Convert to API model format
        return JobStatus(
            job_id=job_id,
            status=status_info.state.value,
            progress=status_info.metadata.get('progress'),
            created_at=status_info.started_at or datetime.now(),
            started_at=status_info.started_at,
            completed_at=status_info.completed_at,
            error=status_info.metadata.get('error'),
            metadata=status_info.metadata
        )
        
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.delete("/{job_id}")
async def cancel_job(
    job_id: str,
    orchestration = Depends(get_orchestration_service)
):
    """
    Cancel a running job
    
    Attempt to cancel a transcription job if it's still running
    """
    try:
        success = await orchestration.cancel_job(job_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Job cannot be cancelled (may already be completed)"
            )
        
        return {
            "job_id": job_id,
            "status": "cancelled",
            "cancelled_at": datetime.now().isoformat(),
            "message": "Job cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {str(e)}"
        )


@router.get("/{job_id}/result")
async def download_job_result(
    job_id: str,
    format: str = Query(default="json", regex="^(json|txt|srt|vtt)$"),
    orchestration = Depends(get_orchestration_service)
):
    """
    Download transcription result
    
    Get the transcription result in various formats (json, txt, srt, vtt)
    """
    try:
        status_info = await orchestration.get_job_status(job_id)
        
        if status_info.state != JobState.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not completed or result not available"
            )
        
        # TODO: Format the result based on requested format
        result = status_info.result or {}
        
        if format == "txt":
            text_result = result.get('text', 'No transcription available')
            return PlainTextResponse(content=text_result)
        elif format == "srt":
            # TODO: Convert to SRT format
            srt_result = "1\n00:00:00,000 --> 00:01:00,000\n" + result.get('text', 'No transcription')
            return PlainTextResponse(content=srt_result, media_type="application/x-subrip")
        elif format == "vtt":
            # TODO: Convert to VTT format
            vtt_result = "WEBVTT\n\n00:00.000 --> 01:00.000\n" + result.get('text', 'No transcription')
            return PlainTextResponse(content=vtt_result, media_type="text/vtt")
        else:
            # Default JSON format
            return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job result: {str(e)}"
        )


@router.get("/{job_id}/logs", response_model=JobLogs)
async def get_job_logs(
    job_id: str,
    lines: int = Query(default=100, ge=1, le=1000),
    orchestration = Depends(get_orchestration_service)
):
    """
    Get job execution logs
    
    Retrieve logs from job execution for debugging and monitoring
    """
    try:
        logs = await orchestration.get_job_logs(job_id, lines=lines)
        
        return JobLogs(
            job_id=job_id,
            logs=logs,
            timestamp=datetime.now()
        )
        
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


@router.get("/", response_model=List[JobStatus])
async def list_jobs(
    status_filter: Optional[JobState] = Query(None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    orchestration = Depends(get_orchestration_service)
):
    """
    List transcription jobs
    
    Get a paginated list of jobs with optional status filtering
    """
    try:
        # TODO: Implement proper job listing in orchestration service
        # For now, return active jobs
        active_jobs = await orchestration.list_active_jobs()
        
        # Convert to API format
        job_list = []
        for job in active_jobs:
            job_status = JobStatus(
                job_id=job.job_id,
                status=job.state.value,
                created_at=job.started_at or datetime.now(),
                started_at=job.started_at,
                completed_at=job.completed_at,
                error=job.metadata.get('error'),
                metadata=job.metadata
            )
            job_list.append(job_status)
        
        # Apply filtering and pagination
        if status_filter:
            job_list = [job for job in job_list if job.status == status_filter]
        
        return job_list[offset:offset + limit]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}"
        )