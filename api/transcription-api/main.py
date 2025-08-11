"""
Transcription API FastAPI Application
Generated from OpenAPI specification

REST API for transcription services supporting multiple providers and formats.

Features:
- Multiple transcription providers (OpenAI Whisper, etc.)
- Async job processing with status tracking
- File upload and download management
- Batch operations for multiple files

"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .routers import transcription_router, jobs_router, providers_router, health_router
from .config import get_settings
from .dependencies import get_service_factory


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print(f"🚀 Starting {get_settings().service_name}")
    
    # Initialize services
    factory = get_service_factory()
    validation = factory.validate_configuration()
    
    if not validation["valid"]:
        print("❌ Configuration validation failed:")
        for error in validation["errors"]:
            print(f"  - {error}")
        raise RuntimeError("Invalid service configuration")
    
    print("✅ Service initialized successfully")
    
    yield
    
    # Shutdown
    print(f"🛑 Shutting down {get_settings().service_name}")


# Create FastAPI application
app = FastAPI(
    title="Transcription API",
    description="""REST API for transcription services supporting multiple providers and formats.

Features:
- Multiple transcription providers (OpenAI Whisper, etc.)
- Async job processing with status tracking
- File upload and download management
- Batch operations for multiple files""",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, tags=["health"])
app.include_router(transcription_router, prefix="/transcribe", tags=["transcription"])
app.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
app.include_router(providers_router, prefix="/providers", tags=["providers"])

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "code": "INTERNAL_ERROR",
            "timestamp": "{__import__('datetime').datetime.now().isoformat()}"
        }
    )


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
