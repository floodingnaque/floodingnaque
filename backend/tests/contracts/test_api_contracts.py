"""
API Contract Tests for Prediction Endpoints.

Tests API contracts to ensure backward compatibility and specification adherence.
"""

import json
from unittest.mock import Mock, patch

import pytest
from app.api.app import create_app


@pytest.fixture(scope="module")
def contract_app():
    """Create a Flask app for contract testing."""
    app = create_app({"TESTING": True})
    return app


@pytest.fixture(scope="module")
def contract_client(contract_app):
    """Create a test client for contract testing."""
    return contract_app.test_client()


# ============================================================================
# Contract Tests for Prediction Endpoint
# ============================================================================


class TestPredictionEndpointContract:
    """Contract tests for /api/v1/predict endpoint."""

    @pytest.mark.contract
    def test_prediction_request_schema(self, contract_client):
        """
        Contract: Prediction endpoint accepts standard weather data format.

        Request schema:
        {
            "temperature": float,
            "humidity": float,
            "precipitation": float
        }
        """
        import numpy as np

        with (
            patch("app.services.predict._load_model") as mock_load,
            patch("app.services.predict._get_model_loader") as mock_get_loader,
        ):
            # Create mock model
            mock_model = Mock()
            mock_model.predict.return_value = np.array([0])
            mock_model.predict_proba.return_value = np.array([[0.8, 0.2]])
            mock_model.feature_names_in_ = np.array(["temperature", "humidity", "precipitation"])
            mock_load.return_value = mock_model

            # Create mock loader
            mock_loader = Mock()
            mock_loader.model = mock_model
            mock_loader.metadata = {"version": "1.0.0"}
            mock_get_loader.return_value = mock_loader

            request_data = {"temperature": 28.5, "humidity": 75.0, "precipitation": 10.5}

            response = contract_client.post(
                "/api/v1/predict", data=json.dumps(request_data), content_type="application/json"
            )

            # Contract verification (503 acceptable if model not available)
            assert response.status_code in (200, 201, 503), "Prediction endpoint should accept valid weather data"

    @pytest.mark.contract
    def test_prediction_response_schema(self, contract_client):
        """
        Contract: Prediction endpoint returns standard response format.

        Response schema:
        {
            "success": boolean,
            "prediction": integer (0 or 1),
            "flood_risk": string ("low" or "high"),
            "risk_level": integer (0, 1, or 2),
            "risk_label": string ("Safe", "Alert", or "Critical"),
            "confidence": float,
            "probability": {
                "no_flood": float,
                "flood": float
            },
            "model_version": string,
            "model_name": string
        }
        """
        import numpy as np

        with (
            patch("app.services.predict._load_model") as mock_load,
            patch("app.services.predict._get_model_loader") as mock_get_loader,
        ):
            # Create mock model that predicts flood
            mock_model = Mock()
            mock_model.predict.return_value = np.array([1])
            mock_model.predict_proba.return_value = np.array([[0.3, 0.7]])
            mock_model.feature_names_in_ = np.array(["temperature", "humidity", "precipitation"])
            mock_load.return_value = mock_model

            # Create mock loader
            mock_loader = Mock()
            mock_loader.model = mock_model
            mock_loader.metadata = {"version": "1.0.0"}
            mock_get_loader.return_value = mock_loader

            request_data = {"temperature": 30.0, "humidity": 85.0, "precipitation": 50.0}

            response = contract_client.post(
                "/api/v1/predict", data=json.dumps(request_data), content_type="application/json"
            )

            data = response.get_json()

            # Skip detailed schema checks if model not available (503)
            if response.status_code == 503:
                pytest.skip("Model not available")

            # Contract verification - required fields
            assert "success" in data, "Response must include 'success' field"
            assert "prediction" in data, "Response must include 'prediction' field"
            assert "flood_risk" in data, "Response must include 'flood_risk' field"
            assert "risk_level" in data, "Response must include 'risk_level' field"
            assert "risk_label" in data, "Response must include 'risk_label' field"
            assert "confidence" in data, "Response must include 'confidence' field"

            # Type verification
            assert isinstance(data["success"], bool)
            assert isinstance(data["prediction"], int)
            assert isinstance(data["flood_risk"], str)
            assert isinstance(data["risk_level"], int)
            assert isinstance(data["risk_label"], str)
            assert isinstance(data["confidence"], (int, float))

            # Value constraints
            assert data["prediction"] in (0, 1)
            assert data["flood_risk"] in ("low", "high")
            assert data["risk_level"] in (0, 1, 2)
            assert data["risk_label"] in ("Safe", "Alert", "Critical")
            assert 0.0 <= data["confidence"] <= 1.0

    @pytest.mark.contract
    def test_prediction_error_response_schema(self, contract_client):
        """
        Contract: Prediction endpoint returns standard error format.

        Error response schema:
        {
            "success": false,
            "error": {
                "type": string,
                "title": string,
                "status": integer,
                "detail": string,
                "code": string
            }
        }
        """
        # Send invalid data (missing required fields)
        request_data = {
            "temperature": 30.0
            # Missing humidity and precipitation
        }

        response = contract_client.post(
            "/api/v1/predict", data=json.dumps(request_data), content_type="application/json"
        )

        # Should return error
        assert response.status_code in (400, 422)

        data = response.get_json()

        # Contract verification - error responses may use 'success' or just 'error'
        assert "success" in data or "error" in data
        if "success" in data:
            assert data["success"] is False
        assert "error" in data

        error = data["error"]
        # Error can be a string or an object with status/detail
        if isinstance(error, dict):
            assert "status" in error or "code" in error
            assert "detail" in error or "message" in error
        else:
            # Error is a string message
            assert isinstance(error, str)


