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
  description = "Tag of the backend image in Artifact Registry (the Git commit it was built from)."
  type        = string
  # No default: every deployment names the exact image it uses.
}
