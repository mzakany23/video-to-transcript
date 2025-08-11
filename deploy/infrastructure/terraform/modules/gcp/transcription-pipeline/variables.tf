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

variable "webhook_source_dir" {
  description = "Directory containing webhook source code"
  type        = string
  default     = "../../../../../webhook"
}