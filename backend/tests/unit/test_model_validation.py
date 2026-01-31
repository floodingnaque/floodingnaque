"""
ML Model Validation Tests.

Tests specific to machine learning model behavior, quality, and robustness.

This module contains two types of tests:
1. Unit Tests: Use mock fixtures, always run, test interfaces and data flow
2. Integration Tests: Marked with @pytest.mark.model, skip if model unavailable

Run unit tests only: pytest tests/unit/test_model_validation.py
Run with real model: pytest tests/unit/test_model_validation.py -m "model"
"""

import os
import tempfile
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest
from app.services.predict import (
    ModelLoader,
    _load_model,
    get_current_model_info,
    get_model_metadata,
    list_available_models,
    load_model_version,
    predict_flood,
)

# ============================================================================
# Unit Tests - Model Loading Interface (Always Run with Mocks)
# ============================================================================


class TestModelLoadingUnit:
    """Unit tests for model loading interface using mocks."""

    def test_model_loads_successfully(self, mock_model_comprehensive):
        """Test that model loading returns a model object."""
        model = mock_model_comprehensive["mocks"]["_load_model"].return_value
        assert model is not None
        assert hasattr(model, "predict")
        assert hasattr(model, "predict_proba")

    def test_model_has_required_methods(self, mock_model_comprehensive):
        """Test that loaded model has required prediction methods."""
        model = mock_model_comprehensive["model"]

        # Should have predict method
        assert hasattr(model, "predict")
        assert callable(model.predict)

        # Should have predict_proba for probability estimation
        assert hasattr(model, "predict_proba")
        assert callable(model.predict_proba)

    def test_model_has_feature_names(self, mock_model_comprehensive):
        """Test that model tracks feature names."""
        model = mock_model_comprehensive["model"]

        # Should have feature names
        assert hasattr(model, "feature_names_in_")
        assert len(model.feature_names_in_) > 0

        # Check for expected features
        features = list(model.feature_names_in_)
        assert "temperature" in features

    def test_model_metadata_structure(self, mock_model_comprehensive):
        """Test that model metadata has expected structure."""
        metadata = mock_model_comprehensive["metadata"]

        assert metadata is not None
        # Should have version info
        assert "version" in metadata or "created_at" in metadata
        # Should have checksum for integrity
        assert "checksum" in metadata
        assert len(metadata["checksum"]) == 64  # SHA-256

    def test_list_available_models_returns_list(self, mock_model_comprehensive):
        """Test that list_available_models returns model list."""
        models = mock_model_comprehensive["model_list"]

        assert isinstance(models, list)
        if models:
            assert "version" in models[0]
            assert "path" in models[0]


# ============================================================================
# Unit Tests - Prediction Quality (Always Run with Mocks)
# ============================================================================


class TestPredictionQualityUnit:
    """Unit tests for prediction quality using mocks."""

    def test_prediction_returns_expected_format(self, mock_model_comprehensive):
        """Test that predictions return expected format."""
        model = mock_model_comprehensive["model"]

        # Model predict should return array
        prediction = model.predict([[298.15, 75.0, 10.0]])
        assert prediction is not None
        assert hasattr(prediction, "__len__")

    def test_prediction_proba_returns_probabilities(self, mock_model_comprehensive):
        """Test that predict_proba returns probability array."""
        model = mock_model_comprehensive["model"]

        proba = model.predict_proba([[298.15, 75.0, 10.0]])
        assert proba is not None
        # Should be 2D array with class probabilities
        assert len(proba[0]) == 2  # Binary classification

    def test_probability_values_in_range(self, mock_model_comprehensive):
        """Test that probabilities are in valid range [0, 1]."""
        model = mock_model_comprehensive["model"]

        proba = model.predict_proba([[298.15, 75.0, 10.0]])
        for p in proba[0]:
            assert 0.0 <= p <= 1.0

    def test_prediction_deterministic_with_mock(self, mock_model_comprehensive):
        """Test that mock predictions are deterministic."""
        model = mock_model_comprehensive["model"]

        # Make the same prediction multiple times
        results = []
        for _ in range(5):
            prediction = model.predict([[298.15, 75.0, 10.0]])
            results.append(prediction[0])

        # All predictions should be identical
        assert all(r == results[0] for r in results)


