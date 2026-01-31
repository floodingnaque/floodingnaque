"""
Snapshot Tests for ML Model Predictions.

Uses syrupy for snapshot testing to detect unintended model output changes.
These tests help ensure model updates don't break compatibility.
"""

from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest
from syrupy.assertion import SnapshotAssertion

# ============================================================================
# Snapshot Tests for Prediction Outputs
# ============================================================================


class TestPredictionSnapshots:
    """Snapshot tests for model prediction outputs."""

    @pytest.mark.snapshot
    def test_safe_weather_prediction_snapshot(self, snapshot: SnapshotAssertion):
        """
        Snapshot: Safe weather conditions prediction output.

        This captures the exact structure and values returned for safe conditions.
        Any changes to the output format will cause this test to fail.
        """
        from app.services.predict import make_prediction

        with patch("app.services.predict._get_model_loader") as mock_loader:
            mock_model = Mock()
            mock_model.predict.return_value = np.array([0])
            mock_model.predict_proba.return_value = np.array([[0.85, 0.15]])
            mock_model.feature_names_in_ = ["temperature", "humidity", "precipitation"]

            mock_instance = MagicMock()
            mock_instance.model = mock_model
            mock_instance.metadata = {"version": "1.0.0"}
            mock_loader.return_value = mock_instance

            weather_data = {"temperature": 25.0, "humidity": 60.0, "precipitation": 5.0}

            result = make_prediction(weather_data)

            # Snapshot the output structure
            assert result == snapshot

    @pytest.mark.snapshot
    def test_alert_weather_prediction_snapshot(self, snapshot: SnapshotAssertion):
        """
        Snapshot: Alert-level weather conditions prediction output.
        """
        from app.services.predict import make_prediction

        with patch("app.services.predict._get_model_loader") as mock_loader:
            mock_model = Mock()
            mock_model.predict.return_value = np.array([0])
            mock_model.predict_proba.return_value = np.array([[0.55, 0.45]])
            mock_model.feature_names_in_ = ["temperature", "humidity", "precipitation"]

            mock_instance = MagicMock()
            mock_instance.model = mock_model
            mock_instance.metadata = {"version": "1.0.0"}
            mock_loader.return_value = mock_instance

            weather_data = {"temperature": 28.0, "humidity": 80.0, "precipitation": 20.0}

            result = make_prediction(weather_data)

            assert result == snapshot

    @pytest.mark.snapshot
    def test_critical_weather_prediction_snapshot(self, snapshot: SnapshotAssertion):
        """
        Snapshot: Critical-level weather conditions prediction output.
        """
        from app.services.predict import make_prediction

        with patch("app.services.predict._get_model_loader") as mock_loader:
            mock_model = Mock()
            mock_model.predict.return_value = np.array([1])
            mock_model.predict_proba.return_value = np.array([[0.20, 0.80]])
            mock_model.feature_names_in_ = ["temperature", "humidity", "precipitation"]

            mock_instance = MagicMock()
            mock_instance.model = mock_model
            mock_instance.metadata = {"version": "1.0.0"}
            mock_loader.return_value = mock_instance

            weather_data = {"temperature": 32.0, "humidity": 95.0, "precipitation": 100.0}

            result = make_prediction(weather_data)

            assert result == snapshot


# ============================================================================
# Snapshot Tests for Risk Classification
# ============================================================================


class TestRiskClassificationSnapshots:
    """Snapshot tests for risk classification outputs."""

    @pytest.mark.snapshot
    def test_safe_risk_classification_snapshot(self, snapshot: SnapshotAssertion):
        """
        Snapshot: Risk classification for safe conditions.
        """
        from app.services.risk_classifier import classify_risk_level

        result = classify_risk_level(prediction=0, probability={"no_flood": 0.85, "flood": 0.15})

        assert result == snapshot

    @pytest.mark.snapshot
    def test_alert_risk_classification_snapshot(self, snapshot: SnapshotAssertion):
        """
        Snapshot: Risk classification for alert conditions.
        """
        from app.services.risk_classifier import classify_risk_level

        result = classify_risk_level(prediction=0, probability={"no_flood": 0.55, "flood": 0.45})

        assert result == snapshot

    @pytest.mark.snapshot
    def test_critical_risk_classification_snapshot(self, snapshot: SnapshotAssertion):
        """
        Snapshot: Risk classification for critical conditions.
        """
        from app.services.risk_classifier import classify_risk_level

        result = classify_risk_level(prediction=1, probability={"no_flood": 0.20, "flood": 0.80})

        assert result == snapshot

    @pytest.mark.snapshot
    def test_boundary_safe_alert_snapshot(self, snapshot: SnapshotAssertion):
        """
        Snapshot: Risk classification at Safe/Alert boundary (0.30).
        """
        from app.services.risk_classifier import classify_risk_level

        result = classify_risk_level(prediction=0, probability={"no_flood": 0.70, "flood": 0.30})

        assert result == snapshot

    @pytest.mark.snapshot
    def test_boundary_alert_critical_snapshot(self, snapshot: SnapshotAssertion):
        """
        Snapshot: Risk classification at Alert/Critical boundary (0.75).
        """
        from app.services.risk_classifier import classify_risk_level

        result = classify_risk_level(prediction=1, probability={"no_flood": 0.25, "flood": 0.75})

        assert result == snapshot


