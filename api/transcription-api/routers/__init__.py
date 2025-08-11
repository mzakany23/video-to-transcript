"""
Routers for Transcription API
"""

from .health import router as health_router
from .transcription import router as transcription_router
from .jobs import router as jobs_router
from .providers import router as providers_router

__all__ = [
    "health_router",
    "transcription_router",
    "jobs_router",
    "providers_router",
]