# ============================================================================
# Unit Tests - Risk Classification (Always Run with Mocks)
# ============================================================================


class TestRiskClassificationUnit:
    """Unit tests for risk classification using mocks."""

    def test_risk_levels_are_integers(self, mock_prediction_flow):
        """Test that risk levels are valid integers."""
        test_data = {"temperature": 298.15, "humidity": 75.0, "precipitation": 10.0}

        result = mock_prediction_flow(test_data, return_proba=True, return_risk_level=True)

        assert "risk_level" in result
        assert isinstance(result["risk_level"], int)
        assert result["risk_level"] in [0, 1, 2]

    def test_risk_labels_are_strings(self, mock_prediction_flow):
        """Test that risk labels are valid strings."""
        test_data = {"temperature": 298.15, "humidity": 75.0, "precipitation": 10.0}

        result = mock_prediction_flow(test_data, return_proba=True, return_risk_level=True)

        assert "risk_label" in result
        assert isinstance(result["risk_label"], str)
        assert result["risk_label"] in ["Safe", "Alert", "Critical"]

    def test_risk_level_label_consistency(self, mock_prediction_flow):
        """Test that risk level matches risk label."""
        level_labels = {0: "Safe", 1: "Alert", 2: "Critical"}

        test_cases = [
            {"temperature": 298.15, "humidity": 30.0, "precipitation": 0.0},  # Low risk
            {"temperature": 298.15, "humidity": 70.0, "precipitation": 30.0},  # Medium risk
            {"temperature": 298.15, "humidity": 95.0, "precipitation": 100.0},  # High risk
        ]

        for data in test_cases:
            result = mock_prediction_flow(data, return_proba=True, return_risk_level=True)
            risk_level = result["risk_level"]
            risk_label = result["risk_label"]

            expected_label = level_labels.get(risk_level)
            assert risk_label == expected_label, f"Mismatch: level={risk_level}, label={risk_label}"

    def test_risk_color_codes_unit(self, mock_prediction_flow):
        """Test that risk color codes are correct."""
        color_map = {"Safe": "#28a745", "Alert": "#ffc107", "Critical": "#dc3545"}

        test_cases = [
            {"temperature": 298.15, "humidity": 30.0, "precipitation": 0.0},  # Should be Safe
            {"temperature": 298.15, "humidity": 70.0, "precipitation": 30.0},  # Should be Alert
            {"temperature": 298.15, "humidity": 95.0, "precipitation": 100.0},  # Should be Critical
        ]

        for data in test_cases:
            result = mock_prediction_flow(data, return_proba=True, return_risk_level=True)
            risk_label = result.get("risk_label")
            risk_color = result.get("risk_color")

            if risk_label and risk_color:
                expected_color = color_map.get(risk_label)
                assert risk_color == expected_color, f"Wrong color for {risk_label}: got {risk_color}"


# ============================================================================
# Unit Tests - Feature Importance (Always Run with Mocks)
# ============================================================================


class TestFeatureImportanceUnit:
    """Unit tests for feature importance using mocks."""

    def test_model_has_feature_importances(self, mock_model_comprehensive):
        """Test that model has feature importances attribute."""
        model = mock_model_comprehensive["model"]

        # Should have feature_importances_
        assert hasattr(model, "feature_importances_")
        importances = model.feature_importances_

        # Should have importance for each feature
        assert len(importances) > 0

    def test_feature_importances_sum_approximately_one(self, mock_model_comprehensive):
        """Test that feature importances sum to approximately 1."""
        model = mock_model_comprehensive["model"]

        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
            assert 0.99 <= sum(importances) <= 1.01


# ============================================================================
# Unit Tests - Model Version Consistency (Always Run with Mocks)
# ============================================================================


class TestModelVersionConsistencyUnit:
    """Unit tests for model version consistency using mocks."""

    def test_model_info_structure(self, mock_model_comprehensive):
        """Test that model info has expected structure."""
        info = mock_model_comprehensive["model_info"]

        if info:
            assert "model_path" in info
            assert "model_type" in info

    def test_version_list_structure(self, mock_model_comprehensive):
        """Test that version list has expected structure."""
        models = mock_model_comprehensive["model_list"]

        if models:
            for model_info in models:
                assert "version" in model_info
                assert "path" in model_info


