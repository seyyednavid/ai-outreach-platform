# Cloud Run Job: runs the database migrations ("alembic upgrade head")
# once, then stops. Same image as the backend, different command, just
# like the "migrate" service in compose.yaml.
#
# Creating or updating the Job does NOT run it. It runs only when started
# by hand:
#   gcloud run jobs execute ai-outreach-migrate --region europe-west2 --wait

resource "google_cloud_run_v2_job" "migrate" {
  project  = var.project_id
  location = var.region
  name     = "ai-outreach-migrate"

  # A temporary demo: allow "terraform destroy" to remove the Job.
  deletion_protection = false

  template {
    # One run = one task. Two migrations at the same time could clash.
    task_count  = 1
    parallelism = 1

    template {
      # The backend identity: it can read the backend secrets, nothing else.
      service_account = google_service_account.backend.email

      # Never retry automatically: a failed migration needs a person to
      # look at the logs. Postgres rolls a failed migration back.
      max_retries = 0

      # Migrations take seconds; 10 minutes is a generous upper limit.
      timeout = "600s"

      containers {
        image = "${local.registry_url}/backend:${var.backend_image_tag}"

        # Replaces the image's default command (uvicorn).
        command = ["alembic"]
        args    = ["upgrade", "head"]

        # The only real secret the migration needs. "latest" = the newest
        # enabled version, so a new password needs no Terraform change.
        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.backend["database-url"].secret_id
              version = "latest"
            }
          }
        }

        # The app's settings refuse to start without these, but migrations
        # never use them. Placeholders, so the Job never sees the real
        # OpenAI key or Google client secret (least privilege).
        env {
          name  = "OPENAI_API_KEY"
          value = "not-used-by-migrations"
        }
        env {
          name  = "GOOGLE_CLIENT_ID"
          value = "not-used-by-migrations"
        }
        env {
          name  = "GOOGLE_CLIENT_SECRET"
          value = "not-used-by-migrations"
        }
        env {
          name  = "GOOGLE_REDIRECT_URI"
          value = "not-used-by-migrations"
        }

        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }
      }
    }
  }

  # The Job's identity must be able to read the secret before it exists.
  depends_on = [
    google_project_service.enabled["run.googleapis.com"],
    google_secret_manager_secret_iam_member.backend_reads["database-url"],
  ]
}

output "migrate_job_name" {
  value = google_cloud_run_v2_job.migrate.name
}
