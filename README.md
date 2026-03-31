# Project Mata-Mata 👁️

**Project Mata-Mata** is an omniscient, multi-agent AI phishing detection ecosystem. Designed as a modernized, decoupled monorepo evolution of the legacy `telegram_url_checker`, it brings deep-evasion threat intelligence directly to Telegram and Web Dashboards.

## Architecture

The platform is strictly decoupled into a powerful unified API and its independent consumers:

```text
project_mata_mata/
├── backend/                  # The FastAPI Brain (Port :8000)
│   ├── api/                  # API Routers mapping endpoints
│   ├── core/                 # Scanners (VT, Web Risk, Gemini) & Orchestrator
│   └── Dockerfile            # Configured natively for Python & Playwright
├── clients/
│   ├── telegram_bot/         # Lightweight bot hitting the FastAPI
│   └── web_frontend/         # Next.js React Threat Dashboard (Port :3000)
├── terraform/                # Infrastructure as Code (including Firestore)
└── docker-compose.yml        # Orchestrates all 3 platforms seamlessly
```

## 🔐 Security & API Authentication

To prevent abuse and protect sensitive threat intelligence keys, Project Mata-Mata implements a strict security layer:
- **HMAC-SHA256 Verification**: The FastAPI backend requires an `X-API-KEY` header on all requests. It verifies the signature using a secure constant-time HMAC-SHA256 hash comparison to protect against timing attacks.
- **Backend-for-Frontend (BFF) Proxy**: The Next.js web dashboard does NOT call the backend directly from the browser. Instead, it hits its own server-side Next.js API route (`/api/scan`), which securely injects the API key from server-side environment variables. This prevents exposing your master keys in client-side network traces!
- **Fail-Hard Resolution**: On startup, the backend attempts to fetch the raw `MATA_API_KEY` from Google Secret Manager. If it is missing or unreachable, the server crashes intentionally on start ("Fail Hard") to avoid running in an unauthenticated exposure state.

## Core Scanners
- **VirusTotal**: Checks raw static community detections and Google Threat Intelligence (GTI) scoring. (Note: Falls back to standard VT scoring if the API key lacks GTI access; requires `x-tool: project-mata-mata` header for tracking).
- **Google Web Risk**: Evaluates domains against global blacklists.
- **Gemini 2.5 Multi-Modal Agent**: Renders Chromium headless instances behind Cloudflare shields to analyze visual DOM spoofing, inline hidden scripts, and exfiltrated background network POSTs.

## 🔄 Job Polling & Caching
- **Firestore Integration**: Results are cached in Google Cloud Firestore (`mata_mata_scans`), keyed by the SHA-256 hash of the URL. Identical scans share results and save API quota!
- **Mobile URL Persistence**: Background tasks and polling allow mobile users to resume active scans even after browser suspensions or locks.

## ⚖️ Final Verdict Scoring

The engine uses a compound priority logic that requires corroboration for high-severity flags:
- **🔴 DANGER**: Requires both a Core Intel hit (GTI/Web Risk) **AND** a Verification hit (AI High or VT detections > 5).
- **🟢 SAFE**: Requires a clean indicator (GTI Benign or Web Risk Safe) **AND** exactly `0` detections.
- **🟡 WARNING**: The fallback state for any link failing both tests above.

## How To Run Locally (Docker)

To test Project Mata-Mata on any local VM, simply populate your private API keys in a `.env` file at the root:

```env
TELEGRAM_TOKEN=your_bot_token_here
VIRUSTOTAL_API_KEY=your_vt_key
WEBRISK_API_KEY=your_webrisk_key
GEMINI_APIKEY=your_gemini_key
MATA_API_KEY=your_internal_secret_key
DEBUG_MODE=false
```

Then, execute Docker Compose to automatically build the Playwright backend, boot the Telegram agent, and compile the Next.js React Web portal:

```bash
docker-compose up --build -d
```

- **Threat Dashboard**: `http://localhost:3000`
- **FastAPI Specs**: `http://localhost:8000/docs`
- **Telegram Bot**: Operates silently in the background, listening to chat payloads.

## 🚀 Production Deployment (Terraform + Cloud Build)

Project Mata-Mata is configured for modern, automated deployments using **Terraform (Infrastructure-as-Code)** and **Google Cloud Build (CI/CD)**.

### Automated CI/CD Workflow (Git Push)
The repository uses Google Cloud Build 2nd Gen Triggers. The moment you push to the `main` branch, GCP intercepts the change and hot-swaps the container:
1. **Intercepts** folder changes (`backend/`, `clients/*`).
2. **Builds** the Dockerfile.
3. **Pushes** image to Artifact Registry.
4. **Deploys** to Google Cloud Run automatically.

### Running Terraform (One-time Setup)

1. **Push Secrets**: Replicate local `.env` keys securely into GCP Secret Manager:
   ```bash
   chmod +x push_secrets.sh
   ./push_secrets.sh
   ```

2. **Provision Infrastructure**:
   ```bash
   cd terraform
   terraform init
   terraform apply
   ```


## 🩺 Troubleshooting

### 🔑 Authentication and ADC
If Terraform or scripts fail to connect to GCP, ensure your Application Default Credentials (ADC) are active:
```bash
gcloud auth application-default login
```

### 🔥 Firestore Conflicts (Error 409)
If `terraform apply` returns `Error 409: Database already exists. Please use another database_id`, it means your project already has a `(default)` Firestore instance running. 
- **Fix**: Comment out or remove the `google_firestore_database` resource in `firestore.tf`. Let Terraform manage only the IAM permissions (`google_project_iam_member`) for it.

### 🔍 View Database State
To verify if Firestore is active and check its properties:
```bash
gcloud firestore databases list --project=virustotal-lab
```

### 🚢 Track CI/CD Build Logs (Cloud Build)
If you push to GitHub and the site doesn't update, verify your Cloud Run triggers ran successfully:
```bash
gcloud builds list --region=asia-southeast1 --limit=5
```


### Roadmap
- [ ] Implement WHOIS Registration
- [ ] Implement URLScan Results
- [x] Upgrade to Gemini 3.0 Flash
- [ ] Add ability to submit to Webrisk (Enterprise)
- [ ] Link analysis engine to [Project Harimau](https://github.com/repulsivityy/project_harimau)