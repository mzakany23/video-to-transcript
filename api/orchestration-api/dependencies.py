"""
Dependency injection for Orchestration API
"""

import sys
from pathlib import Path
from functools import lru_cache

# Add project root to path for services import
sys.path.append(str(Path(__file__).parent.parent.parent))

from services import ServiceFactory, Settings


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
        job_runner=api_settings.default_job_runner,
        storage_provider=api_settings.default_storage_provider,
        environment="development" if api_settings.debug else "production",
        log_level=api_settings.log_level
    )
    
    return ServiceFactory(service_settings)


@lru_cache()
def get_orchestration_service():
    """Get orchestration service instance"""
    factory = get_service_factory()
    return factory.create_orchestration_service()