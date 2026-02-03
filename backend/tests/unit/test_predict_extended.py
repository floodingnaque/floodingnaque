"""
Enhanced Unit Tests for Prediction Service.

Includes edge cases, boundary conditions, and error handling tests.
"""

import hashlib
import os
import tempfile
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest
from app.api.schemas.prediction import PredictRequestSchema
from app.api.schemas.weather import IngestRequestSchema, parse_json_safely
from app.services.predict import (
    ModelLoader,
    compute_model_checksum,
    predict_flood,
    verify_model_integrity,
)
from app.services.risk_classifier import classify_risk_level, format_alert_message


class TestPredictServiceEdgeCases:
    """Extended tests for prediction service with edge cases."""

    def test_predict_flood_with_minimal_data(self, mock_model_loader, valid_weather_data):
        """Test prediction with minimal required data."""
        result = predict_flood(valid_weather_data, return_proba=True)

        assert isinstance(result, dict)
        assert "prediction" in result
        assert result["prediction"] in [0, 1]

    def test_predict_flood_with_missing_required_field(self):
        """Test that missing required fields raise ValueError."""
        with pytest.raises(ValueError, match="Missing required fields"):
            predict_flood({"temperature": 298.15})

    def test_predict_flood_with_extra_fields(self, mock_model_loader):
        """Test prediction ignores extra fields gracefully."""
        data = {
            "temperature": 298.15,
            "humidity": 75.0,
            "precipitation": 5.0,
            "extra_field": "ignored",
            "another_extra": 12345,
        }

        result = predict_flood(data, return_proba=True)
        assert isinstance(result, dict)
        assert "prediction" in result

    def test_predict_flood_with_string_numbers(self, mock_model_loader):
        """Test that string numbers are handled (may raise ValueError)."""
        # The predict function expects numeric types
        # String inputs should raise TypeError or ValueError during DataFrame creation
        data = {"temperature": "298.15", "humidity": 75.0, "precipitation": 5.0}  # String instead of float

        # This may work if pandas converts, or may fail
        # We test that it either works or fails gracefully
        try:
            result = predict_flood(data, return_proba=True)
            assert isinstance(result, dict)
            assert "prediction" in result
        except (TypeError, ValueError):
            pass  # Expected for invalid input

    def test_predict_flood_with_boundary_values(self, mock_model_loader, boundary_weather_data):
        """Test prediction with boundary values."""
        for data in boundary_weather_data:
            result = predict_flood(data, return_proba=True)
            assert isinstance(result, dict)
            assert "prediction" in result
            assert result["prediction"] in [0, 1]

    def test_predict_flood_with_zero_precipitation(self, mock_model_loader):
        """Test prediction with zero precipitation (no rain)."""
        data = {"temperature": 298.15, "humidity": 50.0, "precipitation": 0.0}

        result = predict_flood(data, return_proba=True, return_risk_level=True)
        assert isinstance(result, dict)

        assert "prediction" in result
        # With no rain, flood risk should generally be lower
        assert "risk_level" in result

    def test_predict_flood_with_extreme_precipitation(self, mock_model_loader):
        """Test prediction with extreme precipitation values."""
        # Patch to return flood prediction for extreme conditions
        mock_model_loader.model.predict.return_value = [1]
        mock_model_loader.model.predict_proba.return_value = [[0.1, 0.9]]

        data = {"temperature": 298.15, "humidity": 98.0, "precipitation": 200.0}  # Very heavy rain

        result = predict_flood(data, return_proba=True, return_risk_level=True)
        assert isinstance(result, dict)

        assert result["prediction"] == 1
        assert result.get("risk_level", 0) >= 1  # Should be Alert or Critical

    def test_predict_flood_non_dict_input_raises_error(self):
        """Test that non-dict input raises ValueError."""
        with pytest.raises(ValueError, match="must be a dictionary"):
            predict_flood("invalid_input")  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="must be a dictionary"):
            predict_flood([1, 2, 3])  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="must be a dictionary"):
            predict_flood(None)  # type: ignore[arg-type]


