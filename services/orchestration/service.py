"""
High-level orchestration service for job management
"""

import asyncio
from datetime import datetime
from typing import Any, Optional

from ..core.exceptions import JobError
from ..core.interfaces import JobRunner
from ..core.logging import get_logger
from ..core.models import JobSpec, JobState, JobStatus, ResourceRequirements

logger = get_logger(__name__)


class OrchestrationService:
    """
    High-level orchestration service that works with any job runner
    """

    def __init__(self, job_runner: JobRunner):
        """
        Initialize orchestration service

        Args:
            job_runner: Job runner implementation
        """
        self.job_runner = job_runner
        self.active_jobs: dict[str, JobStatus] = {}

        logger.info(f"Initialized OrchestrationService with {job_runner.__class__.__name__}")

    async def submit_transcription_job(
        self,
        file_path: str,
        file_name: str,
        job_type: str = "transcription",
        environment: Optional[dict[str, str]] = None,
    ) -> str:
        """
        Submit a transcription job

        Args:
            file_path: Path to file to process
            file_name: Name of the file
            job_type: Type of job (default: transcription)
            environment: Additional environment variables

        Returns:
            Job ID for tracking
        """
        try:
            # Prepare job specification
            job_env = environment or {}
            job_env.update(
                {
                    "PROCESS_SINGLE_FILE": "true",
                    "TARGET_FILE_PATH": file_path,
                    "TARGET_FILE_NAME": file_name,
                }
            )

            job_spec = JobSpec(
                job_type=job_type,
                input_data={
                    "file_path": file_path,
                    "file_name": file_name,
                },
                environment=job_env,
                resources=ResourceRequirements(cpu="1", memory="2Gi", timeout_seconds=3600),
                metadata={"submitted_at": datetime.now().isoformat(), "file_name": file_name},
            )

            logger.info(f"Submitting transcription job for file: {file_name}")
            job_id = await self.job_runner.submit_job(job_spec)

            # Track job locally
            self.active_jobs[job_id] = JobStatus(
                job_id=job_id,
                state=JobState.PENDING,
                started_at=datetime.now(),
                metadata={"file_name": file_name, "file_path": file_path},
            )

            logger.info(f"Transcription job submitted: {job_id}")
            return job_id

        except Exception as e:
            logger.error(f"Failed to submit transcription job for {file_name}: {str(e)}")
            raise JobError(f"Job submission failed: {str(e)}")

    async def submit_batch_jobs(
        self, files: list[dict[str, str]], max_concurrent: int = 5
    ) -> list[str]:
        """
        Submit multiple jobs with concurrency control

        Args:
            files: List of file dictionaries with path and name
            max_concurrent: Maximum concurrent job submissions

        Returns:
            List of job IDs
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def submit_single(file_info):
            async with semaphore:
                return await self.submit_transcription_job(file_info["path"], file_info["name"])

        tasks = [submit_single(file_info) for file_info in files]
        job_ids = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and log errors
        successful_job_ids = []
        for i, result in enumerate(job_ids):
            if isinstance(result, Exception):
                logger.error(f"Failed to submit job for {files[i]['name']}: {str(result)}")
            else:
                successful_job_ids.append(result)

        logger.info(f"Submitted {len(successful_job_ids)}/{len(files)} batch jobs successfully")
        return successful_job_ids

    async def get_job_status(self, job_id: str) -> JobStatus:
        """
        Get status of a job

        Args:
            job_id: Job identifier

        Returns:
            JobStatus object
        """
        try:
            # Get status from runner
            status = await self.job_runner.get_status(job_id)

            # Update local tracking
            if job_id in self.active_jobs:
                self.active_jobs[job_id] = status

            return status

        except Exception as e:
            logger.error(f"Failed to get status for job {job_id}: {str(e)}")
            raise JobError(f"Status check failed: {str(e)}")

    async def list_active_jobs(self) -> list[JobStatus]:
        """
        List all active jobs

        Returns:
            List of JobStatus objects
        """
        try:
            # Get latest status for all active jobs
            active_statuses = []
            for job_id in list(self.active_jobs.keys()):
                try:
                    status = await self.get_job_status(job_id)
                    active_statuses.append(status)

                    # Remove completed/failed jobs from active tracking
                    if status.is_terminal:
                        del self.active_jobs[job_id]

                except Exception as e:
                    logger.warning(f"Could not get status for job {job_id}: {str(e)}")

            return active_statuses

        except Exception as e:
            logger.error(f"Failed to list active jobs: {str(e)}")
            raise JobError(f"Job listing failed: {str(e)}")

    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job

        Args:
            job_id: Job identifier

        Returns:
            True if cancelled successfully
        """
        try:
            logger.info(f"Cancelling job: {job_id}")
            result = await self.job_runner.cancel_job(job_id)

            # Update local tracking
            if job_id in self.active_jobs:
                self.active_jobs[job_id].state = JobState.CANCELLED

            return result

        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {str(e)}")
            raise JobError(f"Job cancellation failed: {str(e)}")

    async def wait_for_completion(
        self, job_id: str, timeout_seconds: int = 3600, poll_interval: int = 30
    ) -> JobStatus:
        """
        Wait for a job to complete

        Args:
            job_id: Job identifier
            timeout_seconds: Maximum time to wait
            poll_interval: Seconds between status checks

        Returns:
            Final JobStatus
        """
        start_time = datetime.now()

        while True:
            status = await self.get_job_status(job_id)

            if status.is_terminal:
                logger.info(f"Job {job_id} completed with state: {status.state}")
                return status

            # Check timeout
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > timeout_seconds:
                logger.warning(f"Job {job_id} timed out after {elapsed} seconds")
                raise JobError(f"Job {job_id} timed out")

            # Wait before next poll
            await asyncio.sleep(poll_interval)

    async def get_job_logs(self, job_id: str, lines: int = 100) -> list[str]:
        """
        Get logs for a job (if supported by runner)

        Args:
            job_id: Job identifier
            lines: Number of log lines to retrieve

        Returns:
            List of log lines
        """
        try:
            # Check if runner supports log retrieval
            if hasattr(self.job_runner, "get_job_logs"):
                return await self.job_runner.get_job_logs(job_id, lines)
            else:
                logger.warning(
                    f"Log retrieval not supported by {self.job_runner.__class__.__name__}"
                )
                return []

        except Exception as e:
            logger.error(f"Failed to get logs for job {job_id}: {str(e)}")
            return []

    def get_runner_info(self) -> dict[str, Any]:
        """
        Get information about the current job runner

        Returns:
            Dictionary with runner information
        """
        return {
            "runner_type": self.job_runner.__class__.__name__,
            "active_jobs": len(self.active_jobs),
            "capabilities": {
                "submit_job": True,
                "get_status": True,
                "cancel_job": True,
                "list_jobs": hasattr(self.job_runner, "list_jobs"),
                "get_logs": hasattr(self.job_runner, "get_job_logs"),
            },
        }
