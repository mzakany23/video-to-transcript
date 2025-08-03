# Outputs for Dropbox transcription pipeline

output "webhook_url" {
  description = "URL for Dropbox webhook configuration"
  value       = google_cloud_run_v2_service.webhook_handler.uri
}

output "worker_job_name" {
  description = "Name of the worker Cloud Run job"
  value       = google_cloud_run_v2_job.transcription_processor.name
}

output "service_account_email" {
  description = "Service account email for the transcription service"
  value       = google_service_account.transcription_service.email
}

output "project_id" {
  description = "GCP Project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP Region"
  value       = var.region
}