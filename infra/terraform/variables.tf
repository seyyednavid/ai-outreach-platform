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
