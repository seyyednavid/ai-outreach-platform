# GitHub Actions deployment identity, with no service-account JSON key.
#
# How a deployment logs in (Workload Identity Federation):
#   1. GitHub gives the workflow a short-lived signed token (OIDC) that
#      says which repository, branch and environment it runs for.
#   2. Google checks the signature and the conditions below, then swaps
#      it for a Google token of the deployer account, valid for 1 hour.
# Nothing long-lived is stored in GitHub, so there is no key to leak.
#
# Three locks, all must pass:
#   - provider condition: our repository (by numeric ID, which survives
#     renames and cannot be taken over) and the main branch only
#   - IAM binding: only jobs in the GitHub environment "production"
#   - GitHub side: the "production" environment only allows main

locals {
  github_environment = "production"

  # GitHub's OIDC "sub" claim for a job that uses that environment. This
  # repository uses GitHub's immutable subject format, which adds the
  # numeric IDs to the names:
  #   repo:OWNER@OWNER_ID/REPO@REPO_ID:environment:production
  # Check with: gh api repos/OWNER/REPO/actions/oidc/customization/sub
  # (sub_claim_prefix). The IAM binding must match it exactly.
  github_owner_name = split("/", var.github_repository)[0]
  github_repo_name  = split("/", var.github_repository)[1]
  github_subject    = "repo:${local.github_owner_name}@${var.github_owner_id}/${local.github_repo_name}@${var.github_repository_id}:environment:${local.github_environment}"
}

resource "google_iam_workload_identity_pool" "github" {
  project                   = var.project_id
  workload_identity_pool_id = "github"
  display_name              = "GitHub Actions"
  description               = "Identities from GitHub Actions workflows."

  depends_on = [google_project_service.enabled["iam.googleapis.com"]]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "ai-outreach-platform"
  display_name                       = "ai-outreach-platform repo"
  description                        = "GitHub OIDC tokens from one repository, main branch only."

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }

  # Claims from GitHub's token that Google keeps (for IAM and audit logs).
  attribute_mapping = {
    "google.subject"                = "assertion.sub"
    "attribute.repository"          = "assertion.repository"
    "attribute.repository_id"       = "assertion.repository_id"
    "attribute.repository_owner_id" = "assertion.repository_owner_id"
    "attribute.ref"                 = "assertion.ref"
    "attribute.environment"         = "assertion.environment"
  }

  # Tokens from any other repository or branch are rejected outright.
  attribute_condition = join(" && ", [
    "assertion.repository_id == '${var.github_repository_id}'",
    "assertion.repository_owner_id == '${var.github_owner_id}'",
    "assertion.ref == 'refs/heads/main'",
  ])
}

# The account GitHub Actions acts as. It can push images and roll out
# new revisions, nothing else: no secrets, no IAM changes, no deletes.
resource "google_service_account" "deployer" {
  project      = var.project_id
  account_id   = "ai-outreach-deployer"
  display_name = "AI Outreach deployer (GitHub Actions)"
  description  = "Pushes images and deploys new Cloud Run revisions. Used only through Workload Identity Federation."

  depends_on = [google_project_service.enabled["iam.googleapis.com"]]
}

# Only the "production" environment of our repository may act as the deployer.
resource "google_service_account_iam_member" "deployer_github" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principal://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/subject/${local.github_subject}"
}

# Push images to this one repository (not to any other in the project).
resource "google_artifact_registry_repository_iam_member" "deployer_push" {
  project    = var.project_id
  location   = google_artifact_registry_repository.docker.location
  repository = google_artifact_registry_repository.docker.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.deployer.email}"
}

# Update these two services only. roles/run.developer can change a
# service's image but not its IAM policy (who may call it).
resource "google_cloud_run_v2_service_iam_member" "deployer_backend" {
  project  = google_cloud_run_v2_service.backend.project
  location = google_cloud_run_v2_service.backend.location
  name     = google_cloud_run_v2_service.backend.name
  role     = "roles/run.developer"
  member   = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_cloud_run_v2_service_iam_member" "deployer_frontend" {
  project  = google_cloud_run_v2_service.frontend.project
  location = google_cloud_run_v2_service.frontend.location
  name     = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.developer"
  member   = "serviceAccount:${google_service_account.deployer.email}"
}

# Point the migration job at the new image. The workflow never runs it:
# migrations stay a manual step (gcloud run jobs execute ...).
resource "google_cloud_run_v2_job_iam_member" "deployer_migrate" {
  project  = google_cloud_run_v2_job.migrate.project
  location = google_cloud_run_v2_job.migrate.location
  name     = google_cloud_run_v2_job.migrate.name
  role     = "roles/run.developer"
  member   = "serviceAccount:${google_service_account.deployer.email}"
}

# A new revision runs as the service's own account, so the deployer must
# be allowed to "act as" it. It does not receive that account's
# permissions (secrets) itself.
resource "google_service_account_iam_member" "deployer_acts_as_backend" {
  service_account_id = google_service_account.backend.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_service_account_iam_member" "deployer_acts_as_frontend" {
  service_account_id = google_service_account.frontend.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deployer.email}"
}

# Values for the GitHub environment "production" (not secret).
output "github_workload_identity_provider" {
  description = "GitHub variable GCP_WORKLOAD_IDENTITY_PROVIDER."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "github_deployer_service_account" {
  description = "GitHub variable GCP_DEPLOY_SERVICE_ACCOUNT."
  value       = google_service_account.deployer.email
}
