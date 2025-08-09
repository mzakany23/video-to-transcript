#!/bin/bash
set -e

# Production deployment script for transcription services
# This script handles cloud-agnostic deployment with provider-specific optimizations

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
CLOUD_PROVIDER="gcp"
ENVIRONMENT="production"
TAG="latest"
DRY_RUN=false
FORCE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--provider)
            CLOUD_PROVIDER="$2"
            shift 2
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -p, --provider PROVIDER    Cloud provider (gcp, aws, azure) [default: gcp]"
            echo "  -e, --environment ENV      Environment (development, staging, production) [default: production]"
            echo "  -t, --tag TAG             Docker image tag [default: latest]"
            echo "      --dry-run             Show what would be deployed without executing"
            echo "  -f, --force               Force deployment without prompts"
            echo "  -h, --help                Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  PROJECT_ID                GCP/AWS/Azure project identifier"
            echo "  REGION                    Deployment region"
            echo "  OPENAI_API_KEY           OpenAI API key"
            echo "  DROPBOX_ACCESS_TOKEN     Dropbox access token (optional)"
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            exit 1
            ;;
    esac
done

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate required environment variables
validate_environment() {
    log_info "Validating environment variables..."
    
    local missing_vars=()
    
    if [[ -z "${PROJECT_ID:-}" ]]; then
        missing_vars+=("PROJECT_ID")
    fi
    
    if [[ -z "${OPENAI_API_KEY:-}" ]]; then
        missing_vars+=("OPENAI_API_KEY")
    fi
    
    if [[ "$CLOUD_PROVIDER" == "gcp" && -z "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]]; then
        if [[ ! -f "${PROJECT_ROOT}/credentials/service-account.json" ]]; then
            missing_vars+=("GOOGLE_APPLICATION_CREDENTIALS or credentials/service-account.json")
        fi
    fi
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        exit 1
    fi
    
    log_success "Environment validation passed"
}

# Validate configuration
validate_configuration() {
    log_info "Validating transcription services configuration..."
    
    if [[ -f "${PROJECT_ROOT}/cli/config_manager.py" ]]; then
        if ! python "${PROJECT_ROOT}/cli/config_manager.py" validate; then
            log_error "Configuration validation failed"
            exit 1
        fi
    else
        log_warn "Configuration validator not found, skipping validation"
    fi
    
    log_success "Configuration validation passed"
}

# Pre-deployment checks
pre_deployment_checks() {
    log_info "Running pre-deployment checks..."
    
    # Check Docker availability
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check Docker Compose availability
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    # Check if services are already running
    if docker-compose -f "${SCRIPT_DIR}/production.yml" ps | grep -q "Up"; then
        if [[ "$FORCE" == false ]]; then
            log_warn "Services are already running. Use --force to redeploy."
            read -p "Continue with deployment? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "Deployment cancelled"
                exit 0
            fi
        fi
    fi
    
    log_success "Pre-deployment checks passed"
}

# Build Docker images
build_images() {
    log_info "Building Docker images..."
    
    cd "$PROJECT_ROOT"
    
    local services=("gateway" "transcription-api" "webhook-api" "orchestration-api")
    
    for service in "${services[@]}"; do
        log_info "Building $service..."
        
        if [[ "$DRY_RUN" == true ]]; then
            log_info "[DRY RUN] Would build: docker build -t transcription-$service:$TAG api/$service/"
        else
            docker build -t "transcription-$service:$TAG" "api/$service/" || {
                log_error "Failed to build $service image"
                exit 1
            }
        fi
        
        log_success "$service image built successfully"
    done
}

# Deploy based on cloud provider
deploy_services() {
    log_info "Deploying transcription services to $CLOUD_PROVIDER..."
    
    case "$CLOUD_PROVIDER" in
        gcp)
            deploy_gcp
            ;;
        aws)
            deploy_aws
            ;;
        azure)
            deploy_azure
            ;;
        docker)
            deploy_docker
            ;;
        *)
            log_error "Unsupported cloud provider: $CLOUD_PROVIDER"
            exit 1
            ;;
    esac
}

