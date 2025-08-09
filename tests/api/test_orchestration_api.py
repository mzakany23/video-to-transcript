"""
Tests for Orchestration API
"""

import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient


class TestOrchestrationAPI:
    """Test orchestration API endpoints"""
    
    def test_health_check(self, orchestration_client):
        """Test health check endpoint"""
        response = orchestration_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        
    @patch("api.orchestration_api.dependencies.get_service_factory")
    @patch("api.orchestration_api.dependencies.get_orchestration_service")
    def test_detailed_status(self, mock_orchestration_dep, mock_factory_dep, orchestration_client, mock_service_factory):
        """Test detailed status endpoint"""
        mock_factory_dep.return_value = mock_service_factory
        
        mock_orchestration = Mock()
        mock_orchestration.get_runner_info.return_value = {
            "runner_type": "LocalJobRunner",
            "active_jobs": 2,
            "capabilities": {"max_concurrent": 5}
        }
        mock_orchestration_dep.return_value = mock_orchestration
        
        response = orchestration_client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "runner_info" in data
        assert data["statistics"]["active_jobs"] == 2


class TestJobsAPI:
    """Test job management endpoints"""
    
    @patch("api.orchestration_api.dependencies.get_orchestration_service")
    def test_submit_job(self, mock_orchestration_dep, orchestration_client, sample_job_request):
        """Test job submission"""
        mock_orchestration = Mock()
        mock_orchestration.submit_transcription_job.return_value = "job-12345"
        mock_orchestration.job_runner.__class__.__name__ = "LocalJobRunner"
        mock_orchestration_dep.return_value = mock_orchestration
        
        response = orchestration_client.post("/jobs/", json=sample_job_request)
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job-12345"
        assert data["status"] == "pending"
        assert data["runner"] == "LocalJobRunner"
        
    @patch("api.orchestration_api.dependencies.get_orchestration_service")
    def test_list_jobs(self, mock_orchestration_dep, orchestration_client):
        """Test job listing"""
        # Mock job data
        mock_job = Mock()
        mock_job.job_id = "job-12345"
        mock_job.state.value = "running"
        mock_job.started_at = None
        mock_job.completed_at = None
        mock_job.metadata = {"file_name": "test.mp3"}
        
        mock_orchestration = Mock()
        mock_orchestration.list_active_jobs.return_value = [mock_job]
        mock_orchestration.job_runner.__class__.__name__ = "LocalJobRunner"
        mock_orchestration_dep.return_value = mock_orchestration
        
        response = orchestration_client.get("/jobs/")
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["job_id"] == "job-12345"
        assert data["jobs"][0]["status"] == "running"
        
    @patch("api.orchestration_api.dependencies.get_orchestration_service")
    def test_get_job(self, mock_orchestration_dep, orchestration_client):
        """Test get single job"""
        mock_status = Mock()
        mock_status.state.value = "completed"
        mock_status.started_at = None
        mock_status.completed_at = None
        mock_status.metadata = {"file_name": "test.mp3"}
        mock_status.is_terminal = True
        
        mock_orchestration = Mock()
        mock_orchestration.get_job_status.return_value = mock_status
        mock_orchestration.job_runner.__class__.__name__ = "LocalJobRunner"
        mock_orchestration_dep.return_value = mock_orchestration
        
        response = orchestration_client.get("/jobs/job-12345")
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job-12345"
        assert data["status"] == "completed"
        assert data["is_terminal"] is True
        
    @patch("api.orchestration_api.dependencies.get_orchestration_service")
    def test_cancel_job(self, mock_orchestration_dep, orchestration_client):
        """Test job cancellation"""
        mock_orchestration = Mock()
        mock_orchestration.cancel_job.return_value = True
        mock_orchestration_dep.return_value = mock_orchestration
        
        response = orchestration_client.delete("/jobs/job-12345")
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job-12345"
        assert data["status"] == "cancelled"
        
    @patch("api.orchestration_api.dependencies.get_orchestration_service")
    def test_get_job_logs(self, mock_orchestration_dep, orchestration_client):
        """Test get job logs"""
        mock_orchestration = Mock()
        mock_orchestration.get_job_logs.return_value = [
            "2024-01-01T00:00:00 Starting job",
            "2024-01-01T00:01:00 Job completed"
        ]
        mock_orchestration_dep.return_value = mock_orchestration
        
        response = orchestration_client.get("/jobs/job-12345/logs")
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job-12345"
        assert len(data["logs"]) == 2


