# Outputs for the transcription service setup

output "service_account_email" {
  description = "Email of the created service account"
  value       = google_service_account.transcription_service.email
}

output "service_account_id" {
  description = "ID of the created service account"
  value       = google_service_account.transcription_service.account_id
}

output "project_id" {
  description = "The GCP project ID"
  value       = var.project_id
}

output "enabled_apis" {
  description = "List of enabled APIs"  
  value = [
    google_project_service.drive_api.service,
    google_project_service.iam_api.service,
    google_project_service.run_api.service,
    google_project_service.container_registry_api.service,
    google_project_service.secretmanager_api.service
  ]
}

output "service_account_key_file" {
  description = "Path to the service account key file"
  value       = local_file.service_account_key.filename
  sensitive   = true
}

output "secret_manager_secret_id" {
  description = "Secret Manager secret ID for OpenAI API key"
  value       = google_secret_manager_secret.openai_api_key.secret_id
}

output "secret_manager_secret_name" {
  description = "Full name of the Secret Manager secret"
  value       = google_secret_manager_secret.openai_api_key.name
}