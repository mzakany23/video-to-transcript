"""
Tests for Webhook API
"""

from unittest.mock import Mock, patch


class TestWebhookAPI:
    """Test webhook API endpoints"""

    def test_health_check(self, webhook_client):
        """Test health check endpoint"""
        response = webhook_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    @patch("api.webhook_api.dependencies.get_service_factory")
    def test_detailed_status(self, mock_factory_dep, webhook_client, mock_service_factory):
        """Test detailed status endpoint"""
        mock_factory_dep.return_value = mock_service_factory

        response = webhook_client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "configuration" in data
        assert "validation" in data

    @patch("api.webhook_api.dependencies.get_webhook_service")
    def test_process_webhook(self, mock_webhook_dep, webhook_client, sample_webhook_payload):
        """Test webhook processing"""
        mock_webhook = Mock()
        mock_webhook.process_notification.return_value = {
            "processed": True,
            "jobs_created": 2,
            "handler": "dropbox",
        }
        mock_webhook_dep.return_value = mock_webhook

        response = webhook_client.post("/webhooks/dropbox", json=sample_webhook_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["processed"] is True
        assert data["jobs_created"] == 2

    @patch("api.webhook_api.dependencies.get_webhook_service")
    def test_validate_webhook(self, mock_webhook_dep, webhook_client):
        """Test webhook validation"""
        mock_webhook = Mock()
        mock_webhook.validate_notification.return_value = {
            "valid": True,
            "handler": "dropbox",
            "message": "Webhook payload is valid",
        }
        mock_webhook_dep.return_value = mock_webhook

        # Use sample payload inline since fixture isn't passed to this test
        sample_payload = {
            "list_folder": {"accounts": ["dbid:test123"], "cursor": "cursor123"},
            "delta": {"users": [1234567]},
        }
        response = webhook_client.post("/webhooks/dropbox/validate", json=sample_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["handler"] == "dropbox"


class TestCursorsAPI:
    """Test cursor management endpoints"""

    @patch("api.webhook_api.dependencies.get_cursor_manager")
    def test_get_cursors(self, mock_cursor_dep, webhook_client):
        """Test get all cursors"""
        mock_cursor = Mock()
        mock_cursor.get_all_cursors.return_value = {
            "dropbox": {"user123": "cursor_abc123", "user456": "cursor_def456"}
        }
        mock_cursor_dep.return_value = mock_cursor

        response = webhook_client.get("/cursors/")
        assert response.status_code == 200
        data = response.json()
        assert "dropbox" in data["cursors"]
        assert "user123" in data["cursors"]["dropbox"]

    @patch("api.webhook_api.dependencies.get_cursor_manager")
    def test_get_cursor_by_user(self, mock_cursor_dep, webhook_client):
        """Test get cursor for specific user"""
        mock_cursor = Mock()
        mock_cursor.get_cursor.return_value = "cursor_abc123"
        mock_cursor_dep.return_value = mock_cursor

        response = webhook_client.get("/cursors/dropbox/user123")
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "dropbox"
        assert data["user_id"] == "user123"
        assert data["cursor"] == "cursor_abc123"

    @patch("api.webhook_api.dependencies.get_cursor_manager")
    def test_set_cursor(self, mock_cursor_dep, webhook_client):
        """Test set cursor for user"""
        mock_cursor = Mock()
        mock_cursor.save_cursor.return_value = True
        mock_cursor_dep.return_value = mock_cursor

        request_data = {"cursor": "new_cursor_123"}
        response = webhook_client.post("/cursors/dropbox/user123", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "dropbox"
        assert data["user_id"] == "user123"
        assert data["cursor"] == "new_cursor_123"
        assert data["saved"] is True

    @patch("api.webhook_api.dependencies.get_cursor_manager")
    def test_delete_cursor(self, mock_cursor_dep, webhook_client):
        """Test delete cursor"""
        mock_cursor = Mock()
        mock_cursor.delete_cursor.return_value = True
        mock_cursor_dep.return_value = mock_cursor

        response = webhook_client.delete("/cursors/dropbox/user123")
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "dropbox"
        assert data["user_id"] == "user123"
        assert data["deleted"] is True


class TestTrackingAPI:
    """Test job tracking endpoints"""

    @patch("api.webhook_api.dependencies.get_job_tracker")
    def test_get_tracking_stats(self, mock_tracker_dep, webhook_client):
        """Test get tracking statistics"""
        mock_tracker = Mock()
        mock_tracker.get_statistics.return_value = {
            "total_processed": 150,
            "duplicates_prevented": 12,
            "active_jobs": 3,
            "failed_jobs": 2,
        }
        mock_tracker_dep.return_value = mock_tracker

        response = webhook_client.get("/tracking/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_processed"] == 150
        assert data["duplicates_prevented"] == 12

    @patch("api.webhook_api.dependencies.get_job_tracker")
    def test_check_duplicate(self, mock_tracker_dep, webhook_client):
        """Test duplicate check"""
        mock_tracker = Mock()
        mock_tracker.is_duplicate.return_value = False
        mock_tracker_dep.return_value = mock_tracker

        request_data = {"content_hash": "abc123def456"}
        response = webhook_client.post("/tracking/check-duplicate", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["is_duplicate"] is False
        assert data["content_hash"] == "abc123def456"

    @patch("api.webhook_api.dependencies.get_job_tracker")
    def test_mark_processed(self, mock_tracker_dep, webhook_client):
        """Test mark job as processed"""
        mock_tracker = Mock()
        mock_tracker.mark_processed.return_value = True
        mock_tracker_dep.return_value = mock_tracker

        request_data = {"content_hash": "abc123def456", "job_id": "job-12345"}
        response = webhook_client.post("/tracking/mark-processed", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["marked"] is True
        assert data["content_hash"] == "abc123def456"


class TestAdminAPI:
    """Test admin endpoints"""

    @patch("api.webhook_api.dependencies.get_cursor_manager")
    @patch("api.webhook_api.dependencies.get_job_tracker")
    def test_get_system_info(self, mock_tracker_dep, mock_cursor_dep, webhook_client):
        """Test system information"""
        mock_cursor = Mock()
        mock_cursor.get_statistics.return_value = {
            "total_cursors": 15,
            "providers": ["dropbox", "google_drive"],
        }
        mock_cursor_dep.return_value = mock_cursor

        mock_tracker = Mock()
        mock_tracker.get_statistics.return_value = {
            "total_processed": 150,
            "duplicates_prevented": 12,
        }
        mock_tracker_dep.return_value = mock_tracker

        response = webhook_client.get("/admin/system")
        assert response.status_code == 200
        data = response.json()
        assert "cursor_stats" in data
        assert "tracking_stats" in data
        assert data["cursor_stats"]["total_cursors"] == 15

    @patch("api.webhook_api.dependencies.get_job_tracker")
    def test_cleanup_old_records(self, mock_tracker_dep, webhook_client):
        """Test cleanup old records"""
        mock_tracker = Mock()
        mock_tracker_dep.return_value = mock_tracker

        response = webhook_client.post("/admin/cleanup")
        assert response.status_code == 200
        data = response.json()
        assert data["cleanup_performed"] is True
        assert "records_would_remove" in data

    @patch("api.webhook_api.dependencies.get_cursor_manager")
    @patch("api.webhook_api.dependencies.get_job_tracker")
    def test_reset_cursors(self, mock_tracker_dep, mock_cursor_dep, webhook_client):
        """Test reset all cursors"""
        mock_cursor = Mock()
        mock_cursor.reset_all_cursors.return_value = True
        mock_cursor_dep.return_value = mock_cursor

        mock_tracker = Mock()
        mock_tracker_dep.return_value = mock_tracker

        response = webhook_client.post("/admin/reset-cursors")
        assert response.status_code == 200
        data = response.json()
        assert data["reset"] is True

    @patch("api.webhook_api.dependencies.get_service_factory")
    def test_get_configuration(self, mock_factory_dep, webhook_client, mock_service_factory):
        """Test get configuration"""
        mock_factory_dep.return_value = mock_service_factory

        response = webhook_client.get("/admin/config")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert "settings" in data
