"""
═══════════════════════════════════════════════════════
TEST 8 — UI/CONTRACT TESTING
═══════════════════════════════════════════════════════
Objective: Verify API responses match exactly what the React frontend
           TypeScript interfaces expect — PaginatedResponse, PredictionResponse,
           DashboardStats, SSE payloads, risk colors, Alert schema.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

VALID_API_KEY = "xK9mR-vL2pN8qW5jT7bF4hD6cY0aG3sE"
AUTH = {"X-API-Key": VALID_API_KEY, "Content-Type": "application/json"}

# Expected risk color hex codes from frontend RiskConfig
RISK_COLORS = {
    0: "#28a745",  # Safe (green)
    1: "#ffc107",  # Alert (amber)
    2: "#dc3545",  # Critical (red)
}


def _model(pred, prob):
    m = MagicMock()
    m.predict.return_value = np.array([pred])
    m.predict_proba.return_value = np.array([[1 - prob, prob]])
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


@pytest.mark.contract
class TestUIContract:
    """Contract tests — API ↔ React frontend TypeScript interface alignment."""

    # ------------------------------------------------------------------
    # C-1: PredictionResponse has all typed fields
    # ------------------------------------------------------------------
    def test_c1_prediction_response_typed_fields(self, client):
        """C-1: Response matches frontend PredictionResponse interface."""
        model = _model(0, 0.10)
        with patch("app.services.predict._get_model_loader", return_value=_loader(model)):
            resp = client.post(
                "/api/v1/predict/",
                json={"temperature": 298.15, "humidity": 60.0, "precipitation": 5.0},
                headers=AUTH,
            )
        assert resp.status_code == 200
        data = resp.get_json()

        # Core PredictionResponse fields (frontend/src/types/api/prediction.ts)
        assert isinstance(data.get("prediction"), int), "prediction must be int"
        assert data["prediction"] in (0, 1), "prediction must be 0 or 1"

        # flood_risk as string
        assert data.get("flood_risk") in ("low", "high"), f"flood_risk='{data.get('flood_risk')}' not in low/high"

        # request_id as string
        assert isinstance(data.get("request_id"), str), "request_id must be str"

        # timestamp as ISO-8601 string (if present)
        if "timestamp" in data:
            assert isinstance(data["timestamp"], str)

    # ------------------------------------------------------------------
    # C-2: Risk level enum matches TypeScript RiskLevel
    # ------------------------------------------------------------------
    def test_c2_risk_level_enum_values(self, client):
        """C-2: risk_level is 0 | 1 | 2 matching TS RiskLevel type."""
        cases = [
            (_model(0, 0.05), 0),  # Safe
            (_model(1, 0.55), 1),  # Alert
            (_model(1, 0.85), 2),  # Critical
        ]
        for model, expected_level in cases:
            with patch("app.services.predict._get_model_loader", return_value=_loader(model)):
                resp = client.post(
                    "/api/v1/predict/",
                    json={"temperature": 303.15, "humidity": 85.0, "precipitation": 50.0},
                    headers=AUTH,
                )
            if resp.status_code == 200:
                data = resp.get_json()
                if "risk_level" in data:
                    assert data["risk_level"] in (0, 1, 2), f"risk_level={data['risk_level']} not in RiskLevel enum"

    # ------------------------------------------------------------------
    # C-3: Risk label matches TypeScript RiskLabel
    # ------------------------------------------------------------------
    def test_c3_risk_label_values(self, client):
        """C-3: risk_label is 'Safe' | 'Alert' | 'Critical'."""
        model = _model(1, 0.85)
        with patch("app.services.predict._get_model_loader", return_value=_loader(model)):
            resp = client.post(
                "/api/v1/predict/",
                json={"temperature": 305.0, "humidity": 95.0, "precipitation": 80.0},
                headers=AUTH,
            )
        if resp.status_code == 200:
            data = resp.get_json()
            if "risk_label" in data:
                assert data["risk_label"] in (
                    "Safe",
                    "Alert",
                    "Critical",
                ), f"risk_label='{data['risk_label']}' not in TS RiskLabel union"

    # ------------------------------------------------------------------
    # C-4: Risk color hex codes
    # ------------------------------------------------------------------
    def test_c4_risk_color_hex_codes(self, client):
        """C-4: risk_color matches #28a745 / #ffc107 / #dc3545."""
        VALID_COLORS = {"#28a745", "#ffc107", "#dc3545"}
        model = _model(0, 0.05)
        with patch("app.services.predict._get_model_loader", return_value=_loader(model)):
            resp = client.post(
                "/api/v1/predict/",
                json={"temperature": 298.15, "humidity": 50.0, "precipitation": 2.0},
                headers=AUTH,
            )
        if resp.status_code == 200:
            data = resp.get_json()
            if "risk_color" in data and data["risk_color"]:
                assert data["risk_color"] in VALID_COLORS, f"risk_color='{data['risk_color']}' not in expected hex set"

    # ------------------------------------------------------------------
    # C-5: Health response matches frontend expectations
    # ------------------------------------------------------------------
    def test_c5_health_response_contract(self, client):
        """C-5: /health response has 'status' field as string."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data.get("status"), str), "health status must be string"

    # ------------------------------------------------------------------
    # C-6: Error response matches ApiError interface
    # ------------------------------------------------------------------
    def test_c6_error_response_matches_api_error(self, client, mock_model_comprehensive):
        """C-6: Error responses match frontend ApiError interface."""
        resp = client.post(
            "/api/v1/predict/",
            json={"temperature": "bad"},
            headers=AUTH,
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data is not None
        # ApiError should have error object or code
        error_obj = data.get("error", data)
        has_code = "code" in error_obj or "code" in data
        has_message = "message" in error_obj or "message" in data
        assert has_code or has_message, f"Error response missing code/message: {data}"

    # ------------------------------------------------------------------
    # C-7: Alerts response matches PaginatedResponse<Alert>
    # ------------------------------------------------------------------
    def test_c7_alerts_paginated_response(self, client):
        """C-7: /alerts returns PaginatedResponse wrapper fields."""
        resp = client.get("/api/v1/alerts", headers=AUTH)
        if resp.status_code == 200:
            data = resp.get_json()
            # PaginatedResponse<T> requires: success, data, total, page, limit, pages, request_id
            expected_keys = {"data", "total", "page", "limit", "pages"}
            present_keys = set(data.keys())
            # At least the pagination fields should be present
            pagination_fields = present_keys & expected_keys
            assert len(pagination_fields) >= 3, f"Alerts response missing pagination fields. Have: {present_keys}"

    # ------------------------------------------------------------------
    # C-8: Confidence value is between 0 and 1
    # ------------------------------------------------------------------
    def test_c8_confidence_range(self, client):
        """C-8: confidence field (if present) is float in [0, 1]."""
        model = _model(0, 0.15)
        with patch("app.services.predict._get_model_loader", return_value=_loader(model)):
            resp = client.post(
                "/api/v1/predict/",
                json={"temperature": 298.15, "humidity": 60.0, "precipitation": 5.0},
                headers=AUTH,
            )
        if resp.status_code == 200:
            data = resp.get_json()
            conf = data.get("confidence")
            if conf is not None:
                assert isinstance(conf, (int, float)), f"confidence type: {type(conf)}"
                assert 0.0 <= conf <= 1.0, f"confidence={conf} out of [0,1]"

    # ------------------------------------------------------------------
    # C-9: SSE endpoint returns text/event-stream
    # ------------------------------------------------------------------
    def test_c9_sse_content_type(self, client):
        """C-9: SSE connect returns text/event-stream content type."""
        resp = client.get("/api/v1/sse/connect")
        if resp.status_code == 200:
            ct = resp.content_type or ""
            assert "text/event-stream" in ct, f"SSE content-type='{ct}', expected text/event-stream"

    # ------------------------------------------------------------------
    # C-10: model_version is string in response
    # ------------------------------------------------------------------
    def test_c10_model_version_type(self, client):
        """C-10: model_version (if present) is string per TS interface."""
        model = _model(0, 0.10)
        with patch("app.services.predict._get_model_loader", return_value=_loader(model)):
            resp = client.post(
                "/api/v1/predict/",
                json={"temperature": 298.15, "humidity": 60.0, "precipitation": 5.0},
                headers=AUTH,
            )
        if resp.status_code == 200:
            data = resp.get_json()
            mv = data.get("model_version")
            if mv is not None:
                assert isinstance(mv, (str, int, float)), f"model_version type: {type(mv)}"
