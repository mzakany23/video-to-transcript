# Variables for Dropbox transcription pipeline

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