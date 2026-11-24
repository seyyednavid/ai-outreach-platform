# Google Cloud APIs this project needs. A new project has most APIs
# switched off; a resource such as an Artifact Registry repository can
# only be created after its API is switched on.
#
# One resource block, repeated for each API with for_each. Terraform
# names them google_project_service.enabled["run.googleapis.com"], etc.

locals {
  required_apis = [
    "run.googleapis.com",              # Cloud Run: runs the backend container
    "artifactregistry.googleapis.com", # Artifact Registry: stores Docker images
    "secretmanager.googleapis.com",    # Secret Manager: holds API keys and passwords
    "iam.googleapis.com",              # IAM: needed to create service accounts
    "sts.googleapis.com",              # Security Token Service: swaps GitHub's token for a Google one
    "iamcredentials.googleapis.com",   # IAM Credentials: short-lived tokens for the deployer account
    "monitoring.googleapis.com",       # Cloud Monitoring: uptime check and alerts (on by default)
  ]
}

resource "google_project_service" "enabled" {
  for_each = toset(local.required_apis)

  project = var.project_id
  service = each.value

  # On "terraform destroy", leave the API switched on. Switching an API
  # off can break other things in the project, and it is free to keep on.
  disable_on_destroy = false
}
