"""Sample data, API keys, environment, risk classification, and response validators."""

import os
from typing import Any, Dict
from unittest.mock import patch

import pytest

# ============================================================================
# Sample Data Fixtures
# ============================================================================


@pytest.fixture
def valid_weather_data() -> Dict[str, Any]:
    """Valid weather input data for predictions."""
    return {"temperature": 298.15, "humidity": 75.0, "precipitation": 5.0}  # 25°C in Kelvin


@pytest.fixture
def extreme_weather_data() -> Dict[str, Any]:
    """Extreme weather conditions for edge case testing."""
    return {
        "temperature": 315.0,  # 42°C - very hot
        "humidity": 95.0,  # Very humid
        "precipitation": 100.0,  # Heavy rain (100mm)
    }


@pytest.fixture
def boundary_weather_data():
    """Boundary value test data."""
    return [
        # Minimum valid values
        {"temperature": 200.0, "humidity": 0.0, "precipitation": 0.0},
        # Maximum valid values
        {"temperature": 330.0, "humidity": 100.0, "precipitation": 500.0},
        # Edge cases
        {"temperature": 273.15, "humidity": 50.0, "precipitation": 0.0},  # 0°C
        {"temperature": 298.15, "humidity": 85.1, "precipitation": 10.0},  # High humidity
        {"temperature": 298.15, "humidity": 50.0, "precipitation": 30.1},  # Heavy rain
    ]


@pytest.fixture
def invalid_weather_data():
    """Invalid weather data for error testing."""
    return [
        # Invalid humidity (out of range)
        {"temperature": 298.15, "humidity": 150.0, "precipitation": 5.0},
        {"temperature": 298.15, "humidity": -10.0, "precipitation": 5.0},
        # Invalid precipitation
        {"temperature": 298.15, "humidity": 50.0, "precipitation": -5.0},
        # Missing required fields
        {"temperature": 298.15},
        {"humidity": 50.0},
        # Invalid types
        {"temperature": "hot", "humidity": 50.0, "precipitation": 5.0},
        {"temperature": 298.15, "humidity": "wet", "precipitation": 5.0},
    ]


@pytest.fixture
def sample_coordinates():
    """Sample geographic coordinates for testing."""
    return {
        "paranaque": {"lat": 14.4793, "lon": 121.0198},
        "manila": {"lat": 14.5995, "lon": 120.9842},
        "invalid_lat": {"lat": 91.0, "lon": 121.0198},
        "invalid_lon": {"lat": 14.4793, "lon": 181.0},
        "boundary_lat": {"lat": 90.0, "lon": 0.0},
        "boundary_lon": {"lat": 0.0, "lon": 180.0},
    }


# ============================================================================
# API Key Fixtures
# ============================================================================


@pytest.fixture
def valid_api_key():
    """Generate a valid API key for testing."""
    return "test-api-key-12345-valid"


@pytest.fixture
def invalid_api_key():
    """An invalid API key for testing."""
    return "invalid-api-key-xyz"


@pytest.fixture
def api_headers(valid_api_key):
    """Headers with valid API key."""
    return {"X-API-Key": valid_api_key, "Content-Type": "application/json"}


@pytest.fixture
def api_headers_invalid(invalid_api_key):
    """Headers with invalid API key."""
    return {"X-API-Key": invalid_api_key, "Content-Type": "application/json"}


# ============================================================================
# Environment Fixtures
# ============================================================================


@pytest.fixture
def mock_env_production():
    """Mock production environment variables."""
    env_vars = {
        "FLASK_DEBUG": "false",  # FLASK_ENV deprecated in Flask 2.3+
        "DEBUG": "false",
        "AUTH_BYPASS_ENABLED": "false",
        "VALID_API_KEYS": "prod-key-1,prod-key-2",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        yield


@pytest.fixture
def mock_env_development():
    """Mock development environment variables."""
    env_vars = {
        "FLASK_DEBUG": "true",  # FLASK_ENV deprecated in Flask 2.3+
        "DEBUG": "true",
        "AUTH_BYPASS_ENABLED": "true",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        yield


# ============================================================================
# Risk Classification Fixtures
# ============================================================================


@pytest.fixture
def risk_test_cases():
    """Test cases for risk classification."""
    return [
        # (prediction, probability, precipitation, humidity, expected_risk_level)
        # Safe cases
        (0, {"no_flood": 0.95, "flood": 0.05}, 0.0, 50.0, 0),
        (0, {"no_flood": 0.80, "flood": 0.20}, 5.0, 60.0, 0),
        # Alert cases
        (0, {"no_flood": 0.65, "flood": 0.35}, 15.0, 80.0, 1),
        (1, {"no_flood": 0.45, "flood": 0.55}, 20.0, 85.0, 1),
        # Critical cases
        (1, {"no_flood": 0.20, "flood": 0.80}, 50.0, 95.0, 2),
        (1, {"no_flood": 0.10, "flood": 0.90}, 100.0, 98.0, 2),
    ]


# ============================================================================
# Response Schema Validators
# ============================================================================


def validate_health_response(response_data: Dict) -> bool:
    """Validate health endpoint response schema."""
    required_fields = ["status"]
    return all(field in response_data for field in required_fields)


def validate_prediction_response(response_data: Dict) -> bool:
    """Validate prediction endpoint response schema."""
    required_fields = ["prediction", "flood_risk", "request_id"]
    return all(field in response_data for field in required_fields)


def validate_error_response(response_data: Dict) -> bool:
    """Validate error response schema."""
    required_fields = ["error"]
    return all(field in response_data for field in required_fields)


# Register validators as fixtures
@pytest.fixture
def response_validators():
    """Return response validation functions."""
    return {
        "health": validate_health_response,
        "prediction": validate_prediction_response,
        "error": validate_error_response,
    }
