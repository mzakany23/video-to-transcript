"""
Local implementation of JobRunner for testing and development
"""

import asyncio
import subprocess
import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from ...core.interfaces import JobRunner
from ...core.models import JobSpec, JobStatus, JobState
from ...core.exceptions import JobException
from ...core.logging import get_logger

logger = get_logger(__name__)


class LocalJobRunner(JobRunner):
    """
    Local implementation of job runner using subprocess
    Suitable for testing and development environments
    """
    
    def __init__(self, work_dir: Optional[str] = None):
        """
        Initialize local job runner
        
        Args:
            work_dir: Directory for job execution and logs
        """
        self.work_dir = Path(work_dir) if work_dir else Path.cwd() / ".local_jobs"
        self.work_dir.mkdir(exist_ok=True)
        
        # Track running processes
        self.running_jobs: Dict[str, subprocess.Popen] = {}
        
        logger.info(f"Initialized LocalJobRunner with work_dir: {self.work_dir}")
    
    async def submit_job(self, spec: JobSpec) -> str:
        """
        Submit a job to run locally using subprocess
        
        Args:
            spec: Job specification
            
        Returns:
            Job ID (UUID)
        """
        job_id = str(uuid.uuid4())
        job_dir = self.work_dir / job_id
        job_dir.mkdir(exist_ok=True)
        
        try:
            # Create job metadata file
            job_meta = {
                "job_id": job_id,
                "job_type": spec.job_type,
                "input_data": spec.input_data,
                "environment": spec.environment,
                "resources": {
                    "cpu": spec.resources.cpu if spec.resources else "1",
                    "memory": spec.resources.memory if spec.resources else "1Gi",
                    "timeout_seconds": spec.resources.timeout_seconds if spec.resources else 3600
                },
                "metadata": spec.metadata,
                "submitted_at": datetime.now().isoformat(),
                "status": "submitted"
            }
            
            with open(job_dir / "job.json", "w") as f:
                json.dump(job_meta, f, indent=2)
            
            # For local execution, we'll run the worker directly
            # This assumes the worker can be run as a Python module
            command = [
                "python", "-m", "worker.main"
            ]
            
            # Set up environment variables
            env = os.environ.copy()
            env.update(spec.environment)
            
            # Redirect output to job directory
            stdout_file = open(job_dir / "stdout.log", "w")
            stderr_file = open(job_dir / "stderr.log", "w")
            
            # Start process
            process = subprocess.Popen(
                command,
                cwd=self.work_dir.parent,  # Run from project root
                env=env,
                stdout=stdout_file,
                stderr=stderr_file,
                start_new_session=True
            )
            
            # Track the process
            self.running_jobs[job_id] = process
            
            # Update job metadata
            job_meta["status"] = "running"
            job_meta["started_at"] = datetime.now().isoformat()
            job_meta["pid"] = process.pid
            
            with open(job_dir / "job.json", "w") as f:
                json.dump(job_meta, f, indent=2)
            
            logger.info(f"Local job submitted: {job_id} (PID: {process.pid})")
            return job_id
            
        except Exception as e:
            logger.error(f"Local job submission failed: {str(e)}")
            raise JobException(f"Failed to submit job: {str(e)}")
    
    async def get_status(self, job_id: str) -> JobStatus:
        """
        Get status of a local job
        
        Args:
            job_id: Job identifier
            
        Returns:
            JobStatus object
        """
        job_dir = self.work_dir / job_id
        job_file = job_dir / "job.json"
        
        if not job_file.exists():
            raise JobException(f"Job {job_id} not found")
        
        try:
            with open(job_file, "r") as f:
                job_meta = json.load(f)
            
            # Check if process is still running
            job_state = JobState.PENDING
            completed_at = None
            
            if job_id in self.running_jobs:
                process = self.running_jobs[job_id]
                
                # Check process status
                poll_result = process.poll()
                if poll_result is None:
                    # Still running
                    job_state = JobState.RUNNING
                else:
                    # Process completed
                    if poll_result == 0:
                        job_state = JobState.COMPLETED
                    else:
                        job_state = JobState.FAILED
                    
                    completed_at = datetime.now()
                    
                    # Update metadata and remove from tracking
                    job_meta["status"] = job_state.value
                    job_meta["completed_at"] = completed_at.isoformat()
                    job_meta["exit_code"] = poll_result
                    
                    with open(job_file, "w") as f:
                        json.dump(job_meta, f, indent=2)
                    
                    del self.running_jobs[job_id]
            
            else:
                # Process not in tracking, check metadata
                if job_meta.get("status") == "completed":
                    job_state = JobState.COMPLETED
                elif job_meta.get("status") == "failed":
                    job_state = JobState.FAILED
                elif job_meta.get("status") == "cancelled":
                    job_state = JobState.CANCELLED
                else:
                    job_state = JobState.PENDING
            
            return JobStatus(
                job_id=job_id,
                state=job_state,
                started_at=datetime.fromisoformat(job_meta["started_at"]) if "started_at" in job_meta else None,
                completed_at=completed_at or (datetime.fromisoformat(job_meta["completed_at"]) if "completed_at" in job_meta else None),
                metadata={
                    "job_dir": str(job_dir),
                    "pid": job_meta.get("pid"),
                    "exit_code": job_meta.get("exit_code")
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to get status for job {job_id}: {str(e)}")
            raise JobException(f"Status check failed: {str(e)}")
    
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a local job by terminating the process
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if cancelled successfully
        """
        if job_id not in self.running_jobs:
            logger.warning(f"Job {job_id} not found in running jobs")
            return False
        
        try:
            process = self.running_jobs[job_id]
            
            # Terminate process gracefully first
            process.terminate()
            
            # Wait for graceful termination
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # Force kill if doesn't terminate gracefully
                process.kill()
                process.wait()
            
            # Update job metadata
            job_dir = self.work_dir / job_id
            job_file = job_dir / "job.json"
            
            if job_file.exists():
                with open(job_file, "r") as f:
                    job_meta = json.load(f)
                
                job_meta["status"] = "cancelled"
                job_meta["completed_at"] = datetime.now().isoformat()
                
                with open(job_file, "w") as f:
                    json.dump(job_meta, f, indent=2)
            
            # Remove from tracking
            del self.running_jobs[job_id]
            
            logger.info(f"Local job cancelled: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel local job {job_id}: {str(e)}")
            return False
    
    async def list_jobs(
        self,
        state: Optional[JobState] = None,
        limit: int = 100
    ) -> List[JobStatus]:
        """
        List local jobs
        
        Args:
            state: Filter by job state (optional)
            limit: Maximum number of jobs to return
            
        Returns:
            List of JobStatus objects
        """
        try:
            job_statuses = []
            
            # Get all job directories
            job_dirs = [d for d in self.work_dir.iterdir() if d.is_dir()]
            
            # Sort by creation time (most recent first)
            job_dirs.sort(key=lambda x: x.stat().st_ctime, reverse=True)
            
            for job_dir in job_dirs[:limit]:
                try:
                    job_id = job_dir.name
                    status = await self.get_status(job_id)
                    
                    # Filter by state if specified
                    if state and status.state != state:
                        continue
                    
                    job_statuses.append(status)
                    
                except Exception as e:
                    logger.warning(f"Could not get status for job {job_dir.name}: {str(e)}")
            
            return job_statuses
            
        except Exception as e:
            logger.error(f"Failed to list local jobs: {str(e)}")
            raise JobException(f"Job listing failed: {str(e)}")
    
    async def get_job_logs(self, job_id: str, lines: int = 100) -> List[str]:
        """
        Get logs for a local job
        
        Args:
            job_id: Job identifier
            lines: Number of log lines to retrieve
            
        Returns:
            List of log lines
        """
        job_dir = self.work_dir / job_id
        
        try:
            log_lines = []
            
            # Read stdout
            stdout_file = job_dir / "stdout.log"
            if stdout_file.exists():
                with open(stdout_file, "r") as f:
                    stdout_lines = f.readlines()
                    for line in stdout_lines[-lines:]:
                        log_lines.append(f"STDOUT: {line.strip()}")
            
            # Read stderr  
            stderr_file = job_dir / "stderr.log"
            if stderr_file.exists():
                with open(stderr_file, "r") as f:
                    stderr_lines = f.readlines()
                    for line in stderr_lines[-lines:]:
                        log_lines.append(f"STDERR: {line.strip()}")
            
            # Sort by timestamp if available
            return log_lines[-lines:] if log_lines else ["No logs available"]
            
        except Exception as e:
            logger.error(f"Failed to get logs for job {job_id}: {str(e)}")
            return [f"Error retrieving logs: {str(e)}"]
    
    def cleanup_completed_jobs(self, days_old: int = 7):
        """
        Clean up job directories for completed jobs older than specified days
        
        Args:
            days_old: Remove jobs older than this many days
        """
        import time
        
        cutoff_time = time.time() - (days_old * 24 * 60 * 60)
        
        try:
            for job_dir in self.work_dir.iterdir():
                if job_dir.is_dir():
                    # Check if job is old enough and not running
                    if job_dir.stat().st_ctime < cutoff_time:
                        job_id = job_dir.name
                        
                        # Don't delete if still running
                        if job_id in self.running_jobs:
                            continue
                        
                        # Check job status
                        job_file = job_dir / "job.json"
                        if job_file.exists():
                            with open(job_file, "r") as f:
                                job_meta = json.load(f)
                            
                            # Only delete completed/failed/cancelled jobs
                            if job_meta.get("status") in ["completed", "failed", "cancelled"]:
                                import shutil
                                shutil.rmtree(job_dir)
                                logger.info(f"Cleaned up old job directory: {job_id}")
                        
        except Exception as e:
            logger.error(f"Error during job cleanup: {str(e)}")