"""
Google Cloud Run implementation of JobRunner
"""

import os
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor
import logging

from ...core.interfaces import JobRunner
from ...core.models import JobSpec, JobStatus, JobState
from ...core.exceptions import JobException, AuthenticationException
from ...core.logging import get_logger

logger = get_logger(__name__)

# Thread pool for blocking Google Cloud API calls
executor = ThreadPoolExecutor(max_workers=3)


class CloudRunJobRunner(JobRunner):
    """
    Google Cloud Run implementation of job runner
    """
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        region: Optional[str] = None,
        job_name: Optional[str] = None
    ):
        """
        Initialize Cloud Run job runner
        
        Args:
            project_id: GCP project ID
            region: GCP region  
            job_name: Cloud Run job name
        """
        self.project_id = project_id or os.environ.get('PROJECT_ID')
        self.region = region or os.environ.get('GCP_REGION', 'us-east1')
        self.job_name = job_name or os.environ.get('WORKER_JOB_NAME', 'transcription-worker')
        
        if not self.project_id:
            raise AuthenticationException("PROJECT_ID is required for Cloud Run jobs")
        
        self.job_path = f"projects/{self.project_id}/locations/{self.region}/jobs/{self.job_name}"
        
        # Initialize Cloud Run client
        self._initialize_client()
        
        logger.info(
            f"Initialized CloudRunJobRunner: {self.project_id}/{self.region}/{self.job_name}"
        )
    
    def _initialize_client(self):
        """Initialize Google Cloud Run client"""
        try:
            from google.cloud import run_v2
            self.run_client = run_v2.JobsClient()
            logger.info("Cloud Run client initialized successfully")
        except ImportError:
            raise JobException(
                "Google Cloud Run library not installed. Run: pip install google-cloud-run"
            )
        except Exception as e:
            raise AuthenticationException(f"Failed to initialize Cloud Run client: {str(e)}")
    
    def _run_sync(self, coro):
        """Run async coroutine in thread pool"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    async def submit_job(self, spec: JobSpec) -> str:
        """
        Submit a job to Cloud Run
        
        Args:
            spec: Job specification
            
        Returns:
            Job execution name (used as job ID)
        """
        def _submit():
            try:
                from google.cloud import run_v2
                
                # Create execution request
                container_overrides = []
                
                # Set environment variables
                env_vars = []
                for key, value in spec.environment.items():
                    env_vars.append(run_v2.EnvVar(name=key, value=value))
                
                if env_vars:
                    container_overrides.append(
                        run_v2.RunJobRequest.Overrides.ContainerOverride(
                            env=env_vars
                        )
                    )
                
                # Create request
                request = run_v2.RunJobRequest(
                    name=self.job_path,
                    overrides=run_v2.RunJobRequest.Overrides(
                        container_overrides=container_overrides
                    ) if container_overrides else None
                )
                
                # Submit job
                operation = self.run_client.run_job(request=request)
                
                # Extract execution name from operation
                execution_name = getattr(operation, 'name', str(operation))
                
                logger.info(f"Cloud Run job submitted: {execution_name}")
                return execution_name
                
            except Exception as e:
                logger.error(f"Cloud Run job submission failed: {str(e)}")
                raise JobException(f"Failed to submit job: {str(e)}")
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, _submit)
    
    async def get_status(self, job_id: str) -> JobStatus:
        """
        Get status of a Cloud Run job execution
        
        Args:
            job_id: Job execution name
            
        Returns:
            JobStatus object
        """
        def _get_status():
            try:
                from google.cloud import run_v2
                
                # Parse execution name to get the execution path
                if '/executions/' in job_id:
                    execution_path = job_id
                else:
                    # Construct execution path (this is a simplified approach)
                    # In practice, we'd need to list executions and find the right one
                    execution_path = f"{self.job_path}/executions/{job_id}"
                
                try:
                    # Get execution details
                    execution_client = run_v2.ExecutionsClient()
                    execution = execution_client.get_execution(name=execution_path)
                    
                    # Map Cloud Run conditions to our job states
                    state = self._map_cloud_run_state(execution)
                    
                    return JobStatus(
                        job_id=job_id,
                        state=state,
                        started_at=getattr(execution, 'start_time', None),
                        completed_at=getattr(execution, 'completion_time', None),
                        metadata={
                            "execution_name": execution_path,
                            "project_id": self.project_id,
                            "region": self.region
                        }
                    )
                    
                except Exception as e:
                    # If we can't get execution details, return unknown state
                    logger.warning(f"Could not get execution details for {job_id}: {str(e)}")
                    return JobStatus(
                        job_id=job_id,
                        state=JobState.PENDING,
                        metadata={"error": str(e)}
                    )
                    
            except Exception as e:
                logger.error(f"Failed to get status for {job_id}: {str(e)}")
                raise JobException(f"Status check failed: {str(e)}")
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, _get_status)
    
    def _map_cloud_run_state(self, execution) -> JobState:
        """
        Map Cloud Run execution state to our JobState
        
        Args:
            execution: Cloud Run execution object
            
        Returns:
            JobState enum
        """
        try:
            # Cloud Run uses conditions to indicate state
            conditions = getattr(execution, 'conditions', [])
            
            for condition in conditions:
                condition_type = getattr(condition, 'type', '')
                condition_status = getattr(condition, 'status', '')
                
                if condition_type == 'Completed':
                    if condition_status == 'True':
                        return JobState.COMPLETED
                    elif condition_status == 'False':
                        return JobState.FAILED
                elif condition_type == 'Running':
                    if condition_status == 'True':
                        return JobState.RUNNING
            
            # Default to pending if no clear state
            return JobState.PENDING
            
        except Exception as e:
            logger.warning(f"Could not map Cloud Run state: {str(e)}")
            return JobState.PENDING
    
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a Cloud Run job execution
        
        Args:
            job_id: Job execution name
            
        Returns:
            True if cancelled successfully
        """
        def _cancel():
            try:
                from google.cloud import run_v2
                
                # Parse execution name
                if '/executions/' in job_id:
                    execution_path = job_id
                else:
                    execution_path = f"{self.job_path}/executions/{job_id}"
                
                # Cancel execution
                execution_client = run_v2.ExecutionsClient()
                execution_client.cancel_execution(name=execution_path)
                
                logger.info(f"Cloud Run job cancelled: {job_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to cancel Cloud Run job {job_id}: {str(e)}")
                return False
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, _cancel)
    
    async def list_jobs(
        self,
        state: Optional[JobState] = None,
        limit: int = 100
    ) -> List[JobStatus]:
        """
        List Cloud Run job executions
        
        Args:
            state: Filter by job state (optional)
            limit: Maximum number of jobs to return
            
        Returns:
            List of JobStatus objects
        """
        def _list():
            try:
                from google.cloud import run_v2
                
                # List executions
                execution_client = run_v2.ExecutionsClient()
                executions = execution_client.list_executions(
                    parent=self.job_path,
                    page_size=limit
                )
                
                job_statuses = []
                for execution in executions:
                    execution_state = self._map_cloud_run_state(execution)
                    
                    # Filter by state if specified
                    if state and execution_state != state:
                        continue
                    
                    job_status = JobStatus(
                        job_id=execution.name,
                        state=execution_state,
                        started_at=getattr(execution, 'start_time', None),
                        completed_at=getattr(execution, 'completion_time', None),
                        metadata={
                            "execution_name": execution.name,
                            "project_id": self.project_id,
                            "region": self.region
                        }
                    )
                    job_statuses.append(job_status)
                
                return job_statuses
                
            except Exception as e:
                logger.error(f"Failed to list Cloud Run jobs: {str(e)}")
                raise JobException(f"Job listing failed: {str(e)}")
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, _list)
    
    async def get_job_logs(self, job_id: str, lines: int = 100) -> List[str]:
        """
        Get logs for a Cloud Run job execution
        
        Args:
            job_id: Job execution name
            lines: Number of log lines to retrieve
            
        Returns:
            List of log lines
        """
        def _get_logs():
            try:
                from google.cloud import logging as cloud_logging
                
                # Initialize logging client
                logging_client = cloud_logging.Client(project=self.project_id)
                
                # Build log filter for this execution
                # Cloud Run logs use resource.type="cloud_run_job"
                log_filter = f'''
                resource.type="cloud_run_job"
                resource.labels.job_name="{self.job_name}"
                resource.labels.location="{self.region}"
                '''
                
                # If we have execution details, filter by execution
                if '/executions/' in job_id:
                    execution_id = job_id.split('/executions/')[-1]
                    log_filter += f'\nresource.labels.execution_name="{execution_id}"'
                
                # Get logs
                entries = logging_client.list_entries(
                    filter_=log_filter,
                    order_by=cloud_logging.DESCENDING,
                    max_results=lines
                )
                
                # Extract log messages
                log_lines = []
                for entry in entries:
                    timestamp = entry.timestamp.isoformat() if entry.timestamp else ''
                    payload = entry.payload if hasattr(entry, 'payload') else str(entry)
                    log_lines.append(f"{timestamp} {payload}")
                
                # Reverse to get chronological order
                log_lines.reverse()
                return log_lines
                
            except Exception as e:
                logger.error(f"Failed to get logs for {job_id}: {str(e)}")
                return [f"Error retrieving logs: {str(e)}"]
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, _get_logs)