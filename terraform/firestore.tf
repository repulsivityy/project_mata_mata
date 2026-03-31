# Firestore database already exists in the project (default). 
# We only need to manage the IAM permissions below.

# Grant the background app read/write access to Firestore
# Note: Cloud Run uses the default Compute Engine service account if no service_account is specified.
resource "google_project_iam_member" "backend_firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"
}
