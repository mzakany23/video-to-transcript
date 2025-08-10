# Transcripts v2 - Modular Audio/Video Transcription Pipeline

**Cloud-agnostic, microservices-based transcription system** with pluggable providers and FastAPI REST APIs. Upload files to any storage provider, get transcripts automatically via configurable job runners.

## Architecture Overview

**Fully modular system** with clean API boundaries, allowing easy switching between cloud platforms and storage providers.

### Version 2.0 - **DEVELOPMENT BRANCH**
This is the `v2` development branch focused on:
- **4 FastAPI microservices** with comprehensive testing and documentation
- **AWS-first deployment**: Primary testing and development on AWS infrastructure
- **Pluggable providers**: Easy configuration-based switching between storage/compute providers
- **Modern architecture**: Clean provider abstractions and dependency injection

### Branch Strategy
- **`main`**: Production v1.0 (GCP deployed, no changes)
- **`v2`**: Target branch for v2.0 features
- **`migration-to-modularity`**: Current development branch (merges to v2)
- **Deployment**: v2 testing on AWS, v1 stable on GCP

## Quick Start

### Development Environment
```bash
# Set up everything (uses uv for fast dependency management)
make setup

# Run full test suite with coverage
make test

# Start all microservices locally (production config)
docker-compose -f deploy/docker/compose/production.yml up

# Or development environment with hot reload
docker-compose -f deploy/docker/compose/dev.yml up
```

### Production Deployment
```bash
# Deploy to AWS (v2 primary platform)
export AWS_PROFILE=your-aws-profile
make deploy-aws

# Legacy v1 (GCP - production stable, no changes)
# export PROJECT_ID=your-gcp-project
# make deploy-gcp
```

## Microservices Architecture

The system consists of **4 independent FastAPI microservices**, each containerized and independently deployable:

### 1. **API Gateway** (`api/gateway/`)
- **Purpose**: Single entry point, request routing, load balancing  
- **Routes**: `/transcription/*`, `/orchestration/*`, `/webhook/*`
- **Port**: 8000

### 2. **Transcription API** (`api/transcription-api/`)  
- **Purpose**: Transcription job management and provider switching
- **Routes**: 
  - `POST /transcription/jobs` - Submit transcription jobs
  - `GET /transcription/jobs/{job_id}` - Job status and results  
  - `GET /transcription/providers` - Available transcription providers
- **Port**: 8001

### 3. **Orchestration API** (`api/orchestration-api/`)
- **Purpose**: Job execution across different platforms (Cloud Run, Local, Airflow)
- **Routes**:
  - `POST /jobs` - Submit jobs to any runner
  - `POST /batch` - Batch job processing with concurrency control
  - `GET /jobs/{job_id}` - Job status and logs
  - `GET /runners` - Available job runner providers
- **Port**: 8002  

### 4. **Webhook API** (`api/webhook-api/`)
- **Purpose**: Handle external notifications (Dropbox, S3, etc.) and trigger processing
- **Routes**:
  - `POST /webhooks/dropbox` - Dropbox webhook notifications
  - `GET /admin/stats` - Processing statistics
  - `POST /admin/reset` - Reset processing state (dev only)
- **Port**: 8003

## Core Services (Provider Pattern)

**Pluggable business logic** that powers the APIs. Each service supports multiple implementations:

### Storage Providers (`services/storage/`)
- **`DropboxStorageProvider`**: Original Dropbox integration
- **`GCSStorageProvider`**: Google Cloud Storage  
- **`LocalStorageProvider`**: Local filesystem (development)
- **Interface**: Download, upload, list, delete, batch operations

### Transcription Providers (`services/transcription/`)  
- **`OpenAITranscriptionProvider`**: OpenAI Whisper API
- **Interface**: Transcribe with file validation, format conversion

### Job Runners (`services/orchestration/`)
- **`CloudRunJobRunner`**: Google Cloud Run execution
- **`LocalJobRunner`**: Local process execution  
- **Interface**: Submit, monitor, cancel jobs with resource management

### Webhook Handlers (`services/webhook/`)
- **`DropboxWebhookHandler`**: Dropbox notifications with cursor management
- **Interface**: Process notifications, track changes, prevent duplicate processing

