
# Dropbox-based transcription pipeline infrastructure
# Fixed: Updated Dropbox folder paths to /jos-transcripts/raw and /jos-transcripts/processed

terraform {
  backend "gcs" {
    bucket = "jos-transcripts-terraform-state"
    prefix = "terraform/state"
  }
}

variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region"
  type        = string
  default     = "us-east1"
}

variable "dropbox_access_token" {
  description = "Dropbox app access token"
  type        = string
  sensitive   = true
}

variable "dropbox_app_secret" {
  description = "Dropbox app secret for webhook verification"
  type        = string
  sensitive   = true
}

variable "gmail_address" {
  description = "Gmail address for sending notifications"
  type        = string
}

variable "gmail_app_password" {
  description = "Gmail app password for SMTP authentication"
  type        = string
  sensitive   = true
}

variable "notification_emails" {
  description = "List of email addresses to receive notifications"
  type        = list(string)
}

variable "dropbox_raw_folder" {
  description = "Dropbox folder path for raw audio files"
  type        = string
}

variable "dropbox_processed_folder" {
  description = "Dropbox folder path for processed transcriptions"
  type        = string
}

variable "openai_api_key" {
  description = "OpenAI API key for transcription"
  type        = string
  sensitive   = true
}

variable "dropbox_refresh_token" {
  description = "Dropbox OAuth refresh token"
  type        = string
  sensitive   = true
  default     = "" # Optional - only needed for OAuth flow
}

variable "dropbox_app_key" {
  description = "Dropbox app key"
  type        = string
  default     = "" # Optional - only needed for OAuth flow
}

variable "worker_image_version" {
  description = "Docker image version for transcription worker"
  type        = string
  default     = "v1.1.0"
}

variable "webhook_version" {
  description = "Version tag for webhook Cloud Function"
  type        = string
  default     = "v1.1.0"
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "storage.googleapis.com"
  ])

  project = var.project_id
  service = each.value

  disable_dependent_services = false
}

# Store Dropbox credentials in Secret Manager
resource "google_secret_manager_secret" "dropbox_token" {
  project   = var.project_id
  secret_id = "dropbox-access-token"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "dropbox_token" {
  secret      = google_secret_manager_secret.dropbox_token.id
  secret_data = var.dropbox_access_token
}

resource "google_secret_manager_secret" "dropbox_secret" {
  project   = var.project_id
  secret_id = "dropbox-app-secret"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "dropbox_secret" {
  secret      = google_secret_manager_secret.dropbox_secret.id
  secret_data = var.dropbox_app_secret
}

# Store OpenAI API key in Secret Manager
resource "google_secret_manager_secret" "openai_key" {
  project   = var.project_id
  secret_id = "openai-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "openai_key" {
  secret      = google_secret_manager_secret.openai_key.id
  secret_data = var.openai_api_key
}

# Store Gmail credentials in Secret Manager
resource "google_secret_manager_secret" "gmail_credentials" {
  project   = var.project_id
  secret_id = "gmail-credentials"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "gmail_credentials" {
  secret = google_secret_manager_secret.gmail_credentials.id
  secret_data = jsonencode({
    email        = var.gmail_address
    app_password = var.gmail_app_password
    smtp_server  = "smtp.gmail.com"
    smtp_port    = 587
  })
}

# Optional: Dropbox OAuth tokens (only create if provided)
resource "google_secret_manager_secret" "dropbox_refresh_token" {
  count     = var.dropbox_refresh_token != "" ? 1 : 0
  project   = var.project_id
  secret_id = "dropbox-refresh-token"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "dropbox_refresh_token" {
  count       = var.dropbox_refresh_token != "" ? 1 : 0
  secret      = google_secret_manager_secret.dropbox_refresh_token[0].id
  secret_data = var.dropbox_refresh_token
}

resource "google_secret_manager_secret" "dropbox_app_key" {
  count     = var.dropbox_app_key != "" ? 1 : 0
  project   = var.project_id
  secret_id = "dropbox-app-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "dropbox_app_key" {
  count       = var.dropbox_app_key != "" ? 1 : 0
  secret      = google_secret_manager_secret.dropbox_app_key[0].id
  secret_data = var.dropbox_app_key
}

# Service account for Cloud Run jobs
resource "google_service_account" "transcription_service" {
  project      = var.project_id
  account_id   = "transcription-dropbox-service"
  display_name = "Transcription Service (Dropbox)"
  description  = "Service account for Dropbox-based transcription pipeline"
}

# Grant necessary permissions
resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.transcription_service.email}"
}

resource "google_project_iam_member" "run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.transcription_service.email}"
}

resource "google_project_iam_member" "storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.transcription_service.email}"
}

# Service account for GitHub Actions CI/CD
resource "google_service_account" "github_actions" {
  project      = var.project_id
  account_id   = "github-actions-deploy"
  display_name = "GitHub Actions Deployment"
  description  = "Service account for GitHub Actions CI/CD pipeline"
}

