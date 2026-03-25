"""
Unit tests for prediction service.

Tests for app/services/risk_classifier.py - classify_risk_level(),
format_alert_message(), and get_risk_thresholds().
"""

import pytest
from app.services.risk_classifier import (
    RISK_LEVEL_COLORS,
    RISK_LEVEL_DESCRIPTIONS,
    RISK_LEVELS,
    classify_risk_level,
    format_alert_message,
    get_risk_thresholds,
)

# ── classify_risk_level ──────────────────────────────────────────────────


class TestClassifyRiskLevel:
    """Tests for classify_risk_level() function."""

    # -- Safe level (risk_level 0) --

    def test_safe_with_low_flood_probability(self):
        """No-flood prediction with low probability should return Safe."""
        result = classify_risk_level(
            prediction=0,
            probability={"flood": 0.05, "no_flood": 0.95},
        )
        assert result["risk_level"] == 0
        assert result["risk_label"] == "Safe"
        assert result["risk_color"] == "#28a745"

    def test_safe_no_probability_dict(self):
        """No-flood prediction without probability dict defaults to Safe."""
        result = classify_risk_level(prediction=0)
        assert result["risk_level"] == 0
        assert result["risk_label"] == "Safe"
        assert result["confidence"] == 0.5  # default

    def test_safe_with_low_precipitation(self):
        """Low precipitation should not escalate to Alert."""
        result = classify_risk_level(
            prediction=0,
            probability={"flood": 0.05, "no_flood": 0.95},
            precipitation=5.0,
        )
        assert result["risk_level"] == 0

    # -- Alert level (risk_level 1) --

    def test_alert_moderate_flood_probability(self):
        """No-flood prediction with flood_prob >= 0.30 should return Alert."""
        result = classify_risk_level(
            prediction=0,
            probability={"flood": 0.35, "no_flood": 0.65},
        )
        assert result["risk_level"] == 1
        assert result["risk_label"] == "Alert"
        assert result["risk_color"] == "#ffc107"

    def test_alert_moderate_precipitation(self):
        """Moderate precipitation (10-30mm) triggers Alert even with low probability."""
        result = classify_risk_level(
            prediction=0,
            probability={"flood": 0.10, "no_flood": 0.90},
            precipitation=15.0,
        )
        assert result["risk_level"] == 1
        assert result["risk_label"] == "Alert"

    def test_alert_high_humidity_with_precipitation(self):
        """High humidity (>85%) plus precipitation >5mm triggers Alert."""
        result = classify_risk_level(
            prediction=0,
            probability={"flood": 0.10, "no_flood": 0.90},
            precipitation=8.0,
            humidity=90.0,
        )
        assert result["risk_level"] == 1

    def test_alert_flood_predicted_moderate_prob(self):
        """Flood prediction=1 with moderate probability returns Alert."""
        result = classify_risk_level(
            prediction=1,
            probability={"flood": 0.55, "no_flood": 0.45},
        )
        assert result["risk_level"] == 1
        assert result["risk_label"] == "Alert"

    def test_alert_flood_predicted_low_prob(self):
        """Flood prediction=1 with low probability still returns Alert (conservative)."""
        result = classify_risk_level(
            prediction=1,
            probability={"flood": 0.30, "no_flood": 0.70},
        )
        assert result["risk_level"] == 1

    # -- Critical level (risk_level 2) --

    def test_critical_high_flood_probability(self):
        """Flood prediction=1 with flood_prob >= 0.75 returns Critical."""
        result = classify_risk_level(
            prediction=1,
            probability={"flood": 0.85, "no_flood": 0.15},
        )
        assert result["risk_level"] == 2
        assert result["risk_label"] == "Critical"
        assert result["risk_color"] == "#dc3545"

    def test_critical_at_threshold(self):
        """Exactly 0.75 flood probability should be Critical."""
        result = classify_risk_level(
            prediction=1,
            probability={"flood": 0.75, "no_flood": 0.25},
        )
        assert result["risk_level"] == 2

    def test_critical_no_probability_dict(self):
        """Flood prediction=1 without probability dict defaults to 0.5 → Alert."""
        result = classify_risk_level(prediction=1)
        # 0.5 < 0.75 → Alert (not Critical)
        assert result["risk_level"] == 1

    # -- Output structure --

    def test_output_keys(self):
        """Return dict must contain all required keys."""
        result = classify_risk_level(
            prediction=0,
            probability={"flood": 0.10, "no_flood": 0.90},
        )
        expected_keys = {
            "risk_level",
            "risk_label",
            "risk_color",
            "description",
            "confidence",
            "binary_prediction",
            "probability",
        }
        assert set(result.keys()) == expected_keys

    def test_confidence_is_rounded(self):
        """Confidence should be rounded to 3 decimal places."""
        result = classify_risk_level(
            prediction=0,
            probability={"flood": 0.123456, "no_flood": 0.876544},
        )
        assert result["confidence"] == 0.877  # no_flood rounded

    def test_binary_prediction_preserved(self):
        """Original binary prediction is stored in response."""
        for pred in (0, 1):
            result = classify_risk_level(prediction=pred)
            assert result["binary_prediction"] == pred

    def test_description_matches_label(self):
        """Description should match the risk label."""
        result = classify_risk_level(
            prediction=1,
            probability={"flood": 0.90, "no_flood": 0.10},
        )
        assert result["description"] == RISK_LEVEL_DESCRIPTIONS["Critical"]