class TestBatchAPI:
    """Test batch operations endpoints"""
    
    @patch("api.orchestration_api.dependencies.get_orchestration_service")
    def test_submit_batch_jobs(self, mock_orchestration_dep, orchestration_client, sample_batch_request):
        """Test batch job submission"""
        mock_orchestration = Mock()
        mock_orchestration.submit_batch_jobs.return_value = ["job-1", "job-2"]
        mock_orchestration_dep.return_value = mock_orchestration
        
        response = orchestration_client.post("/batch/", json=sample_batch_request)
        assert response.status_code == 200
        data = response.json()
        assert "batch_id" in data
        assert data["job_ids"] == ["job-1", "job-2"]
        assert data["total_jobs"] == 2
        assert data["successful_submissions"] == 2
        assert data["failed_submissions"] == 0
        
    def test_submit_empty_batch(self, orchestration_client):
        """Test empty batch submission"""
        empty_batch = {"jobs": [], "max_concurrent": 5}
        
        response = orchestration_client.post("/batch/", json=empty_batch)
        assert response.status_code == 400
        data = response.json()
        assert "No jobs provided" in data["detail"]
        
    def test_submit_oversized_batch(self, orchestration_client):
        """Test oversized batch submission"""
        large_batch = {
            "jobs": [{"input_data": {"file_path": f"/files/audio{i}.mp3"}} for i in range(101)],
            "max_concurrent": 5
        }
        
        response = orchestration_client.post("/batch/", json=large_batch)
        assert response.status_code == 400
        data = response.json()
        assert "Maximum 100 jobs" in data["detail"]
        
    def test_get_batch_status(self, orchestration_client):
        """Test get batch status"""
        response = orchestration_client.get("/batch/batch_20240101_120000")
        assert response.status_code == 200
        data = response.json()
        assert data["batch_id"] == "batch_20240101_120000"
        assert "total_jobs" in data
        assert "overall_progress" in data


class TestRunnersAPI:
    """Test runner management endpoints"""
    
    @patch("api.orchestration_api.dependencies.get_service_factory")
    def test_list_runners(self, mock_factory_dep, orchestration_client, mock_service_factory):
        """Test list available runners"""
        mock_factory_dep.return_value = mock_service_factory
        
        response = orchestration_client.get("/runners/")
        assert response.status_code == 200
        data = response.json()
        assert "runners" in data
        assert "current_runner" in data
        assert len(data["runners"]) >= 1
        
    @patch("api.orchestration_api.dependencies.get_orchestration_service")
    def test_get_current_runner(self, mock_orchestration_dep, orchestration_client):
        """Test get current runner info"""
        mock_orchestration = Mock()
        mock_orchestration.get_runner_info.return_value = {
            "runner_type": "LocalJobRunner",
            "active_jobs": 3,
            "capabilities": {"max_concurrent": 5, "supports_cancellation": True}
        }
        mock_orchestration_dep.return_value = mock_orchestration
        
        response = orchestration_client.get("/runners/current")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "LocalJobRunner"
        assert data["active_jobs"] == 3
        assert "capabilities" in data
        
    @patch("api.orchestration_api.dependencies.get_service_factory")
    def test_validate_runner(self, mock_factory_dep, orchestration_client, mock_service_factory):
        """Test runner validation"""
        mock_factory_dep.return_value = mock_service_factory
        
        # Update mock to return runner validation
        mock_service_factory.validate_configuration.return_value = {
            "valid": True,
            "provider_status": {
                "job_runner": {
                    "status": "valid",
                    "name": "local",
                    "error": None
                }
            }
        }
        
        response = orchestration_client.post("/runners/local/validate")
        assert response.status_code == 200
        data = response.json()
        assert data["runner_id"] == "local"
        assert data["valid"] is True
        assert data["available"] is True
        
    @patch("api.orchestration_api.dependencies.get_service_factory")
    def test_validate_nonexistent_runner(self, mock_factory_dep, orchestration_client, mock_service_factory):
        """Test validation of nonexistent runner"""
        mock_factory_dep.return_value = mock_service_factory
        
        # Mock validation with no matching runner
        mock_service_factory.validate_configuration.return_value = {
            "valid": True,
            "provider_status": {}
        }
        
        response = orchestration_client.post("/runners/nonexistent/validate")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]


class TestJobFiltering:
    """Test job filtering and pagination"""
    
    @patch("api.orchestration_api.dependencies.get_orchestration_service")
    def test_filter_jobs_by_status(self, mock_orchestration_dep, orchestration_client):
        """Test filtering jobs by status"""
        # Mock jobs with different statuses
        running_job = Mock()
        running_job.job_id = "job-1"
        running_job.state.value = "running"
        running_job.started_at = None
        running_job.completed_at = None
        running_job.metadata = {}
        
        completed_job = Mock()
        completed_job.job_id = "job-2"
        completed_job.state.value = "completed"
        completed_job.started_at = None
        completed_job.completed_at = None
        completed_job.metadata = {}
        
        mock_orchestration = Mock()
        mock_orchestration.list_active_jobs.return_value = [running_job, completed_job]
        mock_orchestration.job_runner.__class__.__name__ = "LocalJobRunner"
        mock_orchestration_dep.return_value = mock_orchestration
        
        # Filter for running jobs only
        response = orchestration_client.get("/jobs/?status=running")
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["status"] == "running"
        
    @patch("api.orchestration_api.dependencies.get_orchestration_service")  
    def test_job_pagination(self, mock_orchestration_dep, orchestration_client):
        """Test job pagination"""
        # Mock many jobs
        jobs = []
        for i in range(75):
            job = Mock()
            job.job_id = f"job-{i}"
            job.state.value = "completed"
            job.started_at = None
            job.completed_at = None
            job.metadata = {}
            jobs.append(job)
        
        mock_orchestration = Mock()
        mock_orchestration.list_active_jobs.return_value = jobs
        mock_orchestration.job_runner.__class__.__name__ = "LocalJobRunner"
        mock_orchestration_dep.return_value = mock_orchestration
        
        # Test with limit
        response = orchestration_client.get("/jobs/?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 10
        assert data["total"] == 75
        assert data["has_more"] is True