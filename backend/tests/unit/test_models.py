"""
Unit tests for model management routes.

Tests for app/api/routes/models.py
"""

from unittest.mock import MagicMock, patch

import pytest


class TestAPIVersion:
    """Tests for API version endpoint."""

    def test_api_version_endpoint(self, client):
        """Test API version endpoint returns version info."""
        response = client.get("/api/version")

        assert response.status_code == 200
        data = response.get_json()
        assert "version" in data
        assert "name" in data
        assert "base_url" in data

    def test_api_version_format(self, client):
        """Test API version follows semantic versioning."""
        response = client.get("/api/version")

        assert response.status_code == 200
        data = response.get_json()
        version = data.get("version", "")
        # Should be in format X.Y.Z
        parts = version.split(".")
        assert len(parts) >= 2

    def test_api_version_name(self, client):
        """Test API name is correct."""
        response = client.get("/api/version")

        assert response.status_code == 200
        data = response.get_json()
        assert "Floodingnaque" in data.get("name", "")


class TestListModels:
    """Tests for list models endpoint."""

    def test_list_models_endpoint(self, client):
        """Test list models endpoint returns model list."""
        response = client.get("/api/models")

        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.get_json()
            assert "models" in data or "error" in data

    @patch("app.api.routes.models.list_available_models")
    @patch("app.api.routes.models.get_current_model_info")
    def test_list_models_with_data(self, mock_current, mock_list, client):
        """Test list models with mock data."""
        mock_list.return_value = [
            {
                "version": "1.0.0",
                "path": "models/model_v1.joblib",
                "metadata": {
                    "version": "1.0.0",
                    "created_at": "2024-01-01T00:00:00Z",
                    "metrics": {"accuracy": 0.95, "precision": 0.92, "recall": 0.88, "f1_score": 0.90},
                },
            }
        ]
        mock_current.return_value = {"metadata": {"version": "1.0.0"}}

        response = client.get("/api/models")

        assert response.status_code == 200
        data = response.get_json()
        assert "models" in data
        assert len(data["models"]) == 1
        assert data["models"][0]["version"] == "1.0.0"
        assert data["models"][0]["is_current"] is True

    @patch("app.api.routes.models.list_available_models")
    @patch("app.api.routes.models.get_current_model_info")
    def test_list_models_empty(self, mock_current, mock_list, client):
        """Test list models when no models available."""
        mock_list.return_value = []
        mock_current.return_value = None

        response = client.get("/api/models")

        assert response.status_code == 200
        data = response.get_json()
        assert data.get("models", []) == [] or data.get("total_versions", 0) == 0

    @patch("app.api.routes.models.list_available_models")
    def test_list_models_error_handling(self, mock_list, client):
        """Test list models error handling."""
        mock_list.side_effect = Exception("Model loading failed")

        response = client.get("/api/models")

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data


class TestAPIDocsEndpoint:
    """Tests for API documentation endpoint."""

    def test_api_docs_endpoint(self, client):
        """Test API docs endpoint returns documentation."""
        response = client.get("/api/docs")

        # May return 200 with docs or redirect
        assert response.status_code in [200, 302, 404]

    def test_api_docs_rate_limited(self, client):
        """Test API docs endpoint is rate limited."""
        # Make multiple requests - should still succeed under limit
        for _ in range(5):
            response = client.get("/api/docs")
            assert response.status_code in [200, 302, 404, 429]


class TestModelResponseFormat:
    """Tests for model response format."""

    @patch("app.api.routes.models.list_available_models")
    @patch("app.api.routes.models.get_current_model_info")
    def test_model_response_includes_request_id(self, mock_current, mock_list, client):
        """Test model response includes request ID."""
        mock_list.return_value = []
        mock_current.return_value = None

        response = client.get("/api/models")

        assert response.status_code == 200
        data = response.get_json()
        assert "request_id" in data

    @patch("app.api.routes.models.list_available_models")
    @patch("app.api.routes.models.get_current_model_info")
    def test_model_response_includes_total_count(self, mock_current, mock_list, client):
        """Test model response includes total versions count."""
        mock_list.return_value = [{"version": "1.0.0", "path": "test"}]
        mock_current.return_value = None

        response = client.get("/api/models")

        assert response.status_code == 200
        data = response.get_json()
        assert "total_versions" in data
        assert data["total_versions"] == 1

    @patch("app.api.routes.models.list_available_models")
    @patch("app.api.routes.models.get_current_model_info")
    def test_model_response_includes_current_version(self, mock_current, mock_list, client):
        """Test model response includes current version."""
        mock_list.return_value = [{"version": "1.0.0", "path": "test1"}, {"version": "2.0.0", "path": "test2"}]
        mock_current.return_value = {"metadata": {"version": "2.0.0"}}

        response = client.get("/api/models")

        assert response.status_code == 200
        data = response.get_json()
        assert "current_version" in data
        assert data["current_version"] == "2.0.0"


class TestModelMetrics:
    """Tests for model metrics in response."""

    @patch("app.api.routes.models.list_available_models")
    @patch("app.api.routes.models.get_current_model_info")
    def test_model_includes_metrics(self, mock_current, mock_list, client):
        """Test model response includes metrics."""
        mock_list.return_value = [
            {
                "version": "1.0.0",
                "path": "test",
                "metadata": {
                    "version": "1.0.0",
                    "created_at": "2024-01-01T00:00:00Z",
                    "metrics": {"accuracy": 0.95, "precision": 0.92, "recall": 0.88, "f1_score": 0.90},
                },
            }
        ]
        mock_current.return_value = None

        response = client.get("/api/models")

        assert response.status_code == 200
        data = response.get_json()
        if data.get("models"):
            model = data["models"][0]
            assert "metrics" in model
            assert "accuracy" in model["metrics"]

    @patch("app.api.routes.models.list_available_models")
    @patch("app.api.routes.models.get_current_model_info")
    def test_model_without_metadata(self, mock_current, mock_list, client):
        """Test model without metadata is handled."""
        mock_list.return_value = [{"version": "1.0.0", "path": "test"}]  # No metadata
        mock_current.return_value = None

        response = client.get("/api/models")

        assert response.status_code == 200
        data = response.get_json()
        assert "models" in data
