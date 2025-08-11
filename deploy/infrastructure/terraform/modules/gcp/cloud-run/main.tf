variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region"
  type        = string
}

variable "job_name" {
  description = "Name of the Cloud Run job"
  type        = string
}

variable "image" {
  description = "Container image URL"
  type        = string
}

variable "service_account_email" {
  description = "Service account email for the job"
  type        = string
}

variable "environment_variables" {
  description = "Environment variables for the job"
  type        = map(string)
  default     = {}
}

variable "secret_environment_variables" {
  description = "Secret environment variables"
  type = map(object({
    secret_id = string
    version   = string
  }))
  default = {}
}

variable "timeout" {
  description = "Job timeout in seconds"
  type        = string
  default     = "3600s"
}

variable "cpu" {
  description = "CPU allocation"
  type        = string
  default     = "2"
}

variable "memory" {
  description = "Memory allocation"
  type        = string
  default     = "8Gi"
}

resource "google_cloud_run_v2_job" "job" {
  project  = var.project_id
  name     = var.job_name
  location = var.region

  template {
    template {
      service_account = var.service_account_email

      containers {
        image = var.image

        dynamic "env" {
          for_each = var.environment_variables
          content {
            name  = env.key
            value = env.value
          }
        }

        dynamic "env" {
          for_each = var.secret_environment_variables
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value.secret_id
                version = env.value.version
              }
            }
          }
        }

        resources {
          limits = {
            cpu    = var.cpu
            memory = var.memory
          }
        }
      }

      timeout = var.timeout
    }
  }
}

output "job_name" {
  description = "Name of the created Cloud Run job"
  value       = google_cloud_run_v2_job.job.name
}

output "job_id" {
  description = "ID of the created Cloud Run job"
  value       = google_cloud_run_v2_job.job.id
}