# Cloud Run Job for heavy transcription processing
# Replaces Cloud Functions for better resource limits and batch processing

# Cloud Run Job for transcription processing
resource "google_cloud_run_v2_job" "transcription_job" {
  name     = "transcription-processor-job"
  location = var.region

  template {
    # Job execution settings
    parallelism = 1
    task_count  = 1

    template {
      # Task timeout - corrected syntax
      timeout = "3600s"  # 1 hour timeout

      # Service account for permissions
      service_account = google_service_account.transcription_service.email

      # Container resource limits - much better than Cloud Functions
      containers {
        image = "gcr.io/${var.project_id}/transcription-processor:latest"

        # Environment variables
        env {
          name  = "PROJECT_ID"
          value = var.project_id
        }
        env {
          name  = "SECRET_NAME"
          value = google_secret_manager_secret.openai_api_key.secret_id
        }
        env {
          name  = "RAW_FOLDER_ID"
          value = var.raw_folder_id
        }
        env {
          name  = "PROCESSED_FOLDER_ID"
          value = var.processed_folder_id
        }
        env {
          name  = "SERVICE_ACCOUNT_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.service_account_key.secret_id
              version = "latest"
            }
          }
        }

        # Resource limits - much better than Cloud Functions
        resources {
          limits = {
            cpu    = "4"      # 4 CPU cores
            memory = "8Gi"    # 8GB memory (4x Cloud Functions)
          }
        }
      }
    }
  }

  depends_on = [
    google_project_service.run_api
  ]
}

# IAM binding for Cloud Run Job execution
resource "google_cloud_run_v2_job_iam_member" "job_invoker" {
  project  = google_cloud_run_v2_job.transcription_job.project
  location = google_cloud_run_v2_job.transcription_job.location
  name     = google_cloud_run_v2_job.transcription_job.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.transcription_service.email}"
}

# Output the job name for triggering
output "cloud_run_job_name" {
  value       = google_cloud_run_v2_job.transcription_job.name
  description = "Name of the Cloud Run transcription job"
}