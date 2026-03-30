from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging

from backend.core.orchestrator import ScanOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Project Mata-Mata API", version="1.0.0")

# Enable CORS for all domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = ScanOrchestrator()

class ScanRequest(BaseModel):
    url: str
    vt_threshold: int = 5

class ScanResponse(BaseModel):
    url: str
    type: str
    results: dict

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Closing orchestrator sessions...")
    await orchestrator.close()

@app.post("/api/v1/scan", response_model=ScanResponse)
async def scan_url(request: ScanRequest):
    logger.info(f"Received scan request for URL: {request.url}")
    
    # Simple extraction to ensure it handles IP/URL validation
    items = orchestrator.url_extractor.extract_urls_and_domains(request.url)
    if not items:
        raise HTTPException(status_code=400, detail="No valid URL or Domain provided in the request payload.")
    
    target = items[0]
    if target["type"] == "ip_address":
        raise HTTPException(status_code=400, detail="Standalone IPs are not scannable.")
    
    # Wait for the Orchestrator to fully run Playwright + VT + WebRisk
    try:
        report = await orchestrator.scan_url(target["value"], target["type"], vt_threshold=request.vt_threshold)
        if "error" in report and "results" not in report:
            raise HTTPException(status_code=500, detail=report["error"])
        
        return report
    except Exception as e:
        logger.error(f"Scan API failed: {e}")
        raise HTTPException(status_code=500, detail="Internal scanning failure.")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
