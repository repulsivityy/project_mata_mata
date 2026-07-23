from fastapi import FastAPI, HTTPException, Header, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import os
import hashlib
import hmac
from datetime import datetime, timedelta
from google.cloud import secretmanager
from google.cloud import firestore

from backend.core.orchestrator import ScanOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Project Mata-Mata API", version="1.0.0")

# Global variables in memory for security
EXPECTED_HASH = None
SALT = os.urandom(16) # Generate a random salt on startup

def get_api_key_from_secret_manager():
    project_id = os.environ.get("PROJECT_ID", "virustotal-lab")
    secret_id = "MATA_API_KEY"
    
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error(f"❌ Failed to fetch secret from Secret Manager: {e}")
        return None

# Fetch and hash on startup (Fail hard approach)
raw_key = get_api_key_from_secret_manager()
if raw_key:
    # Compute HMAC-SHA256
    EXPECTED_HASH = hmac.new(SALT, raw_key.encode('utf-8'), hashlib.sha256).hexdigest()
    logger.info("🔑 API Key fetched and hashed successfully in memory.")
else:
    logger.error("❌ MATA_API_KEY not configured or unreachable! Failing hard.")
    raise RuntimeError("Server misconfiguration: MATA_API_KEY is not set or unreachable.")

async def verify_api_key(x_api_key: str = Header(None)):
    if not EXPECTED_HASH:
        raise HTTPException(status_code=500, detail="Server misconfiguration: API Key not loaded.")
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Unauthorized: Missing API Key.")
    
    # Compute HMAC-SHA256 of received key
    received_hash = hmac.new(SALT, x_api_key.encode('utf-8'), hashlib.sha256).hexdigest()
    
    # Secure comparison
    if not hmac.compare_digest(received_hash, EXPECTED_HASH):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid API Key.")
# Enable CORS for all domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = ScanOrchestrator()
firestore_client = firestore.AsyncClient()

class ScanRequest(BaseModel):
    url: str
    vt_threshold: int = 5
    allow_early_cancel: bool = False

class ScanResponse(BaseModel):
    url: str
    type: str
    results: dict
    final_verdict: str

class ScanJobResponse(BaseModel):
    job_id: str
    status: str

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Closing orchestrator sessions...")
    await orchestrator.close()

async def perform_scan(job_id: str, url: str, item_type: str, vt_threshold: int, allow_early_cancel: bool = False):
    doc_ref = firestore_client.collection("mata_mata_scans").document(job_id)
    try:
        logger.info(f"Starting background scan for job {job_id}")
        
        # 1. Initialize Firestore document with defaults
        expire_at = datetime.utcnow() + timedelta(hours=48)
        await doc_ref.set({
            "status": "in_progress",
            "results": {
                "VirusTotal": {"summary": "Still analyzing...", "is_pending": True, "error": False},
                "Google Web Risk": {"summary": "Still analyzing...", "is_pending": True, "error": False},
                "AI Analysis": {"summary": "Still analyzing...", "is_pending": True, "error": False}
            },
            "url": url,
            "type": item_type,
            "expireAt": expire_at
        })
        
        # 2. Define callback to update Firestore live
        async def on_update(current_results):
            # Merge with defaults to preserve "Still analyzing..." for pending ones
            merged_results = {
                "VirusTotal": {"summary": "Still analyzing...", "is_pending": True, "error": False},
                "Google Web Risk": {"summary": "Still analyzing...", "is_pending": True, "error": False},
                "AI Analysis": {"summary": "Still analyzing...", "is_pending": True, "error": False}
            }
            merged_results.update(current_results)
            await doc_ref.update({"results": merged_results})
            logger.info(f"Job {job_id} updated with partial results.")

        # 3. Run the scan with callback
        report = await orchestrator.scan_url(url, item_type, vt_threshold=vt_threshold, allow_early_cancel=allow_early_cancel, on_update_callback=on_update)
        
        # 4. Save final completed state
        await doc_ref.update({
            "status": "completed",
            "results": report.get("results", {}),
            "final_verdict": report.get("final_verdict", "UNKNOWN")
        })
        logger.info(f"Job {job_id} completed and saved to Firestore.")
        
    except Exception as e:
        logger.error(f"Background scan failed for job {job_id}: {e}")
        await doc_ref.set({
            "status": "failed",
            "error": "An internal error occurred during analysis.",
            "internal_error": str(e),
            "expireAt": datetime.utcnow() + timedelta(hours=1)
        }, merge=True)

@app.post("/api/v1/scan", response_model=ScanJobResponse, dependencies=[Depends(verify_api_key)])
async def scan_url(request: ScanRequest, background_tasks: BackgroundTasks):
    logger.info(f"Received scan request for URL: {request.url}")
    
    # Simple extraction to ensure it handles IP/URL validation
    items = orchestrator.url_extractor.extract_urls_and_domains(request.url)
    if not items:
        raise HTTPException(status_code=400, detail="No valid URL or Domain provided in the request payload.")
    
    target = items[0]
    if target["type"] == "ip_address":
        raise HTTPException(status_code=400, detail="Standalone IPs are not scannable.")
    
    url_value = target["value"]
    # Compute SHA-256 hash of the URL
    job_id = hashlib.sha256(url_value.encode('utf-8')).hexdigest()
    
    # Check Firestore
    doc_ref = firestore_client.collection("mata_mata_scans").document(job_id)
    doc = await doc_ref.get()
    
    if doc.exists:
        data = doc.to_dict()
        logger.info(f"Found existing job {job_id} with status {data.get('status')}")
        return ScanJobResponse(job_id=job_id, status=data.get("status"))
    
    # Create new job
    await doc_ref.set({
        "status": "in_progress",
        "url": url_value,
        "type": target["type"],
        "expireAt": datetime.utcnow() + timedelta(minutes=5) # Temporary TTL until done
    })
    
    # Add background task
    background_tasks.add_task(perform_scan, job_id, url_value, target["type"], request.vt_threshold, request.allow_early_cancel)
    
    return ScanJobResponse(job_id=job_id, status="in_progress")

@app.get("/api/v1/scan/status/{job_id}")
async def get_scan_status(job_id: str):
    doc_ref = firestore_client.collection("mata_mata_scans").document(job_id)
    doc = await doc_ref.get()
    
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Job not found.")
    
    data = doc.to_dict()
    # Remove large/internal fields if necessary, or just return it!
    # Let's remove expireAt as it's an internal Firestore timestamp
    if "expireAt" in data:
        del data["expireAt"]
    if "internal_error" in data:
        del data["internal_error"]
    
    return data

@app.get("/health")
async def health_check():
    return {"status": "ok"}
