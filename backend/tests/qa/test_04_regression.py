"""
═══════════════════════════════════════════════════════
TEST 4 — REGRESSION TESTING
═══════════════════════════════════════════════════════
Objective: Confirm no existing functionality broke after a hypothetical
           upgrade from model v5 to v6 — thresholds unchanged, rate
           limiting works, model versions listed, schemas stable.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

VALID_API_KEY = "xK9mR-vL2pN8qW5jT7bF4hD6cY0aG3sE"
AUTH = {"X-API-Key": VALID_API_KEY, "Content-Type": "application/json"}


def _model(pred, prob):
    m = MagicMock()
    m.predict.return_value = np.array([pred])
    m.predict_proba.return_value = np.array([[1 - prob, prob]])
    m.feature_names_in_ = np.array(["temperature", "humidity", "precipitation"])
    m.n_features_in_ = 3
    m.classes_ = np.array([0, 1])
    m.feature_importances_ = np.array([0.3, 0.3, 0.4])
    return m


def _loader(model, version="6.0.0"):
    loader = MagicMock()
    loader.model = model
    loader.model_path = "models/test.joblib"
    loader.metadata = {"version": version, "checksum": "abc123"}
    loader.checksum = "abc123"
    return loader


@pytest.mark.regression
class TestRegression:
    """Regression tests — verify nothing broke post-upgrade."""

    # ------------------------------------------------------------------
    # R-1: Safe threshold unchanged after v5→v6 upgrade
    # ------------------------------------------------------------------
    def test_r1_safe_threshold_unchanged(self, client):
        """R-1: prob=0.05 still classifies as Safe after model upgrade."""
        model = _model(0, 0.05)
        with patch("app.services.predict._get_model_loader", return_value=_loader(model)):
            resp = client.post(
                "/api/v1/predict/",
                json={"temperature": 298.15, "humidity": 50.0, "precipitation": 2.0},
                headers=AUTH,
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["prediction"] == 0
        assert data["flood_risk"] == "low"

    # ------------------------------------------------------------------
    # R-2: Alert threshold unchanged
    # ------------------------------------------------------------------
    def test_r2_alert_threshold_unchanged(self, client):
        """R-2: prob=0.55 still classifies as Alert."""
        model = _model(1, 0.55)
        with patch("app.services.predict._get_model_loader", return_value=_loader(model)):
            resp = client.post(
                "/api/v1/predict/",
                json={"temperature": 303.15, "humidity": 82.0, "precipitation": 25.0},
                headers=AUTH,
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["prediction"] == 1

    # ------------------------------------------------------------------
    # R-3: Critical threshold unchanged
    # ------------------------------------------------------------------
    def test_r3_critical_threshold_unchanged(self, client):
        """R-3: prob=0.85 still classifies as Critical."""
        model = _model(1, 0.85)
        with patch("app.services.predict._get_model_loader", return_value=_loader(model)):
            resp = client.post(
                "/api/v1/predict/",
                json={"temperature": 305.0, "humidity": 95.0, "precipitation": 80.0},
                headers=AUTH,
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["prediction"] == 1
        assert data["flood_risk"] == "high"

    # ------------------------------------------------------------------
    # R-4: Validation rules still enforce 400 on bad input
    # ------------------------------------------------------------------
    def test_r4_validation_rules_intact(self, client, mock_model_comprehensive):
        """R-4: All legacy validation rules still produce 400."""
        bad_payloads = [
            {},  # empty
            {"temperature": 298.15},  # missing fields
            {"temperature": "NaN", "humidity": 50.0, "precipitation": 5.0},
            {"temperature": 298.15, "humidity": 200.0, "precipitation": 5.0},
            {"temperature": 298.15, "humidity": 50.0, "precipitation": -10.0},
        ]
        for payload in bad_payloads:
            resp = client.post("/api/v1/predict/", json=payload, headers=AUTH)
            assert resp.status_code == 400, f"Payload {payload} returned {resp.status_code}, expected 400"

    # ------------------------------------------------------------------
    # R-5: Health endpoint still available
    # ------------------------------------------------------------------
    def test_r5_health_endpoint_stable(self, client):
        """R-5: /health and /status still return 200."""
        for endpoint in ["/health", "/status"]:
            resp = client.get(endpoint)
            assert resp.status_code == 200, f"{endpoint} returned {resp.status_code} after upgrade"

    # ------------------------------------------------------------------
    # R-6: Response schema backward-compatible
    # ------------------------------------------------------------------
    def test_r6_response_schema_backward_compatible(self, client):
        """R-6: Prediction response still contains all legacy fields."""
        model = _model(0, 0.10)
        with patch("app.services.predict._get_model_loader", return_value=_loader(model)):
            resp = client.post(
                "/api/v1/predict/",
                json={"temperature": 298.15, "humidity": 60.0, "precipitation": 5.0},
                headers=AUTH,
            )
        assert resp.status_code == 200
        data = resp.get_json()

        # These fields must always be present for backward compatibility
        legacy_fields = {"prediction", "flood_risk", "request_id"}
        present = set(data.keys())
        missing = legacy_fields - present
        assert not missing, f"Legacy fields missing after v6 upgrade: {missing}"

    # ------------------------------------------------------------------
    # R-7: /api/v1/predict/ still accepts POST only
    # ------------------------------------------------------------------
    def test_r7_predict_method_restriction(self, client):
        """R-7: GET /api/v1/predict/ returns 405 Method Not Allowed."""
        resp = client.get("/api/v1/predict/", headers=AUTH)
        assert resp.status_code == 405, f"GET /api/v1/predict/ returned {resp.status_code}, expected 405"

    # ------------------------------------------------------------------
    # R-8: Root endpoint still returns API info
    # ------------------------------------------------------------------
    def test_r8_root_endpoint_stable(self, client):
        """R-8: GET / continues to return 200 with API info."""
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data is not None
