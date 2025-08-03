# Terraform Setup for Transcription Service

This directory contains Terraform configuration to automatically set up Google Cloud Platform resources for the transcription service.

## Prerequisites

1. **Install Terraform**:
   ```bash
   # macOS
   brew install terraform

   # Or download from: https://terraform.io/downloads
   ```

2. **Install Google Cloud CLI**:
   ```bash
   # macOS
   brew install google-cloud-sdk

   # Authenticate
   gcloud auth login
   gcloud auth application-default login
   ```

3. **Set up GCP Project**:
   ```bash
   # Create project (if needed)
   gcloud projects create jos-transcripts

   # Set project
   gcloud config set project jos-transcripts

   # Enable billing (required for API usage)
   # Go to: https://console.cloud.google.com/billing
   ```

## Setup

1. **Configure variables**:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your project details
   ```

2. **Initialize Terraform**:
   ```bash
   terraform init
   ```

3. **Plan deployment**:
   ```bash
   terraform plan
   ```

4. **Deploy infrastructure**:
   ```bash
   terraform apply
   ```

## What Gets Created

- ✅ **Service Account**: `transcription-service@jos-transcripts.iam.gserviceaccount.com`
- ✅ **API Enablement**: Google Drive API, IAM API
- ✅ **IAM Roles**: Drive Admin, Storage Admin
- ✅ **Service Account Key**: Automatically saved to `../service-account.json`

## After Deployment

The `service-account.json` file will be created in the project root. Your transcription service will automatically use this for authentication.

Test the setup:
```bash
cd ..
uv run python setup_google_credentials.py
```

## Cleanup

To remove all resources:
```bash
terraform destroy
```

## Security Notes

- The `service-account.json` file contains sensitive credentials
- It's automatically added to `.gitignore`
- Store securely and never commit to version control
- In production, use Google Secret Manager instead of local files