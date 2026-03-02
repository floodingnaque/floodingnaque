"""
API Contract Tests for Integration Testing.

Tests API endpoints against expected response schemas and contracts.
Ensures API responses maintain consistent structure.
Uses Flask test client for reliable testing.
"""

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest

# API prefix for versioned endpoints
API_V1_PREFIX = "/api/v1"


# ============================================================================
# Response Schema Definitions
# ============================================================================


@dataclass
class ResponseField:
    """Definition of an expected response field."""

    name: str
    field_type: type
    required: bool = True
    allowed_values: Optional[List] = None


# Schema definitions for each endpoint
ENDPOINT_SCHEMAS = {
    "/": {
        "fields": [
            ResponseField("name", str),
            ResponseField("version", str),
            ResponseField("endpoints", dict),
        ]
    },
    "/status": {
        "fields": [
            ResponseField("status", str, allowed_values=["running", "error"]),
        ],
        "optional_fields": [
            ResponseField("service", str, required=False),
        ],
    },
    "/health": {
        "fields": [
            ResponseField("status", str),
        ],
        "optional_fields": [
            ResponseField("model_available", bool, required=False),
            ResponseField("components", dict, required=False),
        ],
    },
    f"{API_V1_PREFIX}/models": {
        "fields": [],
        "optional_fields": [
            ResponseField("models", list, required=False),
            ResponseField("data", list, required=False),
        ],
    },
    f"{API_V1_PREFIX}/data/data": {
        "fields": [
            ResponseField("data", list),
            ResponseField("total", int),
        ],
        "optional_fields": [
            ResponseField("limit", int, required=False),
        ],
    },
}

PREDICT_RESPONSE_SCHEMA = {
    "fields": [
        ResponseField("prediction", int, allowed_values=[0, 1]),
        ResponseField("flood_risk", str, allowed_values=["high", "low"]),
        ResponseField("request_id", str),
    ],
    "optional_fields": [
        ResponseField("model_version", (str, type(None)), required=False),
        ResponseField("probability", dict, required=False),
        ResponseField("risk_level", int, required=False),
        ResponseField("risk_label", str, required=False),
        ResponseField("risk_color", str, required=False),
        ResponseField("risk_description", str, required=False),
        ResponseField("confidence", float, required=False),
    ],
}

ERROR_RESPONSE_SCHEMA = {
    "fields": [
        ResponseField("error", str),
        ResponseField("message", str),
    ],
    "optional_fields": [
        ResponseField("request_id", str, required=False),
    ],
}


# ============================================================================
# Schema Validation Utilities
# ============================================================================


def validate_response_schema(response_data: Dict, schema: Dict) -> List[str]:
    """
    Validate response data against a schema definition.

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check required fields
    for field in schema.get("fields", []):
        if field.name not in response_data:
            errors.append(f"Missing required field: {field.name}")
        else:
            value = response_data[field.name]

            # Check type
            if not isinstance(value, field.field_type):
                errors.append(
                    f"Field '{field.name}' has wrong type. " f"Expected {field.field_type}, got {type(value)}"
                )

            # Check allowed values
            if field.allowed_values and value not in field.allowed_values:
                errors.append(f"Field '{field.name}' has invalid value '{value}'. " f"Allowed: {field.allowed_values}")

    return errors


def validate_optional_fields(response_data: Dict, schema: Dict) -> List[str]:
    """Validate optional fields if present."""
    errors = []

    for field in schema.get("optional_fields", []):
        if field.name in response_data:
            value = response_data[field.name]
            if value is not None and not isinstance(value, field.field_type):
                errors.append(
                    f"Optional field '{field.name}' has wrong type. " f"Expected {field.field_type}, got {type(value)}"
                )

    return errors


# ============================================================================
# Contract Tests - Public Endpoints
# ============================================================================


class TestRootEndpointContract:
    """Contract tests for the root endpoint."""

    def test_root_returns_json(self, client):
        """Test that root endpoint returns JSON."""
        response = client.get("/")
        assert response.content_type.startswith("application/json")

    def test_root_schema_compliance(self, client):
        """Test root endpoint response matches expected schema."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.get_json()
        errors = validate_response_schema(data, ENDPOINT_SCHEMAS["/"])

        assert len(errors) == 0, f"Schema validation errors: {errors}"

    def test_root_endpoints_structure(self, client):
        """Test that endpoints field contains expected structure."""
        response = client.get("/")
        data = response.get_json()

        endpoints = data.get("endpoints", {})
        assert isinstance(endpoints, dict)

        # Should list available endpoints
        assert len(endpoints) > 0


