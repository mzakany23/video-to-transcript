#!/bin/bash

# Transcripts v2 Kubernetes Deployment Script
# Deploys the v2 architecture to the intel-k8s cluster

set -e

CLUSTER_CONTEXT="intel-k8s"
NAMESPACE_ENDPOINTS="endpoints"
NAMESPACE_INFRASTRUCTURE="infrastructure"

echo "🚀 Deploying Transcripts v2 to Kubernetes cluster: $CLUSTER_CONTEXT"

# Check prerequisites
echo "🔍 Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

# Verify cluster context
echo "📋 Verifying cluster context..."
CURRENT_CONTEXT=$(kubectl config current-context)
if [ "$CURRENT_CONTEXT" != "$CLUSTER_CONTEXT" ]; then
    echo "❌ Wrong cluster context. Expected: $CLUSTER_CONTEXT, Got: $CURRENT_CONTEXT"
    echo "   Run: kubectl config use-context $CLUSTER_CONTEXT"
    exit 1
fi

echo "✅ Using correct cluster context: $CURRENT_CONTEXT"

# Check if kustomize is available
if ! command -v kustomize &> /dev/null; then
    echo "❌ kustomize not found. Please install it first."
    echo "   Run: curl -s \"https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh\" | bash"
    exit 1
fi

# Deploy infrastructure first (including registry)
echo "🔧 Deploying infrastructure..."
kustomize build ../../base/infrastructure | kubectl apply -f -

# Wait for registry to be ready
echo "⏳ Waiting for Docker registry to be ready..."
kubectl wait --for=condition=Ready pods -l app.kubernetes.io/name=docker-registry -n $NAMESPACE_INFRASTRUCTURE --timeout=300s

# Set up port forward for registry (in background)
echo "🔗 Setting up registry port forward..."
kubectl port-forward -n infrastructure svc/docker-registry 30500:5000 &
REGISTRY_PID=$!
sleep 5  # Give port forward time to establish

# Build and push images
echo "🐳 Building and pushing Docker images..."
./build-images.sh

# Kill the port forward
kill $REGISTRY_PID 2>/dev/null || true

# Deploy the complete local environment
echo "🔧 Deploying complete local environment..."
kustomize build environments/local | kubectl apply -f -

# Wait for infrastructure to be ready
echo "⏳ Waiting for infrastructure to be ready..."
kubectl wait --for=condition=Ready pods -l app.kubernetes.io/name=postgresql -n $NAMESPACE_INFRASTRUCTURE --timeout=300s || echo "⚠️ PostgreSQL might still be starting"
kubectl wait --for=condition=Ready pods -l app.kubernetes.io/name=minio -n $NAMESPACE_INFRASTRUCTURE --timeout=300s || echo "⚠️ MinIO might still be starting"

# Check ArgoCD status
echo "📊 Checking ArgoCD status..."
kubectl get pods -n argocd

# Check Argo Workflows status
echo "📊 Checking Argo Workflows status..."
kubectl get pods -n argo-workflows

# Check API services status
echo "📊 Checking API services status..."
kubectl get pods -n $NAMESPACE_ENDPOINTS

# Display access information
echo ""
echo "🌐 Access Information:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "ArgoCD UI:"
echo "  - NodePort: http://localhost:30080"
echo "  - Port Forward: kubectl port-forward -n argocd svc/argocd-server 8080:80"
echo "  - Default login: admin / (get password with: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d)"
echo ""
echo "Argo Workflows UI:"
echo "  - NodePort: http://localhost:30746"  
echo "  - Port Forward: kubectl port-forward -n argo-workflows svc/argo-server 2746:2746"
echo ""
echo "MinIO Console:"
echo "  - NodePort: http://localhost:30900"
echo "  - Port Forward: kubectl port-forward -n infrastructure svc/minio 9001:9001"
echo "  - Login: admin / minio123"
echo ""
echo "Gateway API:"
echo "  - NodePort: http://localhost:30800"
echo "  - Port Forward: kubectl port-forward -n endpoints svc/gateway 8000:8000"
echo ""
echo "🔍 Useful commands:"
echo "  - Check all pods: kubectl get pods --all-namespaces"
echo "  - Check services: kubectl get svc --all-namespaces"
echo "  - Check ingresses: kubectl get ingress --all-namespaces"
echo "  - Logs: kubectl logs -n <namespace> <pod-name>"
echo ""
echo "✅ Deployment complete! 🎉"