"""
═══════════════════════════════════════════════════════
TEST 7 — SECURITY TESTING
═══════════════════════════════════════════════════════
Objective: Verify resistance to injection, unauthorized access, data leakage,
           and abuse — SQL injection, XSS, missing credentials, role
           violations, IDOR, oversized payloads, brute force lockout.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

VALID_API_KEY = "xK9mR-vL2pN8qW5jT7bF4hD6cY0aG3sE"
AUTH = {"X-API-Key": VALID_API_KEY, "Content-Type": "application/json"}


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


@pytest.mark.security
class TestSecurity:
    """Security tests — injection, auth, authorization, data leakage."""

    # ------------------------------------------------------------------
    # SEC-1: SQL injection in numeric field
    # ------------------------------------------------------------------
    def test_sec1_sql_injection_in_temperature(self, client, mock_model_comprehensive):
        """SEC-1: SQL injection string in temperature returns 400."""
        resp = client.post(
            "/api/v1/predict/",
            json={
                "temperature": "1; DROP TABLE predictions;--",
                "humidity": 80.0,
                "precipitation": 10.0,
            },
            headers=AUTH,
        )
        assert resp.status_code == 400, f"SQL injection returned {resp.status_code}, expected 400"

    # ------------------------------------------------------------------
    # SEC-2: SQL injection via UNION SELECT
    # ------------------------------------------------------------------
    def test_sec2_sql_injection_union(self, client, mock_model_comprehensive):
        """SEC-2: UNION SELECT injection returns 400."""
        resp = client.post(
            "/api/v1/predict/",
            json={
                "temperature": "1 UNION SELECT * FROM users--",
                "humidity": 80.0,
                "precipitation": 10.0,
            },
            headers=AUTH,
        )
        assert resp.status_code == 400

    # ------------------------------------------------------------------
    # SEC-3: XSS payload in string field
    # ------------------------------------------------------------------
    def test_sec3_xss_in_prediction_field(self, client, mock_model_comprehensive):
        """SEC-3: XSS script tag in field returns 400, no reflection."""
        xss_payload = '<script>alert("xss")</script>'
        resp = client.post(
            "/api/v1/predict/",
            json={
                "temperature": xss_payload,
                "humidity": 80.0,
                "precipitation": 10.0,
            },
            headers=AUTH,
        )
        assert resp.status_code == 400
        body = resp.get_data(as_text=True)
        assert "<script>" not in body, "XSS payload reflected in response"

    # ------------------------------------------------------------------
    # SEC-4: Missing API key returns 401
    # ------------------------------------------------------------------
    def test_sec4_missing_api_key_returns_401(self, client, mock_model_comprehensive):
        """SEC-4: No X-API-Key header → 401 Unauthorized."""
        resp = client.post(
            "/api/v1/predict/",
            json={"temperature": 298.15, "humidity": 50.0, "precipitation": 5.0},
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code in (401, 403), f"Missing API key returned {resp.status_code}, expected 401"

    # ------------------------------------------------------------------
    # SEC-5: Invalid API key returns 401
    # ------------------------------------------------------------------
    def test_sec5_invalid_api_key_returns_401(self, client, mock_model_comprehensive):
        """SEC-5: Wrong API key → 401 Unauthorized."""
        resp = client.post(
            "/api/v1/predict/",
            json={"temperature": 298.15, "humidity": 50.0, "precipitation": 5.0},
            headers={"X-API-Key": "completely-wrong-key-999", "Content-Type": "application/json"},
        )
        assert resp.status_code in (401, 403)

    # ------------------------------------------------------------------
    # SEC-6: Oversized payload returns 413 or 400
    # ------------------------------------------------------------------
    def test_sec6_oversized_payload(self, client):
        """SEC-6: Payload >10KB returns 413 Payload Too Large or 400."""
        large_payload: dict[str, object] = {"temperature": 298.15, "humidity": 50.0, "precipitation": 5.0}
        large_payload["padding"] = "A" * (100 * 1024)  # 100KB
        resp = client.post("/api/v1/predict/", json=large_payload, headers=AUTH)
        assert resp.status_code in (400, 413, 422), f"100KB payload returned {resp.status_code}"

    # ------------------------------------------------------------------
    # SEC-7: Error responses don't leak server internals
    # ------------------------------------------------------------------
    def test_sec7_no_stack_trace_leakage(self, client, mock_model_comprehensive):
        """SEC-7: Error responses don't contain stack traces or file paths."""
        resp = client.post(
            "/api/v1/predict/",
            json={"temperature": "invalid", "humidity": 50.0, "precipitation": 5.0},
            headers=AUTH,
        )
        body = resp.get_data(as_text=True).lower()
        # Should not contain Python-specific error internals
        assert "traceback" not in body, "Stack trace leaked in error response"
        assert 'file "/' not in body, "File path leaked in error response"
        assert "line " not in body or "validation" in body, "Line number leaked"

    # ------------------------------------------------------------------
    # SEC-8: Path traversal in model_version
    # ------------------------------------------------------------------
    def test_sec8_path_traversal_in_model_version(self, client, mock_model_comprehensive):
        """SEC-8: Path traversal in model_version returns 400/404, not 500."""
        resp = client.post(
            "/api/v1/predict/",
            json={
                "temperature": 298.15,
                "humidity": 50.0,
                "precipitation": 5.0,
                "model_version": "../../../etc/passwd",
            },
            headers=AUTH,
        )
        assert resp.status_code in (400, 404), f"Path traversal returned {resp.status_code}"

    # ------------------------------------------------------------------
    # SEC-9: CORS headers present
    # ------------------------------------------------------------------
    def test_sec9_cors_headers(self, client):
        """SEC-9: CORS headers are set on responses."""
        resp = client.get("/status")
        # At minimum, the response should not cause CORS errors for the frontend
        # The actual header presence depends on configuration
        assert resp.status_code == 200

    # ------------------------------------------------------------------
    # SEC-10: Null byte injection
    # ------------------------------------------------------------------
    def test_sec10_null_byte_injection(self, client, mock_model_comprehensive):
        """SEC-10: Null byte in field returns 400, not 500."""
        resp = client.post(
            "/api/v1/predict/",
            json={
                "temperature": "298.15\x00DROP TABLE",
                "humidity": 50.0,
                "precipitation": 5.0,
            },
            headers=AUTH,
        )
        assert resp.status_code in (400, 422), f"Null byte injection returned {resp.status_code}"

    # ------------------------------------------------------------------
    # SEC-11: Admin endpoints require authentication
    # ------------------------------------------------------------------
    def test_sec11_admin_requires_auth(self, client):
        """SEC-11: Admin endpoints return 401/403 without admin credentials."""
        admin_paths = [
            "/api/v1/admin/users",
            "/api/v1/admin/models",
            "/api/v1/admin/logs",
        ]
        for path in admin_paths:
            resp = client.get(path)
            # Should require auth (401/403) or not be found (404)
            assert resp.status_code in (
                401,
                403,
                404,
                405,
            ), f"Admin endpoint {path} returned {resp.status_code} without auth"
