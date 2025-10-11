# CI/CD Pipeline Documentation

This document explains the automated deployment setup for the transcripts project.

## Overview

The project uses **GitHub Actions** for continuous integration and deployment with **Workload Identity Federation** for secure, keyless authentication to Google Cloud.

## Workflows

### 1. `deploy-worker.yml` - Worker Deployment

**Triggers:**
- Push to `main` branch when `worker/` files change
- Manual trigger via Actions UI

**Steps:**
1. Authenticate to GCP using Workload Identity Federation
2. Build Docker image for linux/amd64
3. Push to Google Container Registry with tags:
   - `latest` (always points to newest)
   - `{git-sha}` (specific commit version)
4. Update Cloud Run Job to use new image
5. Verify deployment success

**Build cache:** Uses GitHub Actions cache for faster builds

---

### 2. `deploy-terraform.yml` - Infrastructure Deployment

**Triggers:**
- Push to `main` branch when `terraform/` or `webhook/` files change
- Manual trigger via Actions UI

**Steps:**
1. Authenticate to GCP using Workload Identity Federation
2. Run Terraform format check
3. Initialize Terraform
4. Validate Terraform configuration
5. Generate Terraform plan
6. Apply changes (only on main branch)
7. Display outputs in GitHub Actions summary

**Safety:** Plan is generated before apply to review changes

---

### 3. `pr-checks.yml` - Pull Request Validation

**Triggers:**
- Pull request opened/updated targeting `main`

**Steps:**

**Validate Worker:**
- Set up Python environment
- Install dependencies
- Lint code with ruff
- Check Dockerfile with hadolint

**Validate Terraform:**
- Check Terraform formatting
- Initialize (without backend)
- Validate configuration

**Test Docker Build:**
- Build Docker image (without pushing)
- Use build cache for speed
- Verify image builds successfully

---

## Workload Identity Federation Setup

### Why Workload Identity Federation?

**Traditional approach (❌ Not recommended):**
- Create service account key JSON
- Store in GitHub Secrets
- Keys are long-lived and can be compromised
- Requires manual rotation

**Workload Identity Federation (✅ Recommended):**
- No long-lived credentials
- Short-lived tokens issued on-demand
- Automatic rotation
- Better security posture

### Setup Steps

#### 1. Configure GitHub Repository

Edit `.github/setup-workload-identity.sh`:

```bash
GITHUB_REPO="YOUR_GITHUB_USERNAME/transcripts"  # Update this!
```

Example: `mzakany/transcripts`

#### 2. Run Setup Script

```bash
cd .github
./setup-workload-identity.sh
```

This script will:
- Enable required GCP APIs
- Create service account `github-actions-deploy`
- Grant necessary permissions:
  - `roles/run.admin` - Manage Cloud Run Jobs
  - `roles/storage.admin` - Manage GCS buckets
  - `roles/cloudfunctions.admin` - Deploy Cloud Functions
  - `roles/iam.serviceAccountUser` - Use service accounts
  - `roles/secretmanager.secretAccessor` - Read secrets
- Create Workload Identity Pool
- Create GitHub OIDC provider
- Bind service account to pool

#### 3. Add GitHub Secrets

The script outputs two secrets. Add them to your GitHub repository:

**Navigate to:**
`https://github.com/YOUR_USERNAME/transcripts/settings/secrets/actions`

**Add secrets:**

1. **`WIF_PROVIDER`** - Workload Identity Provider path
   ```
   projects/123456789/locations/global/workloadIdentityPools/github-actions-pool/providers/github-provider
   ```

2. **`WIF_SERVICE_ACCOUNT`** - Service account email
   ```
   github-actions-deploy@jos-transcripts.iam.gserviceaccount.com
   ```

#### 4. Test Deployment

Push a change to `main` branch:

```bash
git checkout main
git pull
# Make a change to worker/main.py
git add .
git commit -m "Test CI/CD pipeline"
git push origin main
```

Check the Actions tab in GitHub to see the workflow running.

---

## Deployment Flow

### Worker Changes (`worker/` directory)

```
Code Change → Push to main → GitHub Actions
                              ↓
                    Build Docker Image (amd64)
                              ↓
                    Push to GCR (latest + SHA)
                              ↓
                    Update Cloud Run Job
                              ↓
                    ✅ Deployed!
```

**Example:** Update `worker/main.py` → Push → Auto-deploy in ~3-5 minutes

---

### Webhook Changes (`webhook/` directory)

```
Code Change → Push to main → GitHub Actions
                              ↓
                         Terraform Apply
                              ↓
                    Zip webhook/ directory
                              ↓
                    Upload to GCS
                              ↓
                    Deploy Cloud Function
                              ↓
                    ✅ Deployed!
```

**Example:** Update `webhook/main.py` → Push → Auto-deploy in ~2-3 minutes

---

### Infrastructure Changes (`terraform/` directory)

```
Config Change → Push to main → GitHub Actions
                                ↓
                          Terraform Plan
                                ↓
                          Terraform Apply
                                ↓
                    Update infrastructure
                                ↓
                          ✅ Deployed!
```

**Example:** Update `terraform/main.tf` → Push → Auto-apply in ~2-4 minutes

---

## Manual Deployment

For local development or troubleshooting:

### Worker Manual Deploy

```bash
cd worker
docker buildx build --platform linux/amd64 \
  -t gcr.io/jos-transcripts/transcription-worker:latest \
  . --push
```

### Terraform Manual Deploy

```bash
cd terraform
terraform plan
terraform apply
```

---

## Monitoring Deployments

### GitHub Actions UI

1. Go to: `https://github.com/YOUR_USERNAME/transcripts/actions`
2. View workflow runs, logs, and status
3. See deployment summaries

### GCP Console

**Worker deployments:**
```bash
gcloud run jobs describe transcription-worker \
  --region us-east1 \
  --project jos-transcripts
```

**Webhook deployments:**
```bash
gcloud functions describe transcription-webhook \
  --region us-east1 \
  --project jos-transcripts
```

---

## Troubleshooting

### "Error: google: could not find default credentials"

**Solution:** Check GitHub Secrets are set correctly:
- `WIF_PROVIDER` - Full path to Workload Identity Provider
- `WIF_SERVICE_ACCOUNT` - Service account email

### "Permission denied" errors

**Solution:** Re-run setup script to ensure all IAM permissions are granted:
```bash
./.github/setup-workload-identity.sh
```

### Docker build fails

**Solution:** Check Dockerfile syntax and dependencies:
```bash
cd worker
docker build --platform linux/amd64 -t test .
```

### Terraform apply fails

**Solution:** Check Terraform state and plan:
```bash
cd terraform
terraform init
terraform plan
```

---

## Security Best Practices

✅ **Do:**
- Use Workload Identity Federation (keyless)
- Keep GitHub Secrets minimal
- Review Terraform plans before applying
- Use branch protection rules

❌ **Don't:**
- Store service account key JSONs in GitHub Secrets
- Commit secrets to repository
- Skip PR checks
- Apply Terraform changes without reviewing plan

---

## Branch Protection (Recommended)

Set up branch protection for `main`:

1. Go to: `Settings > Branches > Add rule`
2. Branch name pattern: `main`
3. Enable:
   - ✅ Require pull request reviews
   - ✅ Require status checks to pass (pr-checks)
   - ✅ Require conversation resolution
   - ✅ Include administrators

This ensures all changes are reviewed and tested before deployment.
