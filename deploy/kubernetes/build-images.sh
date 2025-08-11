#!/bin/bash

# Build Docker images for Transcripts v2 and push to local registry
set -e

# Configuration
REGISTRY_EXTERNAL="docker-registry.infrastructure.svc.cluster.local:5000"  # Using k8s DNS
REGISTRY_INTERNAL="docker-registry.infrastructure.svc.cluster.local:5000"  # Internal k8s DNS
IMAGE_TAG="local-dev"
PROJECT_ROOT="/Users/michaelzakany/projects/transcripts"

# Service definitions (simple array for bash 3.2 compatibility)
SERVICES="gateway transcription-api orchestration-api webhook-api"

echo "🐳 Building Docker images for Transcripts v2"
echo "External registry: $REGISTRY_EXTERNAL (for pushing)"
echo "Internal registry: $REGISTRY_INTERNAL (for k8s)"
echo "Tag: $IMAGE_TAG"
echo ""

# Check if registry is accessible via NodePort
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
REGISTRY_NODEPORT="$NODE_IP:30500"
echo "📡 Checking registry connection via NodePort..."
if ! curl -s http://$REGISTRY_NODEPORT/v2/ > /dev/null; then
    echo "❌ Registry not accessible at $REGISTRY_NODEPORT"
    echo "   Make sure the registry is deployed and NodePort service is running"
    exit 1
fi
echo "✅ Registry is accessible"
echo ""

# Build and push each service
for service in $SERVICES; do
    dockerfile="deploy/docker/images/api/$service.Dockerfile"
    # Build with NodePort registry name (for pushing from local machine)
    nodeport_image="$REGISTRY_NODEPORT/transcripts/$service:$IMAGE_TAG"
    # Tag with internal k8s DNS registry name (for k8s to pull)  
    internal_image="$REGISTRY_INTERNAL/transcripts/$service:$IMAGE_TAG"
    
    echo "🔨 Building $service..."
    echo "   Dockerfile: $dockerfile"
    echo "   NodePort image: $nodeport_image"
    echo "   Internal image: $internal_image"
    
    if [ ! -f "$PROJECT_ROOT/$dockerfile" ]; then
        echo "❌ Dockerfile not found: $dockerfile"
        continue
    fi
    
    # Build image with both tags
    docker build \
        -f "$PROJECT_ROOT/$dockerfile" \
        -t "$nodeport_image" \
        -t "$internal_image" \
        "$PROJECT_ROOT" \
        || { echo "❌ Failed to build $service"; continue; }
    
    # Push image via NodePort (for local machine access)
    echo "📤 Pushing $service to registry..."
    docker push "$nodeport_image" \
        || { echo "❌ Failed to push $service"; continue; }
    
    echo "✅ $service built and pushed successfully"
    echo ""
done

echo "🎉 All images built and pushed!"
echo ""
echo "📋 Built images:"
for service in $SERVICES; do
    echo "   - $REGISTRY_INTERNAL/transcripts/$service:$IMAGE_TAG (internal k8s DNS)"
done
echo ""
echo "🔍 To verify images in registry:"
echo "   curl -s http://$REGISTRY_NODEPORT/v2/_catalog | jq"
echo ""
echo "Next steps:"
echo "1. Update Kubernetes manifests to use the local registry"
echo "2. Deploy to cluster: ./deploy.sh"