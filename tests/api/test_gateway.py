"""
Tests for API Gateway
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock
from fastapi.testclient import TestClient
import httpx


class TestGatewayAPI:
    """Test gateway API endpoints"""
    
    def test_root_endpoint(self, gateway_client):
        """Test root endpoint returns gateway info"""
        response = gateway_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Transcription Platform Gateway"
        assert data["version"] == "1.0.0"
        assert "services" in data
        assert "endpoints" in data
        
    def test_health_check(self, gateway_client):
        """Test health check endpoint"""
        response = gateway_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["gateway"] == "operational"
        
    def test_list_services(self, gateway_client):
        """Test list services endpoint"""
        response = gateway_client.get("/services")
        assert response.status_code == 200
        data = response.json()
        assert "services" in data
        services = data["services"]
        assert "transcription" in services
        assert "webhook" in services
        assert "orchestration" in services
        
        # Check service structure
        transcription_service = services["transcription"]
        assert transcription_service["name"] == "Transcription API"
        assert transcription_service["url"] == "http://localhost:8001"
        assert transcription_service["prefix"] == "/api/v1/transcription"


class TestGatewayHealthChecks:
    """Test gateway health check functionality"""
    
    @patch("api.gateway.main.health_checker.check_all_services")
    async def test_detailed_status_all_healthy(self, mock_check_all, gateway_client):
        """Test detailed status when all services are healthy"""
        mock_check_all.return_value = {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00",
            "services": {
                "transcription": {
                    "name": "Transcription API",
                    "status": "healthy",
                    "url": "http://localhost:8001",
                    "response_time": 0.05,
                    "version": "0.1.0"
                },
                "webhook": {
                    "name": "Webhook API",
                    "status": "healthy",
                    "url": "http://localhost:8002",
                    "response_time": 0.03,
                    "version": "0.1.0"
                },
                "orchestration": {
                    "name": "Orchestration API",
                    "status": "healthy",
                    "url": "http://localhost:8003",
                    "response_time": 0.04,
                    "version": "0.1.0"
                }
            },
            "summary": {
                "total_services": 3,
                "healthy_services": 3,
                "unhealthy_services": 0
            }
        }
        
        response = gateway_client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["summary"]["healthy_services"] == 3
        assert data["summary"]["unhealthy_services"] == 0
        
    @patch("api.gateway.main.health_checker.check_all_services")
    async def test_detailed_status_degraded(self, mock_check_all, gateway_client):
        """Test detailed status when some services are down"""
        mock_check_all.return_value = {
            "status": "degraded",
            "timestamp": "2024-01-01T00:00:00",
            "services": {
                "transcription": {
                    "name": "Transcription API",
                    "status": "healthy",
                    "url": "http://localhost:8001",
                    "response_time": 0.05,
                    "version": "0.1.0"
                },
                "webhook": {
                    "name": "Webhook API",
                    "status": "error",
                    "url": "http://localhost:8002",
                    "error": "Connection refused"
                },
                "orchestration": {
                    "name": "Orchestration API",
                    "status": "timeout",
                    "url": "http://localhost:8003",
                    "error": "Request timeout"
                }
            },
            "summary": {
                "total_services": 3,
                "healthy_services": 1,
                "unhealthy_services": 2
            }
        }
        
        response = gateway_client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["summary"]["healthy_services"] == 1
        assert data["summary"]["unhealthy_services"] == 2
        
    @patch("api.gateway.main.health_checker.check_service")
    async def test_individual_service_health(self, mock_check_service, gateway_client):
        """Test individual service health check"""
        mock_check_service.return_value = {
            "name": "Transcription API",
            "status": "healthy",
            "url": "http://localhost:8001",
            "response_time": 0.05,
            "version": "0.1.0",
            "last_check": "2024-01-01T00:00:00"
        }
        
        response = gateway_client.get("/services/transcription/health")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Transcription API"
        assert data["status"] == "healthy"
        assert data["response_time"] == 0.05
        
    def test_invalid_service_health(self, gateway_client):
        """Test health check for invalid service"""
        response = gateway_client.get("/services/invalid_service/health")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]


class TestGatewayProxy:
    """Test gateway proxy functionality"""
    
    @patch("api.gateway.main.httpx.AsyncClient")
    def test_proxy_transcription_request(self, mock_client, gateway_client):
        """Test proxying request to transcription service"""
        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}
        mock_response.headers = {"content-type": "application/json"}
        
        mock_client_instance = AsyncMock()
        mock_client_instance.request.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        response = gateway_client.get("/api/v1/transcription/health")
        assert response.status_code == 200
        
        # Verify the request was proxied correctly
        mock_client_instance.request.assert_called_once()
        call_args = mock_client_instance.request.call_args
        assert call_args[1]["method"] == "GET"
        assert "localhost:8001/health" in call_args[1]["url"]
        
    @patch("api.gateway.main.httpx.AsyncClient")
    def test_proxy_webhook_request(self, mock_client, gateway_client):
        """Test proxying request to webhook service"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"processed": True}
        mock_response.headers = {"content-type": "application/json"}
        
        mock_client_instance = AsyncMock()
        mock_client_instance.request.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        test_payload = {"test": "data"}
        response = gateway_client.post("/api/v1/webhook/webhooks/dropbox", json=test_payload)
        assert response.status_code == 200
        
        # Verify POST request was proxied with body
        mock_client_instance.request.assert_called_once()
        call_args = mock_client_instance.request.call_args
        assert call_args[1]["method"] == "POST"
        assert "localhost:8002/webhooks/dropbox" in call_args[1]["url"]
        
    @patch("api.gateway.main.httpx.AsyncClient")
    def test_proxy_orchestration_request(self, mock_client, gateway_client):
        """Test proxying request to orchestration service"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"jobs": []}
        mock_response.headers = {"content-type": "application/json"}
        
        mock_client_instance = AsyncMock()
        mock_client_instance.request.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        response = gateway_client.get("/api/v1/orchestration/jobs/?limit=10")
        assert response.status_code == 200
        
        # Verify query parameters were preserved
        mock_client_instance.request.assert_called_once()
        call_args = mock_client_instance.request.call_args
        assert "limit=10" in call_args[1]["url"]
        
    @patch("api.gateway.main.httpx.AsyncClient")
    def test_proxy_service_timeout(self, mock_client, gateway_client):
        """Test proxy handling of service timeout"""
        mock_client_instance = AsyncMock()
        mock_client_instance.request.side_effect = httpx.TimeoutException("Request timed out")
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        response = gateway_client.get("/api/v1/transcription/health")
        assert response.status_code == 504
        data = response.json()
        assert "Gateway timeout" in data["detail"]
        
    @patch("api.gateway.main.httpx.AsyncClient")
    def test_proxy_service_unavailable(self, mock_client, gateway_client):
        """Test proxy handling of service unavailable"""
        mock_client_instance = AsyncMock()
        mock_client_instance.request.side_effect = httpx.ConnectError("Connection failed")
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        response = gateway_client.get("/api/v1/transcription/health")
        assert response.status_code == 503
        data = response.json()
        assert "Service unavailable" in data["detail"]


class TestGatewayErrorHandling:
    """Test gateway error handling"""
    
    def test_proxy_to_invalid_service(self, gateway_client):
        """Test proxy to invalid service path"""
        # This should not match any proxy routes and return 404
        response = gateway_client.get("/api/v1/invalid_service/test")
        assert response.status_code == 404
        
    @patch("api.gateway.main.httpx.AsyncClient")
    def test_proxy_generic_error(self, mock_client, gateway_client):
        """Test proxy handling of generic errors"""
        mock_client_instance = AsyncMock()
        mock_client_instance.request.side_effect = Exception("Unexpected error")
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        response = gateway_client.get("/api/v1/transcription/health")
        assert response.status_code == 502
        data = response.json()
        assert "Bad gateway" in data["detail"]
        
    @patch("api.gateway.main.httpx.AsyncClient")
    def test_proxy_non_json_response(self, mock_client, gateway_client):
        """Test proxy handling of non-JSON response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Plain text response"
        mock_response.headers = {"content-type": "text/plain"}
        
        # Mock json() to raise an exception for non-JSON content
        mock_response.json.side_effect = ValueError("Not JSON")
        
        mock_client_instance = AsyncMock()
        mock_client_instance.request.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        response = gateway_client.get("/api/v1/transcription/health")
        assert response.status_code == 200


class TestGatewayConfiguration:
    """Test gateway configuration"""
    
    @patch.dict("api.gateway.main.SERVICES", {
        "test_service": {
            "name": "Test Service",
            "url": "http://localhost:9999",
            "health_path": "/health",
            "prefix": "/api/v1/test"
        }
    })
    def test_dynamic_service_configuration(self, gateway_client):
        """Test gateway with dynamically configured services"""
        response = gateway_client.get("/services")
        assert response.status_code == 200
        data = response.json()
        assert "test_service" in data["services"]
        assert data["services"]["test_service"]["name"] == "Test Service"