# Cloud Run service for the React frontend: nginx serving the built files.
#
# The image holds only public values (API address, Supabase URL and
# publishable key), baked in at build time. No secrets, so the frontend
# service account has no permissions at all.
#
# Low-cost demo settings: scales to zero when idle, at most one instance.

resource "google_cloud_run_v2_service" "frontend" {
  project  = var.project_id
  location = var.region
  name     = local.frontend_service_name # defined in backend_service.tf

  ingress = "INGRESS_TRAFFIC_ALL"

  # A temporary demo: allow "terraform destroy" to remove the service.
  deletion_protection = false

  template {
    # Its own identity with no roles: nginx needs no Google access.
    service_account = google_service_account.frontend.email

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      image = "${local.registry_url}/frontend:${var.frontend_image_tag}"

      # frontend/nginx.conf listens on port 80.
      ports {
        container_port = 80
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "256Mi" # nginx used about 11 MiB in Docker
        }
        # CPU only while a request is being handled (pay per request).
        cpu_idle = true
      }
    }
  }

  # After the first deployment, GitHub Actions owns the image (deploy.yml).
  # Terraform never resets it to frontend_image_tag (no accidental rollback).
  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
      client,
      client_version,
    ]
  }

  depends_on = [google_project_service.enabled["run.googleapis.com"]]
}

# Anyone may open the website. Login happens in the app (Supabase).
resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  project  = google_cloud_run_v2_service.frontend.project
  location = google_cloud_run_v2_service.frontend.location
  name     = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "frontend_url" {
  description = "Public address of the website. Also allowed in the backend's CORS_ORIGINS."
  value       = local.frontend_url
}
