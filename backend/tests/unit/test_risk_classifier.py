"""
Unit Tests for Risk Classifier Service.

Tests the 3-level risk classification: Safe, Alert, Critical.
"""

from typing import Dict

import pytest

# Import modules at top level for proper coverage tracking
from app.services import risk_classifier
from app.services.risk_classifier import (
    RISK_LEVEL_COLORS,
    RISK_LEVEL_DESCRIPTIONS,
    RISK_LEVELS,
    classify_risk_level,
    format_alert_message,
    get_risk_thresholds,
)


class TestRiskLevelConstants:
    """Test risk level constant definitions."""

    def test_risk_levels_defined(self):
        """Test that all risk levels are defined."""
        assert 0 in RISK_LEVELS
        assert 1 in RISK_LEVELS
        assert 2 in RISK_LEVELS
        assert RISK_LEVELS[0] == "Safe"
        assert RISK_LEVELS[1] == "Alert"
        assert RISK_LEVELS[2] == "Critical"

    def test_risk_level_colors_defined(self):
        """Test that colors are defined for each risk level."""
        assert "Safe" in RISK_LEVEL_COLORS
        assert "Alert" in RISK_LEVEL_COLORS
        assert "Critical" in RISK_LEVEL_COLORS

        # Check color format (hex)
        assert RISK_LEVEL_COLORS["Safe"].startswith("#")
        assert RISK_LEVEL_COLORS["Alert"].startswith("#")
        assert RISK_LEVEL_COLORS["Critical"].startswith("#")

    def test_risk_level_descriptions_defined(self):
        """Test that descriptions are defined for each risk level."""
        assert "Safe" in RISK_LEVEL_DESCRIPTIONS
        assert "Alert" in RISK_LEVEL_DESCRIPTIONS
        assert "Critical" in RISK_LEVEL_DESCRIPTIONS

        # Check descriptions are non-empty
        assert len(RISK_LEVEL_DESCRIPTIONS["Safe"]) > 0
        assert len(RISK_LEVEL_DESCRIPTIONS["Alert"]) > 0
        assert len(RISK_LEVEL_DESCRIPTIONS["Critical"]) > 0


class TestClassifyRiskLevel:
    """Test the classify_risk_level function."""

    def test_safe_level_no_flood_low_probability(self):
        """Test Safe classification when no flood and low probability."""
        result = classify_risk_level(prediction=0, probability={"no_flood": 0.95, "flood": 0.05})

        assert result["risk_level"] == 0
        assert result["risk_label"] == "Safe"
        assert result["binary_prediction"] == 0

    def test_alert_level_no_flood_moderate_probability(self):
        """Test Alert classification when no flood but moderate probability."""
        result = classify_risk_level(prediction=0, probability={"no_flood": 0.65, "flood": 0.35})

        assert result["risk_level"] == 1
        assert result["risk_label"] == "Alert"

    def test_alert_level_flood_moderate_probability(self):
        """Test Alert classification when flood predicted with moderate probability."""
        result = classify_risk_level(prediction=1, probability={"no_flood": 0.40, "flood": 0.60})

        assert result["risk_level"] == 1
        assert result["risk_label"] == "Alert"

    def test_critical_level_high_probability(self):
        """Test Critical classification when flood probability is high."""
        result = classify_risk_level(prediction=1, probability={"no_flood": 0.15, "flood": 0.85})

        assert result["risk_level"] == 2
        assert result["risk_label"] == "Critical"

    def test_alert_due_to_moderate_precipitation(self):
        """Test Alert classification due to moderate precipitation."""
        result = classify_risk_level(
            prediction=0,
            probability={"no_flood": 0.85, "flood": 0.15},
            precipitation=15.0,  # Moderate precipitation (10-30mm)
        )

        assert result["risk_level"] == 1
        assert result["risk_label"] == "Alert"

    def test_alert_due_to_high_humidity_and_precipitation(self):
        """Test Alert classification due to high humidity with precipitation."""
        result = classify_risk_level(
            prediction=0,
            probability={"no_flood": 0.85, "flood": 0.15},
            precipitation=10.0,
            humidity=90.0,  # High humidity
        )

        assert result["risk_level"] == 1
        assert result["risk_label"] == "Alert"

    def test_safe_low_humidity_low_precipitation(self):
        """Test Safe classification with low humidity and precipitation."""
        result = classify_risk_level(
            prediction=0, probability={"no_flood": 0.95, "flood": 0.05}, precipitation=2.0, humidity=50.0
        )

        assert result["risk_level"] == 0
        assert result["risk_label"] == "Safe"

    def test_result_contains_all_fields(self):
        """Test that result contains all expected fields."""
        result = classify_risk_level(prediction=0, probability={"no_flood": 0.80, "flood": 0.20})

        assert "risk_level" in result
        assert "risk_label" in result
        assert "risk_color" in result
        assert "description" in result
        assert "confidence" in result
        assert "binary_prediction" in result
        assert "probability" in result

    def test_confidence_calculation_safe(self):
        """Test confidence calculation for Safe level."""
        result = classify_risk_level(prediction=0, probability={"no_flood": 0.85, "flood": 0.15})

        # For Safe level, confidence should use no_flood probability
        assert result["confidence"] == 0.85

    def test_confidence_calculation_critical(self):
        """Test confidence calculation for Critical level."""
        result = classify_risk_level(prediction=1, probability={"no_flood": 0.10, "flood": 0.90})

        # For Critical level, confidence should use flood probability
        assert result["confidence"] == 0.9

    def test_default_confidence_without_probability(self):
        """Test default confidence when no probability provided."""
        result = classify_risk_level(prediction=0, probability=None)

        assert result["confidence"] == 0.5

    def test_default_probability_for_flood_prediction(self):
        """Test default probability handling for flood prediction."""
        result = classify_risk_level(prediction=1, probability=None)

        # Without probability, flood prediction defaults to Alert
        assert result["risk_level"] == 1
        assert result["risk_label"] == "Alert"


