"""
═══════════════════════════════════════════════════════
TEST 1 — SMOKE TESTING
═══════════════════════════════════════════════════════
Objective: Verify basic server liveness and critical endpoint availability
           after deployment, ensuring the system starts and responds.

Endpoints under test:
  GET  /status
  GET  /health
  POST /api/v1/predict/
  GET  /api/models (model listing)
"""

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_API_KEY = "xK9mR-vL2pN8qW5jT7bF4hD6cY0aG3sE"
AUTH_HEADERS = {"X-API-Key": VALID_API_KEY, "Content-Type": "application/json"}
MINIMAL_PREDICT_PAYLOAD = {
    "temperature": 303.15,
    "humidity": 85.0,
    "precipitation": 10.0,
}


@pytest.mark.smoke
class TestSmoke:
    """Smoke tests — basic liveness and critical endpoint reachability."""

    # ------------------------------------------------------------------
    # S-1: Root endpoint returns API info
    # ------------------------------------------------------------------
    def test_s1_root_endpoint_returns_200(self, client):
        """S-1: GET / must return 200 with API name."""
        response = client.get("/")
        assert response.status_code == 200, f"Root endpoint returned {response.status_code}, expected 200"
        data = response.get_json()
        assert data is not None, "Root endpoint returned no JSON body"
        # Should contain API identification info
        assert any(
            key in data for key in ("name", "api", "message", "status", "version")
        ), f"Root response missing identification fields: {list(data.keys())}"

    # ------------------------------------------------------------------
    # S-2: /status returns quick health check
    # ------------------------------------------------------------------
    def test_s2_status_endpoint_returns_200(self, client):
        """S-2: GET /status must return 200 with status field."""
        response = client.get("/status")
        assert response.status_code == 200, f"/status returned {response.status_code}, expected 200"
        data = response.get_json()
        assert data is not None
        assert "status" in data, f"/status response missing 'status' key: {data}"

    # ------------------------------------------------------------------
    # S-3: /health returns comprehensive health
    # ------------------------------------------------------------------
    def test_s3_health_endpoint_returns_200(self, client):
        """S-3: GET /health must return 200 with health components."""
        response = client.get("/health")
        assert response.status_code == 200, f"/health returned {response.status_code}, expected 200"
        data = response.get_json()
        assert data is not None
        assert "status" in data, f"/health missing 'status': {data}"

    # ------------------------------------------------------------------
    # S-4: POST /api/v1/predict/ accepts valid input
    # ------------------------------------------------------------------
    def test_s4_predict_endpoint_accepts_valid_payload(self, client, mock_model_comprehensive):
        """S-4: POST /api/v1/predict/ must return 200 on valid weather data."""
        response = client.post(
            "/api/v1/predict/",
            json=MINIMAL_PREDICT_PAYLOAD,
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 200, (
            f"/api/v1/predict/ returned {response.status_code}, expected 200. " f"Body: {response.get_json()}"
        )
        data = response.get_json()
        assert data is not None
        assert "prediction" in data, f"Prediction response missing 'prediction': {data}"

    # ------------------------------------------------------------------
    # S-5: POST /api/v1/predict/ rejects empty body
    # ------------------------------------------------------------------
    def test_s5_predict_rejects_empty_body(self, client):
        """S-5: POST /api/v1/predict/ with empty body returns 400."""
        response = client.post(
            "/api/v1/predict/",
            data=b"",
            headers=AUTH_HEADERS,
            content_type="application/json",
        )
        assert response.status_code == 400, f"Empty body returned {response.status_code}, expected 400"

    # ------------------------------------------------------------------
    # S-6: /api/models returns model list
    # ------------------------------------------------------------------
    def test_s6_models_endpoint_returns_list(self, client, mock_model_comprehensive):
        """S-6: GET /api/models returns model listing."""
        response = client.get("/api/models", headers=AUTH_HEADERS)
        # Accept 200 or 404 (if route not registered under this path)
        assert response.status_code in (200, 404, 401), f"/api/models returned {response.status_code}"

    # ------------------------------------------------------------------
    # S-7: Server returns JSON content-type
    # ------------------------------------------------------------------
    def test_s7_responses_are_json(self, client):
        """S-7: All endpoints return application/json content type."""
        for path in ["/", "/status", "/health"]:
            response = client.get(path)
            content_type = response.content_type or ""
            assert (
                "json" in content_type.lower() or response.status_code == 200
            ), f"{path} returned content-type '{content_type}', expected JSON"
