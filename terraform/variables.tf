# Variables for Google Cloud Platform setup

variable "project_id" {
  description = "The GCP project ID"
  type        = string
  default     = ""  # Set this in your .tfvars file
}

variable "region" {
  description = "The GCP region"
  type        = string
  default     = "us-east1"
}

variable "zone" {
  description = "The GCP zone"
  type        = string
  default     = "us-east1-b"
}

variable "service_account_name" {
  description = "Name for the transcription service account"
  type        = string
  default     = "transcription-service"
}

variable "monitored_folder_id" {
  description = "Google Drive folder ID to monitor for new files"
  type        = string
  default     = ""
}

variable "raw_folder_id" {
  description = "Google Drive folder ID to monitor for new files (raw folder)"
  type        = string
  default     = ""  # Set this in your .tfvars file
}

variable "processed_folder_id" {
  description = "Google Drive folder ID where processed transcripts are saved"
  type        = string
  default     = ""  # Set this in your .tfvars file
}