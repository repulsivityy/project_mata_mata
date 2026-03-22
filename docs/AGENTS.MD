# Core Agents Definition

Project Mata-Mata relies heavily on an agentic architecture rather than simple static heuristics. Here are the core conceptual agents operating inside the system.

## 1. Visual Evasion Agent (The "Gemini" Core)
**Role:** Multimodal Phishing Detector
**Responsibilities:**
- Analyzing headless browser screenshots to locate deeply hidden visual discrepancies (such as a misspelled "robiox" masquerading as "roblox").
- Reading inline Javascript extracts supplied by the Orchestrator to identify credential-stealing or HTML-cloaking (hex/Base64 manipulation).
- Processing raw background POST requests to flag malicious webhook drops (e.g. data exfiltrated to a Telegram bot API).
- Judging overall threat level context relative to static Google Threat Intelligence outputs.

## 2. Orchestrator Agent (The Backend API)
**Role:** The Command Pipeline
**Responsibilities:**
- Firing off asynchronous `Playwright` workers across multiple browser rendering engines (Chromium vs Firefox, Mobile vs Desktop).
- Initiating `aiohttp` requests to VirusTotal and Google Web Risk to gather deterministic indicators of compromise (IoC).
- Evaluating threat matrix thresholds (e.g., stopping immediately if VT flags the domain 5+ times, or handing off to Gemini when the score isn't overwhelmingly conclusive).
- Shaping the API response payload cleanly for downstream UI clients.

## 3. The Extraction Agents (Scanners)
**Role:** Individual API Scraper Modules
**Responsibilities:**
- **URL Extractor**: Parses and scrapes bulk text dumps from Telegram or the Web to isolate isolated IPs, Domains, and URLs reliably.
- **VT Scanner**: Packages and hashes queried URLs securely.
- **Web Risk Scanner**: Maps domains to known blacklists.