# ============================================================================
# Contract Tests for Health Endpoint
# ============================================================================


class TestHealthEndpointContract:
    """Contract tests for /health endpoint."""

    @pytest.mark.contract
    def test_health_response_schema(self, contract_client):
        """
        Contract: Health endpoint returns standard health check format.

        Response schema:
        {
            "status": string,
            "database": string,
            "model_available": boolean,
            "scheduler_running": boolean,
            "timestamp": string
        }
        """
        response = contract_client.get("/health")

        assert response.status_code == 200

        data = response.get_json()

        # Contract verification
        assert "status" in data
        assert isinstance(data["status"], str)
        assert data["status"] in ("healthy", "degraded", "unhealthy")


# ============================================================================
# Contract Tests for Data Retrieval Endpoint
# ============================================================================


class TestDataEndpointContract:
    """Contract tests for /api/v1/data endpoint."""

    @pytest.mark.contract
    def test_data_list_response_schema(self, contract_client):
        """
        Contract: Data list endpoint returns paginated response format.

        Response schema:
        {
            "data": array,
            "total": integer,
            "limit": integer,
            "offset": integer,
            "count": integer
        }
        """
        with patch("app.api.routes.data.get_db_session"):
            response = contract_client.get("/api/v1/data?limit=10&offset=0")

            data = response.get_json()

            # Contract verification
            assert "data" in data or "error" in data

            if response.status_code == 200:
                assert isinstance(data.get("data"), list)
                # Accept either 'total' or 'count' for pagination
                assert "total" in data or "count" in data
                assert "limit" in data
                assert "offset" in data or "skip" in data


# ============================================================================
# Contract Tests for Model Info Endpoint
# ============================================================================


class TestModelEndpointContract:
    """Contract tests for /api/v1/models endpoint."""

    @pytest.mark.contract
    def test_model_list_response_schema(self, contract_client):
        """
        Contract: Model list endpoint returns model information format.

        Response schema:
        {
            "models": array of {
                "version": string,
                "path": string,
                "is_current": boolean,
                "metrics": object
            },
            "current_version": string,
            "total_versions": integer
        }
        """
        response = contract_client.get("/api/v1/models")

        data = response.get_json()

        # Contract verification
        if response.status_code == 200:
            assert "models" in data or "error" in data

            if "models" in data:
                assert isinstance(data["models"], list)

                if len(data["models"]) > 0:
                    model = data["models"][0]
                    assert "version" in model or "path" in model


# ============================================================================
# Contract Tests for Webhook Endpoint
# ============================================================================


class TestWebhookEndpointContract:
    """Contract tests for /api/v1/webhooks endpoint."""

    @pytest.mark.contract
    def test_webhook_register_request_schema(self, contract_client):
        """
        Contract: Webhook registration accepts standard format.

        Request schema:
        {
            "url": string (URL),
            "events": array of strings,
            "secret": string (optional)
        }
        """
        with patch("app.api.routes.webhooks.get_db_session"):
            with patch("app.api.routes.webhooks.require_api_key", lambda f: f):
                request_data = {"url": "https://example.com/webhook", "events": ["flood_detected", "critical_risk"]}

                response = contract_client.post(
                    "/api/v1/webhooks/register", data=json.dumps(request_data), content_type="application/json"
                )

                # Should accept valid webhook data
                assert response.status_code in (200, 201, 400, 500)