## Key Features

### **Provider Abstraction**
```python
# Switch storage providers via configuration
STORAGE_PROVIDER=dropbox    # Dropbox
STORAGE_PROVIDER=gcs        # Google Cloud Storage  
STORAGE_PROVIDER=local      # Local filesystem

# Switch job execution platforms  
JOB_RUNNER=cloudrun         # Google Cloud Run
JOB_RUNNER=local            # Local execution
```

### **Configuration-Driven**
- **No code changes** needed to swap providers
- **Environment-based** configuration for different environments
- **ServiceFactory** pattern for dependency injection

### **Production Ready**
- **Comprehensive testing** with contract tests ensuring provider compatibility
- **Structured logging** with JSON format for monitoring tools
- **Error handling** with custom exceptions and automatic retries
- **Resource management** with timeouts and concurrency limits

### **Multi-Format Support**
- **Audio**: `.mp3`, `.wav`, `.m4a`, `.aac`, `.ogg`, `.flac`
- **Video**: `.mp4`, `.mov`, `.avi`, `.webm`, `.mpeg` (auto-converted to audio)
- **Large files**: Automatic compression for files >25MB

## Project Structure

```
transcripts/                           # Monorepo with clear separation
├── api/                              # FastAPI Microservices
│   ├── gateway/                     # API Gateway (port 8000)
│   ├── transcription-api/           # Transcription service (port 8001)  
│   ├── orchestration-api/           # Job orchestration (port 8002)
│   ├── webhook-api/                 # Webhook processing (port 8003)
│   └── schemas/                     # OpenAPI specifications
├── services/                         # Core Business Logic
│   ├── core/                        # Interfaces, models, exceptions
│   ├── storage/                     # Multi-provider storage
│   ├── transcription/               # Multi-provider transcription  
│   ├── orchestration/               # Multi-provider job execution
│   ├── webhook/                     # Webhook processing with tracking
│   └── config/                      # Configuration and service factory
├── deploy/                          # Infrastructure & Deployment
│   ├── docker/                      # Docker deployment configuration
│   │   ├── images/                  # Centralized Dockerfile management
│   │   │   ├── Dockerfile           # Multi-stage build (worker/webhook targets)
│   │   │   └── api/                 # API service Dockerfiles
│   │   │       ├── gateway.Dockerfile
│   │   │       ├── transcription-api.Dockerfile
│   │   │       ├── orchestration-api.Dockerfile
│   │   │       └── webhook-api.Dockerfile
│   │   └── compose/                 # Environment-specific compose files
│   │       ├── dev.yml              # Development environment
│   │       └── production.yml       # Production-ready API services
│   └── infrastructure/terraform/    # Multi-cloud infrastructure modules
│       ├── modules/                 # Reusable Terraform modules
│       │   ├── gcp/                 # Google Cloud Platform modules
│       │   │   ├── cloud-functions/ # Cloud Functions module
│       │   │   ├── cloud-run/       # Cloud Run module
│       │   │   ├── secrets/         # Secret Manager module
│       │   │   ├── storage/         # Storage module
│       │   │   └── transcription-pipeline/ # Complete pipeline module
│       │   └── shared/              # Cross-cloud modules
│       │       └── service-account/ # Service account module
│       └── environments/            # Environment-specific configs
│           ├── dev/                 # Development environment
│           │   ├── main.tf         # Clean, intent-focused configuration
│           │   ├── variables.tf    # Variable declarations
│           │   ├── outputs.tf      # Output definitions
│           │   ├── providers.tf    # Provider configuration
│           │   └── moved.tf        # State migration blocks
│           ├── staging/             # Staging environment (future)
│           └── prod/                # Production environment (future)
├── tests/                           # Comprehensive Testing
│   ├── api/                        # API integration tests
│   └── services/                   # Service unit tests  
├── worker/                          # Legacy Worker (backward compatibility)
├── webhook/                         # Legacy Webhook (backward compatibility)  
├── Makefile                         # Build, test, deploy commands
# Note: docker-compose files moved to deploy/docker/compose/
```

## How It Works

