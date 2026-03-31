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
        import logging
        logger = logging.getLogger(__name__)

        vt = results_map.get("VirusTotal", {})
        wr = results_map.get("Google Web Risk", {})
        ai = results_map.get("AI Analysis", {})

        vt_factors = vt.get("risk_factors", {})
        wr_factors = wr.get("risk_factors", {})
        ai_factors = ai.get("risk_factors", {})

        gti_verdict = vt_factors.get("gti_verdict")
        gti_score = vt_factors.get("gti_score")
        vt_detections = vt_factors.get("classic_score", 0)
        
        # Determine specific states
        gti_is_malicious = (gti_score is not None and gti_score > 60) or gti_verdict == "VERDICT_MALICIOUS" or gti_verdict == "malicious"
        wr_is_malicious = wr_factors.get("has_high_threat", False)
        
        # Condition 1: (GTI or Web Risk)
        cond1 = gti_is_malicious or wr_is_malicious
        
        # Condition 2: (AI or VT > 5)
        cond2 = (ai_factors.get("ai_risk") == "high") or vt_factors.get("is_malicious_threshold", False)
        
        logger.info(f"⚖️ Verdict computation: gti_verdict={gti_verdict}, gti_is_malicious={gti_is_malicious}, wr_is_malicious={wr_is_malicious}")
        logger.info(f"⚖️ Verdict computation: ai_risk={ai_factors.get('ai_risk')}, vt_thresh={vt_factors.get('is_malicious_threshold')}")
        logger.info(f"⚖️ Verdict computation: cond1={cond1}, cond2={cond2}")
        
        # 1. DANGER
        if cond1 and cond2:
            logger.info("⚖️ Verdict: DANGER")
            return "DANGER"

        # 2. SAFE
        wr_is_safe = wr_factors.get("is_clean", False)
        gti_is_benign = gti_verdict == "VERDICT_HARMLESS" or gti_verdict == "benign"
        
        if (gti_is_benign or wr_is_safe) and vt_detections == 0:
            logger.info("⚖️ Verdict: SAFE")
            return "SAFE"

        # 3. Falling back to WARNING
        logger.info("⚖️ Verdict: Falling back to WARNING")
        return "WARNING"

    async def scan_url(self, item_value: str, item_type: str = "url", vt_threshold: int = 5, on_update_callback=None) -> Dict:
        """
        Runs the full scan pipeline and returns a dictionary.
        """
        session = await self._get_session()
        checkers = []
        
        if VIRUSTOTAL_API_KEY and not VIRUSTOTAL_API_KEY.startswith("YOUR_"):
            checkers.append(VirusTotalChecker(VIRUSTOTAL_API_KEY, session, threshold=vt_threshold))
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
                        
                        # Extract GTI as a separate service if available
                        if source_name == "VirusTotal":
                            gti_assessment = result.details.get("gti_assessment")
                            if gti_assessment:
                                results_map["Google Threat Intelligence"] = {
                                    "is_malicious": gti_assessment.get("verdict", {}).get("value") == "VERDICT_MALICIOUS",
                                    "summary": gti_assessment.get("verdict", {}).get("value", "Unknown"),
                                    "details": gti_assessment,
                                    "risk_factors": {
                                        "gti_verdict": gti_assessment.get("verdict", {}).get("value"),
                                        "gti_score": gti_assessment.get("threat_score", {}).get("value")
                                    },
                                    "error": False,
                                    "is_pending": False
                                }
                            else:
                                # Not available (Classic VT key or no data)
                                results_map["Google Threat Intelligence"] = {
                                    "is_malicious": False,
                                    "summary": "Not available",
                                    "details": {},
                                    "risk_factors": {},
                                    "error": False,
                                    "is_pending": False,
                                    "not_available": True
                                }
                        
                        if on_update_callback:
                            await on_update_callback(results_map)

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

