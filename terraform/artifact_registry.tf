resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = local.ar_repo_name
  description   = "Docker repository for Project Mata-Mata Cloud Run containers"
  format        = "DOCKER"
}
