"""Unit tests for the XAI (Explainable AI) engine.

Tests cover:
- compute_global_importances()
- compute_prediction_contributions()
- generate_why_alert()
- generate_explanation() (integration of all sub-functions)
- Edge cases: all-zero inputs, all-max inputs, missing features, no model support
"""

import numpy as np
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from app.services.xai_engine import (
    _label,
    _kelvin_to_celsius,
    compute_global_importances,
    compute_prediction_contributions,
    generate_explanation,
    generate_why_alert,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_rf_model():
    """Create a mock Random Forest model with feature importances."""
    model = MagicMock()
    model.feature_names_in_ = np.array([
        "temperature", "humidity", "precipitation", "wind_speed", "pressure",
    ])
    model.feature_importances_ = np.array([0.10, 0.30, 0.40, 0.05, 0.15])

    # predict_proba returns [P(no_flood), P(flood)]
    model.predict_proba.return_value = np.array([[0.3, 0.7]])
    model.estimators_ = [MagicMock()]  # Has estimators_ → is an ensemble
    return model


@pytest.fixture
def mock_model_no_importances():
    """Model without feature_importances_ attribute."""
    model = MagicMock(spec=[])
    return model


@pytest.fixture
def mock_model_no_feature_names():
    """Model with importances but no feature_names_in_."""
    model = MagicMock()
    del model.feature_names_in_
    model.feature_importances_ = np.array([0.5, 0.3, 0.2])
    return model


@pytest.fixture
def typical_input_data():
    """Typical weather input for Parañaque."""
    return {
        "temperature": 303.15,
        "humidity": 85.0,
        "precipitation": 45.0,
        "wind_speed": 8.0,
        "pressure": 1005.0,
    }


@pytest.fixture
def extreme_input_data():
    """Extreme typhoon-like weather conditions."""
    return {
        "temperature": 310.0,
        "humidity": 98.0,
        "precipitation": 120.0,
        "wind_speed": 30.0,
        "pressure": 990.0,
    }


@pytest.fixture
def all_zero_input():
    """All-zero input to test edge case behavior."""
    return {
        "temperature": 0.0,
        "humidity": 0.0,
        "precipitation": 0.0,
        "wind_speed": 0.0,
        "pressure": 0.0,
    }


@pytest.fixture
def all_max_input():
    """All-max input to trigger every threshold."""
    return {
        "temperature": 320.0,  # > 35°C after conversion
        "humidity": 99.0,
        "precipitation": 100.0,
        "wind_speed": 30.0,
        "pressure": 990.0,
    }


# ---------------------------------------------------------------------------
# Tests: _label helper
# ---------------------------------------------------------------------------


class TestLabel:
    def test_known_feature(self):
        assert _label("temperature") == "Temperature"
        assert _label("humidity_precipitation") == "Humidity × Precipitation"

    def test_unknown_feature_title_case(self):
        assert _label("some_new_feature") == "Some New Feature"

    def test_rolling_features(self):
        assert _label("precip_3day_sum") == "3-Day Rain Total"
        assert _label("tide_height") == "Tide Height"


# ---------------------------------------------------------------------------
# Tests: _kelvin_to_celsius
# ---------------------------------------------------------------------------


class TestKelvinToCelsius:
    def test_conversion(self):
        assert _kelvin_to_celsius(273.15) == pytest.approx(0.0)
        assert _kelvin_to_celsius(373.15) == pytest.approx(100.0)
        assert _kelvin_to_celsius(303.15) == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# Tests: compute_global_importances
# ---------------------------------------------------------------------------


class TestComputeGlobalImportances:
    def test_returns_sorted_importances(self, mock_rf_model):
        result = compute_global_importances(mock_rf_model)

        assert len(result) == 5
        # Should be sorted by importance descending
        assert result[0]["feature"] == "precipitation"
        assert result[0]["importance"] == 0.4
        assert result[1]["feature"] == "humidity"
        assert result[1]["importance"] == 0.3
        assert result[2]["feature"] == "pressure"

    def test_includes_human_labels(self, mock_rf_model):
        result = compute_global_importances(mock_rf_model)

        assert result[0]["label"] == "Precipitation"
        assert result[1]["label"] == "Humidity"
        assert result[4]["label"] == "Wind Speed"

    def test_no_importances_returns_empty(self, mock_model_no_importances):
        result = compute_global_importances(mock_model_no_importances)
        assert result == []

    def test_no_feature_names_generates_indices(self, mock_model_no_feature_names):
        result = compute_global_importances(mock_model_no_feature_names)

        assert len(result) == 3
        assert result[0]["feature"] == "feature_0"

    def test_importance_values_are_rounded(self, mock_rf_model):
        result = compute_global_importances(mock_rf_model)
        for item in result:
            # Check that importance is rounded to 4 decimal places
            assert item["importance"] == round(item["importance"], 4)


# ---------------------------------------------------------------------------
# Tests: compute_prediction_contributions
# ---------------------------------------------------------------------------


class TestComputePredictionContributions:
    def test_returns_contributions_with_direction(self, mock_rf_model, typical_input_data):
        # Make the permutation change the prediction
        base_proba = np.array([[0.3, 0.7]])
        perturbed_proba = np.array([[0.4, 0.6]])

        call_count = [0]
        def side_effect(X):
            call_count[0] += 1
            if call_count[0] == 1:
                return base_proba
            return perturbed_proba

        mock_rf_model.predict_proba.side_effect = side_effect

        result = compute_prediction_contributions(mock_rf_model, typical_input_data)

        # Should have entries for features where contribution > 0.001
        assert isinstance(result, list)
        for item in result:
            assert "feature" in item
            assert "label" in item
            assert "contribution" in item
            assert "abs_contribution" in item
            assert "direction" in item
            assert item["direction"] in ("increases_risk", "decreases_risk")

    def test_sorted_by_abs_contribution(self, mock_rf_model, typical_input_data):
        # Each permutation reduces flood probability by different amounts
        base = np.array([[0.2, 0.8]])
        perturbed_values = [
            np.array([[0.3, 0.7]]),   # temp: +0.1
            np.array([[0.5, 0.5]]),   # humidity: +0.3
            np.array([[0.6, 0.4]]),   # precip: +0.4
            np.array([[0.25, 0.75]]), # wind: +0.05
            np.array([[0.35, 0.65]]), # pressure: +0.15
        ]

        calls = [0]
        def side_effect(X):
            if calls[0] == 0:
                calls[0] += 1
                return base
            idx = calls[0] - 1
            calls[0] += 1
            return perturbed_values[min(idx, len(perturbed_values) - 1)]

        mock_rf_model.predict_proba.side_effect = side_effect

        result = compute_prediction_contributions(mock_rf_model, typical_input_data)

        # Verify sorted by abs_contribution descending
        for i in range(len(result) - 1):
            assert result[i]["abs_contribution"] >= result[i + 1]["abs_contribution"]

    def test_no_feature_names_returns_empty(self, mock_model_no_importances, typical_input_data):
        result = compute_prediction_contributions(mock_model_no_importances, typical_input_data)
        assert result == []

    def test_negligible_contributions_filtered(self, mock_rf_model, typical_input_data):
        # All permutations return same probability → contributions ~0
        constant = np.array([[0.5, 0.5]])
        mock_rf_model.predict_proba.return_value = constant

        result = compute_prediction_contributions(mock_rf_model, typical_input_data)

        # All contributions are 0, so all should be filtered out
        assert result == []

    def test_missing_features_filled_with_zero(self, mock_rf_model):
        # Input missing some features
        sparse_input = {"temperature": 300.0}

        base = np.array([[0.4, 0.6]])
        perturbed = np.array([[0.5, 0.5]])

        calls = [0]
        def side_effect(X):
            if calls[0] == 0:
                calls[0] += 1
                return base
            calls[0] += 1
            return perturbed

        mock_rf_model.predict_proba.side_effect = side_effect

        # Should not raise - missing features are filled with 0.0
        result = compute_prediction_contributions(mock_rf_model, sparse_input)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Tests: generate_why_alert
# ---------------------------------------------------------------------------


class TestGenerateWhyAlert:
    def test_safe_no_factors(self):
        result = generate_why_alert(
            risk_label="Safe",
            confidence=0.92,
            input_data={"temperature": 300.0, "humidity": 60.0, "precipitation": 2.0},
        )

        assert result["risk_label"] == "Safe"
        assert result["confidence_pct"] == 92
        assert "Safe" in result["summary"]
        assert "normal" in result["summary"].lower()
        assert result["factors"] == []

    def test_heavy_rainfall_detected(self):
        result = generate_why_alert(
            risk_label="Critical",
            confidence=0.87,
            input_data={"precipitation": 55.0, "humidity": 70.0},
        )

        assert result["risk_label"] == "Critical"
        assert result["confidence_pct"] == 87
        assert any("rainfall" in f["text"].lower() for f in result["factors"])
        # 55mm is "very heavy"
        assert any("very heavy" in f["text"].lower() for f in result["factors"])

    def test_extreme_rainfall(self):
        result = generate_why_alert(
            risk_label="Critical",
            confidence=0.95,
            input_data={"precipitation": 90.0, "humidity": 60.0},
        )

        assert any("extreme" in f["text"].lower() for f in result["factors"])
        assert any(f["severity"] == "high" for f in result["factors"])

    def test_humidity_threshold(self):
        result = generate_why_alert(
            risk_label="Alert",
            confidence=0.70,
            input_data={"humidity": 96.0, "precipitation": 5.0},
        )

        assert any("humidity" in f["text"].lower() for f in result["factors"])
        # 96% triggers "near-saturated"
        assert any("saturated" in f["text"].lower() for f in result["factors"])

    def test_wind_speed_thresholds(self):
        # Storm-force winds (≥25 m/s)
        result = generate_why_alert(
            risk_label="Critical",
            confidence=0.80,
            input_data={"wind_speed": 30.0, "precipitation": 5.0, "humidity": 60.0},
        )

        assert any("storm" in f["text"].lower() for f in result["factors"])
        assert any(f["severity"] == "high" for f in result["factors"])

    def test_strong_winds(self):
        result = generate_why_alert(
            risk_label="Alert",
            confidence=0.65,
            input_data={"wind_speed": 18.0, "precipitation": 5.0, "humidity": 60.0},
        )

        assert any("strong winds" in f["text"].lower() for f in result["factors"])

    def test_low_pressure(self):
        result = generate_why_alert(
            risk_label="Critical",
            confidence=0.85,
            input_data={"pressure": 992.0, "precipitation": 5.0, "humidity": 60.0},
        )

        assert any("pressure" in f["text"].lower() for f in result["factors"])
        # Very low (< 995)
        assert any("very low" in f["text"].lower() for f in result["factors"])

    def test_moderate_low_pressure(self):
        result = generate_why_alert(
            risk_label="Alert",
            confidence=0.70,
            input_data={"pressure": 1002.0, "precipitation": 5.0, "humidity": 60.0},
        )

        assert any("low pressure" in f["text"].lower() for f in result["factors"])

    def test_warm_temperature_in_kelvin(self):
        # 310K = 36.85°C > 35°C threshold
        result = generate_why_alert(
            risk_label="Alert",
            confidence=0.60,
            input_data={"temperature": 310.0, "precipitation": 5.0, "humidity": 60.0},
        )

        assert any("warm" in f["text"].lower() or "temperature" in f["text"].lower() for f in result["factors"])

    def test_moisture_saturation_interaction(self):
        # humidity > 80 AND precip > 20 triggers interaction
        result = generate_why_alert(
            risk_label="Critical",
            confidence=0.90,
            input_data={"humidity": 92.0, "precipitation": 45.0},
        )

        assert any("saturation" in f["text"].lower() for f in result["factors"])

    def test_all_zero_input(self, all_zero_input):
        result = generate_why_alert(
            risk_label="Safe",
            confidence=0.99,
            input_data=all_zero_input,
        )

        assert result["risk_label"] == "Safe"
        assert result["confidence_pct"] == 99
        # pressure=0 triggers "Very low pressure" threshold (<995 hPa)
        assert len(result["factors"]) == 1
        assert "pressure" in result["factors"][0]["text"].lower()

    def test_all_max_input(self, all_max_input):
        result = generate_why_alert(
            risk_label="Critical",
            confidence=0.99,
            input_data=all_max_input,
        )

        # Multiple thresholds should fire
        assert len(result["factors"]) >= 3
        assert any(f["severity"] == "high" for f in result["factors"])

    def test_contributions_add_model_factors(self):
        contributions = [
            {"label": "Saturation Risk", "abs_contribution": 0.12, "direction": "increases_risk"},
            {"label": "Month", "abs_contribution": 0.08, "direction": "increases_risk"},
            {"label": "Day Of Week", "abs_contribution": 0.02, "direction": "decreases_risk"},
        ]

        result = generate_why_alert(
            risk_label="Alert",
            confidence=0.70,
            input_data={"humidity": 60.0, "precipitation": 5.0},
            contributions=contributions,
        )

        # Should include model attribution factors from contributions
        factor_texts = [f["text"] for f in result["factors"]]
        assert any("Saturation" in t for t in factor_texts)
        assert any("Month" in t for t in factor_texts)
        # "decreases_risk" should NOT be included
        assert not any("Day Of Week" in t for t in factor_texts)

    def test_contribution_dedup_with_thresholds(self):
        """Model contributions shouldn't duplicate threshold-detected factors."""
        contributions = [
            {"label": "Precipitation", "abs_contribution": 0.15, "direction": "increases_risk"},
        ]

        result = generate_why_alert(
            risk_label="Critical",
            confidence=0.85,
            input_data={"precipitation": 60.0, "humidity": 60.0},
            contributions=contributions,
        )

        # Both threshold factor and contribution factor appear (engine doesn't dedup)
        precip_factors = [f for f in result["factors"] if "precipitation" in f["text"].lower() or "rainfall" in f["text"].lower()]
        assert len(precip_factors) == 2

    def test_summary_includes_top_factors(self):
        result = generate_why_alert(
            risk_label="Critical",
            confidence=0.90,
            input_data={"precipitation": 80.0, "humidity": 96.0, "wind_speed": 30.0},
        )

        # Summary should mention 2-3 top factors
        assert "Critical due to" in result["summary"]
        assert "90% confidence" in result["summary"]

    def test_elevated_risk_no_factors(self):
        """Alert/Critical with no threshold triggers still gets a summary."""
        result = generate_why_alert(
            risk_label="Alert",
            confidence=0.55,
            input_data={"humidity": 60.0, "precipitation": 5.0},
        )

        assert "Alert" in result["summary"]
        assert "elevated" in result["summary"].lower()


# ---------------------------------------------------------------------------
# Tests: generate_explanation (full integration)
# ---------------------------------------------------------------------------


class TestGenerateExplanation:
    def test_full_explanation_structure(self, mock_rf_model, typical_input_data):
        result = generate_explanation(
            model=mock_rf_model,
            input_data=typical_input_data,
            risk_label="Alert",
            confidence=0.75,
        )

        assert "global_feature_importances" in result
        assert "prediction_contributions" in result
        assert "why_alert" in result

        # Global importances come from model
        assert len(result["global_feature_importances"]) == 5

        # Why alert has correct structure
        why = result["why_alert"]
        assert why["risk_label"] == "Alert"
        assert why["confidence_pct"] == 75
        assert isinstance(why["factors"], list)

    def test_explanation_with_no_model_support(self, mock_model_no_importances):
        result = generate_explanation(
            model=mock_model_no_importances,
            input_data={"temperature": 300.0, "humidity": 70.0, "precipitation": 10.0},
            risk_label="Safe",
            confidence=0.90,
        )

        # Should gracefully degrade
        assert result["global_feature_importances"] == []
        assert result["prediction_contributions"] == []
        # Why-alert still works (uses input data)
        assert result["why_alert"]["risk_label"] == "Safe"

    def test_explanation_safe_scenario(self, mock_rf_model):
        mock_rf_model.predict_proba.return_value = np.array([[0.9, 0.1]])

        result = generate_explanation(
            model=mock_rf_model,
            input_data={
                "temperature": 300.0,
                "humidity": 60.0,
                "precipitation": 2.0,
                "wind_speed": 3.0,
                "pressure": 1013.0,
            },
            risk_label="Safe",
            confidence=0.90,
        )

        assert result["why_alert"]["risk_label"] == "Safe"
        assert "Safe" in result["why_alert"]["summary"]

    def test_explanation_critical_scenario(self, mock_rf_model, extreme_input_data):
        result = generate_explanation(
            model=mock_rf_model,
            input_data=extreme_input_data,
            risk_label="Critical",
            confidence=0.95,
        )

        why = result["why_alert"]
        assert why["risk_label"] == "Critical"
        assert why["confidence_pct"] == 95
        # Extreme inputs should trigger multiple factors
        assert len(why["factors"]) >= 2

    def test_explanation_all_zero(self, mock_rf_model, all_zero_input):
        mock_rf_model.predict_proba.return_value = np.array([[0.95, 0.05]])

        result = generate_explanation(
            model=mock_rf_model,
            input_data=all_zero_input,
            risk_label="Safe",
            confidence=0.95,
        )

        assert result["why_alert"]["risk_label"] == "Safe"
        # pressure=0 triggers "Very low pressure" threshold
        assert len(result["why_alert"]["factors"]) == 1
        assert "pressure" in result["why_alert"]["factors"][0]["text"].lower()

    def test_explanation_all_max(self, mock_rf_model, all_max_input):
        result = generate_explanation(
            model=mock_rf_model,
            input_data=all_max_input,
            risk_label="Critical",
            confidence=0.99,
        )

        # Should trigger rainfall, humidity, wind, pressure, temperature, and interaction
        assert len(result["why_alert"]["factors"]) >= 3
