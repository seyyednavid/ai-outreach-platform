# Inputs for this configuration. Values go in terraform.tfvars
# (git-ignored). terraform.tfvars.example shows the expected format.

variable "project_id" {
  description = "Google Cloud project ID to deploy into."
  type        = string
  # No default on purpose: Terraform must never fall back to a project
  # by accident. Set it in terraform.tfvars.
}

variable "region" {
  description = "Google Cloud region for all resources (europe-west2 = London)."
  type        = string
  default     = "europe-west2"
}

variable "backend_image_tag" {
  description = "Backend image tag used when the service and job are first created. Later images are deployed by GitHub Actions (deploy.yml); Terraform ignores image changes."
  type        = string
  # No default: the first deployment names the exact image it uses.
}

variable "project_number" {
  description = "Project number (gcloud projects describe <project_id> --format='value(projectNumber)'). Cloud Run URLs are built from it."
  type        = string
}

# Backend settings that are NOT secret. Secrets come from Secret Manager.

variable "google_client_id" {
  description = "OAuth client ID for Gmail (public: it appears in the Google consent URL)."
  type        = string
}

variable "supabase_url" {
  description = "Supabase project URL, e.g. https://<ref>.supabase.co. Login tokens are checked against its public keys."
  type        = string
}

variable "admin_emails" {
  description = "Product owners who can open the Usage page, comma-separated."
  type        = string
  default     = ""
}

variable "frontend_image_tag" {
  description = "Frontend image tag used when the service is first created. Later images are deployed by GitHub Actions (deploy.yml); Terraform ignores image changes."
  type        = string
  # No default: the first deployment names the exact image it uses.
}

# GitHub repository allowed to deploy (github_actions.tf). The numeric IDs
# never change, even if the repository or account is renamed:
#   gh api repos/OWNER/REPO --jq '.id, .owner.id'

variable "github_repository" {
  description = "GitHub repository that deploys, as owner/name."
  type        = string
}

variable "github_repository_id" {
  description = "Numeric ID of that repository."
  type        = string
}

variable "github_owner_id" {
  description = "Numeric ID of the repository's owner (user or organisation)."
  type        = string
}
