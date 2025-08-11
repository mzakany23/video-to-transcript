# Development Environment - Transcription Pipeline
# Intent: Deploy complete transcription pipeline to GCP for development use

module "transcription_pipeline" {
  source = "../../modules/gcp/transcription-pipeline"

  # Basic Configuration
  project_id = var.project_id
  region     = var.region

  # Dropbox Integration
  dropbox_access_token = var.dropbox_access_token
  dropbox_app_secret   = var.dropbox_app_secret

  # Email Notifications
  gmail_address       = var.gmail_address
  gmail_app_password  = var.gmail_app_password
  notification_emails = var.notification_emails
}