### Traditional Workflow (Still Supported)
1. **Upload**: Files → Dropbox `/raw/` folder
2. **Webhook**: Dropbox → Cloud Function → Cloud Run Job  
3. **Processing**: Download → Compress → Transcribe → Upload
4. **Results**: JSON + TXT files in `/processed/` folder

### Modern Microservices Workflow  
1. **Upload**: Files → Any storage provider (Dropbox, GCS, Local)
2. **Webhook**: Webhook API processes notifications
3. **Orchestration**: Orchestration API submits to any job runner
4. **Transcription**: Transcription API processes with any provider
5. **Results**: Structured output to configured storage

## Development

### Local Development (Multi-Service)
```bash
# Start all APIs locally  
docker-compose -f deploy/docker/compose/production.yml up

# Or individual services
cd api/transcription-api && uvicorn main:app --reload --port 8001
cd api/orchestration-api && uvicorn main:app --reload --port 8002
cd api/webhook-api && uvicorn main:app --reload --port 8003
cd api/gateway && uvicorn main:app --reload --port 8000
```

### Testing
```bash
make test                    # Full test suite with coverage
make test-services           # Unit tests for core services  
make test-api               # API integration tests

# Individual test categories
python -m pytest tests/services/ -v          # Service layer
python -m pytest tests/api/ -v               # API layer  
```

### Building & Deployment
```bash
make build                   # Build all Docker containers
make deploy-aws             # Deploy to AWS (v2 primary)
make info                   # Show project status and capabilities
```

## Available Commands

```bash
make help                   # Show all available commands + cloud support matrix
make setup                  # Set up development environment with uv
make test                   # Run full test suite with coverage reporting  
make build                  # Build all Docker containers with multi-stage builds
make deploy-aws            # Deploy to AWS (v2 primary platform)
make clean                 # Clean Docker resources and temporary files
make info                  # Show project status and cloud provider support
```

## Configuration

### Core Environment Variables
```bash
# Provider Selection (no code changes needed to switch)
STORAGE_PROVIDER=dropbox           # dropbox, gcs, local
TRANSCRIPTION_PROVIDER=openai      # openai, local (future)  
JOB_RUNNER=cloudrun               # cloudrun, local, airflow (future)

# Logging & Debug
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json                   # json (prod), text (dev)
SERVICE_NAME=transcription-api    # For structured logging

# Service Selection
USE_NEW_SERVICES=true            # Use microservices APIs (false = legacy worker)
```

### Provider-Specific Configuration

**Dropbox Storage**:
```bash
DROPBOX_ACCESS_TOKEN=your_token
DROPBOX_APP_SECRET=your_secret  
DROPBOX_RAW_FOLDER=/transcripts/raw
DROPBOX_PROCESSED_FOLDER=/transcripts/processed
```

**Google Cloud Storage**:
```bash
PROJECT_ID=your-gcp-project
GCS_BUCKET=your-bucket-name  
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

**OpenAI Transcription**:
```bash
OPENAI_API_KEY=your_openai_key
```

## API Documentation

### OpenAPI Specifications
- **Transcription API**: `http://localhost:8001/docs`
- **Orchestration API**: `http://localhost:8002/docs`  
- **Webhook API**: `http://localhost:8003/docs`
- **Gateway**: `http://localhost:8000/docs`

### Example API Usage

**Submit Transcription Job**:
```bash
curl -X POST "http://localhost:8001/transcription/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/audio.mp3",
    "options": {
      "language": "en",
      "response_format": "json"  
    }
  }'
```

**Check Job Status**:
```bash
curl "http://localhost:8002/jobs/{job_id}"
```

**Process Webhook**:
```bash
curl -X POST "http://localhost:8003/webhooks/dropbox" \
  -H "Content-Type: application/json" \
  -d '{"delta": {"users": [...]}}'
```

## Deployment Options

### Docker Compose (Local Development)
```bash
# All services locally with development config
docker-compose -f deploy/docker/compose/dev.yml up

# Production-ready local deployment
docker-compose -f deploy/docker/compose/production.yml up

# Scale specific services
docker-compose -f deploy/docker/compose/production.yml up --scale transcription-api=3
```

### Cloud Deployment (Production)