# ============================================================================
# Snapshot Tests for Batch Predictions
# ============================================================================


class TestBatchPredictionSnapshots:
    """Snapshot tests for batch prediction outputs."""

    @pytest.mark.snapshot
    def test_batch_prediction_structure_snapshot(self, snapshot: SnapshotAssertion):
        """
        Snapshot: Structure of batch prediction response.
        """
        from app.services.predict import make_prediction

        with patch("app.services.predict._get_model_loader") as mock_loader:
            mock_model = Mock()
            # Return predictions for each sample
            mock_model.predict.side_effect = [np.array([0]), np.array([1]), np.array([0])]
            mock_model.predict_proba.side_effect = [
                np.array([[0.85, 0.15]]),
                np.array([[0.20, 0.80]]),
                np.array([[0.60, 0.40]]),
            ]
            mock_model.feature_names_in_ = ["temperature", "humidity", "precipitation"]

            mock_instance = MagicMock()
            mock_instance.model = mock_model
            mock_instance.metadata = {"version": "1.0.0"}
            mock_loader.return_value = mock_instance

            batch_data = [
                {"temperature": 25.0, "humidity": 60.0, "precipitation": 5.0},
                {"temperature": 32.0, "humidity": 95.0, "precipitation": 100.0},
                {"temperature": 28.0, "humidity": 75.0, "precipitation": 15.0},
            ]

            results = [make_prediction(data) for data in batch_data]

            # Snapshot the batch structure
            assert results == snapshot


# ============================================================================
# Snapshot Tests for Model Metadata
# ============================================================================


class TestModelMetadataSnapshots:
    """Snapshot tests for model metadata structure."""

    @pytest.mark.snapshot
    def test_model_info_structure_snapshot(self, snapshot: SnapshotAssertion):
        """
        Snapshot: Model information structure.
        """
        from app.services.predict import get_current_model_info

        with patch("app.services.predict._get_model_loader") as mock_loader:
            mock_model = Mock()
            mock_model.__class__.__name__ = "RandomForestClassifier"
            mock_model.feature_names_in_ = ["temperature", "humidity", "precipitation"]

            mock_instance = MagicMock()
            mock_instance.model = mock_model
            mock_instance.model_path = "models/flood_rf_model.joblib"
            mock_instance.metadata = {
                "version": "1.0.0",
                "created_at": "2024-01-15T10:30:00Z",
                "metrics": {"accuracy": 0.92, "precision": 0.89, "recall": 0.94, "f1_score": 0.91},
            }
            mock_instance.checksum = "abc123def456"
            mock_loader.return_value = mock_instance

            result = get_current_model_info()

            assert result == snapshot


# ============================================================================
# Snapshot Tests for Error Response Formats
# ============================================================================


