output "webhook_url" {
  description = "URL for Dropbox webhook configuration"
  value       = module.transcription_pipeline.webhook_url
}

output "worker_job_name" {
  description = "Name of the worker Cloud Run job"
  value       = module.transcription_pipeline.worker_job_name
}

output "service_account_email" {
  description = "Service account email for the transcription service"
  value       = module.transcription_pipeline.service_account_email
}

output "project_id" {
  description = "GCP Project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP Region"
  value       = var.region
}