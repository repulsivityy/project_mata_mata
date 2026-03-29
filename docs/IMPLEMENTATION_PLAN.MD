# Project Mata-Mata Migration Roadmap

Instead of refactoring the old `telegram_url_checker` monolithic platform in place, this document outlines the roadmap to building a brand new micro-service monorepo: `project_mata_mata`. This allows deploying a modern, clean architecture. Once the new platform is stable, the old repository is completely retired.

## Phase 1: Initialize the New Repository (COMPLETED)
1. **Directory Tree Framework**: `project_mata_mata` root, separated cleanly into `backend/core/`, `backend/api/`, `clients/telegram_bot/` and `clients/web_frontend/`.
2. **Logic Extraction**: Extract the raw class processors representing `URLExtractor`, `VirusTotalChecker`, `WebRiskChecker` & `GTI` into individual modules within `backend/core`.
3. **Migration of AI Brain**: Import the highly tuned `ai_phishing_detector.py` directly.

## Phase 2: Build the FastAPI Backend API layer (IN PROGRESS)
1. Write `backend/core/orchestrator.py` functioning as the main API coordinator, instantiating `BaseChecker` child scripts synchronously and asynchronously.
2. Form a functional `POST /api/v1/scan` endpoint inside `main.py` allowing clients to query any URL string.
3. Validate robust JSON response structures.

## Phase 3: Build the Lightweight Telegram Client
1. Set up `clients/telegram_bot/bot.py`.
2. Load it securely with the new production `TELEGRAM_TOKEN`.
3. Update the monolithic legacy routing. The new `bot.py` must simply ping `localhost:8000/api/v1/scan` or its cloud counterpart and relay the precise rich-text messages back to Telegram end-users.

## Phase 4: Build the Web Frontend Platform
1. Create a modern web interface in `clients/web_frontend/` using React or Next.js.
2. Architect an immersive dark-mode Threat Intelligence Dashboard featuring neon accents, radar-style loader aesthetics, and crisp tabular views of AI logic findings.
3. Have it call the identical API router logic.

## Phase 5: Containerization & Cloud-Native Deployment (Docker)
1. Build `Dockerfile` configurations specifically optimizing for the installation of heavy system dependencies like `playwright` binaries within the `backend/`.
2. Supply a root `docker-compose.yml` defining the API Backend, Telegram Client, and NextJS UI running as native services side-by-side.
3. Verify that the structure natively translates for immediate production deployments via **Google Cloud Run** and **GKE**.


