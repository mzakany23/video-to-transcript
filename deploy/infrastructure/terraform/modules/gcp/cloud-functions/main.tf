variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region"
  type        = string
}

variable "function_name" {
  description = "Name of the Cloud Function"
  type        = string
}

variable "source_dir" {
  description = "Directory containing function source code"
  type        = string
}

variable "entry_point" {
  description = "Function entry point"
  type        = string
}

variable "runtime" {
  description = "Function runtime"
  type        = string
  default     = "python311"
}

variable "service_account_email" {
  description = "Service account email for the function"
  type        = string
}

variable "environment_variables" {
  description = "Environment variables for the function"
  type        = map(string)
  default     = {}
}

variable "secret_environment_variables" {
  description = "Secret environment variables"
  type = map(object({
    project_id = string
    secret_id  = string
    version    = string
  }))
  default = {}
}

variable "timeout_seconds" {
  description = "Function timeout in seconds"
  type        = number
  default     = 60
}

variable "available_memory" {
  description = "Available memory for the function"
  type        = string
  default     = "256Mi"
}

variable "max_instance_count" {
  description = "Maximum number of instances"
  type        = number
  default     = 10
}

variable "min_instance_count" {
  description = "Minimum number of instances"
  type        = number
  default     = 0
}

variable "allow_public_access" {
  description = "Allow public access to the function"
  type        = bool
  default     = false
}

# Create zip file for function source
data "archive_file" "function_source" {
  type        = "zip"
  source_dir  = var.source_dir
  output_path = "${var.function_name}-source.zip"
}

# Storage bucket for function source
resource "google_storage_bucket" "function_source" {
  name     = "${var.project_id}-${var.function_name}-source"
  location = var.region
  project  = var.project_id
}

# Upload source to bucket
resource "google_storage_bucket_object" "function_source" {
  name   = "${var.function_name}-source.zip"
  bucket = google_storage_bucket.function_source.name
  source = data.archive_file.function_source.output_path
}

# Cloud Function
resource "google_cloudfunctions2_function" "function" {
  name     = var.function_name
  location = var.region
  project  = var.project_id

  build_config {
    runtime     = var.runtime
    entry_point = var.entry_point
    source {
      storage_source {
        bucket = google_storage_bucket.function_source.name
        object = google_storage_bucket_object.function_source.name
      }
    }
  }

  service_config {
    max_instance_count    = var.max_instance_count
    min_instance_count    = var.min_instance_count
    available_memory      = var.available_memory
    timeout_seconds       = var.timeout_seconds
    service_account_email = var.service_account_email

    environment_variables = var.environment_variables

    dynamic "secret_environment_variables" {
      for_each = var.secret_environment_variables
      content {
        key        = secret_environment_variables.key
        project_id = secret_environment_variables.value.project_id
        secret     = secret_environment_variables.value.secret_id
        version    = secret_environment_variables.value.version
      }
    }
  }
}

# Public access (if enabled)
resource "google_cloudfunctions2_function_iam_member" "public_access" {
  count = var.allow_public_access ? 1 : 0

  project        = var.project_id
  location       = google_cloudfunctions2_function.function.location
  cloud_function = google_cloudfunctions2_function.function.name
  role           = "roles/cloudfunctions.invoker"
  member         = "allUsers"
}

output "function_url" {
  description = "URL of the deployed function"
  value       = google_cloudfunctions2_function.function.service_config[0].uri
}

output "function_name" {
  description = "Name of the deployed function"
  value       = google_cloudfunctions2_function.function.name
}