variable "project_id" {
  type        = string
  description = "The GCP Project ID"
}

variable "region" {
  type        = string
  default     = "asia-southeast1"
  description = "The GCP Region for Cloud Run and Artifact Registry"
}

variable "github_owner" {
  type        = string
  description = "The GitHub username or organization name"
}

variable "github_repo" {
  type        = string
  description = "The GitHub repository name"
}

# Add local definitions for naming consistency
locals {
  ar_repo_name = "mata-repo"
}