# ── Boundary / edge cases ────────────────────────────────────────────────


class TestRiskBoundaries:
    """Edge-case tests around classification boundaries."""

    @pytest.mark.parametrize(
        "flood_prob, expected_level",
        [
            (0.0, 0),
            (0.09, 0),
            (0.10, 1),  # boundary: safe_max=0.10 → Alert
            (0.40, 1),
            (0.74, 1),
            (1.0, 1),  # prediction=0, high prob → Alert (no Critical without prediction=1)
        ],
    )
    def test_no_flood_prediction_thresholds(self, flood_prob, expected_level):
        """Verify thresholds when binary prediction is 0."""
        result = classify_risk_level(
            prediction=0,
            probability={"flood": flood_prob, "no_flood": 1 - flood_prob},
        )
        assert result["risk_level"] == expected_level

    @pytest.mark.parametrize(
        "flood_prob, expected_level",
        [
            (0.10, 1),  # prediction=1 conservative → Alert
            (0.50, 1),
            (0.74, 1),
            (0.75, 2),  # boundary: 0.75 → Critical
            (0.99, 2),
        ],
    )
    def test_flood_prediction_thresholds(self, flood_prob, expected_level):
        """Verify thresholds when binary prediction is 1."""
        result = classify_risk_level(
            prediction=1,
            probability={"flood": flood_prob, "no_flood": 1 - flood_prob},
        )
        assert result["risk_level"] == expected_level


# ── format_alert_message ─────────────────────────────────────────────────


class TestFormatAlertMessage:
    """Tests for format_alert_message()."""

    def test_message_includes_label_and_description(self):
        risk_data = classify_risk_level(
            prediction=0,
            probability={"flood": 0.05, "no_flood": 0.95},
        )
        msg = format_alert_message(risk_data)
        assert "Safe" in msg
        assert "Confidence" in msg

    def test_message_with_location(self):
        risk_data = classify_risk_level(
            prediction=1,
            probability={"flood": 0.80, "no_flood": 0.20},
        )
        msg = format_alert_message(risk_data, location="Parañaque City")
        assert "Parañaque City" in msg

    def test_critical_action_callout(self):
        risk_data = classify_risk_level(
            prediction=1,
            probability={"flood": 0.90, "no_flood": 0.10},
        )
        msg = format_alert_message(risk_data)
        assert "TAKE IMMEDIATE ACTION" in msg

    def test_alert_monitor_callout(self):
        risk_data = classify_risk_level(
            prediction=0,
            probability={"flood": 0.40, "no_flood": 0.60},
        )
        msg = format_alert_message(risk_data)
        assert "MONITOR CONDITIONS" in msg


# ── get_risk_thresholds ──────────────────────────────────────────────────


class TestGetRiskThresholds:
    """Tests for get_risk_thresholds()."""

    def test_returns_all_levels(self):
        thresholds = get_risk_thresholds()
        assert set(thresholds.keys()) == {"Safe", "Alert", "Critical"}

    def test_threshold_values(self):
        thresholds = get_risk_thresholds()
        assert thresholds["Safe"]["flood_probability_max"] == 0.10
        assert thresholds["Alert"]["flood_probability_min"] == 0.10
        assert thresholds["Critical"]["flood_probability_min"] == 0.75


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
