# Deployment Directory

This directory contains all deployment configurations and scripts for the transcription services platform.

## Structure

```
deploy/
├── README.md                    # This file
├── scripts/                     # Deployment scripts
│   └── deploy.sh               # Main deployment script
├── env/                        # Environment-specific configurations
│   ├── production/             # Production environment
│   │   ├── docker-compose.yml  # Production Docker Compose config
│   │   └── .env.template       # Production environment variables template
│   └── dev/                   # Development environment
│       └── docker-compose.yml # Development Docker Compose config
├── templates/                 # Configuration templates
├── configs/                   # Additional configuration files
└── k8s/                      # Kubernetes manifests (future)
```

## Quick Start

### Development Deployment

```bash
# Start development services
make api-dev

# Or using Docker Compose directly
docker-compose -f deploy/env/dev/docker-compose.yml up
```

### Development Deployment with Docker

```bash
# Deploy to development environment
make deploy-dev

# Or using the deployment script
./deploy/scripts/deploy.sh --provider docker --environment dev
```

### Production Deployment

```bash
# Set up environment variables
cp deploy/env/production/.env.template .env
# Edit .env with your actual values

# Deploy to production
make deploy-production

# Or using the deployment script with specific provider
./deploy/scripts/deploy.sh --provider gcp --environment production
```

## Environment Configurations

### Development
- Local storage providers
- Local job runners
- Debug logging enabled
- Source code mounted for hot reload
- Exposed ports for direct access
- No authentication required

### Production
- Cloud providers (GCS, Cloud Run)
- High availability setup
- Resource limits and health checks
- Security configurations
- Monitoring and alerting

## Deployment Scripts

### Main Deployment Script (`scripts/deploy.sh`)

```bash
./deploy/scripts/deploy.sh [OPTIONS]

Options:
  -p, --provider PROVIDER    Cloud provider (gcp, docker) [default: gcp]
  -e, --environment ENV      Environment (dev, production) [default: production]
  -t, --tag TAG             Docker image tag [default: latest]
      --dry-run             Show what would be deployed
  -f, --force               Force deployment without prompts
  -h, --help                Show help message

Note: Currently only GCP and Docker are implemented. AWS and Azure support planned for future releases.
```

### Examples

```bash
# Dry run production deployment
./deploy/scripts/deploy.sh --provider gcp --environment production --dry-run

# Deploy to development with specific tag
./deploy/scripts/deploy.sh --provider docker --environment dev --tag v1.2.3

# Force production deployment
./deploy/scripts/deploy.sh --provider gcp --environment production --force
```

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `PROJECT_ID` | Cloud project identifier | `my-transcription-project` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `REGION` | Deployment region | `us-east1` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DROPBOX_ACCESS_TOKEN` | Dropbox API token | - |
| `AUTH_METHOD` | Authentication method | `none` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `GCS_BUCKET` | Google Cloud Storage bucket | - |

## Security Considerations

### Production Environment

1. **Environment Variables**: Never commit `.env` files with real secrets
2. **API Keys**: Use environment-specific API keys
3. **Authentication**: Enable authentication in production (`AUTH_METHOD=api_key`)
4. **CORS**: Restrict CORS origins to your domains
5. **HTTPS**: Use HTTPS in production (configure load balancer/reverse proxy)

### Network Security

- Services communicate over internal Docker network
- Only gateway exposes external ports in production
- Rate limiting configured on APIs
- Health checks use internal endpoints

## Monitoring and Observability

### Health Checks

All services include health check endpoints:
- Gateway: `http://localhost:8000/health`
- Transcription: `http://localhost:8001/health`
- Webhook: `http://localhost:8002/health`
- Orchestration: `http://localhost:8003/health`

### Logging

- Development: DEBUG level, console output
- Staging: INFO level, structured logging
- Production: INFO level, structured JSON logging

### Metrics (Future)

Integration points for:
- Prometheus metrics
- Datadog APM
- Sentry error tracking
- Custom business metrics

## Scaling

### Horizontal Scaling

Production Docker Compose includes:
- Multiple replicas for each service
- Load balancing between replicas
- Resource limits and reservations

### Vertical Scaling

Adjust resource limits in Docker Compose:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '1.0'
      memory: 1G
```

## Troubleshooting

### Common Issues

1. **Services not starting**
   ```bash
   # Check logs
   docker-compose -f deploy/env/production/docker-compose.yml logs [service-name]
   
   # Check service health
   make api-health
   ```

2. **Environment variable issues**
   ```bash
   # Validate configuration
   make config-validate
   
   # Check what variables are loaded
   docker-compose -f deploy/env/production/docker-compose.yml config
   ```

3. **Network connectivity**
   ```bash
   # Test internal service communication
   docker exec -it gateway-container curl http://transcription-api:8001/health
   ```

### Debug Commands

```bash
# Show effective Docker Compose configuration
docker-compose -f deploy/env/production/docker-compose.yml config

# Check resource usage
docker stats

# View service logs
docker-compose -f deploy/env/production/docker-compose.yml logs -f [service]

# Execute shell in container
docker-compose -f deploy/env/production/docker-compose.yml exec [service] sh
```

## Future Enhancements

### Planned Features

- [ ] Kubernetes manifests
- [ ] Terraform infrastructure as code
- [ ] CI/CD pipeline integration
- [ ] Blue/green deployments
- [ ] Auto-scaling policies
- [ ] Multi-region deployments

### Cloud Provider Support

- **GCP**: ✅ Implemented - Cloud Run, Cloud Build, Cloud Storage
- **Docker**: ✅ Implemented - Local deployment with Docker Compose
- **AWS**: 🚧 Planned - ECS/Fargate, ECR, S3
- **Azure**: 🚧 Planned - Container Instances, ACR, Blob Storage

## Support

For deployment issues:

1. Check the troubleshooting section above
2. Validate configuration: `make config-validate`
3. Run dry deployment: `./deploy/scripts/deploy.sh --dry-run`
4. Check service logs and health endpoints
5. Review environment variables and Docker Compose configuration