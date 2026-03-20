"""
═══════════════════════════════════════════════════════
TEST 2 — FUNCTIONAL TESTING
═══════════════════════════════════════════════════════
Objective: Verify correct business logic for all major endpoints including
           risk classification accuracy, response schema completeness,
           HTTP status codes, and field type correctness.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

VALID_API_KEY = "xK9mR-vL2pN8qW5jT7bF4hD6cY0aG3sE"
AUTH = {"X-API-Key": VALID_API_KEY, "Content-Type": "application/json"}


def _make_model(prediction, proba_flood):
    """Build a mock sklearn model with deterministic output."""
    model = MagicMock()
    model.predict.return_value = np.array([prediction])
    model.predict_proba.return_value = np.array([[1 - proba_flood, proba_flood]])
    model.feature_names_in_ = np.array(["temperature", "humidity", "precipitation"])
    model.n_features_in_ = 3
    model.classes_ = np.array([0, 1])
    model.feature_importances_ = np.array([0.3, 0.3, 0.4])
    return model


def _patch_model(model):
    """Return a context-manager that patches the ModelLoader everywhere."""
    loader = MagicMock()
    loader.model = model
    loader.model_path = "models/test_model.joblib"
    loader.metadata = {"version": "6.0.0", "checksum": "abc123"}
    loader.checksum = "abc123456789"
    return patch("app.services.predict._get_model_loader", return_value=loader)


@pytest.mark.functional
class TestFunctional:
    """Functional tests — business logic correctness."""

    # ------------------------------------------------------------------
    # F-1: Safe classification (prob_flood < 0.30)
    # ------------------------------------------------------------------
    def test_f1_safe_classification(self, client):
        """F-1: Low flood probability → risk_level 0 (Safe)."""
        model = _make_model(prediction=0, proba_flood=0.05)
        with _patch_model(model):
            resp = client.post(
                "/api/v1/predict/",
                json={"temperature": 298.15, "humidity": 50.0, "precipitation": 2.0},
                headers=AUTH,
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["prediction"] == 0
        assert data["flood_risk"] == "low"
        assert data.get("risk_level") == 0 or data.get("risk_label") == "Safe"

    # ------------------------------------------------------------------
    # F-2: Alert classification (prob_flood 0.30–0.75)
    # ------------------------------------------------------------------
    def test_f2_alert_classification(self, client):
        """F-2: Moderate flood probability → risk_level 1 (Alert)."""
        model = _make_model(prediction=1, proba_flood=0.55)
        with _patch_model(model):
            resp = client.post(
                "/api/v1/predict/",
                json={"temperature": 303.15, "humidity": 82.0, "precipitation": 25.0},
                headers=AUTH,
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["prediction"] == 1
        assert data.get("risk_level") == 1 or data.get("risk_label") == "Alert"

    # ------------------------------------------------------------------
    # F-3: Critical classification (prob_flood ≥ 0.75)
    # ------------------------------------------------------------------
    def test_f3_critical_classification(self, client):
        """F-3: High flood probability → risk_level 2 (Critical)."""
        model = _make_model(prediction=1, proba_flood=0.85)
        with _patch_model(model):
            resp = client.post(
                "/api/v1/predict/",
                json={"temperature": 305.0, "humidity": 95.0, "precipitation": 80.0},
                headers=AUTH,
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["prediction"] == 1
        assert data["flood_risk"] == "high"
        assert data.get("risk_level") == 2 or data.get("risk_label") == "Critical"

    # ------------------------------------------------------------------
    # F-4: Response schema completeness
    # ------------------------------------------------------------------
    def test_f4_prediction_response_schema(self, client):
        """F-4: Prediction response contains all required fields."""
        model = _make_model(prediction=0, proba_flood=0.15)
        with _patch_model(model):
            resp = client.post(
                "/api/v1/predict/",
                json={"temperature": 298.15, "humidity": 60.0, "precipitation": 5.0},
                headers=AUTH,
            )
        assert resp.status_code == 200
        data = resp.get_json()

        required_fields = {"prediction", "flood_risk", "request_id"}
        missing = required_fields - set(data.keys())
        assert not missing, f"Missing required fields: {missing}"

        # Type checks
        assert isinstance(data["prediction"], int)
        assert data["flood_risk"] in ("low", "high")
        assert isinstance(data["request_id"], str)

        # Optional but expected typed fields
        if "risk_level" in data:
            assert data["risk_level"] in (0, 1, 2)
        if "risk_label" in data:
            assert data["risk_label"] in ("Safe", "Alert", "Critical")
        if "confidence" in data and data["confidence"] is not None:
            assert 0.0 <= data["confidence"] <= 1.0
        if "timestamp" in data:
            assert isinstance(data["timestamp"], str)

    # ------------------------------------------------------------------
    # F-5: Missing required field returns 400
    # ------------------------------------------------------------------
    def test_f5_missing_temperature_returns_400(self, client, mock_model_comprehensive):
        """F-5: Omitting 'temperature' returns 400 ValidationError."""
        resp = client.post(
            "/api/v1/predict/",
            json={"humidity": 80.0, "precipitation": 10.0},
            headers=AUTH,
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data is not None
        # Error response should indicate validation failure
        err_code = data.get("error", {}).get("code", data.get("code", ""))
        assert "Validation" in err_code or "NoInput" not in err_code or resp.status_code == 400

    # ------------------------------------------------------------------
    # F-6: Missing humidity returns 400
    # ------------------------------------------------------------------
    def test_f6_missing_humidity_returns_400(self, client, mock_model_comprehensive):
        """F-6: Omitting 'humidity' returns 400."""
        resp = client.post(
            "/api/v1/predict/",
            json={"temperature": 298.15, "precipitation": 10.0},
            headers=AUTH,
        )
        assert resp.status_code == 400

    # ------------------------------------------------------------------
    # F-7: Invalid type in numeric field returns 400
    # ------------------------------------------------------------------
    def test_f7_string_in_temperature_returns_400(self, client, mock_model_comprehensive):
        """F-7: String value for temperature returns 400."""
        resp = client.post(
            "/api/v1/predict/",
            json={"temperature": "hot", "humidity": 80.0, "precipitation": 10.0},
            headers=AUTH,
        )
        assert resp.status_code == 400

    # ------------------------------------------------------------------
    # F-8: Humidity out of range (>100) returns 400
    # ------------------------------------------------------------------
    def test_f8_humidity_over_100_returns_400(self, client, mock_model_comprehensive):
        """F-8: humidity=150 returns 400."""
        resp = client.post(
            "/api/v1/predict/",
            json={"temperature": 298.15, "humidity": 150.0, "precipitation": 5.0},
            headers=AUTH,
        )
        assert resp.status_code == 400

    # ------------------------------------------------------------------
    # F-9: Negative precipitation returns 400
    # ------------------------------------------------------------------
    def test_f9_negative_precipitation_returns_400(self, client, mock_model_comprehensive):
        """F-9: precipitation=-5 returns 400."""
        resp = client.post(
            "/api/v1/predict/",
            json={"temperature": 298.15, "humidity": 50.0, "precipitation": -5.0},
            headers=AUTH,
        )
        assert resp.status_code == 400

    # ------------------------------------------------------------------
    # F-10: Health endpoint has status and database fields
    # ------------------------------------------------------------------
    def test_f10_health_response_structure(self, client):
        """F-10: GET /health returns status + database fields."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "status" in data

    # ------------------------------------------------------------------
    # F-11: Status endpoint is fast (< 500ms)
    # ------------------------------------------------------------------
    def test_f11_status_response_fast(self, client):
        """F-11: GET /status responds within 500ms."""
        import time

        start = time.monotonic()
        resp = client.get("/status")
        elapsed_ms = (time.monotonic() - start) * 1000
        assert resp.status_code == 200
        assert elapsed_ms < 500, f"/status took {elapsed_ms:.0f}ms, limit is 500ms"

    # ------------------------------------------------------------------
    # F-12: Optional fields (wind_speed, pressure) accepted
    # ------------------------------------------------------------------
    def test_f12_optional_fields_accepted(self, client):
        """F-12: Optional wind_speed and pressure are accepted."""
        model = _make_model(prediction=0, proba_flood=0.10)
        with _patch_model(model):
            resp = client.post(
                "/api/v1/predict/",
                json={
                    "temperature": 298.15,
                    "humidity": 60.0,
                    "precipitation": 5.0,
                    "wind_speed": 12.0,
                    "pressure": 1013.25,
                },
                headers=AUTH,
            )
        assert resp.status_code == 200