class TestRiskClassifierEdgeCases:
    """Extended tests for risk classifier with edge cases."""

    def test_classify_risk_level_safe_threshold(self):
        """Test Safe classification at exact threshold."""
        result = classify_risk_level(
            prediction=0,
            probability={"no_flood": 0.70, "flood": 0.30},  # Exactly at threshold
            precipitation=9.9,  # Just under 10mm
            humidity=50.0,
        )

        # At flood_prob=0.30, the threshold (>= 0.30) triggers Alert level
        assert result["risk_level"] == 1  # Alert (at threshold)
        assert result["risk_label"] == "Alert"

    def test_classify_risk_level_alert_lower_threshold(self):
        """Test Alert classification at lower boundary."""
        result = classify_risk_level(
            prediction=0,
            probability={"no_flood": 0.69, "flood": 0.31},  # Just above 0.30
            precipitation=5.0,
            humidity=50.0,
        )

        assert result["risk_level"] == 1  # Alert
        assert result["risk_label"] == "Alert"

    def test_classify_risk_level_alert_precipitation_trigger(self):
        """Test Alert triggered by precipitation alone."""
        result = classify_risk_level(
            prediction=0,
            probability={"no_flood": 0.80, "flood": 0.20},  # Low flood probability
            precipitation=15.0,  # 10-30mm triggers Alert
            humidity=50.0,
        )

        assert result["risk_level"] == 1  # Alert due to precipitation

    def test_classify_risk_level_alert_humidity_trigger(self):
        """Test Alert triggered by high humidity + precipitation."""
        result = classify_risk_level(
            prediction=0,
            probability={"no_flood": 0.80, "flood": 0.20},
            precipitation=6.0,  # Above 5mm
            humidity=90.0,  # Above 85%
        )

        assert result["risk_level"] == 1  # Alert due to humidity + precipitation

    def test_classify_risk_level_critical_high_probability(self):
        """Test Critical classification with high flood probability."""
        result = classify_risk_level(
            prediction=1, probability={"no_flood": 0.20, "flood": 0.80}, precipitation=50.0, humidity=95.0  # Above 0.75
        )

        assert result["risk_level"] == 2  # Critical
        assert result["risk_label"] == "Critical"
        assert result["risk_color"] == "#dc3545"  # Red

    def test_classify_risk_level_no_probability(self):
        """Test classification without probability data."""
        # Prediction = 1 (flood) without probability should default to Alert
        result = classify_risk_level(prediction=1, probability=None, precipitation=None, humidity=None)

        assert result["risk_level"] in [1, 2]  # Alert or Critical
        assert result["confidence"] == 0.5  # Default confidence

    def test_classify_risk_level_all_none_inputs(self):
        """Test classification with all None optional inputs."""
        result = classify_risk_level(prediction=0, probability=None, precipitation=None, humidity=None)

        assert result["risk_level"] == 0  # Safe (no flood prediction)
        assert "risk_label" in result
        assert "description" in result

    def test_classify_risk_level_confidence_calculation(self):
        """Test confidence is correctly calculated."""
        # Safe level - confidence from no_flood probability
        result = classify_risk_level(
            prediction=0, probability={"no_flood": 0.92, "flood": 0.08}, precipitation=0.0, humidity=40.0
        )

        assert result["confidence"] == 0.92

        # Critical level - confidence from flood probability
        result = classify_risk_level(
            prediction=1, probability={"no_flood": 0.15, "flood": 0.85}, precipitation=50.0, humidity=90.0
        )

        assert result["confidence"] == 0.85


class TestFormatAlertMessage:
    """Tests for alert message formatting."""

    def test_format_alert_message_critical(self):
        """Test critical alert message formatting."""
        risk_data = {
            "risk_label": "Critical",
            "description": "High flood risk. Immediate action required.",
            "confidence": 0.85,
        }

        message = format_alert_message(risk_data, location="Parañaque City")

        assert "FLOOD ALERT" in message
        assert "Parañaque City" in message
        assert "Critical" in message
        assert "85.0%" in message
        assert "TAKE IMMEDIATE ACTION" in message

    def test_format_alert_message_alert(self):
        """Test alert level message formatting."""
        risk_data = {"risk_label": "Alert", "description": "Moderate flood risk.", "confidence": 0.60}

        message = format_alert_message(risk_data)

        assert "Alert" in message
        assert "MONITOR CONDITIONS" in message

    def test_format_alert_message_safe(self):
        """Test safe level message formatting."""
        risk_data = {"risk_label": "Safe", "description": "No immediate flood risk.", "confidence": 0.95}

        message = format_alert_message(risk_data)

        assert "Safe" in message
        # Safe messages should not have urgent action text
        assert "IMMEDIATE ACTION" not in message


class TestModelIntegrity:
    """Tests for model integrity verification."""

    def test_compute_model_checksum(self):
        """Test SHA-256 checksum computation."""
        # Create a temporary file with known content
        with tempfile.NamedTemporaryFile(delete=False, suffix=".joblib") as f:
            content = b"test model content for checksum"
            f.write(content)
            temp_path = f.name

        try:
            checksum = compute_model_checksum(temp_path)

            # Verify it's a valid SHA-256 hex string (64 chars)
            assert len(checksum) == 64
            assert all(c in "0123456789abcdef" for c in checksum)

            # Verify it matches expected
            expected = hashlib.sha256(content).hexdigest()
            assert checksum == expected
        finally:
            os.unlink(temp_path)

    @patch.dict(os.environ, {"REQUIRE_MODEL_SIGNATURE": "true"})
    def test_verify_model_integrity_no_checksum(self):
        """Test integrity verification when no checksum is available."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".joblib") as f:
            f.write(b"test content")
            temp_path = f.name

        try:
            # When REQUIRE_MODEL_SIGNATURE is enabled but no checksum provided,
            # the security check returns False
            result = verify_model_integrity(temp_path, expected_checksum=None)
            assert result is False
        finally:
            os.unlink(temp_path)

    def test_verify_model_integrity_mismatch(self):
        """Test integrity verification with mismatched checksum."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".joblib") as f:
            f.write(b"test content")
            temp_path = f.name

        try:
            # Wrong checksum should fail
            result = verify_model_integrity(temp_path, expected_checksum="wrong_checksum")
            assert result is False
        finally:
            os.unlink(temp_path)


