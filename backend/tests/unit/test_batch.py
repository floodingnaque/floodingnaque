"""
Unit tests for batch prediction routes.

Tests batch prediction functionality for multiple flood predictions.
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

# Test API key used in headers
TEST_API_KEY = "test-api-key-for-batch-tests"


def auth_bypass():
    """Context manager to bypass API key authentication in tests."""
    return patch.multiple(
        "app.api.middleware.auth",
        validate_api_key=Mock(return_value=(True, "")),
        _hash_api_key_pbkdf2=Mock(return_value="mock_hash"),
    )


class TestBatchPredictEndpoint:
    """Tests for batch prediction endpoint."""

    @pytest.fixture
    def valid_batch_data(self):
        """Create valid batch prediction request data."""
        return {
            "predictions": [
                {
                    "temperature": 298.15,
                    "humidity": 65,
                    "precipitation": 5.0,
                    "wind_speed": 10.5,
                    "location": "Paranaque City",
                },
                {"temperature": 300.15, "humidity": 70, "precipitation": 10.0},
                {"temperature": 295.0, "humidity": 80, "precipitation": 25.0, "wind_speed": 15.0},
            ]
        }

    @pytest.fixture
    def mock_prediction_result(self):
        """Create mock prediction result."""
        return {"prediction": 0, "risk_level": 0, "confidence": 0.85, "model_version": "1.0.0"}

    def test_batch_predict_success(self, client, valid_batch_data, mock_prediction_result):
        """Test successful batch prediction."""
        with auth_bypass():
            with patch("app.api.routes.batch.limiter.limit", lambda x: lambda f: f):
                with patch("app.api.routes.batch.predict_flood") as mock_predict:
                    mock_predict.return_value = mock_prediction_result

                    response = client.post(
                        "/api/v1/batch/predict",
                        data=json.dumps(valid_batch_data),
                        content_type="application/json",
                        headers={"X-API-Key": TEST_API_KEY},
                    )

        assert response.status_code == 200
        data = response.get_json()
        assert "results" in data
        assert "successful" in data
        assert "failed" in data
        assert "total_requested" in data
        assert data["total_requested"] == 3
        assert data["successful"] == 3

    def test_batch_predict_missing_predictions_field(self, client):
        """Test batch predict with missing predictions field."""
        with auth_bypass():
            with patch("app.api.routes.batch.limiter.limit", lambda x: lambda f: f):
                response = client.post(
                    "/api/v1/batch/predict",
                    data=json.dumps({}),
                    content_type="application/json",
                    headers={"X-API-Key": TEST_API_KEY},
                )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "predictions" in data["error"]

    def test_batch_predict_predictions_not_list(self, client):
        """Test batch predict when predictions is not a list."""
        with auth_bypass():
            with patch("app.api.routes.batch.limiter.limit", lambda x: lambda f: f):
                response = client.post(
                    "/api/v1/batch/predict",
                    data=json.dumps({"predictions": "not a list"}),
                    content_type="application/json",
                    headers={"X-API-Key": TEST_API_KEY},
                )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "list" in data["error"]

    def test_batch_predict_empty_list(self, client):
        """Test batch predict with empty predictions list."""
        with auth_bypass():
            with patch("app.api.routes.batch.limiter.limit", lambda x: lambda f: f):
                response = client.post(
                    "/api/v1/batch/predict",
                    data=json.dumps({"predictions": []}),
                    content_type="application/json",
                    headers={"X-API-Key": TEST_API_KEY},
                )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "empty" in data["error"]

    def test_batch_predict_exceeds_max_size(self, client):
        """Test batch predict with too many predictions."""
        predictions = [{"temperature": 298.15, "humidity": 65, "precipitation": 5.0} for _ in range(101)]

        with auth_bypass():
            with patch("app.api.routes.batch.limiter.limit", lambda x: lambda f: f):
                response = client.post(
                    "/api/v1/batch/predict",
                    data=json.dumps({"predictions": predictions}),
                    content_type="application/json",
                    headers={"X-API-Key": TEST_API_KEY},
                )

        assert response.status_code == 413
        data = response.get_json()
        assert "error" in data
        assert "100" in data["error"]


class TestBatchPredictValidation:
    """Tests for batch prediction input validation."""

    def test_missing_temperature(self, client):
        """Test batch predict with missing temperature field."""
        data = {"predictions": [{"humidity": 65, "precipitation": 5.0}]}

        with auth_bypass():
            with patch("app.api.routes.batch.limiter.limit", lambda x: lambda f: f):
                response = client.post(
                    "/api/v1/batch/predict",
                    data=json.dumps(data),
                    content_type="application/json",
                    headers={"X-API-Key": TEST_API_KEY},
                )

        assert response.status_code == 200
        result = response.get_json()
        assert result["failed"] == 1
        assert "errors" in result

    def test_missing_humidity(self, client):
        """Test batch predict with missing humidity field."""
        data = {"predictions": [{"temperature": 298.15, "precipitation": 5.0}]}

        with auth_bypass():
            with patch("app.api.routes.batch.limiter.limit", lambda x: lambda f: f):
                response = client.post(
                    "/api/v1/batch/predict",
                    data=json.dumps(data),
                    content_type="application/json",
                    headers={"X-API-Key": TEST_API_KEY},
                )

        assert response.status_code == 200
        result = response.get_json()
        assert result["failed"] == 1

    def test_missing_precipitation(self, client):
        """Test batch predict with missing precipitation field."""
        data = {"predictions": [{"temperature": 298.15, "humidity": 65}]}

        with auth_bypass():
            with patch("app.api.routes.batch.limiter.limit", lambda x: lambda f: f):
                response = client.post(
                    "/api/v1/batch/predict",
                    data=json.dumps(data),
                    content_type="application/json",
                    headers={"X-API-Key": TEST_API_KEY},
                )

        assert response.status_code == 200
        result = response.get_json()
        assert result["failed"] == 1

    def test_invalid_data_types(self, client):
        """Test batch predict with invalid data types."""
        data = {"predictions": [{"temperature": "hot", "humidity": 65, "precipitation": 5.0}]}

        with auth_bypass():
            with patch("app.api.routes.batch.limiter.limit", lambda x: lambda f: f):
                response = client.post(
                    "/api/v1/batch/predict",
                    data=json.dumps(data),
                    content_type="application/json",
                    headers={"X-API-Key": TEST_API_KEY},
                )

        assert response.status_code == 200
        result = response.get_json()
        assert result["failed"] == 1


class TestBatchPredictMixedResults:
    """Tests for batch predictions with mixed success/failure."""

    def test_partial_success(self, client):
        """Test batch predict with some valid and some invalid inputs."""
        data = {
            "predictions": [
                {"temperature": 298.15, "humidity": 65, "precipitation": 5.0},
                {"temperature": "invalid", "humidity": 65, "precipitation": 5.0},
                {"temperature": 300.15, "humidity": 70, "precipitation": 10.0},
            ]
        }

        mock_result = {"prediction": 0, "risk_level": 0, "confidence": 0.85, "model_version": "1.0.0"}

        with auth_bypass():
            with patch("app.api.routes.batch.limiter.limit", lambda x: lambda f: f):
                with patch("app.api.routes.batch.predict_flood") as mock_predict:
                    mock_predict.return_value = mock_result

                    response = client.post(
                        "/api/v1/batch/predict",
                        data=json.dumps(data),
                        content_type="application/json",
                        headers={"X-API-Key": TEST_API_KEY},
                    )

        assert response.status_code == 200
        result = response.get_json()
        assert result["total_requested"] == 3
        assert result["successful"] == 2
        assert result["failed"] == 1


class TestBatchPredictResultFormat:
    """Tests for batch prediction result format."""

    def test_result_contains_required_fields(self, client):
        """Test that each result contains required fields."""
        data = {"predictions": [{"temperature": 298.15, "humidity": 65, "precipitation": 5.0, "location": "Test"}]}

        mock_result = {"prediction": 0, "risk_level": 0, "confidence": 0.85, "model_version": "1.0.0"}

        with auth_bypass():
            with patch("app.api.routes.batch.limiter.limit", lambda x: lambda f: f):
                with patch("app.api.routes.batch.predict_flood") as mock_predict:
                    mock_predict.return_value = mock_result

                    response = client.post(
                        "/api/v1/batch/predict",
                        data=json.dumps(data),
                        content_type="application/json",
                        headers={"X-API-Key": TEST_API_KEY},
                    )

        assert response.status_code == 200
        result = response.get_json()

        assert "timestamp" in result
        assert "results" in result

        if result["results"]:
            item = result["results"][0]
            assert "index" in item
            assert "input" in item
            assert "prediction" in item
            assert "risk_level" in item

    def test_result_preserves_input_data(self, client):
        """Test that result preserves original input data."""
        input_data = {
            "temperature": 298.15,
            "humidity": 65,
            "precipitation": 5.0,
            "wind_speed": 10.5,
            "location": "Paranaque City",
        }

        data = {"predictions": [input_data]}

        mock_result = {"prediction": 0, "risk_level": 0, "confidence": 0.85, "model_version": "1.0.0"}

        with auth_bypass():
            with patch("app.api.routes.batch.limiter.limit", lambda x: lambda f: f):
                with patch("app.api.routes.batch.predict_flood") as mock_predict:
                    mock_predict.return_value = mock_result

                    response = client.post(
                        "/api/v1/batch/predict",
                        data=json.dumps(data),
                        content_type="application/json",
                        headers={"X-API-Key": TEST_API_KEY},
                    )

        assert response.status_code == 200
        result = response.get_json()

        result_input = result["results"][0]["input"]
        assert result_input["temperature"] == input_data["temperature"]
        assert result_input["humidity"] == input_data["humidity"]
        assert result_input["location"] == input_data["location"]


class TestBatchPredictErrorHandling:
    """Tests for batch prediction error handling."""

    def test_no_json_body(self, client):
        """Test batch predict with no JSON body."""
        with auth_bypass():
            with patch("app.api.routes.batch.limiter.limit", lambda x: lambda f: f):
                response = client.post(
                    "/api/v1/batch/predict",
                    content_type="application/json",
                    headers={"X-API-Key": TEST_API_KEY},
                )

        assert response.status_code == 400

    def test_prediction_service_error(self, client):
        """Test batch predict handles prediction service errors."""
        data = {"predictions": [{"temperature": 298.15, "humidity": 65, "precipitation": 5.0}]}

        with auth_bypass():
            with patch("app.api.routes.batch.limiter.limit", lambda x: lambda f: f):
                with patch("app.api.routes.batch.predict_flood") as mock_predict:
                    mock_predict.side_effect = Exception("Prediction service error")

                    response = client.post(
                        "/api/v1/batch/predict",
                        data=json.dumps(data),
                        content_type="application/json",
                        headers={"X-API-Key": TEST_API_KEY},
                    )

        assert response.status_code == 200
        result = response.get_json()
        assert result["failed"] == 1


class TestBatchPredictDefaultValues:
    """Tests for default values in batch predictions."""

    def test_default_wind_speed(self, client):
        """Test that default wind_speed is applied."""
        data = {"predictions": [{"temperature": 298.15, "humidity": 65, "precipitation": 5.0}]}

        mock_result = {"prediction": 0, "risk_level": 0, "confidence": 0.85, "model_version": "1.0.0"}

        with auth_bypass():
            with patch("app.api.routes.batch.limiter.limit", lambda x: lambda f: f):
                with patch("app.api.routes.batch.predict_flood") as mock_predict:
                    mock_predict.return_value = mock_result

                    response = client.post(
                        "/api/v1/batch/predict",
                        data=json.dumps(data),
                        content_type="application/json",
                        headers={"X-API-Key": TEST_API_KEY},
                    )

        assert response.status_code == 200
        result = response.get_json()
        assert result["results"][0]["input"]["wind_speed"] == 0

    def test_default_location(self, client):
        """Test that default location is applied."""
        data = {"predictions": [{"temperature": 298.15, "humidity": 65, "precipitation": 5.0}]}

        mock_result = {"prediction": 0, "risk_level": 0, "confidence": 0.85, "model_version": "1.0.0"}

        with auth_bypass():
            with patch("app.api.routes.batch.limiter.limit", lambda x: lambda f: f):
                with patch("app.api.routes.batch.predict_flood") as mock_predict:
                    mock_predict.return_value = mock_result

                    response = client.post(
                        "/api/v1/batch/predict",
                        data=json.dumps(data),
                        content_type="application/json",
                        headers={"X-API-Key": TEST_API_KEY},
                    )

        assert response.status_code == 200
        result = response.get_json()
        assert result["results"][0]["input"]["location"] == "Paranaque City"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
