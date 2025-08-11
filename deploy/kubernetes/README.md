# Transcripts v2 Kubernetes Deployment

This directory contains Kubernetes manifests for deploying the Transcripts v2 modular architecture.

## Architecture Overview

The deployment includes:

### Infrastructure Components
- **ArgoCD** - GitOps continuous deployment and application management
- **Argo Workflows** - CI/CD pipeline execution and job orchestration  
- **MinIO** - S3-compatible object storage for blob storage
- **PostgreSQL** - Database for OLTP (Online Transaction Processing)
- **Flux** - GitOps toolkit for continuous delivery
- **NGINX Ingress** - Load balancing and ingress management

### API Services (Endpoints Namespace)
- **Gateway API** - Main API gateway and request routing
- **Transcription API** - Audio/video transcription processing
- **Orchestration API** - Job management and workflow coordination
- **Webhook API** - Webhook handling and event processing

## Directory Structure

```
deploy/kubernetes/
├── base/                           # Base Kubernetes manifests
│   ├── infrastructure/            # Infrastructure components
│   │   ├── argocd/                # ArgoCD deployment
│   │   ├── argo-workflows/        # Argo Workflows 
│   │   ├── minio/                 # MinIO object storage
│   │   ├── postgresql/            # PostgreSQL database
│   │   └── flux/                  # Flux GitOps
│   ├── ingress/                   # Ingress configurations
│   ├── services/                  # API service manifests
│   │   ├── gateway/               # Gateway API
│   │   ├── transcription-api/     # Transcription API
│   │   ├── orchestration-api/     # Orchestration API
│   │   └── webhook-api/           # Webhook API
│   └── namespaces.yaml           # Namespace definitions
├── environments/                  # Environment-specific overlays
│   └── local/                    # Local development environment
│       ├── patches/              # Environment-specific patches
│       └── kustomization.yaml    # Local environment config
├── deploy.sh                     # Deployment script
└── README.md                     # This file
```

## Prerequisites

1. **Kubernetes cluster** - Make sure `intel-k8s` context is active:
   ```bash
   kubectl config use-context intel-k8s
   ```

2. **kustomize** - Install kustomize for manifest management:
   ```bash
   curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash
   ```

3. **kubectl** - Kubernetes command-line tool must be configured

## Quick Deployment

**Important**: You need Docker images before deploying. Follow these steps:

### Step 1: Deploy Infrastructure (including local Docker registry)
```bash
cd deploy/kubernetes
kubectl apply -k base/infrastructure
```

### Step 2: Wait for registry and set up access
```bash
# Wait for registry to be ready
kubectl wait --for=condition=Ready pods -l app.kubernetes.io/name=docker-registry -n infrastructure --timeout=300s

# Set up port forward to registry (keep this running in a separate terminal)
kubectl port-forward -n infrastructure svc/docker-registry 30500:5000
```

### Step 3: Build and push images
```bash
# In another terminal, build the images
./build-images.sh
```

### Step 4: Deploy services
```bash
# Deploy the complete environment
kubectl apply -k environments/local
```

### Alternative: Automated deployment
```bash
./deploy.sh
```

## Manual Deployment

If you prefer manual control:

```bash
# Build and preview manifests
kustomize build environments/local

# Deploy to cluster
kustomize build environments/local | kubectl apply -f -

# Check deployment status
kubectl get pods --all-namespaces
```

## Access Information

### Web Interfaces

| Service | NodePort | Port Forward Command | Credentials |
|---------|----------|---------------------|-------------|
| ArgoCD UI | http://localhost:30080 | `kubectl port-forward -n argocd svc/argocd-server 8080:80` | admin / [get password](#argocd-password) |
| Argo Workflows | http://localhost:30746 | `kubectl port-forward -n argo-workflows svc/argo-server 2746:2746` | None (auth disabled) |
| MinIO Console | http://localhost:30900 | `kubectl port-forward -n infrastructure svc/minio 9001:9001` | admin / minio123 |
| Gateway API | http://localhost:30800 | `kubectl port-forward -n endpoints svc/gateway 8000:8000` | None |

### ArgoCD Password

Get the initial ArgoCD admin password:
```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
```

## Namespaces

- **endpoints** - API services (Gateway, Transcription, Orchestration, Webhook APIs)
- **infrastructure** - Core infrastructure (MinIO, PostgreSQL)  
- **argocd** - ArgoCD components
- **argo-workflows** - Argo Workflows components
- **flux-system** - Flux GitOps components
- **ingress-nginx** - NGINX ingress controller
- **apps** - Future frontend applications

## Configuration

### Environment Variables

Key configuration is managed through ConfigMaps and Secrets in each service. See the individual service directories for specific configuration options.

### Storage

- **MinIO** provides S3-compatible object storage on `minio.infrastructure.svc.cluster.local:9000`
- **PostgreSQL** provides relational database on `postgresql.infrastructure.svc.cluster.local:5432`
- **Docker Registry** provides container image storage on `docker-registry.infrastructure.svc.cluster.local:5000` (internal) / `localhost:30500` (external)
- **Local storage** is configured for development with PersistentVolumes

### Job Execution

Jobs are executed using Argo Workflows, with the workflow controller running in the `argo-workflows` namespace. Job templates are defined in the Argo Workflows configuration.

## Monitoring and Debugging

### Check Pod Status
```bash
# All namespaces
kubectl get pods --all-namespaces

# Specific namespace
kubectl get pods -n endpoints
kubectl get pods -n infrastructure
```

### View Logs
```bash
# Service logs
kubectl logs -n endpoints deployment/gateway
kubectl logs -n endpoints deployment/transcription-api

# Infrastructure logs  
kubectl logs -n infrastructure deployment/minio
kubectl logs -n infrastructure deployment/postgresql
```

### Debug Services
```bash
# Check service endpoints
kubectl get svc --all-namespaces

# Check ingress
kubectl get ingress --all-namespaces

# Describe resources for details
kubectl describe pod -n endpoints <pod-name>
```

## Development Workflow

1. **Local Development**: Use the `environments/local` overlay for development
2. **CI/CD**: Argo Workflows handles build/test/deploy pipelines
3. **GitOps**: Flux monitors the repository for changes and auto-deploys
4. **Job Execution**: Use Argo Workflows for transcription job orchestration

## Scaling

To scale services:
```bash
# Scale API services
kubectl scale deployment gateway -n endpoints --replicas=3
kubectl scale deployment transcription-api -n endpoints --replicas=5

# Scale infrastructure (if needed)
kubectl scale deployment minio -n infrastructure --replicas=2
```

## Cleanup

To remove the entire deployment:
```bash
kustomize build environments/local | kubectl delete -f -
```

## Troubleshooting

### Common Issues

1. **Pods stuck in Pending**: Check node resources and storage availability
2. **ImagePullBackOff**: Ensure container images are built and available
3. **Service connection issues**: Check service names and namespace references
4. **Storage issues**: Verify PersistentVolume and PersistentVolumeClaim configuration

### Get Help

```bash
# Check cluster events
kubectl get events --sort-by=.metadata.creationTimestamp

# Check resource usage
kubectl top pods --all-namespaces
kubectl top nodes
```