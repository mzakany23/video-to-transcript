
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

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudbuild.googleapis.com"
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

# Cloud Run Service for webhook handler
resource "google_cloud_run_v2_service" "webhook_handler" {
  project  = var.project_id
  name     = "transcription-webhook"
  location = var.region

  template {
    service_account = google_service_account.transcription_service.email

    containers {
      image = "gcr.io/${var.project_id}/transcription-webhook:latest"

      ports {
        container_port = 8080
      }

      env {
        name = "PROJECT_ID"
        value = var.project_id
      }

      env {
        name = "GCP_REGION"
        value = var.region
      }

      env {
        name = "WORKER_JOB_NAME"
        value = google_cloud_run_v2_job.transcription_processor.name
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
        name = "DROPBOX_APP_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.dropbox_secret.secret_id
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }
    }
  }

  depends_on = [google_project_service.required_apis]
}

# Allow public access to webhook handler
resource "google_cloud_run_service_iam_member" "webhook_public_access" {
  project  = var.project_id
  location = var.region
  service  = google_cloud_run_v2_service.webhook_handler.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Outputs
output "webhook_url" {
  description = "URL for Dropbox webhook configuration"
  value       = "${google_cloud_run_v2_service.webhook_handler.uri}/webhook"
}

output "worker_job_name" {
  description = "Name of the worker Cloud Run job"
  value       = google_cloud_run_v2_job.transcription_processor.name
}

output "service_account_email" {
  description = "Service account email for the transcription service"
  value       = google_service_account.transcription_service.email
}
