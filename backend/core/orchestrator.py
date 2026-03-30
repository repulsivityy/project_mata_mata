import asyncio
import logging
from typing import Dict, List
import aiohttp
import os

from backend.core.models import ScanResult
from backend.core.extractors import URLExtractor
from backend.core.scanners import BaseChecker, VirusTotalChecker, WebRiskChecker, AIImageChecker

logger = logging.getLogger(__name__)

# Constants
VIRUSTOTAL_API_KEY = os.environ.get("VIRUSTOTAL_API_KEY")
WEBRISK_API_KEY = os.environ.get("WEBRISK_API_KEY")

class ScanOrchestrator:
    """
    Coordinates VirusTotal, Web Risk, and Gemini AI Scanners completely decoupled from Telegram.
    Returns a unified JSON-serializable dictionary.
    """
    def __init__(self):
        self.url_extractor = URLExtractor()
        self._session = None
        self._session_lock = asyncio.Lock()

    async def _get_session(self) -> aiohttp.ClientSession:
        async with self._session_lock:
            if self._session is None or self._session.closed:
                self._session = aiohttp.ClientSession()
            return self._session

    async def close(self):
        """Cleanup aiohttp session."""
        async with self._session_lock:
            if self._session and not self._session.closed:
                await self._session.close()

    def _compute_final_verdict(self, results_map: Dict) -> str:
        """
        Unified scoring rule logic to compute "DANGER", "SAFE", or "WARNING" across scanners.
        """
        vt = results_map.get("VirusTotal", {})
        wr = results_map.get("Google Web Risk", {})
        ai = results_map.get("AI Analysis", {})

        # --- 1. DANGER Rules ---
        # GTI Verdict is MALICIOUS
        gti_verdict = vt.get("risk_factors", {}).get("gti_verdict")
        gti_score = vt.get("risk_factors", {}).get("gti_score")
        if gti_verdict == "VERDICT_MALICIOUS" or (gti_score is not None and gti_score > 60):
            return "DANGER"

        # Web Risk has HIGH/EXTREMELY_HIGH
        if wr.get("risk_factors", {}).get("has_high_threat"):
            return "DANGER"

        # VT Classic Vendors Count >= 5
        if vt.get("is_malicious"): # Already decoupled to represent classic only
            return "DANGER"

        # Gemini AI Analysis is HIGH
        if ai.get("risk_factors", {}).get("ai_risk") == "high":
            return "DANGER"

        # --- 2. SAFE Rules ---
        # GTI Verdict is VERDICT_BENIGN
        if gti_verdict == "VERDICT_BENIGN":
            return "SAFE"

        # VT Vendors Count == 0 AND Web Risk is subset of SAFE
        vt_stats = vt.get("details", {})
        vt_count = vt_stats.get("malicious", 0) + vt_stats.get("suspicious", 0) if isinstance(vt_stats, dict) else 1 # Default to 1 if not dict (error)
        wr_is_safe = not wr.get("is_malicious", False)
        
        if vt_count == 0 and wr_is_safe:
            return "SAFE"

        return "WARNING"

    async def scan_url(self, item_value: str, item_type: str = "url") -> Dict:
        """
        Runs the full scan pipeline and returns a dictionary.
        """
        session = await self._get_session()
        checkers = []
        
        if VIRUSTOTAL_API_KEY and not VIRUSTOTAL_API_KEY.startswith("YOUR_"):
            checkers.append(VirusTotalChecker(VIRUSTOTAL_API_KEY, session))
        if WEBRISK_API_KEY and not WEBRISK_API_KEY.startswith("YOUR_"):
            checkers.append(WebRiskChecker(WEBRISK_API_KEY, session))
            
        checkers.append(AIImageChecker())

        results_map = {}
        
        try:
            # 1. Launch all initial checkers concurrently
            initial_tasks = {asyncio.create_task(c.check(item_value, item_type), name=c.SOURCE_NAME) for c in checkers}
            pending_tasks = initial_tasks.copy()

            while pending_tasks:
                done, pending_tasks = await asyncio.wait(pending_tasks, return_when=asyncio.FIRST_COMPLETED)
            
                for task in done:
                    source_name = task.get_name()
                    try:
                        result: ScanResult = task.result()
                        results_map[source_name] = {
                            "is_malicious": result.is_malicious,
                            "summary": result.summary,
                            "details": result.details,
                            "risk_factors": result.risk_factors,
                            "error": result.error,
                            "is_pending": result.is_pending
                        }

                        # Handle VT polling if necessary
                        if result.source == VirusTotalChecker.SOURCE_NAME and result.is_pending:
                            vt_checker = next((c for c in checkers if isinstance(c, VirusTotalChecker)), None)
                            analysis_id = result.details.get("analysis_id")
                            if vt_checker and analysis_id:
                                # Start a polling task
                                polling_task = asyncio.create_task(vt_checker.poll_for_result(analysis_id), name=VirusTotalChecker.SOURCE_NAME)
                                pending_tasks.add(polling_task)

                    except Exception as e:
                        logger.error(f"Task '{source_name}' failed for {item_value}: {e}")
                        results_map[source_name] = {
                            "is_malicious": False,
                            "summary": "Task failed",
                            "error": True
                        }

                # Check for Web Risk early exit condition
                wr_result = results_map.get(WebRiskChecker.SOURCE_NAME)
                if wr_result and wr_result.get("risk_factors", {}).get("has_high_threat"):
                    logger.warning(f"High-confidence threat from Web Risk for {item_value}. Cancelling remaining tasks.")
                    for p_task in pending_tasks:
                        p_task.cancel()
                        s_name = p_task.get_name()
                        if s_name not in results_map:
                            results_map[s_name] = {
                                "is_malicious": False, 
                                "summary": "❌ Cancelled due to confirmed Web Risk threat", 
                                "error": False
                            }
                    break # Exit early

            return {
                "url": item_value,
                "type": item_type,
                "results": results_map,
                "final_verdict": self._compute_final_verdict(results_map)
            }

        except Exception as e:
            logger.error(f"Error in orchestrator for {item_value}: {e}")
            return {"url": item_value, "error": str(e)}

