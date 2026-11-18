import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("GEMINI_APIKEY", "test-gemini-key")

import pytest
from fastapi.testclient import TestClient

from backend.core.models import ScanResult


class SpyFirestoreClient:
    """Spy Firestore client to assert zero Firestore interactions on /api/v1/scan/ai."""

    def __init__(self):
        self.collection_calls: list[str] = []

    def collection(self, name: str):
        self.collection_calls.append(name)
        raise AssertionError(f"Firestore should not be accessed by /api/v1/scan/ai (called collection({name!r}))")


TEST_API_KEY = "test-secret-api-key"


@pytest.fixture
def app_env():
    spy_firestore = SpyFirestoreClient()

    fake_secret_response = MagicMock()
    fake_secret_response.payload.data = TEST_API_KEY.encode("utf-8")
    fake_sm_client = MagicMock()
    fake_sm_client.access_secret_version.return_value = fake_secret_response

    sys.modules.pop("backend.api.main", None)

    with (
        patch("google.cloud.secretmanager.SecretManagerServiceClient", return_value=fake_sm_client),
        patch("google.cloud.firestore.AsyncClient", return_value=spy_firestore),
    ):
        import backend.api.main as main_module

    main_module.firestore_client = spy_firestore
    client = TestClient(main_module.app)
    return client, main_module, spy_firestore


def test_ai_scan_auth_missing_or_invalid_api_key(app_env):
    client, _, spy_firestore = app_env

    resp_missing = client.post("/api/v1/scan/ai", json={"url": "https://example.com"})
    assert resp_missing.status_code == 401

    resp_invalid = client.post(
        "/api/v1/scan/ai",
        json={"url": "https://example.com"},
        headers={"X-API-KEY": "wrong-key"},
    )
    assert resp_invalid.status_code == 401
    assert spy_firestore.collection_calls == []


def test_ai_scan_status_endpoint_removed(app_env):
    client, _, _ = app_env
    resp = client.get("/api/v1/scan/ai/status/somejob", headers={"X-API-KEY": TEST_API_KEY})
    assert resp.status_code == 404


def test_ai_scan_rejects_invalid_url_standalone_ip_and_private_hosts(app_env):
    client, _, spy_firestore = app_env
    headers = {"X-API-KEY": TEST_API_KEY}

    for bad_input in ("not a valid url", "8.8.8.8", "http://127.0.0.1/admin", "http://metadata.google.internal/"):
        resp = client.post("/api/v1/scan/ai", json={"url": bad_input}, headers=headers)
        assert resp.status_code == 400, f"Expected 400 for {bad_input!r}, got {resp.status_code}"

    assert spy_firestore.collection_calls == []