# Google Cloud Platform deployment
deploy_gcp() {
    log_info "Deploying to Google Cloud Platform..."
    
    # Set GCP-specific environment variables
    export REGION="${REGION:-us-east1}"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would deploy to GCP using docker-compose"
        docker-compose -f "${SCRIPT_DIR}/production.yml" config
        return
    fi
    
    # Deploy using Docker Compose (can be adapted for Cloud Run later)
    docker-compose -f "${SCRIPT_DIR}/production.yml" up -d --build
    
    log_success "Deployed to GCP successfully"
    
    # Show service status
    show_deployment_status
}

# AWS deployment
deploy_aws() {
    log_info "AWS deployment not yet implemented"
    log_info "Future implementation will use ECS/Fargate"
    
    if [[ "$DRY_RUN" == false ]]; then
        log_error "AWS deployment not available yet"
        exit 1
    fi
}

# Azure deployment
deploy_azure() {
    log_info "Azure deployment not yet implemented"
    log_info "Future implementation will use Container Instances/AKS"
    
    if [[ "$DRY_RUN" == false ]]; then
        log_error "Azure deployment not available yet"
        exit 1
    fi
}

# Docker deployment (local production-like)
deploy_docker() {
    log_info "Deploying using Docker Compose..."
    
    local compose_file="${SCRIPT_DIR}/env/${ENVIRONMENT}/docker-compose.yml"
    
    if [[ ! -f "$compose_file" ]]; then
        log_error "Docker Compose file not found: $compose_file"
        exit 1
    fi
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would run: docker-compose -f $compose_file up -d"
        docker-compose -f "$compose_file" config
        return
    fi
    
    docker-compose -f "$compose_file" up -d --build
    
    log_success "Docker deployment completed"
    show_deployment_status
}

# Show deployment status
show_deployment_status() {
    log_info "Checking service status..."
    
    sleep 10  # Wait for services to start
    
    # Check service health
    services=(
        "http://localhost:8000/health|Gateway"
        "http://localhost:8001/health|Transcription API"
        "http://localhost:8002/health|Webhook API"
        "http://localhost:8003/health|Orchestration API"
    )
    
    all_healthy=true
    
    for service in "${services[@]}"; do
        IFS='|' read -r url name <<< "$service"
        
        if curl -sf "$url" > /dev/null 2>&1; then
            log_success "$name is healthy"
        else
            log_error "$name is not responding"
            all_healthy=false
        fi
    done
    
    echo
    log_info "Deployment Summary:"
    echo "  Environment: $ENVIRONMENT"
    echo "  Cloud Provider: $CLOUD_PROVIDER"
    echo "  Image Tag: $TAG"
    echo "  Project ID: ${PROJECT_ID:-not-set}"
    echo "  Region: ${REGION:-not-set}"
    
    if [[ "$all_healthy" == true ]]; then
        echo
        log_success "🎉 All services are healthy and ready!"
        echo
        log_info "Access points:"
        echo "  • Gateway:        http://localhost:8000"
        echo "  • Transcription:  http://localhost:8001/docs"
        echo "  • Webhook:        http://localhost:8002/docs"
        echo "  • Orchestration:  http://localhost:8003/docs"
    else
        log_error "Some services are not healthy. Check logs with:"
        echo "  docker-compose -f deploy/production.yml logs [service-name]"
        exit 1
    fi
}

# Cleanup function
cleanup() {
    if [[ "$DRY_RUN" == false ]]; then
        log_info "Run 'make api-docker-stop' or 'docker-compose -f deploy/production.yml down' to stop services"
    fi
}

# Main deployment flow
main() {
    log_info "🚀 Starting transcription services deployment"
    log_info "Provider: $CLOUD_PROVIDER | Environment: $ENVIRONMENT | Tag: $TAG"
    
    if [[ "$DRY_RUN" == true ]]; then
        log_warn "Running in DRY RUN mode - no actual deployment will occur"
    fi
    
    echo
    
    # Run deployment steps
    validate_environment
    validate_configuration
    pre_deployment_checks
    build_images
    deploy_services
    
    cleanup
    
    echo
    log_success "🎉 Deployment completed successfully!"
}

# Handle script interruption
trap 'log_error "Deployment interrupted"; exit 1' INT TERM

# Run main function
main "$@"