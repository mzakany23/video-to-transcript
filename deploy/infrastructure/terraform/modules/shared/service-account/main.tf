variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "account_id" {
  description = "Service account ID"
  type        = string
}

variable "display_name" {
  description = "Service account display name"
  type        = string
}

variable "description" {
  description = "Service account description"
  type        = string
  default     = ""
}

variable "roles" {
  description = "List of roles to assign to the service account"
  type        = list(string)
  default     = []
}

resource "google_service_account" "service_account" {
  project      = var.project_id
  account_id   = var.account_id
  display_name = var.display_name
  description  = var.description
}

resource "google_project_iam_member" "service_account_roles" {
  for_each = toset(var.roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.service_account.email}"
}

output "email" {
  description = "Service account email"
  value       = google_service_account.service_account.email
}

output "name" {
  description = "Service account name"
  value       = google_service_account.service_account.name
}

output "unique_id" {
  description = "Service account unique ID"
  value       = google_service_account.service_account.unique_id
}