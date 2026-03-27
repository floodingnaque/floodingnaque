"""Unit tests for the /api/v1/predict/simulate endpoint."""

import pytest
from unittest.mock import patch, MagicMock


class TestSimulateEndpoint:
    """Tests for the flood simulation what-if endpoint."""

    SIMULATE_URL = "/api/v1/predict/simulate"

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_simulate_defaults(self, client, api_headers):
        """Simulate with default parameters returns 200 and expected shape."""
        mock_result = {
            "prediction": 0,
            "probability": 0.12,
            "risk_level": "Safe",
            "risk_label": "Safe",
            "risk_color": "green",
            "risk_description": "No flood risk",
            "confidence": 0.88,
            "model_version": "v6",
            "explanation": {"factors": []},
            "features_used": ["temperature", "humidity"],
        }

        with patch("app.api.routes.predict.predict_flood", return_value=mock_result):
            response = client.post(self.SIMULATE_URL, json={}, headers=api_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["simulation"] is True
        assert data["prediction"] == 0
        assert data["flood_risk"] == "low"
        assert data["probability"] == 0.12
        assert data["risk_level"] == "Safe"
        assert data["explanation"] is not None
        assert data["preset"] is None
        assert "input_parameters" in data
        assert "available_presets" in data
        assert data["input_parameters"]["temperature"] == 303.15

    def test_simulate_with_preset(self, client, api_headers):
        """Simulate with a named preset overrides defaults."""
        mock_result = {
            "prediction": 1,
            "probability": 0.87,
            "risk_level": "Critical",
            "risk_label": "Critical",
            "risk_color": "red",
            "risk_description": "Severe flood risk",
            "confidence": 0.87,
            "model_version": "v6",
        }

        with patch("app.api.routes.predict.predict_flood", return_value=mock_result) as mock_pf:
            response = client.post(
                self.SIMULATE_URL,
                json={"preset": "typhoon"},
                headers=api_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["prediction"] == 1
        assert data["flood_risk"] == "high"
        assert data["preset"] == "typhoon"
        # Typhoon preset has wind_speed=45
        assert data["input_parameters"]["wind_speed"] == 45.0
        assert data["input_parameters"]["humidity"] == 98.0

    def test_simulate_with_custom_overrides(self, client, api_headers):
        """Explicit parameter values override defaults."""
        mock_result = {"prediction": 0, "model_version": "v6"}

        with patch("app.api.routes.predict.predict_flood", return_value=mock_result):
            response = client.post(
                self.SIMULATE_URL,
                json={"temperature": 310.0, "humidity": 50.0},
                headers=api_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["input_parameters"]["temperature"] == 310.0
        assert data["input_parameters"]["humidity"] == 50.0
        # Others should still be defaults
        assert data["input_parameters"]["precipitation"] == 5.0

    def test_simulate_preset_with_overrides(self, client, api_headers):
        """Custom values can override preset values."""
        mock_result = {"prediction": 0, "model_version": "v6"}

        with patch("app.api.routes.predict.predict_flood", return_value=mock_result):
            response = client.post(
                self.SIMULATE_URL,
                json={"preset": "heavy_monsoon", "humidity": 60.0},
                headers=api_headers,
            )

        assert response.status_code == 200
        data = response.get_json()
        # Override takes precedence over preset value of 95.0
        assert data["input_parameters"]["humidity"] == 60.0

    def test_simulate_scalar_prediction(self, client, api_headers):
        """Handle predict_flood returning a scalar instead of dict."""
        with patch("app.api.routes.predict.predict_flood", return_value=1):
            response = client.post(self.SIMULATE_URL, json={}, headers=api_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data["prediction"] == 1
        assert data["flood_risk"] == "high"

    def test_simulate_all_presets_valid(self, client, api_headers):
        """All four preset names are accepted."""
        mock_result = {"prediction": 0, "model_version": "v6"}

        for preset in ("normal", "heavy_monsoon", "typhoon", "high_tide_rain"):
            with patch("app.api.routes.predict.predict_flood", return_value=mock_result):
                response = client.post(
                    self.SIMULATE_URL,
                    json={"preset": preset},
                    headers=api_headers,
                )
            assert response.status_code == 200, f"Preset '{preset}' returned {response.status_code}"

    # ------------------------------------------------------------------
    # Validation errors
    # ------------------------------------------------------------------

    def test_simulate_unknown_preset(self, client, api_headers):
        """Unknown preset returns 400."""
        response = client.post(
            self.SIMULATE_URL,
            json={"preset": "earthquake"},
            headers=api_headers,
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "Unknown preset" in data.get("detail", data.get("message", ""))

    def test_simulate_non_numeric_param(self, client, api_headers):
        """Non-numeric value for a numeric field returns 400."""
        response = client.post(
            self.SIMULATE_URL,
            json={"temperature": "hot"},
            headers=api_headers,
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "number" in data.get("detail", data.get("message", "")).lower()

    def test_simulate_non_dict_body(self, client, api_headers):
        """Array or non-dict body returns 400."""
        response = client.post(
            self.SIMULATE_URL,
            data="[1,2,3]",
            headers=api_headers,
        )
        assert response.status_code == 400

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    def test_simulate_model_not_found(self, client, api_headers):
        """FileNotFoundError from predict_flood returns 404."""
        with patch("app.api.routes.predict.predict_flood", side_effect=FileNotFoundError("no model")):
            response = client.post(self.SIMULATE_URL, json={}, headers=api_headers)

        assert response.status_code == 404

    def test_simulate_internal_error(self, client, api_headers):
        """Unhandled exception returns 500."""
        with patch("app.api.routes.predict.predict_flood", side_effect=RuntimeError("boom")):
            response = client.post(self.SIMULATE_URL, json={}, headers=api_headers)

        assert response.status_code == 500

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def test_simulate_no_auth(self, client):
        """Request without API key or token is rejected."""
        response = client.post(self.SIMULATE_URL, json={})
        assert response.status_code in (401, 403)