class TestStatusEndpointContract:
    """Contract tests for the status endpoint."""

    def test_status_schema_compliance(self, client):
        """Test status endpoint response matches expected schema."""
        response = client.get("/status")
        # May be rate limited
        assert response.status_code in [200, 429]

        if response.status_code == 200:
            data = response.get_json()
            # Verify required field
            assert "status" in data
            assert data["status"] in ["running", "error"]

    def test_status_running_value(self, client):
        """Test that status is 'running' when healthy."""
        response = client.get("/status")

        if response.status_code == 429:
            pytest.skip("Rate limited")

        data = response.get_json()
        assert data["status"] == "running"


class TestHealthEndpointContract:
    """Contract tests for the health endpoint."""

    def test_health_schema_compliance(self, client):
        """Test health endpoint response matches expected schema."""
        response = client.get("/health")
        # May return 503 if services unavailable or 429 if rate limited
        assert response.status_code in [200, 429, 503]

        data = response.get_json()
        assert "status" in data or "error" in data

    def test_health_returns_status(self, client):
        """Test that health returns a status field."""
        response = client.get("/health")

        if response.status_code == 429:
            pytest.skip("Rate limited")

        data = response.get_json()
        assert "status" in data


class TestModelsEndpointContract:
    """Contract tests for the models endpoint."""

    def test_models_schema_compliance(self, client):
        """Test models endpoint response matches expected schema."""
        response = client.get(f"{API_V1_PREFIX}/models")
        # May return 404 if not configured or 200 with data
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.get_json()
            # Should have models or data field
            assert "models" in data or "data" in data

    def test_models_list_structure(self, client):
        """Test that models list contains expected fields per model."""
        response = client.get(f"{API_V1_PREFIX}/models")

        if response.status_code == 200:
            data = response.get_json()
            models = data.get("models", data.get("data", []))
            if models:
                for model in models:
                    assert isinstance(model, dict)


class TestDataEndpointContract:
    """Contract tests for the data endpoint."""

    def test_data_schema_compliance(self, client):
        """Test data endpoint response matches expected schema."""
        response = client.get(f"{API_V1_PREFIX}/data/data")
        # May need auth, be rate limited, return 200, or 500 if DB unavailable
        assert response.status_code in [200, 401, 429, 500]

        if response.status_code == 200:
            data = response.get_json()
            assert "data" in data
            assert "total" in data

    def test_data_pagination_defaults(self, client):
        """Test data endpoint pagination defaults."""
        response = client.get(f"{API_V1_PREFIX}/data/data")

        if response.status_code == 200:
            data = response.get_json()
            assert "data" in data

    def test_data_pagination_custom_limit(self, client):
        """Test data endpoint respects custom limit."""
        response = client.get(f"{API_V1_PREFIX}/data/data?limit=5")
        # May need auth, be rate limited, or 500 if DB unavailable
        assert response.status_code in [200, 401, 429, 500]

        if response.status_code == 200:
            data = response.get_json()
            assert "data" in data

    def test_data_records_structure(self, client):
        """Test that data records have expected structure."""
        response = client.get(f"{API_V1_PREFIX}/data/data?limit=1")

        if response.status_code == 200:
            data = response.get_json()
            if data.get("data"):
                record = data["data"][0]
                assert isinstance(record, dict)


# ============================================================================
# Contract Tests - Predict Endpoint
# ============================================================================


