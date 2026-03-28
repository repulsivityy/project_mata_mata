#!/bin/bash
set -e

# ==============================================================================
# PROJECT MATA-MATA - GCP CLOUD RUN DEPLOYMENT SCRIPT (UNAUTHENTICATED TESTING)
# ==============================================================================

# 1. Ensure user is authenticated and project is set
PROJECT_ID=$(gcloud config get-value project)
REGION="asia-southeast1" # Defaulting to Singapore, change if needed

echo "🚀 Deploying to GCP Project: $PROJECT_ID in Region: $REGION"
echo "-----------------------------------------------------------------"

# Make sure env vars are exported or read from .env if present
if [ -f ".env" ]; then
    echo "📄 Loading variables from .env file..."
    export $(cat .env | xargs)
else
    echo "⚠️ Warning: No .env file found. Make sure environment variables are exported!"
fi

echo "-----------------------------------------------------------------"
echo "🔐 Step 0: Syncing Local Variables to Google Secret Manager"
echo "-----------------------------------------------------------------"

push_secret() {
  local ENV_VAR_NAME=$1
  local SECRET_NAME=$2
  local SECRET_VALUE="${!ENV_VAR_NAME}"

  if [ -z "$SECRET_VALUE" ]; then
    echo "⚠️ Warning: $ENV_VAR_NAME is empty or not set. Skipping push for $SECRET_NAME."
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

# Ensure the Cloud Run (Compute Engine default service account) has access to read these secrets
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo "🔐 Assigning Secret Accessor role to $COMPUTE_SA..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${COMPUTE_SA}" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None >/dev/null 2>&1 || true

echo "✅ Secrets synced globally."
echo "-----------------------------------------------------------------"

# ==========================================
# 1. DEPLOY BACKEND (FastAPI + Playwright)
# ==========================================
echo "📦 1/3 Deploying Backend..."
# Cloud Run needs the 'Secret Manager Secret Accessor' role given to the Compute Service Account
gcloud run deploy mata-backend \
  --source ./backend \
  --region $REGION \
  --allow-unauthenticated \
  --memory 2Gi \
  --set-secrets="VIRUSTOTAL_API_KEY=MATA_VIRUSTOTAL_API_KEY:latest,WEBRISK_API_KEY=MATA_WEBRISK_API_KEY:latest,GEMINI_APIKEY=MATA_GEMINI_APIKEY:latest" \
  --format 'value(status.url)' > .backend_url.tmp

BACKEND_URL=$(cat .backend_url.tmp)
rm .backend_url.tmp
echo "✅ Backend deployed at: $BACKEND_URL"

# ==========================================
# 2. DEPLOY WEB FRONTEND (Next.js)
# ==========================================
echo "📦 2/3 Deploying Web Frontend..."
gcloud run deploy mata-frontend \
  --source ./clients/web_frontend \
  --region $REGION \
  --allow-unauthenticated \
  --set-build-env-vars NEXT_PUBLIC_API_URL="${BACKEND_URL}/api/v1/scan" \
  --set-env-vars NEXT_PUBLIC_API_URL="${BACKEND_URL}/api/v1/scan"

echo "✅ Web Frontend deployment complete."

# ==========================================
# 3. DEPLOY TELEGRAM BOT (Long Polling)
# ==========================================
echo "📦 3/3 Deploying Telegram Bot..."
gcloud run deploy mata-telegram-bot \
  --source ./clients/telegram_bot \
  --region $REGION \
  --no-allow-unauthenticated \
  --no-cpu-throttling \
  --min-instances 1 \
  --set-secrets="TELEGRAM_TOKEN=MATA_TELEGRAM_TOKEN:latest" \
  --set-env-vars API_BACKEND_URL="${BACKEND_URL}/api/v1/scan",DEBUG_MODE="true"

echo "🎉 All services deployed successfully!"
