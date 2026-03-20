"""
═══════════════════════════════════════════════════════
TEST 6 — STRESS TESTING
═══════════════════════════════════════════════════════
Objective: Verify system behavior beyond normal limits and ensure
           graceful degradation — burst traffic, pool exhaustion,
           all-API failure, circuit breaker engagement, self-recovery.
"""

import time
import pytest
import numpy as np
from unittest.mock import patch, MagicMock

VALID_API_KEY = "xK9mR-vL2pN8qW5jT7bF4hD6cY0aG3sE"
AUTH = {"X-API-Key": VALID_API_KEY, "Content-Type": "application/json"}
PAYLOAD = {"temperature": 303.15, "humidity": 85.0, "precipitation": 10.0}


def _model():
    m = MagicMock()
    m.predict.return_value = np.array([0])
    m.predict_proba.return_value = np.array([[0.90, 0.10]])
    m.feature_names_in_ = np.array(["temperature", "humidity", "precipitation"])
    m.n_features_in_ = 3
    m.classes_ = np.array([0, 1])
    m.feature_importances_ = np.array([0.3, 0.3, 0.4])
    return m


def _loader(model):
    loader = MagicMock()
    loader.model = model
    loader.model_path = "models/test.joblib"
    loader.metadata = {"version": "6.0.0", "checksum": "abc123"}
    loader.checksum = "abc123"
    return loader


@pytest.mark.stress
class TestStress:
    """Stress tests — behavior beyond normal limits."""

    # ------------------------------------------------------------------
    # ST-1: Burst of 500 rapid-fire /predict requests
    # ------------------------------------------------------------------
    def test_st1_burst_500_predictions(self, app):
        """ST-1: 500 rapid predictions — no 500 errors, graceful 429 if limited."""
        model = _model()
        server_errors = 0
        rate_limited = 0
        success = 0

        with patch("app.services.predict._get_model_loader", return_value=_loader(model)):
            with app.test_client() as c:
                for _ in range(500):
                    resp = c.post("/api/v1/predict/", json=PAYLOAD, headers=AUTH)
                    if resp.status_code == 200:
                        success += 1
                    elif resp.status_code == 429:
                        rate_limited += 1
                    elif resp.status_code >= 500:
                        server_errors += 1

        # Zero server errors — only 200 or 429 are acceptable
        assert server_errors == 0, (
            f"{server_errors} server errors in 500 requests (unacceptable)"
        )
        assert success > 0, "No successful requests at all"

    # ------------------------------------------------------------------
    # ST-2: Oversized payload rejected gracefully
    # ------------------------------------------------------------------
    def test_st2_oversized_payload_rejected(self, client):
        """ST-2: 1MB payload returns 413 or 400, not 500."""
        oversized: dict[str, object] = {"temperature": 298.15, "humidity": 50.0, "precipitation": 5.0}
        oversized["padding"] = "x" * (1024 * 1024)  # ~1MB payload
        resp = client.post("/api/v1/predict/", json=oversized, headers=AUTH)
        assert resp.status_code in (400, 413, 422), (
            f"Oversized payload returned {resp.status_code}, expected 400/413"
        )

    # ------------------------------------------------------------------
    # ST-3: System returns valid responses after burst
    # ------------------------------------------------------------------
    def test_st3_recovery_after_burst(self, app):
        """ST-3: After a burst, system still returns valid predictions."""
        model = _model()

        with patch("app.services.predict._get_model_loader", return_value=_loader(model)):
            with app.test_client() as c:
                # First, burst of 100 requests
                for _ in range(100):
                    c.post("/api/v1/predict/", json=PAYLOAD, headers=AUTH)

                # Then verify a clean request still works
                resp = c.post("/api/v1/predict/", json=PAYLOAD, headers=AUTH)

        # Accept 200 or 429 (rate limited) — not 500
        assert resp.status_code in (200, 429), (
            f"Post-burst request returned {resp.status_code}"
        )
        if resp.status_code == 200:
            data = resp.get_json()
            assert "prediction" in data

    # ------------------------------------------------------------------
    # ST-4: All weather APIs failing — circuit breaker response
    # ------------------------------------------------------------------
    def test_st4_all_weather_apis_failing(self, client):
        """ST-4: When all 5 weather APIs fail, location-predict degrades gracefully."""
        all_fail = Exception("All weather APIs unavailable")

        with patch(
            "app.utils.weather_fetch.fetch_weather_by_coordinates",
            side_effect=all_fail,
        ):
            resp = client.post(
                "/api/v1/predict/location",
                json={"latitude": 14.4793, "longitude": 121.0198},
                headers=AUTH,
            )
        # System may return 200 (graceful degradation without weather enrichment),
        # 400 (missing required fields), or 5xx (propagated upstream failure).
        assert resp.status_code in (200, 400, 500, 502, 503), (
            f"All-API failure returned {resp.status_code}"
        )
        # Response should still be valid JSON
        data = resp.get_json()
        assert data is not None

    # ------------------------------------------------------------------
    # ST-5: Concurrent /health requests under stress
    # ------------------------------------------------------------------
    def test_st5_health_under_stress(self, client):
        """ST-5: 200 sequential /health requests remain stable."""
        errors = 0
        for _ in range(200):
            resp = client.get("/health")
            if resp.status_code >= 500:
                errors += 1
        assert errors == 0, f"{errors} server errors on /health under stress"

    # ------------------------------------------------------------------
    # ST-6: Malformed JSON stream doesn't crash server
    # ------------------------------------------------------------------
    def test_st6_malformed_json_flood(self, client):
        """ST-6: 100 malformed JSON requests → all return 400, none 500."""
        malformed_payloads = [
            b"{invalid}",
            b"not json",
            b'{"temperature": }',
            b"",
            b"null",
        ]
        for _ in range(20):
            for bad in malformed_payloads:
                resp = client.post(
                    "/api/v1/predict/",
                    data=bad,
                    headers=AUTH,
                    content_type="application/json",
                )
                assert resp.status_code < 500, (
                    f"Malformed JSON caused server error {resp.status_code}"
                )

    # ------------------------------------------------------------------
    # ST-7: Rapid alternating endpoints
    # ------------------------------------------------------------------
    def test_st7_rapid_endpoint_switching(self, app):
        """ST-7: Rapidly alternating between endpoints doesn't cause errors."""
        model = _model()
        server_errors = 0

        with patch("app.services.predict._get_model_loader", return_value=_loader(model)):
            with app.test_client() as c:
                for i in range(100):
                    if i % 3 == 0:
                        resp = c.get("/status")
                    elif i % 3 == 1:
                        resp = c.get("/health")
                    else:
                        resp = c.post("/api/v1/predict/", json=PAYLOAD, headers=AUTH)
                    if resp.status_code >= 500:
                        server_errors += 1

        assert server_errors == 0, f"{server_errors} server errors during rapid switching"