# Grant GitHub Actions service account necessary permissions
resource "google_project_iam_member" "github_cloudbuild" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.builder"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "github_storage" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "github_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "github_service_account_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "github_logging_viewer" {
  project = var.project_id
  role    = "roles/logging.viewer"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "github_secret_admin" {
  project = var.project_id
  role    = "roles/secretmanager.admin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "github_iam_admin" {
  project = var.project_id
  role    = "roles/iam.serviceAccountAdmin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "github_compute_admin" {
  project = var.project_id
  role    = "roles/compute.admin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# Cloud Run Job for transcription processing
resource "google_cloud_run_v2_job" "transcription_processor" {
  project  = var.project_id
  name     = "transcription-worker"
  location = var.region

  template {
    template {
      service_account = google_service_account.transcription_service.email

      containers {
        image = "gcr.io/${var.project_id}/transcription-worker:${var.worker_image_version}"

        env {
          name  = "PROJECT_ID"
          value = var.project_id
        }

        env {
          name  = "SECRET_NAME"
          value = "openai-api-key"
        }

        env {
          name = "DROPBOX_ACCESS_TOKEN"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.dropbox_token.secret_id
              version = "latest"
            }
          }
        }

        env {
          name  = "ENABLE_EMAIL_NOTIFICATIONS"
          value = "true"
        }

        env {
          name  = "NOTIFICATION_EMAIL"
          value = join(",", var.notification_emails)
        }

        env {
          name  = "GMAIL_SECRET_NAME"
          value = google_secret_manager_secret.gmail_credentials.secret_id
        }

        env {
          name  = "DROPBOX_RAW_FOLDER"
          value = var.dropbox_raw_folder
        }

        env {
          name  = "DROPBOX_PROCESSED_FOLDER"
          value = var.dropbox_processed_folder
        }

        resources {
          limits = {
            cpu    = "2"
            memory = "8Gi"
          }
        }
      }

      timeout = "3600s" # 1 hour timeout
    }
  }

  depends_on = [google_project_service.required_apis]
}

# Create zip file for Cloud Function source
data "archive_file" "webhook_source" {
  type        = "zip"
  source_dir  = "../webhook"
  output_path = "webhook-source.zip"
}

# Storage bucket for Cloud Function source
resource "google_storage_bucket" "webhook_source" {
  name     = "${var.project_id}-webhook-source"
  location = var.region
  project  = var.project_id

  depends_on = [google_project_service.required_apis]
}

# Upload source to bucket
resource "google_storage_bucket_object" "webhook_source" {
  name   = "webhook-source.zip"
  bucket = google_storage_bucket.webhook_source.name
  source = data.archive_file.webhook_source.output_path
}

# Cloud Function for webhook handler (scales to zero = no cost when not used!)
resource "google_cloudfunctions2_function" "webhook_handler" {
  name     = "transcription-webhook"
  location = var.region
  project  = var.project_id

  labels = {
    version     = replace(var.webhook_version, ".", "-")
    managed-by  = "terraform"
    environment = "production"
  }

  build_config {
    runtime     = "python311"
    entry_point = "webhook_handler"
    source {
      storage_source {
        bucket = google_storage_bucket.webhook_source.name
        object = google_storage_bucket_object.webhook_source.name
      }
    }
  }

  service_config {
    max_instance_count    = 10
    min_instance_count    = 0 # Scale to zero = $0 when not used!
    available_memory      = "256Mi"
    timeout_seconds       = 60
    service_account_email = google_service_account.transcription_service.email

    environment_variables = {
      VERSION                  = var.webhook_version
      PROJECT_ID               = var.project_id
      GCP_REGION               = var.region
      WORKER_JOB_NAME          = google_cloud_run_v2_job.transcription_processor.name
      DROPBOX_RAW_FOLDER       = var.dropbox_raw_folder
      DROPBOX_PROCESSED_FOLDER = var.dropbox_processed_folder
    }

    secret_environment_variables {
      key        = "DROPBOX_ACCESS_TOKEN"
      project_id = var.project_id
      secret     = google_secret_manager_secret.dropbox_token.secret_id
      version    = "latest"
    }

    secret_environment_variables {
      key        = "DROPBOX_APP_SECRET"
      project_id = var.project_id
      secret     = google_secret_manager_secret.dropbox_secret.secret_id
      version    = "latest"
    }

    secret_environment_variables {
      key        = "DROPBOX_REFRESH_TOKEN"
      project_id = var.project_id
      secret     = "dropbox-refresh-token"
      version    = "latest"
    }

    secret_environment_variables {
      key        = "DROPBOX_APP_KEY"
      project_id = var.project_id
      secret     = "dropbox-app-key"
      version    = "latest"
    }
  }

  depends_on = [google_project_service.required_apis]
}

# Allow public access to webhook (for Dropbox to call it)
resource "google_cloudfunctions2_function_iam_member" "webhook_public_access" {
  project        = var.project_id
  location       = google_cloudfunctions2_function.webhook_handler.location
  cloud_function = google_cloudfunctions2_function.webhook_handler.name
  role           = "roles/cloudfunctions.invoker"
  member         = "allUsers"
}

# Outputs
output "webhook_url" {
  description = "URL for Dropbox webhook configuration"
  value       = google_cloudfunctions2_function.webhook_handler.service_config[0].uri
}

output "worker_job_name" {
  description = "Name of the worker Cloud Run job"
  value       = google_cloud_run_v2_job.transcription_processor.name
}

output "service_account_email" {
  description = "Service account email for the transcription service"
  value       = google_service_account.transcription_service.email
}
