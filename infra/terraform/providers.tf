# Which Terraform and which provider (plugin) this configuration needs,
# and how that provider connects to Google Cloud.

terraform {
  # The version installed locally is 1.17.2. Anything from 1.9 on works.
  required_version = ">= 1.9"

  required_providers {
    google = {
      source = "hashicorp/google"
      # "~> 7.0" = any 7.x release, but never 8.0, so a future major
      # version with breaking changes is not picked up by surprise.
      version = "~> 7.0"
    }
  }

  # State: for now Terraform keeps its record of what it created in a
  # local file (terraform.tfstate, git-ignored). A later step can move
  # it to a Cloud Storage bucket so GitHub Actions can use it too.
}

# No credentials here. With no "credentials" setting, the provider uses
# Application Default Credentials: locally, the login made with
#   gcloud auth application-default login
# In GitHub Actions it will use Workload Identity Federation instead.
provider "google" {
  project = var.project_id
  region  = var.region
}
