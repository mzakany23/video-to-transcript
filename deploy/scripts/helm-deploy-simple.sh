#!/bin/bash

# Simple Helm-based deployment script for Transcripts v2 core infrastructure
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CLUSTER_CONTEXT="intel-k8s"

echo "🚀 Deploying Transcripts v2 Core Infrastructure"

# Verify cluster context
CURRENT_CONTEXT=$(kubectl config current-context)
if [ "$CURRENT_CONTEXT" != "$CLUSTER_CONTEXT" ]; then
    echo "❌ Wrong cluster context. Expected: $CLUSTER_CONTEXT, Got: $CURRENT_CONTEXT"
    exit 1
fi

# Create namespaces
echo "📦 Creating namespaces..."
kubectl create namespace infrastructure --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace endpoints --dry-run=client -o yaml | kubectl apply -f -

# Add Helm repositories
echo "📚 Adding Helm repositories..."
helm repo add bitnami https://charts.bitnami.com/bitnami || true
helm repo add minio https://charts.min.io/ || true
helm repo add argo https://argoproj.github.io/argo-helm || true
helm repo update

echo "🗄️ Deploying PostgreSQL..."
helm upgrade --install postgresql bitnami/postgresql \
  --namespace infrastructure \
  --values "$PROJECT_ROOT/deploy/helm/postgresql/values.yaml" \
  --wait --timeout=300s || {
    echo "❌ PostgreSQL deployment failed, but continuing..."
  }

echo "💾 Deploying MinIO..."
helm upgrade --install minio minio/minio \
  --namespace infrastructure \
  --values "$PROJECT_ROOT/deploy/helm/minio/values.yaml" \
  --wait --timeout=300s || {
    echo "❌ MinIO deployment failed, but continuing..."
  }

# Create Docker registry (simple deployment, not Helm)
echo "🐳 Deploying Docker Registry..."
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: docker-registry
  namespace: infrastructure
  labels:
    app: docker-registry
spec:
  replicas: 1
  selector:
    matchLabels:
      app: docker-registry
  template:
    metadata:
      labels:
        app: docker-registry
    spec:
      containers:
      - name: registry
        image: registry:2.8.3
        ports:
        - containerPort: 5000
        volumeMounts:
        - name: storage
          mountPath: /var/lib/registry
        env:
        - name: REGISTRY_STORAGE_FILESYSTEM_ROOTDIRECTORY
          value: /var/lib/registry
        resources:
          limits:
            memory: 256Mi
            cpu: 200m
          requests:
            memory: 128Mi
            cpu: 100m
      volumes:
      - name: storage
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: docker-registry
  namespace: infrastructure
  labels:
    app: docker-registry
spec:
  type: ClusterIP
  ports:
  - port: 5000
    targetPort: 5000
    name: registry
  selector:
    app: docker-registry
---
apiVersion: v1
kind: Service
metadata:
  name: docker-registry-nodeport
  namespace: infrastructure
  labels:
    app: docker-registry
spec:
  type: NodePort
  ports:
  - port: 5000
    targetPort: 5000
    nodePort: 30500
    name: registry
  selector:
    app: docker-registry
EOF

# Wait for core infrastructure
echo "⏳ Waiting for core infrastructure..."
kubectl wait --for=condition=Ready pods -n infrastructure -l app=docker-registry --timeout=180s || echo "⚠️ Registry still starting"

# Check PostgreSQL and MinIO status
echo "📊 Infrastructure Status:"
kubectl get pods -n infrastructure

# Create ArgoCD and Argo Workflows namespaces
echo "📦 Creating ArgoCD and Argo Workflows namespaces..."
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace argo-workflows --dry-run=client -o yaml | kubectl apply -f -

echo "📊 Deploying ArgoCD (simple version)..."
helm upgrade --install argocd argo/argo-cd \
  --namespace argocd \
  --set server.service.type=NodePort \
  --set server.service.nodePortHttp=30080 \
  --set configs.params."server.insecure"=true \
  --set controller.resources.limits.cpu=500m \
  --set controller.resources.limits.memory=512Mi \
  --set controller.resources.requests.cpu=250m \
  --set controller.resources.requests.memory=256Mi \
  --wait --timeout=300s || {
    echo "❌ ArgoCD deployment failed, continuing without it..."
  }

echo "⚡ Deploying Argo Workflows (simple version)..."
helm upgrade --install argo-workflows argo/argo-workflows \
  --namespace argo-workflows \
  --set server.service.type=NodePort \
  --set server.service.nodePort=30746 \
  --set server.secure=false \
  --set controller.workflowNamespaces[0]=argo-workflows \
  --set controller.workflowNamespaces[1]=endpoints \
  --wait --timeout=300s || {
    echo "❌ Argo Workflows deployment failed, continuing without it..."
  }

echo ""
echo "✅ Core Infrastructure Deployment Complete! 🎉"
echo ""
echo "🌐 Access Information:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Docker Registry:"
echo "  Internal: docker-registry.infrastructure.svc.cluster.local:5000"
echo "  External: localhost:30500"
echo ""
echo "PostgreSQL:"
echo "  Host: postgresql.infrastructure.svc.cluster.local:5432"
echo "  Database: transcripts_db"
echo "  Username: transcripts / Password: transcripts123"
echo ""
echo "MinIO:"
echo "  Internal: minio.infrastructure.svc.cluster.local:9000"
echo "  Console: http://localhost:30900"
echo "  Username: admin / Password: minio123"
echo ""

# Try to get ArgoCD password if it exists
if kubectl get secret argocd-initial-admin-secret -n argocd >/dev/null 2>&1; then
    ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d 2>/dev/null || echo "password-not-ready")
    echo "ArgoCD:"
    echo "  URL: http://localhost:30080"
    echo "  Username: admin"
    echo "  Password: $ARGOCD_PASSWORD"
    echo ""
fi

if kubectl get pods -n argo-workflows >/dev/null 2>&1; then
    echo "Argo Workflows:"
    echo "  URL: http://localhost:30746"
    echo ""
fi

echo "🔧 Next Steps:"
echo "  1. Start port forwards: $PROJECT_ROOT/deploy/scripts/port-forwards.sh start registry"
echo "  2. Build images: $PROJECT_ROOT/deploy/kubernetes/build-images.sh"
echo "  3. Deploy services: kubectl apply -k $PROJECT_ROOT/deploy/kubernetes/environments/local"
echo ""