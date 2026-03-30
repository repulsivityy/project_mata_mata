# Define the 4 Core API Key Secrets (Values must be populated manually or via gcloud to keep state clean)

resource "google_secret_manager_secret" "virustotal_key" {
  secret_id = "MATA_VIRUSTOTAL_API_KEY"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "webrisk_key" {
  secret_id = "MATA_WEBRISK_API_KEY"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "gemini_key" {
  secret_id = "MATA_GEMINI_APIKEY"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret" "telegram_token" {
  secret_id = "MATA_TELEGRAM_TOKEN"
  replication {
    auto {}
  }
}
resource "google_secret_manager_secret" "mata_api_key" {
  secret_id = "MATA_API_KEY"
  replication {
    auto {}
  }
}

# The default Compute Engine service account used by Cloud Run
locals {
  compute_sa = "${data.google_project.project.number}-compute@developer.gserviceaccount.com"
}

# Grant the Cloud Run instances permission to read Secret values
resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${local.compute_sa}"
}
