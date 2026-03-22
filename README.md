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
└── docker-compose.yml        # Orchestrates all 3 platforms seamlessly
```

## Core Scanners
- **VirusTotal**: Checks raw static community detections and Google Threat Intelligence.
- **Google Web Risk**: Evaluates domains against global blacklists.
- **Gemini 2.5 Multi-Modal Agent**: Renders Chromium headless instances behind Cloudflare shields to analyze visual DOM spoofing, inline hidden scripts, and exfiltrated background network POSTs.

## How To Run Locally (Docker)

To test Project Mata-Mata on any local VM, simply populate your private API keys in a `.env` file at the root:

```env
TELEGRAM_TOKEN=your_bot_token_here
VIRUSTOTAL_API_KEY=your_vt_key
WEBRISK_API_KEY=your_webrisk_key
GEMINI_APIKEY=your_gemini_key
DEBUG_MODE=false
```

Then, execute Docker Compose to automatically build the Playwright backend, boot the Telegram agent, and compile the Next.js React Web portal:

```bash
docker-compose up --build -d
```

- **Threat Dashboard**: `http://localhost:3000`
- **FastAPI Specs**: `http://localhost:8000/docs`
- **Telegram Bot**: Operates silently in the background, listening to chat payloads.

## Production Deployments
The `backend` and `web_frontend` Dockerfiles are entirely self-contained. You can immediately push the builds into Google Artifact Registry and bind them to **Google Cloud Run** or **GKE**.
