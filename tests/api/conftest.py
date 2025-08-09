"""
Shared test fixtures for API testing
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Import API apps
from api.transcription_api.main import app as transcription_app
from api.webhook_api.main import app as webhook_app  
from api.orchestration_api.main import app as orchestration_app
from api.gateway.main import app as gateway_app

# Import services for mocking
from services.config.factory import ServiceFactory
from services.core.interfaces import (
    StorageProvider, TranscriptionProvider, 
    JobRunner, NotificationProvider
)


@pytest.fixture
def mock_storage_provider():
    """Mock storage provider"""
    mock = AsyncMock(spec=StorageProvider)
    mock.download.return_value = Mock(success=True, local_path="/tmp/test.mp3")
    mock.upload.return_value = Mock(success=True, url="https://storage.example.com/result.json")
    mock.list_files.return_value = [
        Mock(name="test1.mp3", path="/files/test1.mp3", size=1024),
        Mock(name="test2.wav", path="/files/test2.wav", size=2048)
    ]
    return mock


@pytest.fixture
def mock_transcription_provider():
    """Mock transcription provider"""
    mock = AsyncMock(spec=TranscriptionProvider)
    mock.transcribe.return_value = Mock(
        text="Hello, this is a test transcription.",
        confidence=0.95,
        segments=[
            Mock(start=0.0, end=2.5, text="Hello, this is"),
            Mock(start=2.5, end=5.0, text="a test transcription.")
        ]
    )
    mock.get_supported_formats.return_value = ["mp3", "wav", "m4a", "flac"]
    return mock


@pytest.fixture
def mock_job_runner():
    """Mock job runner"""
    mock = AsyncMock(spec=JobRunner)
    mock.submit_job.return_value = "job-12345"
    mock.get_job_status.return_value = Mock(
        job_id="job-12345",
        state=Mock(value="completed"),
        started_at=None,
        completed_at=None,
        is_terminal=True,
        metadata={}
    )
    mock.cancel_job.return_value = True
    mock.list_jobs.return_value = []
    return mock


@pytest.fixture  
def mock_notification_provider():
    """Mock notification provider"""
    mock = AsyncMock(spec=NotificationProvider)
    mock.send_notification.return_value = Mock(success=True, message_id="msg-123")
    return mock


@pytest.fixture
def mock_service_factory(
    mock_storage_provider,
    mock_transcription_provider, 
    mock_job_runner,
    mock_notification_provider
):
    """Mock service factory with all providers"""
    factory = Mock(spec=ServiceFactory)
    factory.get_storage_provider.return_value = mock_storage_provider
    factory.get_transcription_provider.return_value = mock_transcription_provider
    factory.get_job_runner.return_value = mock_job_runner
    factory.get_notification_provider.return_value = mock_notification_provider
    
    # Mock settings
    factory.settings = Mock()
    factory.settings.environment = "test"
    factory.settings.job_runner = "local"
    factory.settings.storage_provider = "local"
    factory.settings.transcription_provider = "openai"
    factory.settings.notification_provider = "email"
    
    # Mock validation
    factory.validate_configuration.return_value = {
        "valid": True,
        "provider_status": {
            "storage": {"status": "valid", "name": "local"},
            "transcription": {"status": "valid", "name": "openai"},
            "job_runner": {"status": "valid", "name": "local"},
            "notification": {"status": "valid", "name": "email"}
        }
    }
    
    # Mock available providers
    factory.get_available_providers.return_value = {
        "storage": {
            "available": ["local", "gcs", "dropbox"],
            "enabled": ["local"]
        },
        "transcription": {
            "available": ["openai"], 
            "enabled": ["openai"]
        },
        "job_runner": {
            "available": ["local", "cloud_run"],
            "enabled": ["local"]
        },
        "notification": {
            "available": ["email"],
            "enabled": ["email"]
        }
    }
    
    return factory


@pytest.fixture
def transcription_client():
    """Test client for transcription API"""
    return TestClient(transcription_app)


@pytest.fixture
def webhook_client():
    """Test client for webhook API"""
    return TestClient(webhook_app)


@pytest.fixture
def orchestration_client():
    """Test client for orchestration API"""
    return TestClient(orchestration_app)


@pytest.fixture
def gateway_client():
    """Test client for gateway"""
    return TestClient(gateway_app)


@pytest.fixture
async def async_transcription_client():
    """Async test client for transcription API"""
    async with AsyncClient(app=transcription_app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def async_webhook_client():
    """Async test client for webhook API"""
    async with AsyncClient(app=webhook_app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def async_orchestration_client():
    """Async test client for orchestration API"""
    async with AsyncClient(app=orchestration_app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def async_gateway_client():
    """Async test client for gateway"""
    async with AsyncClient(app=gateway_app, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for session scope"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Sample test data
@pytest.fixture
def sample_job_request():
    """Sample job request data"""
    return {
        "job_type": "transcription",
        "input_data": {
            "file_path": "/files/test-audio.mp3",
            "file_name": "test-audio.mp3"
        },
        "environment": {
            "PROJECT_ID": "test-project",
            "LOG_LEVEL": "DEBUG"
        }
    }


@pytest.fixture
def sample_webhook_payload():
    """Sample webhook payload"""
    return {
        "list_folder": {
            "accounts": ["dbid:test123"],
            "cursor": "cursor123"
        },
        "delta": {
            "users": [1234567]
        }
    }


@pytest.fixture
def sample_batch_request():
    """Sample batch job request"""
    return {
        "jobs": [
            {
                "input_data": {
                    "file_path": "/files/audio1.mp3",
                    "file_name": "audio1.mp3"
                }
            },
            {
                "input_data": {
                    "file_path": "/files/audio2.wav", 
                    "file_name": "audio2.wav"
                }
            }
        ],
        "max_concurrent": 2
    }