#!/bin/bash

# Helm-based deployment script for Transcripts v2
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CLUSTER_CONTEXT="intel-k8s"

echo "🚀 Deploying Transcripts v2 using Helm charts"

# Verify cluster context
echo "📋 Verifying cluster context..."
CURRENT_CONTEXT=$(kubectl config current-context)
if [ "$CURRENT_CONTEXT" != "$CLUSTER_CONTEXT" ]; then
    echo "❌ Wrong cluster context. Expected: $CLUSTER_CONTEXT, Got: $CURRENT_CONTEXT"
    echo "   Run: kubectl config use-context $CLUSTER_CONTEXT"
    exit 1
fi

echo "✅ Using correct cluster context: $CURRENT_CONTEXT"

# Check if Helm is available
if ! command -v helm &> /dev/null; then
    echo "❌ Helm not found. Please install Helm first."
    echo "   Run: curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash"
    exit 1
fi

# Create namespaces
echo "📦 Creating namespaces..."
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace argo-workflows --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace infrastructure --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace endpoints --dry-run=client -o yaml | kubectl apply -f -

# Add Helm repositories
echo "📚 Adding Helm repositories..."
helm repo add argo https://argoproj.github.io/argo-helm
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add minio https://charts.min.io/
helm repo update

echo "🗄️ Deploying PostgreSQL..."
helm upgrade --install postgresql bitnami/postgresql \
  --namespace infrastructure \
  --values "$PROJECT_ROOT/deploy/helm/postgresql/values.yaml" \
  --wait --timeout=300s

echo "💾 Deploying MinIO..."
helm upgrade --install minio minio/minio \
  --namespace infrastructure \
  --values "$PROJECT_ROOT/deploy/helm/minio/values.yaml" \
  --wait --timeout=300s

echo "📊 Deploying ArgoCD..."
helm upgrade --install argocd argo/argo-cd \
  --namespace argocd \
  --values "$PROJECT_ROOT/deploy/helm/argocd/values.yaml" \
  --wait --timeout=300s

echo "⚡ Deploying Argo Workflows..."
helm upgrade --install argo-workflows argo/argo-workflows \
  --namespace argo-workflows \
  --values "$PROJECT_ROOT/deploy/helm/argo-workflows/values.yaml" \
  --wait --timeout=300s

# Create Docker registry (simple deployment)
echo "🐳 Deploying Docker Registry..."
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: docker-registry
  namespace: infrastructure
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
      volumes:
      - name: storage
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: docker-registry
  namespace: infrastructure
spec:
  type: ClusterIP
  ports:
  - port: 5000
    targetPort: 5000
  selector:
    app: docker-registry
---
apiVersion: v1
kind: Service
metadata:
  name: docker-registry-nodeport
  namespace: infrastructure
spec:
  type: NodePort
  ports:
  - port: 5000
    targetPort: 5000
    nodePort: 30500
  selector:
    app: docker-registry
EOF

# Create secrets for Argo Workflows artifact repository
echo "🔐 Creating MinIO secret for Argo Workflows..."
kubectl create secret generic argo-artifacts-secret \
  --namespace argo-workflows \
  --from-literal=accesskey=admin \
  --from-literal=secretkey=minio123 \
  --dry-run=client -o yaml | kubectl apply -f -

# Wait for all pods to be ready
echo "⏳ Waiting for all deployments to be ready..."
kubectl wait --for=condition=Ready pods -n infrastructure -l app=docker-registry --timeout=300s
kubectl wait --for=condition=Ready pods -n argocd -l app.kubernetes.io/name=argocd-server --timeout=300s
kubectl wait --for=condition=Ready pods -n argo-workflows -l app.kubernetes.io/name=argo-workflows-server --timeout=300s

# Get ArgoCD admin password
echo "🔑 Getting ArgoCD admin password..."
ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)

echo ""
echo "✅ Deployment complete! 🎉"
echo ""
echo "🌐 Access Information:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "ArgoCD UI:"
echo "  URL: http://localhost:30080"
echo "  Username: admin"
echo "  Password: $ARGOCD_PASSWORD"
echo ""
echo "Argo Workflows UI:"
echo "  URL: http://localhost:30746"
echo ""
echo "MinIO Console:"
echo "  URL: http://localhost:30900"
echo "  Username: admin"
echo "  Password: minio123"
echo ""
echo "Docker Registry:"
echo "  Internal: docker-registry.infrastructure.svc.cluster.local:5000"
echo "  External: localhost:30500"
echo ""
echo "PostgreSQL:"
echo "  Host: postgresql.infrastructure.svc.cluster.local"
echo "  Port: 5432"
echo "  Database: transcripts_db"
echo "  Username: transcripts"
echo "  Password: transcripts123"
echo ""
echo "🔧 Next Steps:"
echo "  1. Start port forwards: $PROJECT_ROOT/deploy/scripts/port-forwards.sh start"
echo "  2. Build images: $PROJECT_ROOT/deploy/kubernetes/build-images.sh"
echo "  3. Deploy services: kubectl apply -k $PROJECT_ROOT/deploy/kubernetes/environments/local"
echo ""