class TestGetRiskThresholds:
    """Test the get_risk_thresholds function."""

    def test_returns_all_risk_levels(self):
        """Test that thresholds are returned for all risk levels."""
        thresholds = get_risk_thresholds()

        assert "Safe" in thresholds
        assert "Alert" in thresholds
        assert "Critical" in thresholds

    def test_safe_thresholds(self):
        """Test Safe level thresholds."""
        thresholds = get_risk_thresholds()
        safe = thresholds["Safe"]

        assert "flood_probability_max" in safe
        assert safe["flood_probability_max"] == 0.10
        assert "precipitation_max" in safe
        assert safe["precipitation_max"] == 7.5

    def test_alert_thresholds(self):
        """Test Alert level thresholds."""
        thresholds = get_risk_thresholds()
        alert = thresholds["Alert"]

        assert alert["flood_probability_min"] == 0.10
        assert alert["flood_probability_max"] == 0.75
        assert alert["precipitation_min"] == 7.5
        assert alert["precipitation_max"] == 30.0

    def test_critical_thresholds(self):
        """Test Critical level thresholds."""
        thresholds = get_risk_thresholds()
        critical = thresholds["Critical"]

        assert critical["flood_probability_min"] == 0.75
        assert critical["precipitation_min"] == 30.0


class TestFormatAlertMessage:
    """Test the format_alert_message function."""

    def test_basic_message_format(self):
        """Test basic alert message formatting."""
        risk_data = {"risk_label": "Alert", "description": "Moderate flood risk.", "confidence": 0.65}

        message = format_alert_message(risk_data)

        assert "FLOOD ALERT" in message
        assert "Risk Level: Alert" in message
        assert "Moderate flood risk." in message
        assert "65.0%" in message

    def test_message_with_location(self):
        """Test alert message with location."""
        from app.services.risk_classifier import format_alert_message

        risk_data = {"risk_label": "Critical", "description": "High flood risk.", "confidence": 0.90}

        message = format_alert_message(risk_data, location="Parañaque City")

        assert "Parañaque City" in message
        assert "FLOOD ALERT in Parañaque City" in message

    def test_critical_message_has_action_warning(self):
        """Test that Critical level includes immediate action warning."""
        risk_data = {"risk_label": "Critical", "description": "High flood risk.", "confidence": 0.85}

        message = format_alert_message(risk_data)

        assert "TAKE IMMEDIATE ACTION" in message

    def test_alert_message_has_monitor_warning(self):
        """Test that Alert level includes monitor conditions warning."""
        risk_data = {"risk_label": "Alert", "description": "Moderate flood risk.", "confidence": 0.55}

        message = format_alert_message(risk_data)

        assert "MONITOR CONDITIONS" in message

    def test_safe_message_no_extra_warning(self):
        """Test that Safe level has no extra warning."""
        risk_data = {"risk_label": "Safe", "description": "No immediate flood risk.", "confidence": 0.90}

        message = format_alert_message(risk_data)

        assert "TAKE IMMEDIATE ACTION" not in message
        assert "MONITOR CONDITIONS" not in message


