variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "secrets" {
  description = "Map of secret names to their values"
  type        = map(string)
  sensitive   = true
}

variable "secret_ids" {
  description = "Map of secret names to their GCP secret IDs"
  type        = map(string)
  default     = {}
}

locals {
  # Use keys from secret_ids or fallback to secret names
  secret_keys = keys(var.secrets)
  secret_id_map = merge(
    { for k in local.secret_keys : k => k },
    var.secret_ids
  )
}

resource "google_secret_manager_secret" "secrets" {
  for_each = toset(local.secret_keys)

  project   = var.project_id
  secret_id = local.secret_id_map[each.key]

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "secrets" {
  for_each = toset(local.secret_keys)

  secret      = google_secret_manager_secret.secrets[each.key].id
  secret_data = var.secrets[each.key]
}

output "secret_ids" {
  description = "Map of secret names to their GCP secret IDs"
  value       = { for k, v in google_secret_manager_secret.secrets : k => v.secret_id }
}

output "secret_names" {
  description = "Map of secret names to their full resource names"
  value       = { for k, v in google_secret_manager_secret.secrets : k => v.name }
}