**AWS** (v2 Primary Platform):
```bash  
# Deploy v2 infrastructure to AWS
export AWS_PROFILE=your-aws-profile
make deploy-aws
# Creates: ECS services, Lambda functions, Parameter Store, S3 buckets
```

**Google Cloud Platform** (v1 Legacy - Stable):
```bash
# v1 production deployment (no changes)
export PROJECT_ID=your-gcp-project
make deploy-gcp
# Maintains: Cloud Run services, Cloud Functions, Secret Manager
```

**Note**: v2 development focuses on AWS infrastructure while v1 remains stable on GCP.

### Deployment Structure

The new **hybrid deployment structure** (Option 3) provides:

#### Benefits
- **Clear Domain Separation**: Docker for containerization, infrastructure for cloud resources
- **Module Reusability**: Terraform modules abstract cloud-specific implementations
- **Environment Isolation**: Each environment has its own configuration while sharing modules
- **Scalability**: Easy to add new cloud providers or deployment methods
- **Multi-Environment Ready**: Supports dev, staging, and production with consistent patterns

#### Directory Organization
```
deploy/
├── docker/
│   ├── compose/                    # Environment-specific compose files
│   │   └── dev.yml                # Local development
│   └── images/                     # Shared Docker images (future)
└── infrastructure/                 # Cloud infrastructure
    └── terraform/
        ├── modules/               # Reusable modules
        │   ├── gcp/              # Google Cloud Platform
        │   │   ├── cloud-run/    # Cloud Run jobs
        │   │   ├── cloud-functions/ # Cloud Functions
        │   │   ├── secrets/      # Secret Manager
        │   │   └── storage/      # Storage buckets
        │   └── shared/           # Cross-cloud modules
        │       └── service-account/ # IAM service accounts
        └── environments/         # Environment configs
            ├── dev/              # Development
            │   ├── main.tf      # Infrastructure definition
            │   ├── variables.tf # Variable declarations
            │   ├── moved.tf     # State migration blocks
            │   └── terraform.tfvars # Environment values
            ├── staging/          # Staging (future)
            └── prod/            # Production (future)
```

#### Implementation Notes
- Terraform organized into reusable modules for better maintainability
- Environment-specific configurations isolated while sharing common modules
- Terraform state managed per environment for isolation and safety
- Docker compose configurations organized by deployment type

## Monitoring & Troubleshooting

### Health Checks
```bash
# Check all service health
curl http://localhost:8000/health     # Gateway
curl http://localhost:8001/health     # Transcription API
curl http://localhost:8002/health     # Orchestration API  
curl http://localhost:8003/health     # Webhook API
```

### Logs & Metrics
```bash  
# View logs (structured JSON in production)
docker-compose -f deploy/docker/compose/production.yml logs transcription-api

# In production (GCP)  
gcloud logging read "resource.type=cloud_run_service" --limit=50

# Get processing statistics
curl http://localhost:8003/admin/stats
```

### Common Issues

**"Provider not configured"**: Check environment variables for selected provider
**"Service unavailable"**: Ensure all dependent services are running  
**"Authentication failed"**: Verify API keys and service account credentials

## Key Features & Capabilities

### **Architecture Benefits**
- **Modularity**: Services importable into other projects
- **Flexibility**: Easy provider swapping via configuration  
- **Scalability**: Independent microservices with container orchestration
- **Maintainability**: Clean separation of concerns with comprehensive testing
- **Cloud Agnostic**: Multi-cloud deployment ready

## For Future Sessions

**Context Setup**: Point future Claude conversations to this README for instant project understanding.

**Quick Architecture Summary**:
- **4 FastAPI microservices** (gateway, transcription, orchestration, webhook)  
- **Provider pattern** for storage, transcription, job execution
- **Configuration-driven** provider switching (no code changes)
- **Comprehensive testing** with contract tests for provider compatibility
- **Multi-cloud ready** with Terraform infrastructure modules

**Current Capabilities**:
- Production-ready microservices architecture
- Backward compatibility maintained 
- Multi-cloud infrastructure prepared
- Comprehensive test coverage (80%+)
- API documentation and examples

This system demonstrates enterprise-grade modularity and cloud portability while maintaining simplicity for development and deployment.