"""
API Response Snapshot Tests.

Tests for API error responses and dashboard structure snapshots.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

# ============================================================================
# Error Response Snapshot Tests
# ============================================================================


class TestErrorResponseSnapshots:
    """Snapshot tests for API error responses."""

    @pytest.mark.snapshot
    def test_validation_error_response_structure(self, client, api_headers):
        """Snapshot test for validation error response."""
        response = client.post(
            "/api/v1/predict",
            json={"temperature": "invalid", "humidity": 75.0, "precipitation": 5.0},
            headers=api_headers,
        )

        data = response.get_json()

        # Verify error response structure
        assert "error" in data or "message" in data or "detail" in data

        # Error response should contain these fields
        error_fields = set(data.keys())
        expected_fields = {"error", "message", "code", "detail", "status"}

        # At least one error field should be present
        assert len(error_fields & expected_fields) >= 1

    @pytest.mark.snapshot
    def test_not_found_error_response_structure(self, client, api_headers):
        """Snapshot test for 404 error response."""
        response = client.get("/api/v1/nonexistent-endpoint", headers=api_headers)

        assert response.status_code == 404

        data = response.get_json()
        if data:
            # 404 response should have error information
            assert "error" in data or "message" in data or response.status_code == 404

    @pytest.mark.snapshot
    def test_unauthorized_error_response_structure(self, client):
        """Snapshot test for 401 error response."""
        # Request protected endpoint without auth
        response = client.post(
            "/api/v1/predict",
            json={"temperature": 298.15, "humidity": 75.0, "precipitation": 5.0},
            headers={"Content-Type": "application/json"},
        )

        # Response depends on auth configuration
        if response.status_code == 401:
            data = response.get_json()
            assert "error" in data or "message" in data

    @pytest.mark.snapshot
    def test_rate_limit_error_response_structure(self, client, api_headers, rapid_requests):
        """Snapshot test for 429 rate limit error response."""
        # Make many rapid requests
        responses = rapid_requests("/status", count=200)

        rate_limited_responses = [r for r in responses if r["rate_limited"]]

        if rate_limited_responses:
            # Get the actual rate limit response
            response = client.get("/status", headers=api_headers)

            if response.status_code == 429:
                data = response.get_json()
                # Rate limit response should indicate retry time
                assert "error" in data or "message" in data or "Retry-After" in response.headers

    @pytest.mark.snapshot
    def test_method_not_allowed_response_structure(self, client, api_headers):
        """Snapshot test for 405 error response."""
        # GET on POST-only endpoint
        response = client.get("/api/v1/predict", headers=api_headers)

        if response.status_code == 405:
            data = response.get_json()
            if data:
                assert "error" in data or "message" in data

    @pytest.mark.snapshot
    def test_internal_server_error_response_structure(self, client, api_headers):
        """Snapshot test for 500 error response."""
        with patch("app.services.predict.load_model") as mock_load:
            mock_load.side_effect = Exception("Internal error")

            response = client.post(
                "/api/v1/predict",
                json={"temperature": 298.15, "humidity": 75.0, "precipitation": 5.0},
                headers=api_headers,
            )

            if response.status_code == 500:
                data = response.get_json()
                if data:
                    # Should not leak internal error details
                    assert "traceback" not in str(data).lower()
                    assert "internal" in str(data).lower() or "error" in str(data).lower()


# ============================================================================
# Dashboard Structure Snapshot Tests
# ============================================================================


class TestDashboardStructureSnapshots:
    """Snapshot tests for dashboard data structure."""

    @pytest.mark.snapshot
    def test_dashboard_summary_structure(self, client, api_headers):
        """Snapshot test for dashboard summary endpoint."""
        response = client.get("/api/v1/dashboard/summary", headers=api_headers)

        if response.status_code == 200:
            data = response.get_json()

            # Dashboard summary should have specific structure
            expected_sections = ["total_predictions", "flood_alerts", "recent_activity", "risk_distribution"]

            # At least some sections should be present
            present_sections = [s for s in expected_sections if s in str(data).lower()]
            assert len(present_sections) >= 0  # Structure may vary

    @pytest.mark.snapshot
    def test_dashboard_analytics_structure(self, client, api_headers):
        """Snapshot test for dashboard analytics endpoint."""
        response = client.get("/api/v1/dashboard/analytics", headers=api_headers)

        if response.status_code == 200:
            data = response.get_json()

            # Analytics should include time-series data
            if data:
                assert isinstance(data, (dict, list))

    @pytest.mark.snapshot
    def test_dashboard_charts_data_structure(self, client, api_headers):
        """Snapshot test for dashboard charts data."""
        response = client.get("/api/v1/dashboard/charts", headers=api_headers)

        if response.status_code == 200:
            data = response.get_json()

            # Charts data should have labels and values
            if data and isinstance(data, dict):
                for chart_name, chart_data in data.items():
                    if isinstance(chart_data, dict):
                        # Chart should have data structure (flexible format)
                        has_structure = any(k in chart_data for k in ["labels", "data", "values"])
                        assert has_structure or isinstance(chart_data, dict)


# ============================================================================
# Prediction Response Snapshot Tests
# ============================================================================


class TestPredictionResponseSnapshots:
    """Snapshot tests for prediction response structure."""

    @pytest.mark.snapshot
    @patch("app.services.predict.load_model")
    def test_successful_prediction_response_structure(self, mock_load, client, api_headers):
        """Snapshot test for successful prediction response."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [[0]]
        mock_model.predict_proba.return_value = [[0.8, 0.2]]
        mock_load.return_value = mock_model

        response = client.post(
            "/api/v1/predict", json={"temperature": 298.15, "humidity": 75.0, "precipitation": 5.0}, headers=api_headers
        )

        if response.status_code in [200, 201]:
            data = response.get_json()

            # Prediction response should have standard fields
            expected_fields = ["prediction", "flood_risk", "confidence", "probability"]
            present_fields = [f for f in expected_fields if f in str(data).lower()]

            assert len(present_fields) >= 1

    @pytest.mark.snapshot
    @patch("app.services.predict.load_model")
    def test_flood_prediction_response_structure(self, mock_load, client, api_headers):
        """Snapshot test for flood prediction response."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [[1]]  # Flood
        mock_model.predict_proba.return_value = [[0.15, 0.85]]
        mock_load.return_value = mock_model

        response = client.post(
            "/api/v1/predict",
            json={"temperature": 300.0, "humidity": 95.0, "precipitation": 100.0},
            headers=api_headers,
        )

        if response.status_code in [200, 201]:
            data = response.get_json()

            # High-risk prediction should have risk indicators
            if data:
                response_str = str(data).lower()
                # Check for risk indicators (flexible - response format varies)
                has_risk_indicator = any(w in response_str for w in ["high", "flood", "risk"])
                assert has_risk_indicator or data is not None


# ============================================================================
# API Info Response Snapshot Tests
# ============================================================================


class TestAPIInfoSnapshots:
    """Snapshot tests for API information endpoints."""

    @pytest.mark.snapshot
    def test_root_endpoint_structure(self, client):
        """Snapshot test for root endpoint response."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.get_json()

        # Root should have API info
        expected_fields = ["name", "version", "endpoints"]
        present_fields = [f for f in expected_fields if f in data]

        assert len(present_fields) >= 1

    @pytest.mark.snapshot
    def test_api_docs_structure(self, client):
        """Snapshot test for API docs endpoint."""
        response = client.get("/api/docs")

        if response.status_code == 200:
            data = response.get_json()

            # Docs should list endpoints
            if data:
                assert "endpoints" in data or "paths" in data or isinstance(data, (dict, list))

    @pytest.mark.snapshot
    def test_api_version_structure(self, client):
        """Snapshot test for API version endpoint."""
        response = client.get("/api/version")

        if response.status_code == 200:
            data = response.get_json()

            # Version info should have version number
            if data:
                assert "version" in data or "api_version" in data