def test_ai_scan_synchronous_http_200_danger_zero_firestore_zero_vt_webrisk(app_env):
    client, _, spy_firestore = app_env
    headers = {"X-API-KEY": TEST_API_KEY}
    target_url = "https://phishing-test.example/login"

    structured_return = {
        "reachable": True,
        "http_status": 200,
        "http_status_text": "OK",
        "final_url": "https://phishing-test.example/microsoft-login",
        "reachability_reason": "OK",
        "analysis_text": '{"risk_level": "High", "final_assessment_summary": "Fake Microsoft login harvesting credentials."}',
        "internal_error": False,
    }

    with (
        patch("backend.core.scanners.analyze_url_for_phishing_structured", new=AsyncMock(return_value=structured_return)) as mock_struct,
        patch("backend.core.orchestrator.VirusTotalChecker") as mock_vt_cls,
        patch("backend.core.orchestrator.WebRiskEvalChecker") as mock_wre_cls,
        patch("backend.core.orchestrator.WebRiskLookupChecker") as mock_wrl_cls,
    ):
        resp = client.post("/api/v1/scan/ai", json={"url": target_url}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        mock_struct.assert_awaited_once_with(target_url, debug_mode=False)
        mock_vt_cls.assert_not_called()
        mock_wre_cls.assert_not_called()
        mock_wrl_cls.assert_not_called()

    assert spy_firestore.collection_calls == []
    assert data["url"] == target_url
    assert data["type"] == "url"
    assert data["reachable"] is True
    assert data["http_status"] == 200
    assert data["http_status_text"] == "OK"
    assert data["final_url"] == "https://phishing-test.example/microsoft-login"
    assert data["reachability_reason"] == "OK"
    assert data["final_verdict"] == "DANGER"
    assert data["ai_result"]["is_malicious"] is True
    assert data["ai_result"]["error"] is False
    assert "Fake Microsoft login" in data["ai_result"]["summary"]


def test_ai_scan_surfaces_http_404_clean_and_spoofed_404_phishing(app_env):
    client, _, spy_firestore = app_env
    headers = {"X-API-KEY": TEST_API_KEY}
    target_url = "https://taken-down.example/phish"

    # Case 1: Genuine HTTP 404 Not Found page
    clean_404 = {
        "reachable": True,
        "http_status": 404,
        "http_status_text": "Not Found",
        "final_url": target_url,
        "reachability_reason": "HTTP_404",
        "analysis_text": '{"risk_level": "Low", "final_assessment_summary": "Standard nginx 404 page with no interactive elements."}',
        "internal_error": False,
    }

    with patch("backend.core.scanners.analyze_url_for_phishing_structured", new=AsyncMock(return_value=clean_404)):
        resp = client.post("/api/v1/scan/ai", json={"url": target_url}, headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["reachable"] is True
        assert body["http_status"] == 404
        assert body["http_status_text"] == "Not Found"
        assert body["reachability_reason"] == "HTTP_404"
        assert body["final_verdict"] == "SAFE"
        assert body["ai_result"]["summary"].startswith("[HTTP 404 Not Found] Risk: Low")

    # Case 2: Phishing kit returning HTTP 404 header to evade scanners while rendering a login form
    spoofed_404 = {
        "reachable": True,
        "http_status": 404,
        "http_status_text": "Not Found",
        "final_url": target_url,
        "reachability_reason": "HTTP_404",
        "analysis_text": '{"risk_level": "High", "final_assessment_summary": "Page returns 404 status but renders fake banking credential form."}',
        "internal_error": False,
    }

    with patch("backend.core.scanners.analyze_url_for_phishing_structured", new=AsyncMock(return_value=spoofed_404)):
        resp2 = client.post("/api/v1/scan/ai", json={"url": target_url}, headers=headers)
        assert resp2.status_code == 200
        body2 = resp2.json()
        assert body2["http_status"] == 404
        assert body2["final_verdict"] == "DANGER"
        assert body2["ai_result"]["is_malicious"] is True
        assert body2["ai_result"]["summary"].startswith("[HTTP 404 Not Found] Risk: High")

    assert spy_firestore.collection_calls == []


def test_ai_scan_unreachable_site_returns_unreachable_not_internal_error(app_env):
    client, _, spy_firestore = app_env
    headers = {"X-API-KEY": TEST_API_KEY}

    unreachable_dns = {
        "reachable": False,
        "http_status": None,
        "http_status_text": None,
        "final_url": None,
        "reachability_reason": "DNS_NOT_FOUND",
        "analysis_text": "Currently unreachable (DNS resolution failed)",
        "internal_error": False,
    }

    with patch("backend.core.scanners.analyze_url_for_phishing_structured", new=AsyncMock(return_value=unreachable_dns)):
        resp = client.post("/api/v1/scan/ai", json={"url": "dead-phish-domain.example"}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["url"] == "dead-phish-domain.example"
        assert data["type"] == "domain"
        assert data["reachable"] is False
        assert data["http_status"] is None
        assert data["reachability_reason"] == "DNS_NOT_FOUND"
        assert data["final_verdict"] == "UNREACHABLE"
        assert data["ai_result"]["error"] is False
        assert data["ai_result"]["is_malicious"] is False
        assert data["ai_result"]["summary"] == "Currently unreachable (DNS resolution failed)"
        assert data["ai_result"]["risk_factors"]["verdict"] == "Unreachable"

    assert spy_firestore.collection_calls == []


def test_ai_scan_internal_gemini_failure_returns_error_verdict(app_env):
    client, _, _ = app_env
    headers = {"X-API-KEY": TEST_API_KEY}

    gemini_err = {
        "reachable": True,
        "http_status": 200,
        "http_status_text": "OK",
        "final_url": "https://example.com/",
        "reachability_reason": "INTERNAL_ERROR",
        "analysis_text": "API request failed (HTTP 500).",
        "internal_error": True,
    }

    with patch("backend.core.scanners.analyze_url_for_phishing_structured", new=AsyncMock(return_value=gemini_err)):
        resp = client.post("/api/v1/scan/ai", json={"url": "https://example.com"}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["final_verdict"] == "ERROR"
        assert data["ai_result"]["error"] is True
        assert data["http_status"] == 200


def test_detector_select_best_result_handles_empty_404_page_and_failure_classification():
    from backend.core.ai_phishing_detector import _classify_navigation_failure, select_best_result

    # Empty HTTP 404 body has score 0 (html="", links=[], forms=[]) — must still be selected
    empty_404_results = {
        "chrome_windows": {
            "html": "",
            "links": [],
            "forms": [],
            "http_status": 404,
            "http_status_text": "Not Found",
            "final_url": "https://example.com/missing",
        }
    }
    selected = select_best_result(empty_404_results)
    assert selected is not None
    assert selected[0] == "chrome_windows"
    assert selected[1]["http_status"] == 404

    # Navigation failure classifications
    assert _classify_navigation_failure(
        {"chrome_windows": {"error": "Page.goto: net::ERR_NAME_NOT_RESOLVED at https://dead.example/"}}
    )[0] == "DNS_NOT_FOUND"

    assert _classify_navigation_failure(
        {"firefox_windows": {"error": "Page.goto: NS_ERROR_CONNECTION_REFUSED"}}
    )[0] == "CONNECTION_REFUSED"

    assert _classify_navigation_failure(
        {"chrome_windows": {"error": "Timeout 30000ms exceeded"}}
    )[0] == "TIMEOUT"

    assert _classify_navigation_failure(
        {"chrome_windows": {"error": "Page.goto: net::ERR_BLOCKED_BY_CLIENT (blockedbyclient)"}}
    )[0] == "BLOCKED"


@pytest.mark.asyncio
async def test_orchestrator_scan_ai_only_none_ai_risk_does_not_crash():
    from backend.core.orchestrator import ScanOrchestrator

    orchestrator = ScanOrchestrator()
    scan_result = ScanResult(
        is_malicious=False,
        summary="Indeterminate",
        source="AI Analysis",
        details={"reachable": True, "http_status": 200},
        risk_factors={"ai_risk": None},
    )

    with patch("backend.core.orchestrator.AIImageChecker") as mock_ai_cls:
        mock_ai = MagicMock()
        mock_ai.check = AsyncMock(return_value=scan_result)
        mock_ai_cls.return_value = mock_ai

        res = await orchestrator.scan_ai_only("https://example.com", "url")
        assert res["final_verdict"] == "WARNING"
        assert res["reachable"] is True
        assert res["http_status"] == 200
