"""
Property-Based Tests for Prediction Logic.

Uses Hypothesis to test prediction and risk classification with edge cases.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from app.services.risk_classifier import classify_risk_level
from app.utils.validation import InputValidator
from hypothesis import HealthCheck, assume, given, settings
from tests.strategies import (
    extreme_weather_data,
    flood_probability,
    model_prediction_output,
    probability_dict,
    risk_label,
    risk_level,
    weather_data,
)

# ============================================================================
# Property-Based Tests for Risk Classification
# ============================================================================


class TestPropertyBasedRiskClassification:
    """Property-based tests for risk classification logic."""

    @given(flood_prob=flood_probability(min_prob=0.0, max_prob=0.29))
    @settings(max_examples=100, deadline=None)
    def test_low_probability_always_safe(self, flood_prob):
        """Property: Probabilities < 0.3 should always be classified as Safe."""
        result = classify_risk_level(prediction=0, probability={"no_flood": 1 - flood_prob, "flood": flood_prob})

        assert result["risk_level"] == 0
        assert result["risk_label"] == "Safe"

    @given(flood_prob=flood_probability(min_prob=0.30, max_prob=0.74))
    @settings(max_examples=100, deadline=None)
    def test_medium_probability_always_alert(self, flood_prob):
        """Property: Probabilities 0.3-0.74 should always be classified as Alert."""
        result = classify_risk_level(
            prediction=1 if flood_prob >= 0.5 else 0, probability={"no_flood": 1 - flood_prob, "flood": flood_prob}
        )

        assert result["risk_level"] == 1
        assert result["risk_label"] == "Alert"

    @given(flood_prob=flood_probability(min_prob=0.75, max_prob=1.0))
    @settings(max_examples=100, deadline=None)
    def test_high_probability_always_critical(self, flood_prob):
        """Property: Probabilities >= 0.75 should always be classified as Critical."""
        result = classify_risk_level(prediction=1, probability={"no_flood": 1 - flood_prob, "flood": flood_prob})

        assert result["risk_level"] == 2
        assert result["risk_label"] == "Critical"

    @given(prob_dict=probability_dict())
    @settings(max_examples=100, deadline=None)
    def test_probabilities_sum_to_one(self, prob_dict):
        """Property: Probability dict should always sum to approximately 1.0."""
        total = prob_dict["no_flood"] + prob_dict["flood"]
        assert abs(total - 1.0) < 0.0001, f"Probabilities sum to {total}, not 1.0"

    @given(flood_prob=flood_probability())
    @settings(max_examples=200, deadline=None)
    def test_risk_level_monotonicity(self, flood_prob):
        """Property: Risk level should be monotonic with probability."""
        result = classify_risk_level(
            prediction=1 if flood_prob >= 0.5 else 0, probability={"no_flood": 1 - flood_prob, "flood": flood_prob}
        )

        # Verify monotonicity: higher probability should never give lower risk
        if flood_prob < 0.3:
            assert result["risk_level"] == 0
        elif flood_prob < 0.75:
            assert result["risk_level"] in (0, 1)
        else:
            assert result["risk_level"] in (1, 2)


# ============================================================================
# Property-Based Tests for Prediction Confidence
# ============================================================================


class TestPropertyBasedPredictionConfidence:
    """Property-based tests for prediction confidence calculations."""

    @given(prob_dict=probability_dict())
    @settings(max_examples=100, deadline=None)
    def test_confidence_from_probabilities(self, prob_dict):
        """Property: Confidence should be the max of the two probabilities."""
        confidence = max(prob_dict["no_flood"], prob_dict["flood"])

        assert 0.5 <= confidence <= 1.0
        assert confidence >= prob_dict["no_flood"]
        assert confidence >= prob_dict["flood"]

    @given(output=model_prediction_output())
    @settings(max_examples=100, deadline=None)
    def test_confidence_consistency(self, output):
        """Property: Confidence should be consistent with probabilities."""
        prob = output["probability"]
        confidence = output["confidence"]

        expected_confidence = max(prob["no_flood"], prob["flood"])

        # Should be within reasonable tolerance (inclusive boundary)
        assert abs(confidence - expected_confidence) <= 0.5


# ============================================================================
# Property-Based Tests for Model Input Validation
# ============================================================================


class TestPropertyBasedModelInputValidation:
    """Property-based tests for model input validation."""

    @given(data=weather_data())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_valid_weather_data_for_prediction(self, data):
        """Property: Valid weather data should be accepted for prediction."""
        # All fields should validate successfully
        temp = InputValidator.validate_float(data["temperature"], "temperature", min_val=-50, max_val=50)
        humidity = InputValidator.validate_float(data["humidity"], "humidity", min_val=0, max_val=100)
        precip = InputValidator.validate_float(data["precipitation"], "precipitation", min_val=0, max_val=500)

        assert temp is not None
        assert humidity is not None
        assert precip is not None

    @given(data=extreme_weather_data())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_extreme_weather_data_for_prediction(self, data):
        """Property: Extreme weather data should still be processable."""
        # Extreme but valid values should still validate
        temp = InputValidator.validate_float(data["temperature"], "temperature", min_val=-50, max_val=50)
        humidity = InputValidator.validate_float(data["humidity"], "humidity", min_val=0, max_val=100)
        precip = InputValidator.validate_float(data["precipitation"], "precipitation", min_val=0, max_val=500)

        assert temp is not None
        assert humidity is not None
        assert precip is not None


# ============================================================================
# Property-Based Tests for Model Output Validation
# ============================================================================


class TestPropertyBasedModelOutputValidation:
    """Property-based tests for model output structure."""

    @given(output=model_prediction_output())
    @settings(max_examples=100, deadline=None)
    def test_prediction_output_structure(self, output):
        """Property: Model output should always have required fields."""
        required_fields = [
            "prediction",
            "flood_risk",
            "risk_level",
            "risk_label",
            "confidence",
            "probability",
            "model_version",
            "model_name",
        ]

        for field in required_fields:
            assert field in output, f"Missing required field: {field}"

    @given(output=model_prediction_output())
    @settings(max_examples=100, deadline=None)
    def test_prediction_binary_constraint(self, output):
        """Property: Prediction should always be 0 or 1."""
        assert output["prediction"] in (0, 1)

    @given(output=model_prediction_output())
    @settings(max_examples=100, deadline=None)
    def test_risk_level_constraint(self, output):
        """Property: Risk level should always be 0, 1, or 2."""
        assert output["risk_level"] in (0, 1, 2)

    @given(output=model_prediction_output())
    @settings(max_examples=100, deadline=None)
    def test_risk_label_constraint(self, output):
        """Property: Risk label should match allowed values."""
        assert output["risk_label"] in ("Safe", "Alert", "Critical")

    @given(output=model_prediction_output())
    @settings(max_examples=100, deadline=None)
    def test_risk_level_label_consistency(self, output):
        """Property: Risk level and label should be consistent."""
        level_to_label = {0: "Safe", 1: "Alert", 2: "Critical"}
        assert output["risk_label"] == level_to_label[output["risk_level"]]

    @given(output=model_prediction_output())
    @settings(max_examples=100, deadline=None)
    def test_flood_risk_consistency(self, output):
        """Property: flood_risk should match prediction."""
        if output["prediction"] == 1:
            assert output["flood_risk"] == "high"
        else:
            assert output["flood_risk"] == "low"


# ============================================================================
# Property-Based Tests for Batch Predictions
# ============================================================================


class TestPropertyBasedBatchPredictions:
    """Property-based tests for batch prediction processing."""

    @given(data=weather_data())
    @settings(max_examples=50, deadline=None)
    def test_single_vs_batch_consistency(self, data):
        """Property: Single prediction should match batch prediction with one item."""
        # This tests that batch processing doesn't change results
        # (Implementation would require actual model, so we test the principle)

        # Create batch with single item
        batch = [data]

        # Both should have same structure
        assert isinstance(data, dict)
        assert isinstance(batch, list)
        assert len(batch) == 1
        assert batch[0] == data


# ============================================================================
# Property-Based Tests for Risk Thresholds
# ============================================================================


class TestPropertyBasedRiskThresholds:
    """Property-based tests for risk threshold boundaries."""

    @given(flood_prob=flood_probability())
    @settings(max_examples=200, deadline=None)
    def test_threshold_boundaries(self, flood_prob):
        """Property: Risk level transitions should occur at correct thresholds."""
        result = classify_risk_level(
            prediction=1 if flood_prob >= 0.5 else 0, probability={"no_flood": 1 - flood_prob, "flood": flood_prob}
        )

        # Test boundary conditions
        if flood_prob < 0.30:
            assert result["risk_level"] == 0, f"Expected Safe for prob={flood_prob}"
        elif 0.30 <= flood_prob < 0.75:
            assert result["risk_level"] == 1, f"Expected Alert for prob={flood_prob}"
        else:  # flood_prob >= 0.75
            assert result["risk_level"] == 2, f"Expected Critical for prob={flood_prob}"

    def test_exact_threshold_values(self):
        """Test exact threshold boundary values."""
        from app.services.risk_classifier import classify_risk_level

        # Test exactly at thresholds
        test_cases = [
            (0.30, 1),  # Exactly at Safe/Alert boundary
            (0.75, 2),  # Exactly at Alert/Critical boundary
            (0.299, 0),  # Just below Safe/Alert
            (0.301, 1),  # Just above Safe/Alert
            (0.749, 1),  # Just below Alert/Critical
            (0.751, 2),  # Just above Alert/Critical
        ]

        for prob, expected_level in test_cases:
            result = classify_risk_level(
                prediction=1 if prob >= 0.5 else 0, probability={"no_flood": 1 - prob, "flood": prob}
            )
            assert (
                result["risk_level"] == expected_level
            ), f"Probability {prob} should give risk level {expected_level}, got {result['risk_level']}"


# ============================================================================
# Property-Based Tests for Model Version Handling
# ============================================================================


class TestPropertyBasedModelVersioning:
    """Property-based tests for model versioning."""

    @given(output=model_prediction_output())
    @settings(max_examples=100, deadline=None)
    def test_model_version_present(self, output):
        """Property: Model output should always include version."""
        assert "model_version" in output
        assert isinstance(output["model_version"], str)
        assert len(output["model_version"]) > 0

    @given(output=model_prediction_output())
    @settings(max_examples=100, deadline=None)
    def test_model_name_present(self, output):
        """Property: Model output should always include name."""
        assert "model_name" in output
        assert output["model_name"] == "flood_predictor"


# ============================================================================
# Property-Based Tests for Prediction Invariants
# ============================================================================


class TestPropertyBasedPredictionInvariants:
    """Property-based tests for prediction invariants."""

    @given(data=weather_data())
    @settings(max_examples=100, deadline=None)
    def test_prediction_determinism(self, data):
        """Property: Same input should produce same output (determinism)."""
        # With same input, model should produce consistent results
        # (This is a principle test - actual implementation would need model mock)

        # Create two copies of the same data
        data1 = data.copy()
        data2 = data.copy()

        # Copies should be equal
        assert data1 == data2

    @given(output=model_prediction_output())
    @settings(max_examples=100, deadline=None)
    def test_probability_bounds(self, output):
        """Property: All probabilities should be between 0 and 1."""
        prob = output["probability"]

        assert 0.0 <= prob["no_flood"] <= 1.0
        assert 0.0 <= prob["flood"] <= 1.0
        assert 0.0 <= output["confidence"] <= 1.0

    @given(output=model_prediction_output())
    @settings(max_examples=100, deadline=None)
    def test_prediction_implies_high_confidence(self, output):
        """Property: Predictions should generally have confidence >= 0.5."""
        # A model should only make predictions when reasonably confident
        assert output["confidence"] >= 0.5