# ============================================================================
# Integration Tests - Real Model (Skip if model unavailable)
# ============================================================================


@pytest.mark.model
class TestModelLoadingIntegration:
    """Integration tests for model loading with real model files."""

    def test_model_loads_successfully(self):
        """Test that real model can be loaded without errors."""
        ModelLoader.reset_instance()

        try:
            model = _load_model()
            assert model is not None
        except FileNotFoundError:
            pytest.skip("Model file not found - run training first")

    def test_model_has_required_methods(self):
        """Test that loaded model has required prediction methods."""
        ModelLoader.reset_instance()

        try:
            model = _load_model()

            # Should have predict method
            assert hasattr(model, "predict")
            assert callable(model.predict)

            # Should have predict_proba for probability estimation
            assert hasattr(model, "predict_proba")
            assert callable(model.predict_proba)

        except FileNotFoundError:
            pytest.skip("Model file not found")

    def test_model_has_feature_names(self):
        """Test that model tracks feature names."""
        ModelLoader.reset_instance()

        try:
            model = _load_model()

            # Should have feature names (for Random Forest)
            assert hasattr(model, "feature_names_in_")
            assert len(model.feature_names_in_) > 0

            # Check for expected features
            features = list(model.feature_names_in_)
            assert "temperature" in features or any("temp" in f.lower() for f in features)

        except FileNotFoundError:
            pytest.skip("Model file not found")

    def test_model_metadata_exists(self):
        """Test that model metadata file exists and is valid."""
        metadata = get_model_metadata()

        if metadata is None:
            pytest.skip("No model metadata available")

        # Should have version info
        assert "version" in metadata or "created_at" in metadata

        # Should have checksum for integrity
        if "checksum" in metadata:
            assert len(metadata["checksum"]) == 64  # SHA-256

    def test_model_version_loading(self):
        """Test loading specific model versions."""
        models = list_available_models()

        if not models:
            pytest.skip("No versioned models available")

        # Try loading the latest version
        latest = models[0]
        try:
            model = load_model_version(latest["version"])
            assert model is not None
        except FileNotFoundError:
            pytest.skip(f"Model version {latest['version']} not found")


@pytest.mark.model
class TestPredictionQualityIntegration:
    """Integration tests for prediction quality with real model."""

    def test_prediction_deterministic(self):
        """Test that predictions are deterministic (same input = same output)."""
        ModelLoader.reset_instance()

        test_data = {"temperature": 298.15, "humidity": 75.0, "precipitation": 10.0}

        try:
            # Make the same prediction multiple times
            results = []
            for _ in range(5):
                result = predict_flood(test_data, return_proba=True)
                assert isinstance(result, dict)
                results.append(result["prediction"])

            # All predictions should be identical
            assert all(r == results[0] for r in results)

        except FileNotFoundError:
            pytest.skip("Model file not found")

    def test_prediction_probability_range(self):
        """Test that prediction probabilities are in valid range [0, 1]."""
        ModelLoader.reset_instance()

        test_data = {"temperature": 298.15, "humidity": 75.0, "precipitation": 10.0}

        try:
            result = predict_flood(test_data, return_proba=True)
            assert isinstance(result, dict)

            if "probability" in result:
                for key, prob in result["probability"].items():
                    assert 0.0 <= prob <= 1.0, f"Probability {key}={prob} out of range"

        except FileNotFoundError:
            pytest.skip("Model file not found")

    def test_probability_sum_to_one(self):
        """Test that class probabilities sum to approximately 1."""
        ModelLoader.reset_instance()

        test_data = {"temperature": 298.15, "humidity": 75.0, "precipitation": 10.0}

        try:
            result = predict_flood(test_data, return_proba=True)
            assert isinstance(result, dict)

            if "probability" in result:
                prob_sum = sum(result["probability"].values())
                assert 0.99 <= prob_sum <= 1.01, f"Probabilities sum to {prob_sum}"

        except FileNotFoundError:
            pytest.skip("Model file not found")

    def test_extreme_conditions_trigger_flood(self):
        """Test that extreme weather conditions tend to predict flood risk."""
        ModelLoader.reset_instance()

        extreme_data = {"temperature": 298.15, "humidity": 98.0, "precipitation": 200.0}

        try:
            result = predict_flood(extreme_data, return_proba=True, return_risk_level=True)
            assert isinstance(result, dict)

            flood_prob = result.get("probability", {}).get("flood", 0)
            risk_level = result.get("risk_level", 0)

            assert (
                flood_prob > 0.3 or risk_level >= 1 or result["prediction"] == 1
            ), f"Extreme conditions not detected: prob={flood_prob}, risk={risk_level}"

        except FileNotFoundError:
            pytest.skip("Model file not found")

    def test_normal_conditions_low_risk(self):
        """Test that normal weather conditions predict low risk."""
        ModelLoader.reset_instance()

        normal_data = {"temperature": 298.15, "humidity": 50.0, "precipitation": 0.0}

        try:
            result = predict_flood(normal_data, return_proba=True, return_risk_level=True)
            assert isinstance(result, dict)

            flood_prob = result.get("probability", {}).get("flood", 0)
            assert flood_prob < 0.7, f"Normal conditions show high risk: {flood_prob}"

        except FileNotFoundError:
            pytest.skip("Model file not found")


