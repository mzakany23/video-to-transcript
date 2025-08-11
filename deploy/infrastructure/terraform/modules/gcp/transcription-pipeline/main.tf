# Transcription Pipeline - Complete GCP Implementation
# This module encapsulates all resources needed for the transcription pipeline

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "storage.googleapis.com"
  ])

  project = var.project_id
  service = each.value

  disable_dependent_services = false
}

# Service Account with all required permissions
module "service_account" {
  source = "../../shared/service-account"

  project_id   = var.project_id
  account_id   = "transcription-dropbox-service"
  display_name = "Transcription Service (Dropbox)"
  description  = "Service account for Dropbox-based transcription pipeline"

  roles = [
    "roles/secretmanager.secretAccessor",
    "roles/run.invoker",
    "roles/storage.admin"
  ]

  depends_on = [google_project_service.required_apis]
}

# Secrets Management
resource "google_secret_manager_secret" "dropbox_token" {
  project   = var.project_id
  secret_id = "dropbox-access-token"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "dropbox_token" {
  secret      = google_secret_manager_secret.dropbox_token.id
  secret_data = var.dropbox_access_token
}

resource "google_secret_manager_secret" "dropbox_secret" {
  project   = var.project_id
  secret_id = "dropbox-app-secret"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "dropbox_secret" {
  secret      = google_secret_manager_secret.dropbox_secret.id
  secret_data = var.dropbox_app_secret
}

resource "google_secret_manager_secret" "gmail_credentials" {
  project   = var.project_id
  secret_id = "gmail-credentials"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "gmail_credentials" {
  secret = google_secret_manager_secret.gmail_credentials.id
  secret_data = jsonencode({
    email        = var.gmail_address
    app_password = var.gmail_app_password
    smtp_server  = "smtp.gmail.com"
    smtp_port    = 587
  })
}

resource "google_secret_manager_secret" "openai_key" {
  project   = var.project_id
  secret_id = "openai-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis]
}

# Transcription Worker (Cloud Run Job)
module "transcription_worker" {
  source = "../cloud-run"

  project_id            = var.project_id
  region                = var.region
  job_name              = "transcription-worker"
  image                 = "gcr.io/${var.project_id}/transcription-worker:latest"
  service_account_email = module.service_account.email

  environment_variables = {
    PROJECT_ID                = var.project_id
    SECRET_NAME              = google_secret_manager_secret.openai_key.secret_id
    ENABLE_EMAIL_NOTIFICATIONS = "true"
    NOTIFICATION_EMAIL       = join(",", var.notification_emails)
    GMAIL_SECRET_NAME        = google_secret_manager_secret.gmail_credentials.secret_id
    DROPBOX_RAW_FOLDER       = "/jos-transcripts/raw"
    DROPBOX_PROCESSED_FOLDER = "/jos-transcripts/processed"
  }

  secret_environment_variables = {
    DROPBOX_ACCESS_TOKEN = {
      secret_id = google_secret_manager_secret.dropbox_token.secret_id
      version   = "latest"
    }
  }

  timeout = "3600s"
  cpu     = "2"
  memory  = "8Gi"

  depends_on = [google_project_service.required_apis]
}

# Webhook Handler (Cloud Function)
module "webhook_handler" {
  source = "../cloud-functions"

  project_id            = var.project_id
  region                = var.region
  function_name         = "transcription-webhook"
  source_dir            = var.webhook_source_dir
  entry_point           = "webhook_handler"
  runtime               = "python311"
  service_account_email = module.service_account.email

  environment_variables = {
    PROJECT_ID               = var.project_id
    GCP_REGION               = var.region
    WORKER_JOB_NAME          = module.transcription_worker.job_name
    DROPBOX_RAW_FOLDER       = "/jos-transcripts/raw"
    DROPBOX_PROCESSED_FOLDER = "/jos-transcripts/processed"
  }

  secret_environment_variables = {
    DROPBOX_ACCESS_TOKEN = {
      project_id = var.project_id
      secret_id  = google_secret_manager_secret.dropbox_token.secret_id
      version    = "latest"
    }
    DROPBOX_APP_SECRET = {
      project_id = var.project_id
      secret_id  = google_secret_manager_secret.dropbox_secret.secret_id
      version    = "latest"
    }
    DROPBOX_REFRESH_TOKEN = {
      project_id = var.project_id
      secret_id  = "dropbox-refresh-token"
      version    = "latest"
    }
    DROPBOX_APP_KEY = {
      project_id = var.project_id
      secret_id  = "dropbox-app-key"
      version    = "latest"
    }
  }

  timeout_seconds      = 60
  available_memory     = "256Mi"
  max_instance_count   = 10
  min_instance_count   = 0
  allow_public_access  = true

  depends_on = [google_project_service.required_apis]
}