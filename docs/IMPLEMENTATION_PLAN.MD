# Project Mata-Mata Migration Roadmap

Instead of refactoring the old `telegram_url_checker` monolithic platform in place, this document outlines the roadmap to building a brand new micro-service monorepo: `project_mata_mata`. This allows deploying a modern, clean architecture. Once the new platform is stable, the old repository is completely retired.

## Phase 1: Initialize the New Repository (COMPLETED)
1. **Directory Tree Framework**: `project_mata_mata` root, separated cleanly into `backend/core/`, `backend/api/`, `clients/telegram_bot/` and `clients/web_frontend/`.
2. **Logic Extraction**: Extract the raw class processors representing `URLExtractor`, `VirusTotalChecker`, `WebRiskChecker` & `GTI` into individual modules within `backend/core`.
3. **Migration of AI Brain**: Import the highly tuned `ai_phishing_detector.py` directly.

## Phase 2: Build the FastAPI Backend API layer (COMPLETED)
1. Write `backend/core/orchestrator.py` functioning as the main API coordinator, instantiating `BaseChecker` child scripts synchronously and asynchronously.
2. Form a functional `POST /api/v1/scan` endpoint inside `main.py` allowing clients to query any URL string.
3. Validate robust JSON response structures.

## Phase 3: Build the Lightweight Telegram Client (COMPLETED)
1. Set up `clients/telegram_bot/bot.py`.
2. Load it securely with the new production `TELEGRAM_TOKEN`.
3. Update it to use asynchronous polling to support the new Firestore queue, enabling live updates tracking partial results. Add standard HTTP dummy server on `$PORT` to prevent serverless deployment closures on Cloud Run.

## Phase 4: Build the Web Frontend Platform (COMPLETED)
1. Create a modern web interface in `clients/web_frontend/` using Next.js and React.
2. Architect a Neo-Brutalist Threat Intelligence Dashboard featuring verdict banners, scanner breakdown cards, and expandable GTI URL screenshot modals.
3. Route browser requests through a server-side Next.js BFF proxy (`/api/scan`) to keep `MATA_API_KEY` off the client.

## Phase 5: Containerization & Cloud-Native Deployment (COMPLETED)
1. Build `Dockerfile` configurations specifically optimizing for the installation of heavy system dependencies like `playwright` binaries within the `backend/`.
2. Supply a root `docker-compose.yml` defining the API Backend, Telegram Client, and NextJS UI running as native services side-by-side.
3. Provision automated CI/CD and serverless infrastructure via **Terraform**, **Cloud Build**, and **Google Cloud Run**.

## Phase 6: Async Polling & Firestore Caching (COMPLETED)
1. Transition API from blocking requests to job-based background workers to resolve mobile browser timeouts.
2. Integrate **Google Cloud Firestore** to cache results by computing a SHA-256 hash on input URLs.
3. Hook React `useEffect` loops to poll endpoints checking status properties before releasing final state data.
