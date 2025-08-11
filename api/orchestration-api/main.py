"""
Orchestration API FastAPI Application
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .routers import jobs_router, batch_router, runners_router, health_router
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
        print("⚠️ Configuration validation failed (some providers may be unavailable)")
        for error in validation["errors"]:
            print(f"  - {error}")
    else:
        print("✅ Orchestration API initialized successfully")
    
    yield
    
    # Shutdown
    print(f"🛑 Shutting down {get_settings().service_name}")


# Create FastAPI application
app = FastAPI(
    title="Orchestration API",
    description="""REST API for job orchestration and management across different execution environments.

Features:
- Multi-provider job execution (Cloud Run, local, Airflow, etc.)
- Job lifecycle management (submit, monitor, cancel)
- Batch job operations with concurrency control
- Real-time job status and progress tracking
- Job logs and result retrieval
- Provider management and switching""",
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
app.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
app.include_router(batch_router, prefix="/batch", tags=["batch"])
app.include_router(runners_router, prefix="/runners", tags=["runners"])


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    import traceback
    print(f"❌ Unhandled exception: {str(exc)}")
    print(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "code": "INTERNAL_ERROR",
            "timestamp": f"{__import__('datetime').datetime.now().isoformat()}"
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