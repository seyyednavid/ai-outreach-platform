# Service accounts: identities for programs, not people. Each Cloud Run
# service runs as its own account, so it only has the permissions we
# give it here. Without them, Cloud Run would use the project's default
# compute account, which has Editor rights on the whole project.
#
# No JSON keys are created: Cloud Run uses these accounts directly.

# Runs the FastAPI backend and the migration job. Its only permission is
# reading the four secrets below (see secrets.tf).
resource "google_service_account" "backend" {
  project      = var.project_id
  account_id   = "ai-outreach-backend"
  display_name = "AI Outreach backend (Cloud Run)"
  description  = "Runs the FastAPI backend and the database migration job."

  depends_on = [google_project_service.enabled["iam.googleapis.com"]]
}

# Runs the nginx frontend. It only serves static files, so it gets no
# permissions at all.
resource "google_service_account" "frontend" {
  project      = var.project_id
  account_id   = "ai-outreach-frontend"
  display_name = "AI Outreach frontend (Cloud Run)"
  description  = "Runs the nginx frontend. Has no permissions."

  depends_on = [google_project_service.enabled["iam.googleapis.com"]]
}

output "backend_service_account_email" {
  value = google_service_account.backend.email
}

output "frontend_service_account_email" {
  value = google_service_account.frontend.email
}
