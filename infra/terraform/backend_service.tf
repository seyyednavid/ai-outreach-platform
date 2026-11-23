# Cloud Run service for the FastAPI backend.
#
# Public on purpose: the browser calls the API directly, so Google must
# let every request through. The app itself checks the Supabase login
# token on every route except /health, /health/ready and the Gmail
# callback (protected by a one-time state value and PKCE).
#
# Low-cost demo settings: scales to zero when idle (no traffic = no cost)
# and never runs more than one instance.

locals {
  backend_service_name  = "ai-outreach-backend"
  frontend_service_name = "ai-outreach-frontend" # created in a later step

  # Cloud Run addresses are predictable: https://<service>-<project number>.<region>.run.app
  # Knowing them in advance avoids a chicken-and-egg problem: the backend
  # needs its own URL (Gmail callback) and the frontend's URL (CORS).
  backend_url  = "https://${local.backend_service_name}-${var.project_number}.${var.region}.run.app"
  frontend_url = "https://${local.frontend_service_name}-${var.project_number}.${var.region}.run.app"

  # Settings that are not secret: stored as plain environment variables.
  backend_plain_env = {
    GOOGLE_CLIENT_ID    = var.google_client_id
    GOOGLE_REDIRECT_URI = "${local.backend_url}/api/v1/gmail/callback"
    SUPABASE_URL        = var.supabase_url
    CORS_ORIGINS        = local.frontend_url
    ADMIN_EMAILS        = var.admin_emails

    # Traces keep timing and structure, but never prompts or outputs
    # (email text, names of real people).
    TRACE_INCLUDE_SENSITIVE_DATA = "false"

    # Uvicorn ignores X-Forwarded-Proto unless it trusts the sender. Only
    # Google's front end can reach the container, so trust it: redirects
    # then keep https instead of switching to http.
    FORWARDED_ALLOW_IPS = "*"
  }

  # Secrets: environment variable -> Secret Manager secret. Cloud Run reads
  # the value when an instance starts. Terraform never sees it.
  backend_secret_env = {
    DATABASE_URL         = "database-url"
    OPENAI_API_KEY       = "openai-api-key"
    GOOGLE_CLIENT_SECRET = "google-client-secret"
    TOKEN_ENCRYPTION_KEY = "token-encryption-key"
  }
}

resource "google_cloud_run_v2_service" "backend" {
  project  = var.project_id
  location = var.region
  name     = local.backend_service_name

  # Reachable from the internet (the browser calls it directly).
  ingress = "INGRESS_TRAFFIC_ALL"

  # A temporary demo: allow "terraform destroy" to remove the service.
  deletion_protection = false

  template {
    service_account = google_service_account.backend.email

    scaling {
      # 0 = no instance (and no cost) while nobody uses the app.
      min_instance_count = 0
      # 1 = cost ceiling. Also required by the app: Gmail sign-in keeps a
      # short-lived value in memory, which a second instance would not see.
      max_instance_count = 1
    }

    # An outreach run calls several AI agents (with web search) inside one
    # request. 10 minutes is a generous upper limit (default: 5).
    timeout = "600s"

    containers {
      image = "${local.registry_url}/backend:${var.backend_image_tag}"

      # The image's default command runs uvicorn on port 8000.
      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi" # measured about 180 MiB in Docker; room for agent runs
        }
        # CPU only while a request is being handled (pay per request).
        cpu_idle = true
        # Extra CPU while starting, so the first request after idle is faster.
        startup_cpu_boost = true
      }

      dynamic "env" {
        for_each = local.backend_plain_env
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = local.backend_secret_env
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.backend[env.value].secret_id
              version = "latest"
            }
          }
        }
      }

      # Traffic is sent only after this answers. It does not touch the
      # database, so a slow database cannot block a deployment.
      startup_probe {
        http_get {
          path = "/api/v1/health"
          port = 8000
        }
        period_seconds    = 5
        timeout_seconds   = 3
        failure_threshold = 12 # up to 60 s to start
      }
    }
  }

  depends_on = [
    google_project_service.enabled["run.googleapis.com"],
    # The service account must be able to read every secret before the
    # first instance starts.
    google_secret_manager_secret_iam_member.backend_reads,
  ]
}

# Anyone may send requests to the backend. Logging in is enforced by the
# app (Supabase token check), not by Google.
resource "google_cloud_run_v2_service_iam_member" "backend_public" {
  project  = google_cloud_run_v2_service.backend.project
  location = google_cloud_run_v2_service.backend.location
  name     = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "backend_url" {
  description = "Public address of the backend API."
  value       = local.backend_url
}

output "gmail_redirect_uri" {
  description = "Add this to the OAuth client's Authorized redirect URIs in Google Cloud Console."
  value       = local.backend_plain_env.GOOGLE_REDIRECT_URI
}