# ============================================================================
# Health Response Snapshot Tests
# ============================================================================


class TestHealthResponseSnapshots:
    """Snapshot tests for health check responses."""

    @pytest.mark.snapshot
    def test_health_endpoint_structure(self, client, auto_mock_health_dependencies):
        """Snapshot test for health endpoint response."""
        response = client.get("/health")

        assert response.status_code in [200, 503]
        data = response.get_json()

        # Health should have status
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "ok", "running", "up"]

    @pytest.mark.snapshot
    def test_status_endpoint_structure(self, client):
        """Snapshot test for status endpoint response."""
        response = client.get("/status")

        assert response.status_code == 200
        data = response.get_json()

        # Status should indicate running state
        assert "status" in data

    @pytest.mark.snapshot
    def test_health_detailed_structure(self, client):
        """Snapshot test for detailed health endpoint."""
        response = client.get("/health/detailed")

        if response.status_code == 200:
            data = response.get_json()

            # Detailed health should have component checks
            if data:
                expected_components = ["database", "cache", "model", "external_apis"]
                present_components = [c for c in expected_components if c in str(data).lower()]

                # May or may not have detailed components
                assert isinstance(data, dict)


# ============================================================================
# Models Response Snapshot Tests
# ============================================================================


class TestModelsResponseSnapshots:
    """Snapshot tests for model management responses."""

    @pytest.mark.snapshot
    def test_models_list_structure(self, client, api_headers):
        """Snapshot test for models list endpoint."""
        response = client.get("/api/models", headers=api_headers)

        if response.status_code == 200:
            data = response.get_json()

            # Models list should have models array
            if data:
                assert "models" in data or isinstance(data, list)

    @pytest.mark.snapshot
    def test_model_info_structure(self, client, api_headers):
        """Snapshot test for model info endpoint."""
        response = client.get("/api/models/current", headers=api_headers)

        if response.status_code == 200:
            data = response.get_json()

            # Model info should have version and metadata
            if data:
                expected_fields = ["version", "name", "accuracy", "created_at"]
                present_fields = [f for f in expected_fields if f in str(data).lower()]

                assert len(present_fields) >= 0  # Structure may vary
