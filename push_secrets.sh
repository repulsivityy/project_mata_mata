#!/bin/bash
set -e

PROJECT_ID=$(gcloud config get-value project)
echo "🚀 Syncing Secrets to GCP Project: $PROJECT_ID"
echo "-----------------------------------------------------------------"

if [ -f ".env" ]; then
    echo "📄 Loading variables from .env file..."
    export $(cat .env | xargs)
else
    echo "⚠️ Warning: No .env file found. Make sure environment variables are exported!"
    exit 1
fi

push_secret() {
  local ENV_VAR_NAME=$1
  local SECRET_NAME=$2
  local SECRET_VALUE="${!ENV_VAR_NAME}"

  if [ -z "$SECRET_VALUE" ]; then
    echo "⚠️ Warning: $ENV_VAR_NAME is empty. Skipping $SECRET_NAME."
    return
  fi

  # Check if secret exists, create if not
  if ! gcloud secrets describe "$SECRET_NAME" --project "$PROJECT_ID" >/dev/null 2>&1; then
    echo "   ➡️ Creating Secret Manager entity: $SECRET_NAME..."
    gcloud secrets create "$SECRET_NAME" --replication-policy="automatic" --project "$PROJECT_ID" >/dev/null
  fi

  # Add new version
  echo "   ➡️ Pushing new secret version for $SECRET_NAME..."
  echo -n "$SECRET_VALUE" | gcloud secrets versions add "$SECRET_NAME" --data-file=- --project "$PROJECT_ID" >/dev/null
}

push_secret "VIRUSTOTAL_API_KEY" "MATA_VIRUSTOTAL_API_KEY"
push_secret "WEBRISK_API_KEY" "MATA_WEBRISK_API_KEY"
push_secret "GEMINI_APIKEY" "MATA_GEMINI_APIKEY"
push_secret "TELEGRAM_TOKEN" "MATA_TELEGRAM_TOKEN"

echo "✅ Secrets synced successfully!"
