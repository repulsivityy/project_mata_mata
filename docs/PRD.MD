# Product Requirements Document (PRD)

## 1. Product Name
**Project Mata-Mata**
*A cross-platform, multi-agent AI phishing detection ecosystem.*

## 2. Overview
Project Mata-Mata is the evolution of the monolithic `telegram_url_checker`. It serves as a unified SaaS-style backend designed to detect sophisticated phishing campaigns, impersonation, and fraudulent URLs by combining static Threat Intelligence APIs (VirusTotal, Google Web Risk) with dynamic, headless dual-browser visualization and Gemini 2.5 Pro multi-modal analysis. 

The monolithic system is heavily refactored into a scalable API to service downstream clients such as Telegram Bots, Web Dashboards, and third-party services.

## 3. Core Objectives
- **Decoupled Architecture:** Isolate specific capabilities (Scanners, AI Agents, Telegram Integrations) into singular, decoupled endpoints so frontend logic never has to manage Playwright or web drivers.
- **Deep Evasion Detection:** Headless chromium and firefox instances fetch sites synchronously, bypassing Cloudflare cloaking to extract visual DOMs, inline javascript, and exfiltrated background network requests.
- **Cloud-Native Deployability:** Ensure the `backend` operates effortlessly behind `FastAPI` inside stateless Docker containers, explicitly deployable to Google Cloud Run or GKE. 
- **Reliable Session Persistence:** Implement an asynchronous background-job pattern with polling to ensure scans complete successfully even if a mobile client loses connection or goes to sleep mid-transit.
- **Progressive Results Rendering:** Support web and chat clients reading partial results states while slow dynamic analysis agents (like Playwright/Gemini) compute heavy logic sets.

## 4. Key Components
1. **Core Scanners:** `VirusTotalChecker`, `WebRiskChecker`, `GTI`.
2. **AI Extractor Agent (`ai_phishing_detector`):** Extracts screenshots, POST endpoints, DOM forms, and Javascript arrays to evaluate behavioral maliciousness using LLM vision.
3. **Orchestrator Logic:** Ingests the unified findings and scores the probability of compromise. 
4. **Clients:** 
   - A minimalist Telegram Bot (acting strictly as a presentation UI for users).
   - A modern React/Next.js "Threat Intelligence" dark-mode web dashboard.
5. **Persistence Real-Time Caching:** Google Firestore acts as a centralized results pool for clients and third parties to share asset intelligence based on URL hashes without repeatedly burning expensive external API rate limits.
