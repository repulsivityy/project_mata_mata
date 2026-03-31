# ===================================================================================
# CLOUD RUN V2 SERVICES
# Note: Initial deployments use a placeholder image. Real images injected by Cloud Build.
# ===================================================================================

# 1. BACKEND SERVICE
resource "google_cloud_run_v2_service" "backend" {
  name     = "mata-backend"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      max_instance_count = 10
      min_instance_count = 0
    }
    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello:latest"
      resources {
        limits = {
          memory = "2Gi"
        }
      }
      env {
        name = "VIRUSTOTAL_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.virustotal_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "WEBRISK_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.webrisk_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "GEMINI_APIKEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].containers[0].image]
  }
}

# 2. FRONTEND SERVICE
resource "google_cloud_run_v2_service" "frontend" {
  name     = "mata-frontend"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      max_instance_count = 10
    }
    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello:latest"
      env {
        name  = "NEXT_PUBLIC_API_URL"
        value = "${google_cloud_run_v2_service.backend.uri}/api/v1/scan"
      }
      env {
        name = "MATA_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.mata_api_key.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].containers[0].image]
  }
}

# 3. TELEGRAM BOT SERVICE
resource "google_cloud_run_v2_service" "bot" {
  name     = "mata-telegram-bot"
  location = var.region

  template {
    scaling {
      max_instance_count = 2
      # Required for Long Polling to survive
      min_instance_count = 1
    }
    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello:latest"
      env {
        name = "TELEGRAM_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.telegram_token.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "MATA_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.mata_api_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name  = "API_BACKEND_URL"
        value = "${google_cloud_run_v2_service.backend.uri}/api/v1/scan"
      }
      env {
        name  = "DEBUG_MODE"
        value = "true"
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].containers[0].image]
  }
}

# ===================================================================================
# IAM (Make Frontend and Backend Publicly Accessible)
# Note: Bot should remain private (no unauthenticated access)
# ===================================================================================

resource "google_cloud_run_service_iam_member" "public_backend" {
  location = google_cloud_run_v2_service.backend.location
  service  = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "public_frontend" {
  location = google_cloud_run_v2_service.frontend.location
  service  = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
