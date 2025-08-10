# Terraform moved blocks for state migration
# These blocks tell Terraform that resources have been moved to the transcription_pipeline module

# Service Account moves
moved {
  from = google_service_account.transcription_service
  to   = module.transcription_pipeline.module.service_account.google_service_account.service_account
}

moved {
  from = google_project_iam_member.secret_accessor
  to   = module.transcription_pipeline.module.service_account.google_project_iam_member.service_account_roles["roles/secretmanager.secretAccessor"]
}

moved {
  from = google_project_iam_member.run_invoker
  to   = module.transcription_pipeline.module.service_account.google_project_iam_member.service_account_roles["roles/run.invoker"]
}

moved {
  from = google_project_iam_member.storage_admin
  to   = module.transcription_pipeline.module.service_account.google_project_iam_member.service_account_roles["roles/storage.admin"]
}

# Secrets moves
moved {
  from = google_secret_manager_secret.dropbox_token
  to   = module.transcription_pipeline.google_secret_manager_secret.dropbox_token
}

moved {
  from = google_secret_manager_secret_version.dropbox_token
  to   = module.transcription_pipeline.google_secret_manager_secret_version.dropbox_token
}

moved {
  from = google_secret_manager_secret.dropbox_secret
  to   = module.transcription_pipeline.google_secret_manager_secret.dropbox_secret
}

moved {
  from = google_secret_manager_secret_version.dropbox_secret
  to   = module.transcription_pipeline.google_secret_manager_secret_version.dropbox_secret
}

moved {
  from = google_secret_manager_secret.gmail_credentials
  to   = module.transcription_pipeline.google_secret_manager_secret.gmail_credentials
}

moved {
  from = google_secret_manager_secret_version.gmail_credentials
  to   = module.transcription_pipeline.google_secret_manager_secret_version.gmail_credentials
}

moved {
  from = google_secret_manager_secret.openai_key
  to   = module.transcription_pipeline.google_secret_manager_secret.openai_key
}

# Cloud Run moves
moved {
  from = google_cloud_run_v2_job.transcription_processor
  to   = module.transcription_pipeline.module.transcription_worker.google_cloud_run_v2_job.job
}

# Cloud Function moves
moved {
  from = data.archive_file.webhook_source
  to   = module.transcription_pipeline.module.webhook_handler.data.archive_file.function_source
}

moved {
  from = google_storage_bucket.webhook_source
  to   = module.transcription_pipeline.module.webhook_handler.google_storage_bucket.function_source
}

moved {
  from = google_storage_bucket_object.webhook_source
  to   = module.transcription_pipeline.module.webhook_handler.google_storage_bucket_object.function_source
}

moved {
  from = google_cloudfunctions2_function.webhook_handler
  to   = module.transcription_pipeline.module.webhook_handler.google_cloudfunctions2_function.function
}

moved {
  from = google_cloudfunctions2_function_iam_member.webhook_public_access
  to   = module.transcription_pipeline.module.webhook_handler.google_cloudfunctions2_function_iam_member.public_access[0]
}

# API Services moves
moved {
  from = google_project_service.required_apis["run.googleapis.com"]
  to   = module.transcription_pipeline.google_project_service.required_apis["run.googleapis.com"]
}

moved {
  from = google_project_service.required_apis["secretmanager.googleapis.com"]
  to   = module.transcription_pipeline.google_project_service.required_apis["secretmanager.googleapis.com"]
}

moved {
  from = google_project_service.required_apis["cloudbuild.googleapis.com"]
  to   = module.transcription_pipeline.google_project_service.required_apis["cloudbuild.googleapis.com"]
}

moved {
  from = google_project_service.required_apis["cloudfunctions.googleapis.com"]
  to   = module.transcription_pipeline.google_project_service.required_apis["cloudfunctions.googleapis.com"]
}

moved {
  from = google_project_service.required_apis["storage.googleapis.com"]
  to   = module.transcription_pipeline.google_project_service.required_apis["storage.googleapis.com"]
}