class TestRiskClassificationEdgeCases:
    """Test edge cases in risk classification."""

    def test_boundary_probability_010(self):
        """Test classification at probability boundary 0.10 (safe_max)."""
        result = classify_risk_level(prediction=0, probability={"no_flood": 0.90, "flood": 0.10})

        # 0.10 at safe_max boundary should trigger Alert
        assert result["risk_level"] == 1
        assert result["risk_label"] == "Alert"

    def test_boundary_probability_075(self):
        """Test classification at probability boundary 0.75."""
        result = classify_risk_level(prediction=1, probability={"no_flood": 0.25, "flood": 0.75})

        # 0.75 should trigger Critical
        assert result["risk_level"] == 2
        assert result["risk_label"] == "Critical"

    def test_boundary_precipitation_10(self):
        """Test classification at precipitation boundary 10mm."""
        result = classify_risk_level(prediction=0, probability={"no_flood": 0.85, "flood": 0.15}, precipitation=10.0)

        # 10mm is in moderate range (10-30), should trigger Alert
        assert result["risk_level"] == 1

    def test_low_precipitation_no_alert(self):
        """Test that low precipitation doesn't trigger Alert."""
        result = classify_risk_level(
            prediction=0, probability={"no_flood": 0.95, "flood": 0.05}, precipitation=7.4  # Just below 7.5mm threshold
        )

        assert result["risk_level"] == 0
        assert result["risk_label"] == "Safe"

    def test_high_humidity_requires_precipitation(self):
        """Test that high humidity alone doesn't trigger Alert without precipitation."""
        result = classify_risk_level(
            prediction=0,
            probability={"no_flood": 0.95, "flood": 0.05},
            precipitation=3.0,  # Low precipitation (below humidity_precip_min=5.0)
            humidity=95.0,  # High humidity
        )

        # High humidity with low precip shouldn't trigger Alert
        assert result["risk_level"] == 0


class TestRiskClassificationParameterized:
    """Parameterized tests for risk classification."""

    @pytest.mark.parametrize(
        "prediction,flood_prob,expected_level,expected_label",
        [
            # Safe cases (below safe_max=0.10)
            (0, 0.05, 0, "Safe"),
            (0, 0.09, 0, "Safe"),
            # Alert cases (above safe_max=0.10 or flood predicted with moderate prob)
            (0, 0.10, 1, "Alert"),
            (0, 0.20, 1, "Alert"),
            (0, 0.30, 1, "Alert"),
            (0, 0.50, 1, "Alert"),
            (1, 0.55, 1, "Alert"),
            (1, 0.74, 1, "Alert"),
            # Critical cases (flood predicted with prob >= 0.75)
            (1, 0.75, 2, "Critical"),
            (1, 0.85, 2, "Critical"),
            (1, 0.95, 2, "Critical"),
        ],
    )
    def test_risk_level_based_on_probability(self, prediction, flood_prob, expected_level, expected_label):
        """Test risk level classification based on probability thresholds."""
        result = classify_risk_level(
            prediction=prediction, probability={"no_flood": 1 - flood_prob, "flood": flood_prob}
        )

        assert result["risk_level"] == expected_level
        assert result["risk_label"] == expected_label