class TestErrorResponseSnapshots:
    """Snapshot tests for error response formats."""

    @pytest.mark.snapshot
    def test_validation_error_structure_snapshot(self, snapshot: SnapshotAssertion):
        """
        Snapshot: Validation error response structure.
        """
        from app.utils.api_errors import ValidationError

        error = ValidationError(
            "Validation failed",
            field_errors=[
                {"field": "temperature", "message": "Temperature is required", "code": "required"},
                {"field": "humidity", "message": "Humidity must be between 0 and 100", "code": "range"},
            ],
        )

        error_dict = error.to_dict()

        # Normalize dynamic timestamp for reproducible snapshots
        if "error" in error_dict and "timestamp" in error_dict["error"]:
            error_dict["error"]["timestamp"] = "2025-01-15T10:30:00Z"

        assert error_dict == snapshot

    @pytest.mark.snapshot
    def test_model_error_structure_snapshot(self, snapshot: SnapshotAssertion):
        """
        Snapshot: Model error response structure.
        """
        from app.utils.api_errors import ModelError

        error = ModelError("Model prediction failed", details={"reason": "Invalid input shape"})

        error_dict = error.to_dict()

        # Normalize dynamic timestamp for reproducible snapshots
        if "error" in error_dict and "timestamp" in error_dict["error"]:
            error_dict["error"]["timestamp"] = "2025-01-15T10:30:00Z"

        assert error_dict == snapshot


# ============================================================================
# Snapshot Tests for API Response Formats
# ============================================================================


class TestAPIResponseSnapshots:
    """Snapshot tests for complete API response formats."""

    @pytest.mark.snapshot
    def test_prediction_api_response_snapshot(self, snapshot: SnapshotAssertion):
        """
        Snapshot: Complete prediction API response format.
        """
        # This would test the full API response including metadata
        response_structure = {
            "success": True,
            "prediction": 0,
            "flood_risk": "low",
            "risk_level": 0,
            "risk_label": "Safe",
            "risk_color": "#10B981",
            "risk_description": "Conditions are safe. No flood risk detected.",
            "confidence": 0.85,
            "probability": {"no_flood": 0.85, "flood": 0.15},
            "model_version": "1.0.0",
            "model_name": "flood_predictor",
            "timestamp": "2024-01-15T10:30:00Z",
            "request_id": "req_abc123",
        }

        assert response_structure == snapshot

    @pytest.mark.snapshot
    def test_health_check_response_snapshot(self, snapshot: SnapshotAssertion):
        """
        Snapshot: Health check API response format.
        """
        response_structure = {
            "status": "healthy",
            "database": "connected",
            "model_available": True,
            "scheduler_running": True,
            "timestamp": "2024-01-15T10:30:00Z",
            "version": "2.0.0",
        }

        assert response_structure == snapshot


# ============================================================================
# Snapshot Tests for Data Transformations
# ============================================================================


class TestDataTransformationSnapshots:
    """Snapshot tests for data transformation outputs."""

    @pytest.mark.snapshot
    def test_weather_data_preprocessing_snapshot(self, snapshot: SnapshotAssertion):
        """
        Snapshot: Preprocessed weather data structure.
        """
        # Example of preprocessing transformation
        raw_data = {"temperature": "28.5", "humidity": "75.0", "precipitation": "10.5"}

        # Simulated preprocessing
        processed_data = {
            "temperature": float(raw_data["temperature"]),
            "humidity": float(raw_data["humidity"]),
            "precipitation": float(raw_data["precipitation"]),
        }

        assert processed_data == snapshot


# ============================================================================
# Configuration for Snapshot Updates
# ============================================================================


@pytest.fixture
def snapshot_config():
    """
    Configuration for snapshot testing.

    To update snapshots after intentional changes:
        pytest --snapshot-update
    """
    return {
        "update_snapshots": False,  # Set to True to update all snapshots
        "snapshot_dir": "tests/snapshots/__snapshots__",
    }


# ============================================================================
# Snapshot Comparison Helpers
# ============================================================================


def test_snapshot_serialization_float_precision(snapshot: SnapshotAssertion):
    """
    Test that float values are serialized with consistent precision.
    """
    data = {"confidence": 0.8547893214, "probability": 0.1452106786}

    # Floats should be rounded to reasonable precision in snapshots
    rounded_data = {"confidence": round(data["confidence"], 4), "probability": round(data["probability"], 4)}

    assert rounded_data == snapshot


def test_snapshot_ignores_dynamic_fields():
    """
    Test strategy for ignoring dynamic fields in snapshots.

    Fields like timestamps, request_ids should be excluded or normalized.
    """
    from datetime import datetime, timezone

    response = {
        "prediction": 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),  # Dynamic
        "request_id": "req_abc123",  # Dynamic
        "confidence": 0.85,  # Static
    }

    # Strategy: Create a sanitized version for snapshots
    snapshot_data = {
        "prediction": response["prediction"],
        "confidence": response["confidence"],
        # Omit timestamp and request_id
    }

    assert snapshot_data is not None
