
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

variable "developer_emails" {
  description = "List of developer email addresses (receives debug emails: kickoff, success, failure)"
  type        = list(string)
}

variable "user_emails" {
  description = "List of user email addresses (receives polished summary emails only)"
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

variable "sentry_dsn" {
  description = "Sentry DSN for error tracking"
  type        = string
  sensitive   = true
  default     = "" # Optional - only needed if Sentry is configured
}

variable "worker_image_version" {
  description = "Docker image version for transcription worker (set in terraform.tfvars)"
  type        = string
}

variable "webhook_version" {
  description = "Version tag for webhook Cloud Function (set in terraform.tfvars)"
  type        = string
}

variable "downloader_version" {
  description = "Version tag for downloader Cloud Function (set in terraform.tfvars)"
  type        = string
  default     = "1.0.0"
}

variable "zoom_account_id" {
  description = "Zoom account ID for Server-to-Server OAuth"
  type        = string
  sensitive   = true
  default     = "" # Optional - only needed if using downloader service
}

variable "zoom_client_id" {
  description = "Zoom client ID for Server-to-Server OAuth"
  type        = string
  sensitive   = true
  default     = "" # Optional - only needed if using downloader service
}

variable "zoom_client_secret" {
  description = "Zoom client secret for Server-to-Server OAuth"
  type        = string
  sensitive   = true
  default     = "" # Optional - only needed if using downloader service
}

variable "zoom_webhook_secret" {
  description = "Zoom webhook secret token for signature verification"
  type        = string
  sensitive   = true
  default     = "" # Optional - only needed if using downloader service
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

# Sentry DSN for error tracking
resource "google_secret_manager_secret" "sentry_dsn" {
  count     = var.sentry_dsn != "" ? 1 : 0
  project   = var.project_id
  secret_id = "sentry-dsn"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "sentry_dsn" {
  count       = var.sentry_dsn != "" ? 1 : 0
  secret      = google_secret_manager_secret.sentry_dsn[0].id
  secret_data = var.sentry_dsn
}

# Zoom credentials for downloader service
resource "google_secret_manager_secret" "zoom_account_id" {
  count     = var.zoom_account_id != "" ? 1 : 0
  project   = var.project_id
  secret_id = "zoom-account-id"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "zoom_account_id" {
  count       = var.zoom_account_id != "" ? 1 : 0
  secret      = google_secret_manager_secret.zoom_account_id[0].id
  secret_data = var.zoom_account_id
}

resource "google_secret_manager_secret" "zoom_client_id" {
  count     = var.zoom_client_id != "" ? 1 : 0
  project   = var.project_id
  secret_id = "zoom-client-id"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "zoom_client_id" {
  count       = var.zoom_client_id != "" ? 1 : 0
  secret      = google_secret_manager_secret.zoom_client_id[0].id
  secret_data = var.zoom_client_id
}

resource "google_secret_manager_secret" "zoom_client_secret" {
  count     = var.zoom_client_secret != "" ? 1 : 0
  project   = var.project_id
  secret_id = "zoom-client-secret"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "zoom_client_secret" {
  count       = var.zoom_client_secret != "" ? 1 : 0
  secret      = google_secret_manager_secret.zoom_client_secret[0].id
  secret_data = var.zoom_client_secret
}

resource "google_secret_manager_secret" "zoom_webhook_secret" {
  count     = var.zoom_webhook_secret != "" ? 1 : 0
  project   = var.project_id
  secret_id = "zoom-webhook-secret"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "zoom_webhook_secret" {
  count       = var.zoom_webhook_secret != "" ? 1 : 0
  secret      = google_secret_manager_secret.zoom_webhook_secret[0].id
  secret_data = var.zoom_webhook_secret
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
          name  = "DEVELOPER_EMAILS"
          value = join(",", var.developer_emails)
        }

        env {
          name  = "USER_EMAILS"
          value = join(",", var.user_emails)
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

        dynamic "env" {
          for_each = var.sentry_dsn != "" ? [1] : []
          content {
            name = "SENTRY_DSN"
            value_source {
              secret_key_ref {
                secret  = google_secret_manager_secret.sentry_dsn[0].secret_id
                version = "latest"
              }
            }
          }
        }

        dynamic "env" {
          for_each = var.sentry_dsn != "" ? [1] : []
          content {
            name  = "SENTRY_ENVIRONMENT"
            value = "production"
          }
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

    dynamic "secret_environment_variables" {
      for_each = var.sentry_dsn != "" ? [1] : []
      content {
        key        = "SENTRY_DSN"
        project_id = var.project_id
        secret     = google_secret_manager_secret.sentry_dsn[0].secret_id
        version    = "latest"
      }
    }
  }

  depends_on = [google_project_service.required_apis]
}

# Allow public access to webhook (for Dropbox to call it)
# SECURITY NOTE: While this allows unauthenticated HTTP access, the webhook handler
# validates all requests using HMAC-SHA256 signature verification with the Dropbox
# app secret. This is the industry-standard security model for webhooks (GitHub,
# Stripe, Dropbox, etc.) - the HMAC signature provides cryptographic authentication.
resource "google_cloudfunctions2_function_iam_member" "webhook_public_access" {
  project        = var.project_id
  location       = google_cloudfunctions2_function.webhook_handler.location
  cloud_function = google_cloudfunctions2_function.webhook_handler.name
  role           = "roles/cloudfunctions.invoker"
  member         = "allUsers"
}

# Also allow public access to the underlying Cloud Run service
# (Gen2 Cloud Functions are backed by Cloud Run services)
resource "google_cloud_run_service_iam_member" "webhook_public_access" {
  project  = var.project_id
  location = google_cloudfunctions2_function.webhook_handler.location
  service  = google_cloudfunctions2_function.webhook_handler.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ============================================================================
# ZOOM DOWNLOADER SERVICE
# ============================================================================

# Create zip file for downloader Cloud Function source
data "archive_file" "downloader_source" {
  count       = var.zoom_account_id != "" ? 1 : 0
  type        = "zip"
  source_dir  = "../downloader"
  output_path = "downloader-source.zip"
  excludes    = ["tests", "__pycache__", "*.pyc", ".pytest_cache"]
}

# Storage bucket for downloader source
resource "google_storage_bucket" "downloader_source" {
  count    = var.zoom_account_id != "" ? 1 : 0
  name     = "${var.project_id}-downloader-source"
  location = var.region
  project  = var.project_id

  depends_on = [google_project_service.required_apis]
}

# Upload downloader source to bucket
resource "google_storage_bucket_object" "downloader_source" {
  count  = var.zoom_account_id != "" ? 1 : 0
  name   = "downloader-source-${var.downloader_version}.zip"
  bucket = google_storage_bucket.downloader_source[0].name
  source = data.archive_file.downloader_source[0].output_path
}

# Cloud Function for Zoom downloader (scales to zero = no cost when not used!)
resource "google_cloudfunctions2_function" "downloader_handler" {
  count    = var.zoom_account_id != "" ? 1 : 0
  name     = "zoom-downloader"
  location = var.region
  project  = var.project_id

  labels = {
    version     = replace(var.downloader_version, ".", "-")
    managed-by  = "terraform"
    environment = "production"
  }

  build_config {
    runtime     = "python311"
    entry_point = "zoom_downloader_handler"
    source {
      storage_source {
        bucket = google_storage_bucket.downloader_source[0].name
        object = google_storage_bucket_object.downloader_source[0].name
      }
    }
  }

  service_config {
    max_instance_count    = 5
    min_instance_count    = 0 # Scale to zero = $0 when not used!
    available_memory      = "512Mi"
    timeout_seconds       = 1200 # 20 minutes for large downloads (handles 1-2 hour recordings, 1-2GB files)
    service_account_email = google_service_account.transcription_service.email

    environment_variables = {
      VERSION            = var.downloader_version
      PROJECT_ID         = var.project_id
      GCP_REGION         = var.region
      DROPBOX_RAW_FOLDER = var.dropbox_raw_folder
    }

    # Zoom OAuth credentials
    dynamic "secret_environment_variables" {
      for_each = var.zoom_account_id != "" ? [1] : []
      content {
        key        = "ZOOM_ACCOUNT_ID"
        project_id = var.project_id
        secret     = google_secret_manager_secret.zoom_account_id[0].secret_id
        version    = "latest"
      }
    }

    dynamic "secret_environment_variables" {
      for_each = var.zoom_client_id != "" ? [1] : []
      content {
        key        = "ZOOM_CLIENT_ID"
        project_id = var.project_id
        secret     = google_secret_manager_secret.zoom_client_id[0].secret_id
        version    = "latest"
      }
    }

    dynamic "secret_environment_variables" {
      for_each = var.zoom_client_secret != "" ? [1] : []
      content {
        key        = "ZOOM_CLIENT_SECRET"
        project_id = var.project_id
        secret     = google_secret_manager_secret.zoom_client_secret[0].secret_id
        version    = "latest"
      }
    }

    dynamic "secret_environment_variables" {
      for_each = var.zoom_webhook_secret != "" ? [1] : []
      content {
        key        = "ZOOM_WEBHOOK_SECRET"
        project_id = var.project_id
        secret     = google_secret_manager_secret.zoom_webhook_secret[0].secret_id
        version    = "latest"
      }
    }

    # Dropbox credentials (reuse from webhook)
    secret_environment_variables {
      key        = "DROPBOX_ACCESS_TOKEN"
      project_id = var.project_id
      secret     = google_secret_manager_secret.dropbox_token.secret_id
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

    secret_environment_variables {
      key        = "DROPBOX_APP_SECRET"
      project_id = var.project_id
      secret     = google_secret_manager_secret.dropbox_secret.secret_id
      version    = "latest"
    }

    # Sentry (optional)
    dynamic "secret_environment_variables" {
      for_each = var.sentry_dsn != "" ? [1] : []
      content {
        key        = "SENTRY_DSN"
        project_id = var.project_id
        secret     = google_secret_manager_secret.sentry_dsn[0].secret_id
        version    = "latest"
      }
    }

  }

  depends_on = [google_project_service.required_apis]
}

# Allow public access to downloader (for Zoom to call it)
# SECURITY NOTE: While this allows unauthenticated HTTP access, the webhook handler
# validates all requests using HMAC-SHA256 signature verification with the Zoom
# webhook secret. This is the industry-standard security model for webhooks.
resource "google_cloudfunctions2_function_iam_member" "downloader_public_access" {
  count          = var.zoom_account_id != "" ? 1 : 0
  project        = var.project_id
  location       = google_cloudfunctions2_function.downloader_handler[0].location
  cloud_function = google_cloudfunctions2_function.downloader_handler[0].name
  role           = "roles/cloudfunctions.invoker"
  member         = "allUsers"
}

# Also allow public access to the underlying Cloud Run service
# (Gen2 Cloud Functions are backed by Cloud Run services)
resource "google_cloud_run_service_iam_member" "downloader_public_access" {
  count    = var.zoom_account_id != "" ? 1 : 0
  project  = var.project_id
  location = google_cloudfunctions2_function.downloader_handler[0].location
  service  = google_cloudfunctions2_function.downloader_handler[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Outputs
output "webhook_url" {
  description = "URL for Dropbox webhook configuration"
  value       = google_cloudfunctions2_function.webhook_handler.service_config[0].uri
}

output "downloader_url" {
  description = "URL for Zoom webhook configuration"
  value       = var.zoom_account_id != "" ? google_cloudfunctions2_function.downloader_handler[0].service_config[0].uri : "Not deployed (Zoom credentials not provided)"
}

output "worker_job_name" {
  description = "Name of the worker Cloud Run job"
  value       = google_cloud_run_v2_job.transcription_processor.name
}

output "service_account_email" {
  description = "Service account email for the transcription service"
  value       = google_service_account.transcription_service.email
}