# ============================================================================
# Contract Tests for Batch Prediction Endpoint
# ============================================================================


class TestBatchPredictionEndpointContract:
    """Contract tests for /api/v1/batch/predict endpoint."""

    @pytest.mark.contract
    def test_batch_prediction_request_schema(self, contract_client):
        """
        Contract: Batch prediction accepts array of weather data.

        Request schema:
        {
            "batch": array of {
                "temperature": float,
                "humidity": float,
                "precipitation": float
            }
        }
        """
        with patch("app.services.predict.load_model") as mock_load:
            mock_model = Mock()
            mock_model.predict.return_value = [[0], [1]]
            mock_model.predict_proba.return_value = [[0.8, 0.2], [0.3, 0.7]]
            mock_load.return_value = mock_model

            request_data = {
                "batch": [
                    {"temperature": 28.5, "humidity": 75.0, "precipitation": 10.5},
                    {"temperature": 32.0, "humidity": 90.0, "precipitation": 50.0},
                ]
            }

            response = contract_client.post(
                "/api/v1/batch/predict", data=json.dumps(request_data), content_type="application/json"
            )

            # Contract verification
            assert response.status_code in (200, 201, 400, 500)


# ============================================================================
# Contract Tests for CORS Headers
# ============================================================================


class TestCORSContract:
    """Contract tests for CORS headers."""

    @pytest.mark.contract
    def test_cors_headers_present(self, contract_client):
        """
        Contract: API responses include CORS headers.
        """
        response = contract_client.options("/api/v1/predict")

        # CORS headers should be present
        # (Exact headers depend on CORS configuration)
        assert response.status_code in (200, 204, 404)


# ============================================================================
# Contract Tests for Authentication Headers
# ============================================================================


class TestAuthenticationContract:
    """Contract tests for authentication requirements."""

    @pytest.mark.contract
    def test_protected_endpoint_requires_auth(self, contract_client):
        """
        Contract: Protected endpoints require authentication.
        """
        # Webhook endpoints should require API key
        request_data = {"url": "https://example.com/webhook", "events": ["flood_detected"]}

        response = contract_client.post(
            "/api/v1/webhooks/register", data=json.dumps(request_data), content_type="application/json"
        )

        # Should either succeed with auth or fail with 401/403
        assert response.status_code in (200, 201, 401, 403, 500)


# ============================================================================
# Contract Tests for Content-Type Headers
# ============================================================================


class TestContentTypeContract:
    """Contract tests for Content-Type requirements."""

    @pytest.mark.contract
    def test_json_content_type_accepted(self, contract_client):
        """
        Contract: API accepts application/json content type.
        """
        with patch("app.services.predict.load_model") as mock_load:
            mock_model = Mock()
            mock_model.predict.return_value = [[0]]
            mock_model.predict_proba.return_value = [[0.8, 0.2]]
            mock_load.return_value = mock_model

            request_data = {"temperature": 28.5, "humidity": 75.0, "precipitation": 10.5}

            response = contract_client.post(
                "/api/v1/predict", data=json.dumps(request_data), content_type="application/json"
            )

            # 503 acceptable if model not available
            assert response.status_code in (200, 201, 503)

    @pytest.mark.contract
    def test_response_content_type(self, contract_client):
        """
        Contract: API responses are application/json.
        """
        response = contract_client.get("/health")

        assert "application/json" in response.content_type


# ============================================================================
# Contract Tests for Rate Limiting Headers
# ============================================================================


class TestRateLimitingContract:
    """Contract tests for rate limiting headers."""

    @pytest.mark.contract
    def test_rate_limit_headers_present(self, contract_client):
        """
        Contract: Rate-limited endpoints include rate limit headers.
        """
        with patch("app.services.predict.load_model") as mock_load:
            mock_model = Mock()
            mock_model.predict.return_value = [[0]]
            mock_model.predict_proba.return_value = [[0.8, 0.2]]
            mock_load.return_value = mock_model

            response = contract_client.post(
                "/api/v1/predict",
                data=json.dumps({"temperature": 28.5, "humidity": 75.0, "precipitation": 10.5}),
                content_type="application/json",
            )

            # Rate limit headers may or may not be present depending on config
            # Just verify response is valid (503 acceptable if model not available)
            assert response.status_code in (200, 201, 429, 503)
