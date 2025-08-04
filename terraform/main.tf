
# Dropbox-based transcription pipeline infrastructure

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

# Cloud Run Job for transcription processing
resource "google_cloud_run_v2_job" "transcription_processor" {
  project  = var.project_id
  name     = "transcription-worker"
  location = var.region

  template {
    template {
      service_account = google_service_account.transcription_service.email

      containers {
        image = "gcr.io/${var.project_id}/transcription-worker:latest"

        env {
          name = "PROJECT_ID"
          value = var.project_id
        }

        env {
          name = "SECRET_NAME"
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

        resources {
          limits = {
            cpu    = "2"
            memory = "8Gi"
          }
        }
      }

      timeout = "3600s"  # 1 hour timeout
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
    max_instance_count = 10
    min_instance_count = 0  # Scale to zero = $0 when not used!
    available_memory   = "256Mi"
    timeout_seconds    = 60
    service_account_email = google_service_account.transcription_service.email

    environment_variables = {
      PROJECT_ID               = var.project_id
      GCP_REGION               = var.region
      WORKER_JOB_NAME          = google_cloud_run_v2_job.transcription_processor.name
      DROPBOX_RAW_FOLDER       = "/jos-transcripts/raw"
      DROPBOX_PROCESSED_FOLDER = "/jos-transcripts/processed"
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
