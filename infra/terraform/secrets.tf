# Secret Manager: the backend's secrets. Terraform creates only the
# empty "boxes". The values (versions) are added by hand with gcloud,
# so they never appear in Terraform files or in terraform.tfstate.

locals {
  backend_secrets = [
    "openai-api-key",       # OPENAI_API_KEY
    "google-client-secret", # GOOGLE_CLIENT_SECRET (Gmail OAuth)
    "database-url",         # DATABASE_URL (Supabase session pooler, with password)
    "token-encryption-key", # TOKEN_ENCRYPTION_KEY (encrypts Gmail tokens)
  ]
}

resource "google_secret_manager_secret" "backend" {
  for_each = toset(local.backend_secrets)

  project   = var.project_id
  secret_id = each.value

  # Store the values in London only (UK data residency).
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  depends_on = [google_project_service.enabled["secretmanager.googleapis.com"]]
}

# Least privilege: the backend may read these four secrets, and only
# these. The role is granted on each secret, not on the whole project,
# so a secret added later is not readable unless it is granted here.
# The frontend account gets nothing.
resource "google_secret_manager_secret_iam_member" "backend_reads" {
  for_each = google_secret_manager_secret.backend

  project   = var.project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend.email}"
}

output "secret_ids" {
  description = "Secrets that need a value: gcloud secrets versions add <id> --data-file=<file>"
  value       = [for secret in google_secret_manager_secret.backend : secret.secret_id]
}
