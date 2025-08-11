output "webhook_url" {
  description = "URL for Dropbox webhook configuration"
  value       = module.webhook_handler.function_url
}

output "worker_job_name" {
  description = "Name of the worker Cloud Run job"
  value       = module.transcription_worker.job_name
}

output "service_account_email" {
  description = "Service account email for the transcription service"
  value       = module.service_account.email
}

output "secret_ids" {
  description = "Map of secret names to their IDs"
  value = {
    dropbox_token     = google_secret_manager_secret.dropbox_token.secret_id
    dropbox_secret    = google_secret_manager_secret.dropbox_secret.secret_id
    gmail_credentials = google_secret_manager_secret.gmail_credentials.secret_id
    openai_key        = google_secret_manager_secret.openai_key.secret_id
  }
  sensitive = true
}