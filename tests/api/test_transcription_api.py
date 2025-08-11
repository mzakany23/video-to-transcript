"""
Tests for Transcription API
"""

from unittest.mock import Mock, patch


class TestTranscriptionAPI:
    """Test transcription API endpoints"""

    def test_health_check(self, transcription_client):
        """Test health check endpoint"""
        response = transcription_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    @patch("api.transcription_api.dependencies.get_service_factory")
    def test_detailed_status(self, mock_factory_dep, transcription_client, mock_service_factory):
        """Test detailed status endpoint"""
        mock_factory_dep.return_value = mock_service_factory

        response = transcription_client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "configuration" in data
        assert "validation" in data

    @patch("api.transcription_api.dependencies.get_orchestration_service")
    def test_submit_job(self, mock_orchestration_dep, transcription_client, sample_job_request):
        """Test job submission"""
        # Mock orchestration service
        mock_orchestration = Mock()
        mock_orchestration.submit_transcription_job.return_value = "job-12345"
        mock_orchestration.job_runner.__class__.__name__ = "LocalJobRunner"
        mock_orchestration_dep.return_value = mock_orchestration

        response = transcription_client.post("/jobs/", json=sample_job_request)
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job-12345"
        assert data["status"] == "pending"
        assert "submitted_at" in data

    @patch("api.transcription_api.dependencies.get_orchestration_service")
    def test_list_jobs(self, mock_orchestration_dep, transcription_client):
        """Test job listing"""
        # Mock job data
        mock_job = Mock()
        mock_job.job_id = "job-12345"
        mock_job.state.value = "completed"
        mock_job.started_at = None
        mock_job.completed_at = None
        mock_job.metadata = {"file_name": "test.mp3"}

        mock_orchestration = Mock()
        mock_orchestration.list_active_jobs.return_value = [mock_job]
        mock_orchestration.job_runner.__class__.__name__ = "LocalJobRunner"
        mock_orchestration_dep.return_value = mock_orchestration

        response = transcription_client.get("/jobs/")
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["job_id"] == "job-12345"

    @patch("api.transcription_api.dependencies.get_orchestration_service")
    def test_get_job(self, mock_orchestration_dep, transcription_client):
        """Test get single job"""
        # Mock job status
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

        response = transcription_client.get("/jobs/job-12345")
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job-12345"
        assert data["status"] == "completed"
        assert data["is_terminal"] is True

    @patch("api.transcription_api.dependencies.get_orchestration_service")
    def test_cancel_job(self, mock_orchestration_dep, transcription_client):
        """Test job cancellation"""
        mock_orchestration = Mock()
        mock_orchestration.cancel_job.return_value = True
        mock_orchestration_dep.return_value = mock_orchestration

        response = transcription_client.delete("/jobs/job-12345")
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job-12345"
        assert data["status"] == "cancelled"

    @patch("api.transcription_api.dependencies.get_orchestration_service")
    def test_get_job_logs(self, mock_orchestration_dep, transcription_client):
        """Test get job logs"""
        mock_orchestration = Mock()
        mock_orchestration.get_job_logs.return_value = [
            "2024-01-01T00:00:00 Starting transcription job",
            "2024-01-01T00:01:00 Job completed successfully",
        ]
        mock_orchestration_dep.return_value = mock_orchestration

        response = transcription_client.get("/jobs/job-12345/logs")
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job-12345"
        assert len(data["logs"]) == 2

    @patch("api.transcription_api.dependencies.get_service_factory")
    def test_list_providers(self, mock_factory_dep, transcription_client, mock_service_factory):
        """Test list providers endpoint"""
        mock_factory_dep.return_value = mock_service_factory

        response = transcription_client.get("/providers/")
        assert response.status_code == 200
        data = response.json()
        assert "storage" in data["providers"]
        assert "transcription" in data["providers"]
        assert "job_runner" in data["providers"]

    @patch("api.transcription_api.dependencies.get_service_factory")
    def test_get_provider(self, mock_factory_dep, transcription_client, mock_service_factory):
        """Test get specific provider"""
        mock_factory_dep.return_value = mock_service_factory

        response = transcription_client.get("/providers/storage")
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "storage"
        assert "available" in data
        assert "enabled" in data

    @patch("api.transcription_api.dependencies.get_service_factory")
    def test_validate_provider(self, mock_factory_dep, transcription_client, mock_service_factory):
        """Test provider validation"""
        mock_factory_dep.return_value = mock_service_factory

        response = transcription_client.post("/providers/storage/validate")
        assert response.status_code == 200
        data = response.json()
        assert data["provider_type"] == "storage"
        assert "valid" in data
        assert "message" in data


class TestTranscriptionEndpoints:
    """Test transcription-specific endpoints"""

    @patch("api.transcription_api.dependencies.get_orchestration_service")
    def test_transcribe_file(self, mock_orchestration_dep, transcription_client):
        """Test file transcription"""
        mock_orchestration = Mock()
        mock_orchestration.submit_transcription_job.return_value = "job-12345"
        mock_orchestration_dep.return_value = mock_orchestration

        request_data = {
            "file_path": "/files/test.mp3",
            "options": {"language": "en", "format": "json"},
        }

        response = transcription_client.post("/transcription/file", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job-12345"
        assert data["status"] == "pending"

    def test_transcribe_url_validation(self, transcription_client):
        """Test URL transcription validation"""
        request_data = {"url": "not-a-valid-url", "options": {"language": "en"}}

        response = transcription_client.post("/transcription/url", json=request_data)
        assert response.status_code == 422  # Validation error

    @patch("api.transcription_api.dependencies.get_service_factory")
    def test_get_formats(self, mock_factory_dep, transcription_client, mock_service_factory):
        """Test get supported formats"""
        mock_factory_dep.return_value = mock_service_factory
        mock_service_factory.get_transcription_provider().get_supported_formats.return_value = [
            "mp3",
            "wav",
            "m4a",
            "flac",
        ]

        response = transcription_client.get("/transcription/formats")
        assert response.status_code == 200
        data = response.json()
        assert "formats" in data
        assert "mp3" in data["formats"]

    @patch("api.transcription_api.dependencies.get_service_factory")
    def test_get_languages(self, mock_factory_dep, transcription_client, mock_service_factory):
        """Test get supported languages"""
        mock_factory_dep.return_value = mock_service_factory
        mock_provider = mock_service_factory.get_transcription_provider()
        mock_provider.get_supported_languages.return_value = [
            {"code": "en", "name": "English"},
            {"code": "es", "name": "Spanish"},
        ]

        response = transcription_client.get("/transcription/languages")
        assert response.status_code == 200
        data = response.json()
        assert "languages" in data
        assert len(data["languages"]) == 2
