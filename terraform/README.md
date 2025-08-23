# Terraform Setup for Dropbox Transcription Service

This directory contains Terraform configuration to automatically set up Google Cloud Platform resources for an automated audio transcription pipeline that monitors Dropbox folders and sends email notifications.

**Note**: This is not a fully automated deployment. You'll need to:
1. Build and push the Docker container for the worker before running Terraform
2. Provide all API keys and tokens in terraform.tfvars

## Prerequisites

1. **Install Terraform**:
   ```bash
   # macOS
   brew install terraform

   # Or download from: https://terraform.io/downloads
   ```

2. **Install Google Cloud CLI** (needed for authentication and Docker push):
   ```bash
   # macOS
   brew install google-cloud-sdk

   # Authenticate
   gcloud auth login
   gcloud auth application-default login
   ```

3. **Install Docker** (needed to build worker container):
   ```bash
   # macOS
   brew install docker
   # Or download Docker Desktop from: https://www.docker.com/products/docker-desktop
   ```

4. **Set up GCP Project**:
   ```bash
   # Create project (if needed)
   gcloud projects create YOUR-PROJECT-ID

   # Set project
   gcloud config set project YOUR-PROJECT-ID

   # Enable billing (required for API usage)
   # Go to: https://console.cloud.google.com/billing
   ```

## Setup

1. **Build and push the worker container** (must be done before Terraform):
   ```bash
   # Configure Docker for GCR
   gcloud auth configure-docker
   
   # Build and push the container
   docker buildx build --platform linux/amd64 \
     -t gcr.io/YOUR-PROJECT-ID/transcription-worker:latest \
     ../worker/ --push
   ```

2. **Configure variables**:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your project details
   ```

3. **Initialize Terraform**:
   ```bash
   terraform init
   ```

4. **Plan deployment**:
   ```bash
   terraform plan
   ```

5. **Deploy infrastructure**:
   ```bash
   terraform apply
   ```

## What Gets Created

- **Cloud Functions**: Webhook handler for Dropbox notifications
- **Cloud Run Job**: Transcription worker using OpenAI Whisper
- **Service Account**: `transcription-dropbox-service@YOUR-PROJECT-ID.iam.gserviceaccount.com`
- **Secret Manager**: Stores Dropbox tokens, OpenAI API key, Gmail credentials
- **Storage Buckets**: For function source code
- **IAM Roles**: Secret Manager access, Cloud Run invoker, Storage admin

## Required Variables

Edit `terraform.tfvars` with these required values:

```hcl
# Project Configuration
project_id = "your-gcp-project-id"
region     = "us-east1"  # or your preferred region

# Dropbox Configuration
dropbox_access_token = "your-dropbox-access-token"
dropbox_app_secret   = "your-dropbox-app-secret"

# Optional: Dropbox OAuth (if using OAuth flow instead of access token)
dropbox_refresh_token = "your-dropbox-refresh-token"  # Optional
dropbox_app_key      = "your-dropbox-app-key"        # Optional

# OpenAI Configuration
openai_api_key = "your-openai-api-key"

# Gmail Configuration
gmail_address      = "your-email@gmail.com"
gmail_app_password = "your-16-char-app-password"
notification_emails = ["recipient@example.com"]

# Optional: Custom folder paths (defaults shown)
# dropbox_raw_folder       = "/raw"
# dropbox_processed_folder = "/processed"
```

## Adding Email Notification Recipients

To add more people to email notifications, simply add their email addresses to the list in `terraform.tfvars`:

```hcl
notification_emails = [
  "user1@example.com",
  "user2@example.com",
  "user3@example.com"
]
```

Then apply the changes:
```bash
terraform apply
```

The system will automatically convert this list to a comma-separated format for the notification service.

## After Deployment

1. **Get webhook URL**:
   ```bash
   terraform output webhook_url
   ```

2. **Configure Dropbox webhook**:
   - Go to Dropbox App Console
   - Add the webhook URL to your app
   - Verify webhook with the challenge response

3. **Test the pipeline**:
   - Upload an audio file to your configured Dropbox folder (default: `/raw/`)
   - Check logs: `gcloud functions logs read transcription-webhook --region=us-east1 --limit=10`
   - Verify email notification received
   - Check transcribed file appears in processed folder (default: `/processed/`)

## Making Changes

When updating worker code:

1. **Build and push new container**:
   ```bash
   docker buildx build --platform linux/amd64 -t gcr.io/YOUR-PROJECT-ID/transcription-worker:latest worker/ --push
   ```

2. **Apply terraform changes**:
   ```bash
   terraform apply
   ```

## Monitoring

- **Webhook logs**: `gcloud functions logs read transcription-webhook --region=us-east1 --limit=20`
- **Worker logs**: `gcloud logging read "resource.type=cloud_run_job" --limit=10`
- **Job executions**: `gcloud run jobs executions list --job=transcription-worker --region=us-east1`
- **Secrets**: `gcloud secrets list`

## Cleanup

To remove all resources:
```bash
terraform destroy
```

## Security Notes

- All sensitive credentials are stored in Google Secret Manager
- Never commit `terraform.tfvars` to version control (it's gitignored)
- Service account has minimal required permissions
- Webhook uses signature verification for security
- Gmail uses app-specific passwords, not account passwords