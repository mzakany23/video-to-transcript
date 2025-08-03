# Google Drive Webhook Handler Cloud Function
# Receives push notifications from Google Drive when files are added/modified

# Storage object for webhook function source
resource "google_storage_bucket_object" "webhook_source_zip" {
  name   = "webhook-function-${formatdate("YYYY-MM-DD-hhmm", timestamp())}.zip"
  bucket = google_storage_bucket.function_source.name
  source = "../webhook-function.zip"

  lifecycle {
    ignore_changes = [source]
  }
}

# Cloud Function for handling Drive webhooks
resource "google_cloudfunctions2_function" "drive_webhook_handler" {
  name        = "drive-webhook-handler"
  location    = var.region
  description = "Handles Google Drive push notifications and triggers transcription processing"

  build_config {
    runtime     = "python311"
    entry_point = "drive_webhook_handler"
    
    source {
      storage_source {
        bucket = google_storage_bucket.function_source.name
        object = google_storage_bucket_object.webhook_source_zip.name
      }
    }
  }

  service_config {
    max_instance_count               = 3    # Limit to 3 instances max
    min_instance_count               = 0
    available_memory                 = "256Mi"  # Minimal memory for fast, cheap execution
    timeout_seconds                  = 30   # Short timeout - webhook should be fast
    max_instance_request_concurrency = 10   # Limit concurrent requests per instance
    available_cpu                    = "1"
    
    environment_variables = {
      PROJECT_ID           = var.project_id
      PUBSUB_TOPIC         = google_pubsub_topic.transcription_events.name
      MONITORED_FOLDER_ID  = var.monitored_folder_id
      CLOUD_RUN_REGION     = var.region
      CLOUD_RUN_JOB_NAME   = "transcription-processor-job"
    }
    
    service_account_email = google_service_account.transcription_service.email
    
    # Allow public access for Google Drive webhooks
    ingress_settings = "ALLOW_ALL"
  }

  depends_on = [
    google_project_service.cloudfunctions_api,
    google_project_service.cloudbuild_api,
    google_storage_bucket_object.webhook_source_zip
  ]
}

# Allow public access to the webhook function
resource "google_cloudfunctions2_function_iam_member" "webhook_public_access" {
  project        = google_cloudfunctions2_function.drive_webhook_handler.project
  location       = google_cloudfunctions2_function.drive_webhook_handler.location
  cloud_function = google_cloudfunctions2_function.drive_webhook_handler.name
  role           = "roles/cloudfunctions.invoker"
  member         = "allUsers"
}

# Output the webhook URL for Drive notification setup
output "webhook_url" {
  value       = google_cloudfunctions2_function.drive_webhook_handler.url
  description = "URL for Google Drive webhook notifications"
}