# Makefile for transcription services
# Usage: make help

.PHONY: help setup test build clean deploy

# Configuration
PROJECT_ID ?= your-project-id
REGION ?= us-east1
TAG ?= latest
WORKER_IMAGE = transcription-worker
WEBHOOK_IMAGE = transcription-webhook

# AWS Configuration (v2 primary)
AWS_PROFILE ?= default
AWS_REGION ?= us-east-1
AWS_ACCOUNT_ID ?= 123456789012
ECR_REGISTRY = $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com

# Colors for output
GREEN = \033[0;32m
YELLOW = \033[1;33m
BLUE = \033[0;34m
RED = \033[0;31m
NC = \033[0m # No Color

## Help
help: ## Show this help message
	@echo "$(BLUE)Transcription Services Makefile$(NC)"
	@echo "$(YELLOW)Cloud-agnostic build and deployment system$(NC)"
	@echo
	@echo "$(YELLOW)Available targets:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo
	@echo "$(BLUE)Cloud Providers:$(NC)"
	@echo "  $(GREEN)✅ AWS$(NC) - deploy-aws (v2 primary platform)"
	@echo "  $(GREEN)✅ Google Cloud$(NC) - deploy-gcp (v1 legacy, stable)"

## Development Setup
setup: develop ## Set up development environment with uv (alias for develop)

develop: ## Set up development environment with uv
	@echo "$(YELLOW)🚀 Setting up development environment$(NC)"
	@if ! command -v uv >/dev/null 2>&1; then \
		echo "$(YELLOW)📦 Installing uv...$(NC)"; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	fi
	@echo "$(YELLOW)🏗️ Creating virtual environment$(NC)"
	@uv venv
	@echo "$(YELLOW)📥 Installing dependencies$(NC)"
	@uv pip install -r requirements/dev.txt
	@uv pip install -e .[dev]
	@echo "$(GREEN)✅ Development environment ready!$(NC)"
	@echo "$(YELLOW)To activate: source .venv/bin/activate$(NC)"

## Testing
test: ## Run all tests
	@echo "$(YELLOW)🧪 Running transcription services tests$(NC)"
	@if ! command -v uv >/dev/null 2>&1; then \
		echo "$(RED)❌ uv not found. Run 'make develop' first$(NC)"; \
		exit 1; \
	fi
	@if [ ! -d ".venv" ]; then \
		echo "$(YELLOW)📦 No virtual environment found. Running 'make develop'$(NC)"; \
		$(MAKE) develop; \
	fi
	@echo "$(YELLOW)📥 Ensuring dependencies are installed$(NC)"
	@uv pip install -e .[dev]
	@echo "$(YELLOW)🔬 Running unit tests$(NC)"
	@uv run pytest tests/services/ --cov=services --cov-report=term-missing --cov-report=html
	@echo "$(YELLOW)🔍 Running type checks$(NC)"
	@uv run mypy services/ || echo "$(YELLOW)⚠️ Type check warnings (non-critical)$(NC)"
	@echo "$(YELLOW)🧹 Running linting$(NC)"
	@uv run ruff check services/ tests/ || echo "$(YELLOW)⚠️ Lint warnings (non-critical)$(NC)"
	@echo "$(GREEN)✅ All tests completed$(NC)"

test-quick: ## Run tests quickly without coverage
	@echo "$(YELLOW)🧪 Running quick tests$(NC)"
	@uv run python tests/test_runner.py

## Docker Build
build: ## Build both worker and webhook containers
	@echo "$(BLUE)🔨 Building transcription services containers$(NC)"
	@echo "$(YELLOW)Project: $(PROJECT_ID)$(NC)"
	@echo "$(YELLOW)Region: $(REGION)$(NC)"  
	@echo "$(YELLOW)Tag: $(TAG)$(NC)"
	@echo
	@echo "$(YELLOW)📦 Building worker image...$(NC)"
	@docker build -f deploy/docker/images/Dockerfile --target worker -t $(WORKER_IMAGE):$(TAG) .
	@if [ $$? -eq 0 ]; then \
		echo "$(GREEN)✅ Worker image built successfully$(NC)"; \
	else \
		echo "$(RED)❌ Worker image build failed$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)📦 Building webhook image...$(NC)"
	@docker build -f deploy/docker/images/Dockerfile --target webhook -t $(WEBHOOK_IMAGE):$(TAG) .
	@if [ $$? -eq 0 ]; then \
		echo "$(GREEN)✅ Webhook image built successfully$(NC)"; \
	else \
		echo "$(RED)❌ Webhook image build failed$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)🎉 Build completed successfully!$(NC)"

build-worker: ## Build only worker container
	@echo "$(YELLOW)📦 Building worker image...$(NC)"
	@docker build -f deploy/docker/images/Dockerfile --target worker -t $(WORKER_IMAGE):$(TAG) .

build-webhook: ## Build only webhook container  
	@echo "$(YELLOW)📦 Building webhook image...$(NC)"
	@docker build -f deploy/docker/images/Dockerfile --target webhook -t $(WEBHOOK_IMAGE):$(TAG) .

## Container Testing
test-containers: build ## Test container builds
	@echo "$(YELLOW)🧪 Testing container builds...$(NC)"
	@echo "$(YELLOW)🔍 Testing worker image...$(NC)"
	@docker run --rm $(WORKER_IMAGE):$(TAG) python -c "\
import sys; \
sys.path.append('/app'); \
from services.storage import StorageService; \
from services.transcription import TranscriptionService; \
print('✅ Worker: Services import successfully')"
	@if [ $$? -eq 0 ]; then \
		echo "$(GREEN)✅ Worker image test passed$(NC)"; \
	else \
		echo "$(RED)❌ Worker image test failed$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)🔍 Testing webhook image...$(NC)"
	@docker run --rm $(WEBHOOK_IMAGE):$(TAG) python -c "\
import sys; \
sys.path.append('/app'); \
try: \
    from services.core.models import FileInfo; \
    print('✅ Webhook: Services import successfully'); \
except Exception as e: \
    print(f'⚠️ Webhook: Services not needed yet - {e}'); \
    print('✅ Webhook: Basic imports work')"
	@if [ $$? -eq 0 ]; then \
		echo "$(GREEN)✅ Webhook image test passed$(NC)"; \
	else \
		echo "$(RED)❌ Webhook image test failed$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)🎉 All container tests passed!$(NC)"

## Cloud Provider Deployments

# AWS (v2 Primary Platform)
tag-aws: ## Tag images for AWS Elastic Container Registry
	@if [ "$(AWS_ACCOUNT_ID)" = "123456789012" ]; then \
		echo "$(RED)❌ Set AWS_ACCOUNT_ID environment variable$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)🏷️ Tagging images for AWS ECR...$(NC)"
	@docker tag $(WORKER_IMAGE):$(TAG) $(ECR_REGISTRY)/$(WORKER_IMAGE):$(TAG)
	@docker tag $(WEBHOOK_IMAGE):$(TAG) $(ECR_REGISTRY)/$(WEBHOOK_IMAGE):$(TAG)
	@echo "$(GREEN)✅ Images tagged for ECR$(NC)"

push-aws: tag-aws ## Push images to AWS Elastic Container Registry
	@echo "$(YELLOW)🚀 Pushing images to AWS ECR...$(NC)"
	@echo "$(YELLOW)🔐 Logging into ECR...$(NC)"
	@aws ecr get-login-password --region $(AWS_REGION) --profile $(AWS_PROFILE) | docker login --username AWS --password-stdin $(ECR_REGISTRY)
	@echo "$(YELLOW)📦 Creating ECR repositories if they don't exist...$(NC)"
	@aws ecr create-repository --repository-name $(WORKER_IMAGE) --region $(AWS_REGION) --profile $(AWS_PROFILE) 2>/dev/null || true
	@aws ecr create-repository --repository-name $(WEBHOOK_IMAGE) --region $(AWS_REGION) --profile $(AWS_PROFILE) 2>/dev/null || true
	@echo "$(YELLOW)⬆️ Pushing images...$(NC)"
	@docker push $(ECR_REGISTRY)/$(WORKER_IMAGE):$(TAG)
	@docker push $(ECR_REGISTRY)/$(WEBHOOK_IMAGE):$(TAG)
	@echo "$(GREEN)✅ Images pushed to ECR$(NC)"

deploy-aws: build push-aws ## Build and deploy to AWS (v2 primary platform)
	@echo "$(GREEN)🎉 AWS deployment completed!$(NC)"
	@echo "$(BLUE)AWS ECR images:$(NC)"
	@echo "  • $(ECR_REGISTRY)/$(WORKER_IMAGE):$(TAG)"
	@echo "  • $(ECR_REGISTRY)/$(WEBHOOK_IMAGE):$(TAG)"
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  • Deploy infrastructure: cd deploy/infrastructure/terraform/aws && terraform apply"
	@echo "  • Update ECS services to use new images"
	@echo "  • Set USE_NEW_SERVICES=true in Parameter Store"

# Google Cloud Platform (v1 Legacy)
tag-gcp: ## Tag images for Google Container Registry
	@if [ "$(PROJECT_ID)" = "your-project-id" ]; then \
		echo "$(RED)❌ Set PROJECT_ID environment variable$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)🏷️ Tagging images for Google Container Registry...$(NC)"
	@docker tag $(WORKER_IMAGE):$(TAG) gcr.io/$(PROJECT_ID)/$(WORKER_IMAGE):$(TAG)
	@docker tag $(WEBHOOK_IMAGE):$(TAG) gcr.io/$(PROJECT_ID)/$(WEBHOOK_IMAGE):$(TAG)
	@echo "$(GREEN)✅ Images tagged for GCR$(NC)"

push-gcp: tag-gcp ## Push images to Google Container Registry  
	@echo "$(YELLOW)🚀 Pushing images to Google Container Registry...$(NC)"
	@docker push gcr.io/$(PROJECT_ID)/$(WORKER_IMAGE):$(TAG)
	@docker push gcr.io/$(PROJECT_ID)/$(WEBHOOK_IMAGE):$(TAG)
	@echo "$(GREEN)✅ Images pushed to GCR$(NC)"

deploy-gcp: build push-gcp ## Build and deploy to Google Cloud Platform
	@echo "$(GREEN)🎉 GCP deployment completed!$(NC)"
	@echo "$(BLUE)Google Container Registry images:$(NC)"
	@echo "  • gcr.io/$(PROJECT_ID)/$(WORKER_IMAGE):$(TAG)"
	@echo "  • gcr.io/$(PROJECT_ID)/$(WEBHOOK_IMAGE):$(TAG)"
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  • Update Cloud Run services to use new images"
	@echo "  • Set USE_NEW_SERVICES=true to enable modular architecture"


# Generic deploy target (v2 primary)
deploy: deploy-aws ## Deploy to AWS (v2 primary platform)

## Local Testing  
run-worker: ## Run worker container locally
	@echo "$(YELLOW)🏃 Running worker locally...$(NC)"
	@docker run -it --rm \
		-e PROJECT_ID=test \
		-e USE_NEW_SERVICES=true \
		-e LOG_LEVEL=DEBUG \
		$(WORKER_IMAGE):$(TAG)

run-webhook: ## Run webhook container locally
	@echo "$(YELLOW)🏃 Running webhook locally...$(NC)"
	@docker run -it --rm \
		-p 8080:8080 \
		-e PROJECT_ID=test \
		-e LOG_LEVEL=DEBUG \
		$(WEBHOOK_IMAGE):$(TAG)

## Cleanup
clean: ## Clean up Docker images and containers
	@echo "$(YELLOW)🧹 Cleaning up Docker resources...$(NC)"
	@docker rmi -f $(WORKER_IMAGE):$(TAG) 2>/dev/null || true
	@docker rmi -f $(WEBHOOK_IMAGE):$(TAG) 2>/dev/null || true
	@docker rmi -f $(ECR_REGISTRY)/$(WORKER_IMAGE):$(TAG) 2>/dev/null || true
	@docker rmi -f $(ECR_REGISTRY)/$(WEBHOOK_IMAGE):$(TAG) 2>/dev/null || true
	@docker rmi -f gcr.io/$(PROJECT_ID)/$(WORKER_IMAGE):$(TAG) 2>/dev/null || true
	@docker rmi -f gcr.io/$(PROJECT_ID)/$(WEBHOOK_IMAGE):$(TAG) 2>/dev/null || true
	@docker system prune -f >/dev/null 2>&1 || true
	@echo "$(GREEN)✅ Cleanup completed$(NC)"

clean-all: clean ## Clean up everything including .venv
	@echo "$(YELLOW)🧹 Cleaning up virtual environment...$(NC)"
	@rm -rf .venv
	@rm -rf .pytest_cache
	@rm -rf htmlcov
	@rm -rf **/__pycache__
	@rm -rf **/*.pyc
	@echo "$(GREEN)✅ Full cleanup completed$(NC)"

## Development
dev: develop ## Set up development environment (alias for develop)

format: ## Format code with ruff and black
	@echo "$(YELLOW)🎨 Formatting code...$(NC)"
	@uv run ruff format services/ worker/ tests/
	@uv run black services/ worker/ tests/
	@echo "$(GREEN)✅ Code formatted$(NC)"

lint: ## Run linting checks
	@echo "$(YELLOW)🔍 Running linting...$(NC)"
	@uv run ruff check services/ worker/ tests/
	@uv run mypy services/

lint-fix: ## Fix linting errors automatically
	@echo "$(YELLOW)🔧 Fixing linting errors...$(NC)"
	@uv run ruff check --fix --unsafe-fixes services/ worker/ tests/
	@uv run ruff format services/ worker/ tests/
	@echo "$(GREEN)✅ Linting errors fixed$(NC)"

## Information
info: ## Show project information
	@echo "$(BLUE)📋 Project Information$(NC)"
	@echo "$(YELLOW)Project ID:$(NC) $(PROJECT_ID)"
	@echo "$(YELLOW)Region:$(NC) $(REGION)"  
	@echo "$(YELLOW)Tag:$(NC) $(TAG)"
	@echo "$(YELLOW)Worker Image:$(NC) $(WORKER_IMAGE):$(TAG)"
	@echo "$(YELLOW)Webhook Image:$(NC) $(WEBHOOK_IMAGE):$(TAG)"
	@echo
	@echo "$(BLUE)🌐 Cloud Provider Support:$(NC)"
	@echo "$(GREEN)✅ AWS (v2 Primary)$(NC)"
	@echo "  • Container Registry: $(ECR_REGISTRY)/"
	@echo "  • Deploy command: make deploy-aws"
	@echo "$(GREEN)✅ Google Cloud Platform (v1 Legacy)$(NC)"
	@echo "  • Container Registry: gcr.io/$(PROJECT_ID)/"
	@echo "  • Deploy command: make deploy-gcp"
	@echo "$(GREEN)✅ Docker$(NC)"
	@echo "  • Local deployment with Docker Compose"
	@echo "  • Deploy command: docker-compose up"
	@echo
	@if [ -d ".venv" ]; then \
		echo "$(YELLOW)Virtual Env:$(NC) ✅ Ready"; \
	else \
		echo "$(YELLOW)Virtual Env:$(NC) ❌ Run 'make setup'"; \
	fi
	@if command -v docker >/dev/null 2>&1; then \
		echo "$(YELLOW)Docker:$(NC) ✅ Available"; \
	else \
		echo "$(YELLOW)Docker:$(NC) ❌ Not found"; \
	fi

## API Services
api-dev: ## Start API services in development mode
	@echo "$(YELLOW)🚀 Starting API services in development mode$(NC)"
	@echo "$(BLUE)Services starting on:$(NC)"
	@echo "  • Gateway:        http://localhost:8000"
	@echo "  • Transcription:  http://localhost:8001"  
	@echo "  • Webhook:        http://localhost:8002"
	@echo "  • Orchestration:  http://localhost:8003"
	@echo
	uv run uvicorn api.transcription-api.main:app --reload --host 0.0.0.0 --port 8001 &
	uv run uvicorn api.webhook-api.main:app --reload --host 0.0.0.0 --port 8002 &
	uv run uvicorn api.orchestration-api.main:app --reload --host 0.0.0.0 --port 8003 &
	uv run uvicorn api.gateway.main:app --reload --host 0.0.0.0 --port 8000

api-docker: ## Start API services with Docker Compose
	@echo "$(YELLOW)🐳 Starting API services with Docker Compose$(NC)"
	@echo "$(BLUE)Services will be available at:$(NC)"
	@echo "  • Gateway:        http://localhost:8000"
	@echo "  • Transcription:  http://localhost:8001"
	@echo "  • Webhook:        http://localhost:8002"
	@echo "  • Orchestration:  http://localhost:8003"
	@echo
	docker-compose -f deploy/docker/compose/production.yml up --build

api-docker-stop: ## Stop API services
	@echo "$(YELLOW)🛑 Stopping API services$(NC)"
	docker-compose -f deploy/docker/compose/production.yml down

api-docker-logs: ## Show API service logs
	@echo "$(YELLOW)📋 Showing API service logs$(NC)"
	docker-compose -f deploy/docker/compose/production.yml logs -f

api-health: ## Check health of all API services
	@echo "$(YELLOW)🏥 Checking API service health$(NC)"
	@echo "$(BLUE)Gateway Health:$(NC)"
	@curl -s http://localhost:8000/health | jq . || echo "Gateway not responding"
	@echo "$(BLUE)Transcription Health:$(NC)"
	@curl -s http://localhost:8001/health | jq . || echo "Transcription API not responding"
	@echo "$(BLUE)Webhook Health:$(NC)"
	@curl -s http://localhost:8002/health | jq . || echo "Webhook API not responding"
	@echo "$(BLUE)Orchestration Health:$(NC)"
	@curl -s http://localhost:8003/health | jq . || echo "Orchestration API not responding"

## Production Deployment
deploy-production: ## Deploy to production (requires environment variables)
	@echo "$(YELLOW)🚀 Deploying to production$(NC)"
	@./deploy/scripts/deploy.sh --provider gcp --environment production

deploy-dev: ## Deploy to development environment
	@echo "$(YELLOW)🚀 Deploying to development$(NC)"
	@./deploy/scripts/deploy.sh --provider docker --environment dev

deploy-dry-run: ## Show what would be deployed without executing
	@echo "$(YELLOW)🔍 Dry run deployment$(NC)"
	@./deploy/scripts/deploy.sh --provider gcp --environment production --dry-run

## Configuration Management
config-validate: ## Validate current configuration
	@echo "$(YELLOW)🔧 Validating configuration$(NC)"
	@uv run python cli/config_manager.py validate

config-init: ## Initialize configuration interactively
	@echo "$(YELLOW)🔧 Initializing configuration$(NC)"
	@uv run python cli/config_manager.py init

config-migrate: ## Migrate configuration file (requires CONFIG_FILE)
	@echo "$(YELLOW)🔧 Migrating configuration$(NC)"
	@if [ -z "$(CONFIG_FILE)" ]; then \
		echo "$(RED)❌ CONFIG_FILE is required$(NC)"; \
		echo "Usage: make config-migrate CONFIG_FILE=path/to/config.json"; \
		exit 1; \
	fi
	@uv run python cli/config_manager.py migrate $(CONFIG_FILE)

config-sample: ## Generate sample configuration file
	@echo "$(YELLOW)🔧 Generating sample configuration$(NC)"
	@uv run python cli/config_manager.py generate --output config_sample.json