# ===================================================================================
# CLOUD BUILD TRIGGERS (GITHUB 2ND GEN CONTINUOUS INTEGRATION)
# Located in var.region against connection "repulsivityy"
# ===================================================================================

# 1. BACKEND TRIGGER
resource "google_cloudbuild_trigger" "backend_trigger" {
  name        = "mata-backend-ci"
  description = "Builds and deploys the FastAPI backend on push to main"
  location    = var.region

  repository_event_config {
    repository = "projects/${var.project_id}/locations/${var.region}/connections/repulsivityy/repositories/${var.github_owner}-${var.github_repo}"
    push {
      branch = "^main$"
    }
  }

  included_files = ["backend/**"]
  filename       = "backend/cloudbuild.yaml"
}

# 2. FRONTEND TRIGGER
resource "google_cloudbuild_trigger" "frontend_trigger" {
  name        = "mata-frontend-ci"
  description = "Builds and deploys the Next.js frontend on push to main"
  location    = var.region

  repository_event_config {
    repository = "projects/${var.project_id}/locations/${var.region}/connections/repulsivityy/repositories/${var.github_owner}-${var.github_repo}"
    push {
      branch = "^main$"
    }
  }

  included_files = ["clients/web_frontend/**"]
  filename       = "clients/web_frontend/cloudbuild.yaml"
}

# 3. TELEGRAM BOT TRIGGER
resource "google_cloudbuild_trigger" "bot_trigger" {
  name        = "mata-telegram-bot-ci"
  description = "Builds and deploys the Python bot on push to main"
  location    = var.region

  repository_event_config {
    repository = "projects/${var.project_id}/locations/${var.region}/connections/repulsivityy/repositories/${var.github_owner}-${var.github_repo}"
    push {
      branch = "^main$"
    }
  }

  included_files = ["clients/telegram_bot/**"]
  filename       = "clients/telegram_bot/cloudbuild.yaml"
}