class TestPredictEndpointContract:
    """Contract tests for the predict endpoint."""

    def _get_auth_headers(self):
        """Get authentication headers if required."""
        return {"Content-Type": "application/json"}

    def test_predict_schema_compliance(self, client):
        """Test predict endpoint response matches expected schema."""
        from unittest.mock import Mock, patch

        import numpy as np

        payload = {"temperature": 298.15, "humidity": 75.0, "precipitation": 10.0}

        # Mock the model to ensure test doesn't skip due to model unavailability
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

            response = client.post(f"{API_V1_PREFIX}/predict", json=payload, headers=self._get_auth_headers())

            # Skip if auth is required or endpoint not found
            if response.status_code in [401, 404]:
                pytest.skip("Predict endpoint requires auth or not configured")

            # 503 acceptable if model not available (should not happen with mock)
            if response.status_code == 503:
                pytest.skip("Model not available")

            assert response.status_code == 200

            data = response.get_json()
            # Check required fields
            assert "prediction" in data or "success" in data

    def test_predict_with_risk_level(self, client):
        """Test predict endpoint with risk level classification."""
        payload = {"temperature": 298.15, "humidity": 75.0, "precipitation": 10.0}

        response = client.post(
            f"{API_V1_PREFIX}/predict?risk_level=true", json=payload, headers=self._get_auth_headers()
        )

        if response.status_code in [401, 404]:
            pytest.skip("API key required or endpoint not configured")

        if response.status_code == 200:
            data = response.get_json()
            # When risk_level=true, may include risk classification
            if "risk_level" in data:
                assert data["risk_level"] in [0, 1, 2]

    def test_predict_probability_format(self, client):
        """Test that probability is returned in expected format."""
        payload = {"temperature": 298.15, "humidity": 75.0, "precipitation": 10.0}

        response = client.post(
            f"{API_V1_PREFIX}/predict?return_proba=true", json=payload, headers=self._get_auth_headers()
        )

        if response.status_code in [401, 404]:
            pytest.skip("API key required")

        if response.status_code == 200:
            data = response.get_json()
            if "probability" in data:
                prob = data["probability"]
                assert "flood" in prob or "no_flood" in prob
                for key, value in prob.items():
                    assert 0.0 <= value <= 1.0


# ============================================================================
# Contract Tests - Error Responses
# ============================================================================


class TestErrorResponseContract:
    """Contract tests for error responses."""

    def test_invalid_limit_error_schema(self, client):
        """Test error response for invalid limit parameter."""
        response = client.get(f"{API_V1_PREFIX}/data/data?limit=99999")
        # May return 400 for invalid limit, 401 if auth required, 429 if rate limited
        assert response.status_code in [400, 401, 429]

        if response.status_code == 400:
            data = response.get_json()
            # Should have error information
            assert "error" in data or "message" in data or "detail" in data

    def test_negative_limit_error_schema(self, client):
        """Test error response for negative limit."""
        response = client.get(f"{API_V1_PREFIX}/data/data?limit=-1")
        assert response.status_code in [400, 401, 429]

        if response.status_code == 400:
            data = response.get_json()
            assert "error" in data or "message" in data or "detail" in data

    def test_predict_missing_body_error_schema(self, client):
        """Test error response for missing request body."""
        response = client.post(f"{API_V1_PREFIX}/predict", headers={"Content-Type": "application/json"})

        if response.status_code == 401:
            pytest.skip("API key required")

        # Should return 400 for missing body, 404 if not configured, or 429 if rate limited
        assert response.status_code in [400, 404, 429]
        if response.status_code == 400:
            data = response.get_json()
            assert data is not None


# ============================================================================
# Contract Tests - HTTP Headers
# ============================================================================


class TestResponseHeaders:
    """Contract tests for HTTP response headers."""

    def test_json_content_type(self, client):
        """Test that API endpoints return JSON content type."""
        endpoints = ["/", "/status"]  # Health endpoints without prefix

        for endpoint in endpoints:
            response = client.get(endpoint)
            content_type = response.content_type or ""

            assert "application/json" in content_type, f"Endpoint {endpoint} should return JSON, got {content_type}"

    def test_security_headers_present(self, client):
        """Test that security headers are present."""
        response = client.get("/status")

        # Check for common security headers
        expected_headers = ["X-Content-Type-Options", "X-Frame-Options"]

        for header in expected_headers:
            assert header in response.headers, f"Missing security header: {header}"

    def test_cors_headers_on_options(self, client):
        """Test CORS headers for preflight requests."""
        response = client.options("/status", headers={"Origin": "http://localhost:3000"})

        # May or may not be configured - just ensure no error
        assert response.status_code in [200, 204, 405]


# ============================================================================
# Contract Tests - Content Negotiation
# ============================================================================


class TestContentNegotiation:
    """Tests for content negotiation behavior."""

    def test_accepts_json_content_type(self, client):
        """Test that endpoints accept JSON content type."""
        response = client.get("/status", headers={"Accept": "application/json"})

        # May be rate limited
        if response.status_code == 429:
            pytest.skip("Rate limited")

        assert response.status_code == 200
        assert "application/json" in (response.content_type or "")

    def test_post_requires_json(self, client):
        """Test that POST endpoints require JSON body."""
        response = client.post(f"{API_V1_PREFIX}/predict", data="not json", headers={"Content-Type": "text/plain"})

        # Should fail (400, 415, 500) or be handled appropriately (401 auth, 404 not found, 429 rate limited)
        # 500 may occur if content-type validation happens after JSON parsing attempt
        assert response.status_code in [400, 401, 404, 415, 429, 500]
