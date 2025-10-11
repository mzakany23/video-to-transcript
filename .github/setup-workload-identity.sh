#!/bin/bash
#
# Setup script for GitHub Actions Workload Identity Federation with GCP
# This allows GitHub Actions to authenticate to GCP without storing long-lived service account keys
#
# Usage: ./setup-workload-identity.sh
#

set -e

PROJECT_ID="jos-transcripts"
REGION="us-east1"
GITHUB_REPO="mzakany23/video-to-transcript"
SERVICE_ACCOUNT_NAME="github-actions-deploy"
WORKLOAD_IDENTITY_POOL="github-actions-pool"
WORKLOAD_IDENTITY_PROVIDER="github-provider"

echo "🔧 Setting up Workload Identity Federation for GitHub Actions"
echo "Project: $PROJECT_ID"
echo "GitHub Repo: $GITHUB_REPO"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install it first."
    exit 1
fi

# Set project
echo "📍 Setting GCP project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔌 Enabling required APIs..."
gcloud services enable \
    iamcredentials.googleapis.com \
    cloudresourcemanager.googleapis.com \
    sts.googleapis.com

# Create service account for GitHub Actions
echo "👤 Creating service account..."
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
    --display-name="GitHub Actions Deployment" \
    --description="Service account for GitHub Actions CI/CD" \
    || echo "Service account already exists"

SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant necessary permissions
echo "🔐 Granting permissions to service account..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/cloudfunctions.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"

# Create Workload Identity Pool
echo "🏊 Creating Workload Identity Pool..."
gcloud iam workload-identity-pools create $WORKLOAD_IDENTITY_POOL \
    --location="global" \
    --display-name="GitHub Actions Pool" \
    || echo "Pool already exists"

# Create Workload Identity Provider for GitHub
echo "🔗 Creating Workload Identity Provider..."
gcloud iam workload-identity-pools providers create-oidc $WORKLOAD_IDENTITY_PROVIDER \
    --location="global" \
    --workload-identity-pool=$WORKLOAD_IDENTITY_POOL \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
    --attribute-condition="assertion.repository=='${GITHUB_REPO}'" \
    || echo "Provider already exists"

# Allow GitHub Actions to impersonate the service account
echo "🎭 Binding service account to Workload Identity..."
gcloud iam service-accounts add-iam-policy-binding $SERVICE_ACCOUNT_EMAIL \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/projects/$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')/locations/global/workloadIdentityPools/${WORKLOAD_IDENTITY_POOL}/attribute.repository/${GITHUB_REPO}"

# Get the Workload Identity Provider resource name
WORKLOAD_IDENTITY_PROVIDER_PATH="projects/$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')/locations/global/workloadIdentityPools/${WORKLOAD_IDENTITY_POOL}/providers/${WORKLOAD_IDENTITY_PROVIDER}"

echo ""
echo "✅ Workload Identity Federation setup complete!"
echo ""
echo "📝 Add these secrets to your GitHub repository:"
echo "   Settings > Secrets and variables > Actions > New repository secret"
echo ""
echo "WIF_PROVIDER:"
echo "$WORKLOAD_IDENTITY_PROVIDER_PATH"
echo ""
echo "WIF_SERVICE_ACCOUNT:"
echo "$SERVICE_ACCOUNT_EMAIL"
echo ""
echo "🔗 GitHub Secrets URL:"
echo "   https://github.com/${GITHUB_REPO}/settings/secrets/actions"
