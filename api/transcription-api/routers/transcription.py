"""
Transcription router for Transcription API
"""

import os
import tempfile
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List, Optional

from ..models import JobResponse, BatchJobResponse, TranscribeUrlRequest, TranscriptionOptions
from ..dependencies import get_orchestration_service, get_settings

router = APIRouter()


@router.post("/", response_model=JobResponse)
async def transcribe_file(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    model: str = Form("whisper-1"),
    orchestration = Depends(get_orchestration_service),
    settings = Depends(get_settings)
):
    """
    Transcribe an audio file
    
    Submit an audio file for transcription processing
    """
    try:
        # Validate file size
        if hasattr(file, 'size') and file.size > settings.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {settings.max_file_size} bytes"
            )
        
        # Validate file extension
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in settings.allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format: {file_extension}"
            )
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Submit transcription job
            job_id = await orchestration.submit_transcription_job(
                file_path=temp_file_path,
                file_name=file.filename,
                environment={
                    "TRANSCRIPTION_LANGUAGE": language or "auto",
                    "TRANSCRIPTION_MODEL": model,
                }
            )
            
            return JobResponse(
                job_id=job_id,
                status="pending",
                created_at=datetime.now(),
                estimated_duration=60.0  # Rough estimate
            )
            
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file_path)
            except:
                pass
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription submission failed: {str(e)}"
        )


@router.post("/url", response_model=JobResponse)
async def transcribe_from_url(
    request: TranscribeUrlRequest,
    orchestration = Depends(get_orchestration_service)
):
    """
    Transcribe audio from URL
    
    Submit a file URL for transcription processing
    """
    try:
        # TODO: Download file from URL and validate
        # For now, just submit the job with the URL
        
        job_id = await orchestration.submit_transcription_job(
            file_path=request.url,
            file_name=os.path.basename(request.url),
            environment={
                "TRANSCRIPTION_SOURCE": "url",
                "TRANSCRIPTION_LANGUAGE": request.options.language if request.options else "auto",
                "TRANSCRIPTION_MODEL": request.options.model if request.options else "whisper-1",
            }
        )
        
        return JobResponse(
            job_id=job_id,
            status="pending",
            created_at=datetime.now(),
            estimated_duration=90.0  # URL downloads take longer
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"URL transcription submission failed: {str(e)}"
        )


@router.post("/batch", response_model=BatchJobResponse)
async def transcribe_batch(
    files: List[UploadFile] = File(...),
    language: Optional[str] = Form(None),
    model: str = Form("whisper-1"),
    orchestration = Depends(get_orchestration_service),
    settings = Depends(get_settings)
):
    """
    Batch transcribe multiple files
    
    Submit multiple files for batch transcription processing
    """
    if len(files) > 10:  # Limit batch size
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 files per batch"
        )
    
    try:
        job_ids = []
        successful = 0
        failed = 0
        
        for file in files:
            try:
                # Validate each file
                file_extension = os.path.splitext(file.filename)[1].lower()
                if file_extension not in settings.allowed_extensions:
                    failed += 1
                    continue
                
                # Save temporarily and submit job
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                    content = await file.read()
                    temp_file.write(content)
                    temp_file_path = temp_file.name
                
                job_id = await orchestration.submit_transcription_job(
                    file_path=temp_file_path,
                    file_name=file.filename,
                    environment={
                        "TRANSCRIPTION_LANGUAGE": language or "auto",
                        "TRANSCRIPTION_MODEL": model,
                    }
                )
                
                job_ids.append(job_id)
                successful += 1
                
                # Clean up temp file
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                    
            except Exception as e:
                print(f"Error processing file {file.filename}: {e}")
                failed += 1
        
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return BatchJobResponse(
            batch_id=batch_id,
            job_ids=job_ids,
            total_jobs=len(files),
            successful_submissions=successful,
            failed_submissions=failed,
            created_at=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch transcription submission failed: {str(e)}"
        )