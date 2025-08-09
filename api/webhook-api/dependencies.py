"""
Dependency injection for Webhook API
"""

import sys
from pathlib import Path
from functools import lru_cache

# Add project root to path for services import
sys.path.append(str(Path(__file__).parent.parent.parent))

from services import ServiceFactory, Settings
from services.webhook import WebhookService, CursorManager, JobTracker


@lru_cache()
def get_settings():
    """Get API settings"""
    from .config import get_settings
    return get_settings()


@lru_cache()
def get_service_factory() -> ServiceFactory:
    """Get service factory instance"""
    api_settings = get_settings()
    
    service_settings = Settings(
        storage_provider=api_settings.default_storage_provider,
        job_runner=api_settings.default_job_runner,
        environment="development" if api_settings.debug else "production",
        log_level=api_settings.log_level
    )
    
    return ServiceFactory(service_settings)


@lru_cache()
def get_webhook_service() -> WebhookService:
    """Get webhook service instance"""
    factory = get_service_factory()
    api_settings = get_settings()
    
    # Create required services
    storage_service = factory.create_storage_service()
    orchestration_service = factory.create_orchestration_service()
    
    # Create cursor manager and job tracker
    cursor_manager = CursorManager(
        storage_provider=storage_service.provider,
        cursor_file_path="webhook/cursors.json"
    )
    
    job_tracker = JobTracker(
        storage_provider=storage_service.provider,
        tracking_file_path="webhook/processed_jobs.json"
    )
    
    # Create webhook service
    return WebhookService(
        orchestration_service=orchestration_service,
        cursor_manager=cursor_manager,
        job_tracker=job_tracker,
        supported_formats=api_settings.supported_formats
    )


def get_cursor_manager():
    """Get cursor manager instance"""
    webhook_service = get_webhook_service()
    return webhook_service.cursor_manager


def get_job_tracker():
    """Get job tracker instance"""
    webhook_service = get_webhook_service()
    return webhook_service.job_tracker