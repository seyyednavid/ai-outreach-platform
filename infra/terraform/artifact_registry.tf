# A private Docker image repository in London. GitHub Actions (later)
# pushes the backend image here, and Cloud Run pulls it from here.
# Image address:
#   europe-west2-docker.pkg.dev/<project_id>/ai-outreach/<image>:<tag>

resource "google_artifact_registry_repository" "docker" {
  project       = var.project_id
  location      = var.region
  repository_id = "ai-outreach"
  description   = "Docker images for the AI Outreach Platform"
  format        = "DOCKER"

  # The API must be on before the repository can be created. Terraform
  # cannot see that link by itself, so it is stated here.
  depends_on = [google_project_service.enabled["artifactregistry.googleapis.com"]]
}

output "artifact_registry_url" {
  description = "Prefix for image names pushed to this repository."
  value       = "${google_artifact_registry_repository.docker.location}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}"
}
