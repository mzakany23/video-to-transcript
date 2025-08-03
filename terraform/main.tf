# Google Cloud Platform Configuration for Transcription Service
terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Configure the Google Cloud Provider
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Enable required APIs
resource "google_project_service" "drive_api" {
  service = "drive.googleapis.com"
}

resource "google_project_service" "iam_api" {
  service = "iam.googleapis.com"
}

resource "google_project_service" "cloudfunctions_api" {
  service = "cloudfunctions.googleapis.com"
}

resource "google_project_service" "cloudbuild_api" {
  service = "cloudbuild.googleapis.com"
}

resource "google_project_service" "pubsub_api" {
  service = "pubsub.googleapis.com"
}

resource "google_project_service" "storage_api" {
  service = "storage-api.googleapis.com"
}

resource "google_project_service" "secretmanager_api" {
  service = "secretmanager.googleapis.com"
}

resource "google_project_service" "eventarc_api" {
  service = "eventarc.googleapis.com"
}

resource "google_project_service" "run_api" {
  service = "run.googleapis.com"
}

resource "google_project_service" "container_registry_api" {
  service = "containerregistry.googleapis.com"
}

# Create service account for transcription service
resource "google_service_account" "transcription_service" {
  account_id   = "transcription-service"
  display_name = "Transcription Service Account"
  description  = "Service account for automated audio/video transcription pipeline"
}

# Create and download service account key
resource "google_service_account_key" "transcription_service_key" {
  service_account_id = google_service_account.transcription_service.name
  public_key_type    = "TYPE_X509_PEM_FILE"
}

# Save the private key to local file
resource "local_file" "service_account_key" {
  content  = base64decode(google_service_account_key.transcription_service_key.private_key)
  filename = "../service-account.json"
}

# Grant necessary IAM roles to service account
# Note: Google Drive permissions are managed through domain admin console or OAuth scopes
# For service accounts, we only need basic project-level permissions
resource "google_project_iam_member" "storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.transcription_service.email}"
}

# Note: Pub/Sub and Cloud Functions IAM roles removed - using Cloud Run Jobs

resource "google_project_iam_member" "secretmanager_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.transcription_service.email}"
}

# Cloud Run Job permissions
resource "google_project_iam_member" "run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.transcription_service.email}"
}

resource "google_project_iam_member" "run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.transcription_service.email}"
}

# Container Registry permissions for Cloud Run Job images
resource "google_project_iam_member" "storage_object_viewer" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.transcription_service.email}"
}

# Cloud Storage bucket for temporary file processing
resource "google_storage_bucket" "transcription_temp" {
  name          = "${var.project_id}-transcription-temp"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 1
    }
    action {
      type = "Delete"
    }
  }

  versioning {
    enabled = false
  }
}

# Grant service account access to storage bucket
resource "google_storage_bucket_iam_member" "transcription_bucket_admin" {
  bucket = google_storage_bucket.transcription_temp.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.transcription_service.email}"
}

# Pub/Sub topic for transcription events
resource "google_pubsub_topic" "transcription_events" {
  name = "transcription-events"
}

# Pub/Sub subscription for processing events
resource "google_pubsub_subscription" "transcription_processor" {
  name  = "transcription-processor"
  topic = google_pubsub_topic.transcription_events.name

  ack_deadline_seconds = 600  # 10 minutes for processing

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.transcription_dlq.id
    max_delivery_attempts = 5
  }
}

# Dead letter queue for failed messages
resource "google_pubsub_topic" "transcription_dlq" {
  name = "transcription-dead-letter"
}

# Secret Manager for OpenAI API key
resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "openai-api-key"

  replication {
    auto {}
  }
}

# Secret for service account key (for Cloud Run Job)
resource "google_secret_manager_secret" "service_account_key" {
  secret_id = "service-account-key"

  replication {
    auto {}
  }
}

# Store service account key in Secret Manager
resource "google_secret_manager_secret_version" "service_account_key_version" {
  secret      = google_secret_manager_secret.service_account_key.id
  secret_data = base64decode(google_service_account_key.transcription_service_key.private_key)
}

# Note: The actual secret value should be set manually or via separate process
# This is just the secret definition, not the value