@pytest.mark.model
class TestModelRobustnessIntegration:
    """Integration tests for model robustness with real model."""

    def test_handles_boundary_values(self):
        """Test model handles boundary values without crashing."""
        ModelLoader.reset_instance()

        boundary_cases = [
            {"temperature": 200.0, "humidity": 0.0, "precipitation": 0.0},
            {"temperature": 330.0, "humidity": 100.0, "precipitation": 500.0},
            {"temperature": 273.15, "humidity": 50.0, "precipitation": 0.001},
        ]

        try:
            for data in boundary_cases:
                result = predict_flood(data, return_proba=True)
                assert isinstance(result, dict)
                assert "prediction" in result
                assert result["prediction"] in [0, 1]

        except FileNotFoundError:
            pytest.skip("Model file not found")

    def test_handles_integer_inputs(self):
        """Test model handles integer inputs (converted to float)."""
        ModelLoader.reset_instance()

        int_data = {"temperature": 298, "humidity": 75, "precipitation": 10}

        try:
            result = predict_flood(int_data, return_proba=True)
            assert isinstance(result, dict)
            assert "prediction" in result

        except FileNotFoundError:
            pytest.skip("Model file not found")

    def test_prediction_with_additional_features(self):
        """Test prediction when extra features are provided."""
        ModelLoader.reset_instance()

        data_with_extras = {
            "temperature": 298.15,
            "humidity": 75.0,
            "precipitation": 10.0,
            "wind_speed": 15.0,
            "pressure": 1013.25,
        }

        try:
            result = predict_flood(data_with_extras, return_proba=True)
            assert isinstance(result, dict)
            assert "prediction" in result

        except FileNotFoundError:
            pytest.skip("Model file not found")

    def test_multiple_sequential_predictions(self):
        """Test that model handles many sequential predictions."""
        ModelLoader.reset_instance()

        import random

        try:
            for _ in range(100):
                data = {
                    "temperature": random.uniform(273.15, 320.0),
                    "humidity": random.uniform(0.0, 100.0),
                    "precipitation": random.uniform(0.0, 200.0),
                }

                result = predict_flood(data, return_proba=True)
                assert isinstance(result, dict)
                assert "prediction" in result
                assert result["prediction"] in [0, 1]

        except FileNotFoundError:
            pytest.skip("Model file not found")