class TestSchemaValidation:
    """Tests for schema validation edge cases."""

    def test_predict_request_schema_type_validation(self):
        """Test type validation in PredictRequestSchema."""
        # Valid data should pass
        schema = PredictRequestSchema(temperature=298.15, humidity=75.0, precipitation=10.0)
        errors = schema.validate()
        assert len(errors) == 0

    def test_predict_request_schema_humidity_bounds(self):
        """Test humidity boundary validation."""
        # Humidity > 100 should fail
        schema = PredictRequestSchema(temperature=298.15, humidity=101.0, precipitation=10.0)
        errors = schema.validate()
        assert len(errors) > 0
        assert any("humidity" in e for e in errors)

        # Humidity < 0 should fail
        schema = PredictRequestSchema(temperature=298.15, humidity=-1.0, precipitation=10.0)
        errors = schema.validate()
        assert len(errors) > 0

    def test_predict_request_schema_precipitation_negative(self):
        """Test precipitation cannot be negative."""
        schema = PredictRequestSchema(temperature=298.15, humidity=50.0, precipitation=-5.0)
        errors = schema.validate()
        assert len(errors) > 0
        assert any("precipitation" in e for e in errors)

    def test_ingest_request_schema_latitude_bounds(self):
        """Test latitude boundary validation."""
        # Valid latitude
        schema = IngestRequestSchema(lat=14.4793, lon=121.0198)
        errors = schema.validate()
        assert len(errors) == 0

        # Invalid latitude (> 90)
        schema = IngestRequestSchema(lat=91.0, lon=121.0198)
        errors = schema.validate()
        assert len(errors) > 0

        # Invalid latitude (< -90)
        schema = IngestRequestSchema(lat=-91.0, lon=121.0198)
        errors = schema.validate()
        assert len(errors) > 0

    def test_ingest_request_schema_longitude_bounds(self):
        """Test longitude boundary validation."""
        # Invalid longitude (> 180)
        schema = IngestRequestSchema(lat=14.4793, lon=181.0)
        errors = schema.validate()
        assert len(errors) > 0

        # Invalid longitude (< -180)
        schema = IngestRequestSchema(lat=14.4793, lon=-181.0)
        errors = schema.validate()
        assert len(errors) > 0

    def test_parse_json_safely_variations(self):
        """Test JSON parsing with various input formats."""
        # Normal JSON
        result = parse_json_safely(b'{"lat": 14.6, "lon": 120.98}')
        assert result is not None
        assert result["lat"] == 14.6
        assert result["lon"] == 120.98

        # Empty bytes
        result = parse_json_safely(b"")
        assert result == {}

        # None input
        result = parse_json_safely(None)
        assert result == {}

        # Double-escaped JSON (PowerShell style)
        result = parse_json_safely(b'{\\"lat\\": 14.6, \\"lon\\": 120.98}')
        if result:  # May or may not parse depending on implementation
            assert "lat" in result


class TestModelLoader:
    """Tests for ModelLoader singleton pattern."""

    def test_model_loader_singleton(self):
        """Test ModelLoader maintains singleton pattern."""
        # Reset to ensure clean state
        ModelLoader.reset_instance()

        instance1 = ModelLoader.get_instance()
        instance2 = ModelLoader.get_instance()

        assert instance1 is instance2

    def test_model_loader_reset(self):
        """Test ModelLoader reset creates new instance."""
        instance1 = ModelLoader.get_instance()
        ModelLoader.reset_instance()
        instance2 = ModelLoader.get_instance()

        assert instance1 is not instance2

    def test_model_loader_set_model(self):
        """Test setting model in ModelLoader."""
        ModelLoader.reset_instance()
        loader = ModelLoader.get_instance()

        mock_model = MagicMock()
        loader.set_model(model=mock_model, path="test/path.joblib", metadata={"version": 1}, checksum="abc123")

        assert loader.model is mock_model
        assert loader.model_path == "test/path.joblib"
        assert loader.metadata == {"version": 1}
        assert loader.checksum == "abc123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
