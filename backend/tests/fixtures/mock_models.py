"""Mock ML model fixtures for prediction service testing."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_model():
    """Create a mock ML model for testing."""
    import numpy as np

    model = MagicMock()
    model.predict.return_value = np.array([0])  # No flood by default
    model.predict_proba.return_value = np.array([[0.8, 0.2]])  # 80% no flood, 20% flood
    model.feature_names_in_ = np.array(["temperature", "humidity", "precipitation"])
    model.n_features_in_ = 3
    model.classes_ = np.array([0, 1])
    model.feature_importances_ = np.array([0.3, 0.3, 0.4])  # Precipitation most important
    return model


@pytest.fixture
def mock_model_flood():
    """Create a mock ML model that predicts flood."""
    import numpy as np

    model = MagicMock()
    model.predict.return_value = np.array([1])  # Flood predicted
    model.predict_proba.return_value = np.array([[0.15, 0.85]])  # 85% flood probability
    model.feature_names_in_ = np.array(["temperature", "humidity", "precipitation"])
    model.n_features_in_ = 3
    model.classes_ = np.array([0, 1])
    model.feature_importances_ = np.array([0.3, 0.3, 0.4])
    return model


@pytest.fixture
def mock_model_loader(mock_model):
    """Patch the ModelLoader to use mock model."""
    with patch("app.services.predict._get_model_loader") as mock_loader:
        loader_instance = MagicMock()
        loader_instance.model = mock_model
        loader_instance.model_path = "models/test_model.joblib"
        loader_instance.metadata = {"version": 1, "checksum": "abc123"}
        loader_instance.checksum = "abc123456789"
        mock_loader.return_value = loader_instance
        yield loader_instance


@pytest.fixture
def mock_model_comprehensive(mock_model):
    """
    Comprehensive model mocking fixture that patches ALL model-related functions.

    This fixture patches:
    - ModelLoader singleton (_instance and get_instance)
    - _load_model() function
    - get_model_metadata() function
    - list_available_models() function
    - get_current_model_info() function

    Use this for tests that need complete isolation from actual model files.
    """
    import numpy as np

    test_metadata = {
        "version": "1.0.0",
        "checksum": "abc123def456789abcdef123456789abcdef123456789abcdef123456789abcd",
        "created_at": "2025-01-15T10:00:00Z",
        "metrics": {"accuracy": 0.95, "f1": 0.92, "precision": 0.94, "recall": 0.90},
        "features": ["temperature", "humidity", "precipitation"],
        "model_type": "RandomForestClassifier",
        "n_estimators": 100,
    }

    test_model_list = [
        {
            "version": 1,
            "path": "models/flood_rf_model_v1.joblib",
            "metadata": test_metadata,
        }
    ]

    test_model_info = {
        "model_path": "models/flood_rf_model.joblib",
        "model_type": "RandomForestClassifier",
        "features": ["temperature", "humidity", "precipitation"],
        "n_features": 3,
        "metadata": test_metadata,
    }

    # Create loader instance mock
    loader_instance = MagicMock()
    loader_instance.model = mock_model
    loader_instance.model_path = "models/flood_rf_model.joblib"
    loader_instance.metadata = test_metadata
    loader_instance.checksum = test_metadata["checksum"]

    with (
        patch("app.services.predict.ModelLoader") as MockModelLoader,
        patch("app.services.predict._load_model") as mock_load_model,
        patch("app.services.predict.get_model_metadata") as mock_get_metadata,
        patch("app.services.predict.list_available_models") as mock_list_models,
        patch("app.services.predict.get_current_model_info") as mock_get_info,
        patch("app.services.predict.load_model_version") as mock_load_version,
    ):

        # Configure ModelLoader mock
        MockModelLoader._instance = loader_instance
        MockModelLoader.get_instance.return_value = loader_instance
        MockModelLoader.reset_instance = MagicMock()

        # Configure function mocks
        mock_load_model.return_value = mock_model
        mock_get_metadata.return_value = test_metadata
        mock_list_models.return_value = test_model_list
        mock_get_info.return_value = test_model_info
        mock_load_version.return_value = mock_model

        yield {
            "model": mock_model,
            "loader": loader_instance,
            "metadata": test_metadata,
            "model_list": test_model_list,
            "model_info": test_model_info,
            "mocks": {
                "ModelLoader": MockModelLoader,
                "_load_model": mock_load_model,
                "get_model_metadata": mock_get_metadata,
                "list_available_models": mock_list_models,
                "get_current_model_info": mock_get_info,
                "load_model_version": mock_load_version,
            },
        }


@pytest.fixture
def mock_prediction_flow(mock_model):
    """
    Mock the entire prediction flow for API endpoint testing.

    This patches predict_flood() to return consistent results without
    requiring an actual model file. Use for API contract and endpoint tests.
    """
    import numpy as np

    def mock_predict_flood(data, return_proba=True, return_risk_level=True):
        """Mock prediction that simulates real model behavior."""
        # Extract values, defaulting if not present
        temp = data.get("temperature", 298.15)
        humidity = data.get("humidity", 50.0)
        precip = data.get("precipitation", 0.0)

        # Simple logic: high humidity + precipitation = flood risk
        flood_prob = min(0.95, (humidity / 100) * 0.4 + (precip / 100) * 0.6)
        no_flood_prob = 1 - flood_prob

        prediction = 1 if flood_prob >= 0.5 else 0

        # Determine risk level based on probability
        if prediction == 1 and flood_prob >= 0.75:
            risk_level = 2  # Critical
            risk_label = "Critical"
            risk_color = "#dc3545"
        elif prediction == 1 or flood_prob >= 0.3:
            risk_level = 1  # Alert
            risk_label = "Alert"
            risk_color = "#ffc107"
        else:
            risk_level = 0  # Safe
            risk_label = "Safe"
            risk_color = "#28a745"

        result = {
            "prediction": prediction,
            "flood_risk": "high" if prediction == 1 else "low",
            "success": True,
        }

        if return_proba:
            result["probability"] = {"no_flood": no_flood_prob, "flood": flood_prob}
            result["confidence"] = max(flood_prob, no_flood_prob)

        if return_risk_level:
            result["risk_level"] = risk_level
            result["risk_label"] = risk_label
            result["risk_color"] = risk_color

        return result

    with patch("app.services.predict.predict_flood", side_effect=mock_predict_flood) as mock:
        yield mock