@pytest.mark.model
class TestRiskClassificationIntegration:
    """Integration tests for risk classification with real model."""

    def test_risk_level_consistency(self):
        """Test that risk level is consistent with prediction and probability."""
        ModelLoader.reset_instance()

        test_cases = [
            {"temperature": 298.15, "humidity": 50.0, "precipitation": 0.0},
            {"temperature": 298.15, "humidity": 80.0, "precipitation": 20.0},
            {"temperature": 298.15, "humidity": 95.0, "precipitation": 100.0},
        ]

        try:
            for data in test_cases:
                result = predict_flood(data, return_proba=True, return_risk_level=True)
                assert isinstance(result, dict)

                prediction = result["prediction"]
                risk_level = result.get("risk_level", -1)
                flood_prob = result.get("probability", {}).get("flood", 0)

                if prediction == 1 and flood_prob >= 0.75:
                    assert risk_level == 2, f"Expected Critical for high prob {flood_prob}"

        except FileNotFoundError:
            pytest.skip("Model file not found")

    def test_risk_label_matches_level(self):
        """Test that risk label matches risk level."""
        ModelLoader.reset_instance()

        level_labels = {0: "Safe", 1: "Alert", 2: "Critical"}

        try:
            for _ in range(20):
                data = {
                    "temperature": np.random.uniform(273.15, 320.0),
                    "humidity": np.random.uniform(0.0, 100.0),
                    "precipitation": np.random.uniform(0.0, 200.0),
                }

                result = predict_flood(data, return_proba=True, return_risk_level=True)
                assert isinstance(result, dict)

                risk_level = result.get("risk_level")
                risk_label = result.get("risk_label")

                if risk_level is not None and risk_label is not None:
                    expected_label = level_labels.get(risk_level)
                    assert risk_label == expected_label

        except FileNotFoundError:
            pytest.skip("Model file not found")

    def test_risk_color_codes(self):
        """Test that risk color codes are correct."""
        ModelLoader.reset_instance()

        color_map = {"Safe": "#28a745", "Alert": "#ffc107", "Critical": "#dc3545"}

        try:
            for _ in range(20):
                data = {
                    "temperature": np.random.uniform(273.15, 320.0),
                    "humidity": np.random.uniform(0.0, 100.0),
                    "precipitation": np.random.uniform(0.0, 200.0),
                }

                result = predict_flood(data, return_proba=True, return_risk_level=True)
                assert isinstance(result, dict)

                risk_label = result.get("risk_label")
                risk_color = result.get("risk_color")

                if risk_label and risk_color:
                    expected_color = color_map.get(risk_label)
                    assert risk_color == expected_color

        except FileNotFoundError:
            pytest.skip("Model file not found")


@pytest.mark.model
class TestFeatureImportanceIntegration:
    """Integration tests for feature importance with real model."""

    def test_model_has_feature_importances(self):
        """Test that Random Forest model has feature importances."""
        ModelLoader.reset_instance()

        try:
            model = _load_model()

            if hasattr(model, "feature_importances_"):
                importances = model.feature_importances_
                assert len(importances) > 0
                assert 0.99 <= sum(importances) <= 1.01

        except FileNotFoundError:
            pytest.skip("Model file not found")

    def test_precipitation_is_important(self):
        """Test that precipitation is a significant feature."""
        ModelLoader.reset_instance()

        try:
            model = _load_model()

            if hasattr(model, "feature_importances_") and hasattr(model, "feature_names_in_"):
                feature_names = list(model.feature_names_in_)
                importances = model.feature_importances_

                for i, name in enumerate(feature_names):
                    if "precip" in name.lower():
                        assert importances[i] > 0.01, f"Precipitation importance too low: {importances[i]}"
                        break

        except FileNotFoundError:
            pytest.skip("Model file not found")


@pytest.mark.model
class TestModelVersionConsistencyIntegration:
    """Integration tests for model version consistency with real models."""

    def test_all_versions_produce_valid_output(self):
        """Test that all available model versions produce valid outputs."""
        models = list_available_models()

        if not models:
            pytest.skip("No versioned models available")

        test_data = pd.DataFrame([{"temperature": 298.15, "humidity": 75.0, "precipitation": 10.0}])

        for model_info in models:
            version = model_info["version"]
            try:
                model = load_model_version(version)

                if hasattr(model, "feature_names_in_"):
                    test_df = test_data.reindex(columns=model.feature_names_in_, fill_value=0)
                else:
                    test_df = test_data

                prediction = model.predict(test_df)
                assert prediction[0] in [0, 1], f"Version {version} produced invalid prediction"

            except FileNotFoundError:
                continue

    def test_current_model_info(self):
        """Test that current model info is accessible."""
        ModelLoader.reset_instance()

        try:
            info = get_current_model_info()

            if info:
                assert "model_path" in info
                assert "model_type" in info

        except FileNotFoundError:
            pytest.skip("Model file not found")


# ============================================================================
# Run Model Validation Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
