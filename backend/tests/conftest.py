"""
Pytest Configuration and Shared Fixtures.

Provides reusable fixtures and configuration for all tests.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# ============================================================================
# Set Test Environment Variables BEFORE importing app modules
# This ensures module-level code (like db.py) sees the test configuration
# ============================================================================
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("FLASK_DEBUG", "true")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-not-for-production")
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("AUTH_BYPASS_ENABLED", "true")
os.environ.setdefault("STARTUP_HEALTH_CHECK", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")
os.environ.setdefault("ENV_VALIDATION_ENABLED", "false")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")  # Disable rate limiting in tests
# Clear VALID_API_KEYS to enable auth bypass in tests (AUTH_BYPASS_ENABLED=true)
os.environ["VALID_API_KEYS"] = ""


# ============================================================================
# Deterministic UUIDs for Reproducible Snapshot Tests
# ============================================================================
# Use fixed UUIDs for reproducible snapshots - these ensure consistent
# test output across different runs and environments

FLOOD_EVENT_UUID_1 = UUID("11111111-1111-1111-1111-111111111111")
FLOOD_EVENT_UUID_2 = UUID("22222222-2222-2222-2222-222222222222")
SENSOR_UUID_1 = UUID("33333333-3333-3333-3333-333333333333")
SENSOR_UUID_2 = UUID("44444444-4444-4444-4444-444444444444")
ALERT_UUID_1 = UUID("55555555-5555-5555-5555-555555555555")
ALERT_UUID_2 = UUID("66666666-6666-6666-6666-666666666666")
PREDICTION_UUID_1 = UUID("77777777-7777-7777-7777-777777777777")
PREDICTION_UUID_2 = UUID("88888888-8888-8888-8888-888888888888")
REQUEST_UUID_1 = UUID("99999999-9999-9999-9999-999999999999")

# Fixed timestamps for reproducible snapshots
FIXED_TIMESTAMP = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
FIXED_TIMESTAMP_ISO = "2025-01-15T10:30:00+00:00"


# ============================================================================
# Flask Application Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def app():
    """Create a Flask application for testing."""
    # Invalidate any cached API keys to ensure test environment settings are used
    from app.api.middleware.auth import invalidate_api_key_cache

    invalidate_api_key_cache()

    from app.api.app import create_app

    application = create_app()

    # Configure for testing
    application.config.update(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "PRESERVE_CONTEXT_ON_EXCEPTION": False,
            # Use in-memory SQLite for tests
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    yield application


@pytest.fixture(scope="function")
def client(app):
    """Create a test client for making HTTP requests."""
    with app.test_client() as testing_client:
        with app.app_context():
            yield testing_client


@pytest.fixture(scope="function")
def app_context(app):
    """Push application context for each test."""
    with app.app_context() as ctx:
        yield ctx


@pytest.fixture(scope="function")
def request_context(app):
    """Push request context for tests needing request/session."""
    with app.test_request_context() as ctx:
        yield ctx


@pytest.fixture(scope="function")
def client_with_db(app, app_context):
    """Test client with database initialized."""
    try:
        from app.models.db import init_db

        init_db(app)
    except ImportError:
        pass  # init_db may not exist
    with app.test_client() as testing_client:
        yield testing_client


# ============================================================================
# Concurrent Test Support Fixtures
# ============================================================================


@pytest.fixture(scope="function")
def isolated_client(app):
    """
    Fully isolated client for concurrent tests.

    Each call creates fresh context, solving the
    LookupError: <ContextVar name='flask.request_ctx'> issue.

    Usage in tests:
        def test_concurrent(isolated_client):
            def make_request():
                with isolated_client() as client:
                    return client.get('/health')

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_request) for _ in range(10)]
                results = [f.result() for f in futures]
    """
    from contextlib import contextmanager

    @contextmanager
    def make_client():
        with app.app_context():
            with app.test_client() as client:
                yield client

    return make_client


@pytest.fixture(scope="function")
def thread_safe_app(app):
    """
    App fixture safe for multi-threaded tests.

    Ensures each thread gets its own context.
    Returns tuple of (app, get_client_in_context function).

    Usage:
        def test_threading(thread_safe_app):
            app, get_client = thread_safe_app

            def thread_task():
                client = get_client()
                return client.get('/health')
    """

    def get_client_in_context():
        """Get a client within proper app context."""
        with app.app_context():
            with app.test_client() as client:
                return client

    return app, get_client_in_context


# ============================================================================
# Mock Model Fixtures
# ============================================================================


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


# ============================================================================
# Singleton Reset Fixture (Critical for Test Isolation)
# ============================================================================


@pytest.fixture(scope="function", autouse=True)
def reset_singletons():
    """
    Reset singleton instances between tests.

    This is CRITICAL for test isolation. Without this, singleton state
    from one test can leak into another, causing flaky tests.

    This fixture runs automatically before AND after each test.
    """
    # Setup: Clear any existing singleton state before test
    _reset_all_singletons()

    yield

    # Teardown: Clean up singletons after test
    _reset_all_singletons()


def _reset_all_singletons():
    """Helper function to reset all known singleton instances."""
    # Reset ModelLoader singleton
    try:
        from app.services.predict import ModelLoader

        ModelLoader._instance = None
    except (ImportError, AttributeError):
        pass

    # Reset FeatureFlagService singleton
    try:
        from config.feature_flags import FeatureFlagService

        FeatureFlagService._instance = None
    except (ImportError, AttributeError):
        pass

    # Reset MeteostatService singleton
    try:
        from app.services.meteostat_service import MeteostatService

        if hasattr(MeteostatService, "_instance"):
            MeteostatService._instance = None
    except (ImportError, AttributeError):
        pass

    # Reset AsyncMeteostatService singleton
    try:
        from app.services.meteostat_service_async import AsyncMeteostatService

        if hasattr(AsyncMeteostatService, "_instance"):
            AsyncMeteostatService._instance = None
    except (ImportError, AttributeError):
        pass

    # Reset GoogleWeatherService singleton
    try:
        from app.services.google_weather_service import GoogleWeatherService

        if hasattr(GoogleWeatherService, "_instance"):
            GoogleWeatherService._instance = None
    except (ImportError, AttributeError):
        pass

    # Reset AsyncGoogleWeatherService singleton
    try:
        from app.services.google_weather_service_async import AsyncGoogleWeatherService

        if hasattr(AsyncGoogleWeatherService, "_instance"):
            AsyncGoogleWeatherService._instance = None
    except (ImportError, AttributeError):
        pass

    # Reset WorldTidesService singleton
    try:
        from app.services.worldtides_service import WorldTidesService

        if hasattr(WorldTidesService, "_instance"):
            WorldTidesService._instance = None
    except (ImportError, AttributeError):
        pass

    # Reset AsyncWorldTidesService singleton
    try:
        from app.services.worldtides_service_async import AsyncWorldTidesService

        if hasattr(AsyncWorldTidesService, "_instance"):
            AsyncWorldTidesService._instance = None
    except (ImportError, AttributeError):
        pass


# ============================================================================
# Mock External Service Fixtures for Test Isolation
# ============================================================================


@pytest.fixture(scope="function")
def mock_prediction_service():
    """
    Mock prediction service for tests.

    Provides consistent, predictable prediction results
    without requiring actual model loading.
    """
    with patch("app.services.predict.PredictionService", autospec=True) as mock_class:
        mock_instance = MagicMock()
        mock_instance.predict.return_value = {
            "prediction": 0,
            "probability": {"flood": 0.15, "no_flood": 0.85},
            "confidence": 0.85,
            "risk_level": 0,
        }
        mock_instance.model = MagicMock()
        mock_instance.is_model_loaded.return_value = True
        mock_instance.model_version = "1.0.0"
        mock_instance.model_path = "models/test_model.joblib"
        mock_class.get_instance.return_value = mock_instance
        yield mock_instance


@pytest.fixture(scope="function")
def mock_worldtides_service():
    """
    Mock WorldTides service for tide tests.

    Provides consistent tide data without requiring API calls.
    """
    with patch("app.api.routes.tides._get_worldtides_service") as mock_get:
        mock_service = MagicMock()
        mock_service.is_available.return_value = True
        mock_service.get_current_tide.return_value = {
            "height": 1.5,
            "timestamp": "2026-01-30T10:00:00Z",
            "type": "rising",
        }
        mock_service.get_extremes.return_value = {
            "data": [
                {"type": "high", "height": 2.1, "time": "2026-01-30T12:00:00Z"},
                {"type": "low", "height": 0.3, "time": "2026-01-30T18:00:00Z"},
            ]
        }
        mock_service.get_prediction.return_value = {
            "heights": [1.5, 1.8, 2.0, 1.9],
            "times": ["10:00", "11:00", "12:00", "13:00"],
        }
        mock_get.return_value = mock_service
        yield mock_service


@pytest.fixture(scope="function")
def mock_health_checks():
    """
    Mock all health check dependencies.

    This prevents tests from failing due to external service unavailability.
    """
    with (
        patch("app.api.routes.health.check_database") as mock_db,
        patch("app.api.routes.health.check_model") as mock_model,
        patch("app.api.routes.health.check_redis") as mock_redis,
    ):
        mock_db.return_value = {"status": "healthy", "latency_ms": 5}
        mock_model.return_value = {"status": "healthy", "loaded": True}
        mock_redis.return_value = {"status": "healthy", "connected": True}
        yield {
            "database": mock_db,
            "model": mock_model,
            "redis": mock_redis,
        }


@pytest.fixture(scope="function", autouse=True)
def auto_mock_health_dependencies(request):
    """
    Auto-mock health check dependencies for all tests unless marked otherwise.

    This prevents tests from failing due to:
    - Database not being available
    - Model not being loaded
    - Redis not being connected
    - External APIs being unavailable

    To skip this mocking (e.g., for integration tests that need real health checks),
    mark your test with: @pytest.mark.no_health_mock

    Example:
        @pytest.mark.no_health_mock
        def test_real_health_check(self, client):
            # This test will use real health check implementations
            ...
    """
    # Skip mocking if test is marked with 'no_health_mock'
    if "no_health_mock" in request.keywords:
        yield
        return

    # Mock all health check helper functions used by /health and /status endpoints
    with (
        patch("app.api.routes.health.check_database_health") as mock_db,
        patch("app.api.routes.health.check_redis_health") as mock_redis,
        patch("app.api.routes.health.check_external_api_health") as mock_external,
        patch("app.api.routes.health.check_cache_health") as mock_cache,
        patch("app.api.routes.health.get_pool_status") as mock_pool,
        patch("app.api.routes.health.get_current_model_info") as mock_model,
    ):
        # Return healthy status for database - include all keys expected by various routes
        mock_db.return_value = {
            "status": "healthy",
            "connected": True,
            "latency_ms": 5.0,
            "pool_size": 5,
            "pool_checked_out": 0,
            "pool_checked_in": 5,
            "pool_overflow": 0,
        }
        # Return healthy status for redis
        mock_redis.return_value = {
            "status": "healthy",
            "connected": True,
            "latency_ms": 1.0,
        }
        # Return healthy status for external APIs
        mock_external.return_value = {
            "google_weather": {"status": "healthy", "circuit_state": "closed"},
            "meteostat": {"status": "healthy", "circuit_state": "closed"},
            "worldtides": {"status": "healthy", "circuit_state": "closed"},
        }
        # Return healthy status for cache
        mock_cache.return_value = {
            "status": "healthy",
            "type": "memory",
        }
        # Return healthy database pool status
        mock_pool.return_value = {
            "pool_size": 5,
            "checked_out": 0,
            "checked_in": 5,
            "overflow": 0,
        }
        # Return mock model info so model_available is True
        mock_model.return_value = {
            "model_type": "RandomForestClassifier",
            "features": ["temperature", "humidity", "precipitation"],
            "metadata": {
                "version": "1.0.0",
                "created_at": "2025-01-15T10:00:00Z",
                "metrics": {"accuracy": 0.95, "f1": 0.92},
            },
        }
        yield


# ============================================================================
# Database Fixtures with Proper Cleanup
# ============================================================================


@pytest.fixture(scope="function")
def db_session_isolated(app, app_context):
    """
    Provide clean database session with rollback.

    Ensures each test starts with a clean database state.
    """
    try:
        from app.models.db import db

        db.create_all()

        yield db.session

        db.session.rollback()
        db.session.remove()
        db.drop_all()
    except ImportError:
        # If db module doesn't exist, yield None
        yield None


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


# ============================================================================
# Utility Functions
# ============================================================================


@pytest.fixture
def assert_json_response():
    """Helper to assert JSON response structure."""

    def _assert(response, expected_status, required_fields=None):
        assert response.status_code == expected_status
        data = response.get_json()
        assert data is not None
        if required_fields:
            for field in required_fields:
                assert field in data, f"Missing field: {field}"
        return data

    return _assert


# ============================================================================
# Database Mocking Fixtures
# ============================================================================


@pytest.fixture
def mock_db():
    """Mock database session for testing."""
    mock = MagicMock()
    mock.session = MagicMock()
    mock.session.add = MagicMock()
    mock.session.commit = MagicMock()
    mock.session.rollback = MagicMock()
    mock.session.query = MagicMock()
    mock.session.execute = MagicMock()
    mock.session.close = MagicMock()
    return mock


@pytest.fixture
def mock_db_session(mock_db):
    """Patch database session for testing."""
    with patch("app.models.db", mock_db):
        with patch("app.services.db", mock_db):
            yield mock_db


@pytest.fixture
def mock_sqlalchemy_engine():
    """Mock SQLAlchemy engine for connection testing."""
    engine = MagicMock()
    engine.connect.return_value.__enter__ = MagicMock(return_value=MagicMock())
    engine.connect.return_value.__exit__ = MagicMock(return_value=None)
    engine.execute = MagicMock()
    engine.dispose = MagicMock()
    return engine


@pytest.fixture
def sample_db_records():
    """Sample database records for testing."""
    return [
        {
            "id": 1,
            "timestamp": "2025-01-15T10:00:00Z",
            "temperature": 298.15,
            "humidity": 75.0,
            "precipitation": 5.0,
            "prediction": 0,
            "flood_risk": "low",
        },
        {
            "id": 2,
            "timestamp": "2025-01-15T11:00:00Z",
            "temperature": 300.0,
            "humidity": 85.0,
            "precipitation": 25.0,
            "prediction": 1,
            "flood_risk": "high",
        },
    ]


# ============================================================================
# Redis/Cache Mocking Fixtures
# ============================================================================


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value=None)
    redis_mock.set = MagicMock(return_value=True)
    redis_mock.setex = MagicMock(return_value=True)
    redis_mock.delete = MagicMock(return_value=1)
    redis_mock.exists = MagicMock(return_value=0)
    redis_mock.incr = MagicMock(return_value=1)
    redis_mock.expire = MagicMock(return_value=True)
    redis_mock.ttl = MagicMock(return_value=3600)
    redis_mock.keys = MagicMock(return_value=[])
    redis_mock.flushdb = MagicMock(return_value=True)
    redis_mock.pipeline = MagicMock(return_value=MagicMock())
    redis_mock.ping = MagicMock(return_value=True)
    # Sorted set operations for sliding window rate limiting
    redis_mock.zcard = MagicMock(return_value=0)
    redis_mock.zadd = MagicMock(return_value=1)
    redis_mock.zremrangebyscore = MagicMock(return_value=0)
    return redis_mock


@pytest.fixture
def mock_redis_client(mock_redis):
    """Patch Redis client globally for testing."""
    with patch("app.utils.cache.redis_client", mock_redis):
        with patch("app.utils.rate_limit.redis_client", mock_redis):
            with patch("app.api.middleware.rate_limit.redis_client", mock_redis):
                yield mock_redis


@pytest.fixture
def mock_cache():
    """Mock cache decorator/manager for testing."""
    cache_mock = MagicMock()
    cache_mock.get = MagicMock(return_value=None)
    cache_mock.set = MagicMock(return_value=True)
    cache_mock.delete = MagicMock(return_value=True)
    cache_mock.clear = MagicMock(return_value=True)
    cache_mock.mget = MagicMock(return_value=[])
    cache_mock.mset = MagicMock(return_value=True)
    return cache_mock


# ============================================================================
# Celery/Task Queue Mocking Fixtures
# ============================================================================


@pytest.fixture
def mock_celery():
    """Mock Celery app for testing."""
    celery_mock = MagicMock()
    celery_mock.send_task = MagicMock()
    celery_mock.AsyncResult = MagicMock()
    return celery_mock


@pytest.fixture
def mock_celery_task():
    """Mock Celery task for testing."""
    task_mock = MagicMock()
    task_mock.delay = MagicMock()
    task_mock.apply_async = MagicMock()
    task_mock.s = MagicMock()  # Signature shortcut

    # Task result
    result_mock = MagicMock()
    result_mock.id = "task-id-12345"
    result_mock.state = "PENDING"
    result_mock.result = None
    result_mock.ready = MagicMock(return_value=False)
    result_mock.successful = MagicMock(return_value=False)
    result_mock.failed = MagicMock(return_value=False)
    result_mock.get = MagicMock(return_value=None)

    task_mock.delay.return_value = result_mock
    task_mock.apply_async.return_value = result_mock

    return task_mock


@pytest.fixture
def mock_task_queue(mock_celery_task):
    """Patch task queue for testing."""
    with patch("app.tasks.prediction_tasks.predict_flood", mock_celery_task):
        with patch("app.tasks.data_tasks.ingest_weather_data", mock_celery_task):
            yield mock_celery_task


# ============================================================================
# External API Mocking Fixtures
# ============================================================================


@pytest.fixture
def mock_weather_api():
    """Mock weather API responses."""
    return {
        "current": {
            "temperature": 298.15,
            "humidity": 75.0,
            "precipitation": 5.0,
            "wind_speed": 10.0,
            "pressure": 1013.25,
        },
        "forecast": [
            {"time": "2025-01-15T12:00:00Z", "temperature": 299.0, "precipitation": 2.0},
            {"time": "2025-01-15T15:00:00Z", "temperature": 301.0, "precipitation": 0.0},
            {"time": "2025-01-15T18:00:00Z", "temperature": 298.0, "precipitation": 10.0},
        ],
    }


@pytest.fixture
def mock_requests(mock_weather_api):
    """Mock requests library for external API calls."""
    with patch("requests.get") as mock_get:
        response_mock = MagicMock()
        response_mock.status_code = 200
        response_mock.json.return_value = mock_weather_api
        response_mock.text = '{"status": "ok"}'
        response_mock.headers = {"Content-Type": "application/json"}
        response_mock.raise_for_status = MagicMock()
        mock_get.return_value = response_mock
        yield mock_get


@pytest.fixture
def mock_httpx():
    """Mock httpx library for async HTTP calls."""
    with patch("httpx.AsyncClient") as mock_client:
        client_instance = MagicMock()
        response_mock = MagicMock()
        response_mock.status_code = 200
        response_mock.json.return_value = {"status": "ok"}
        client_instance.get = MagicMock(return_value=response_mock)
        client_instance.post = MagicMock(return_value=response_mock)
        mock_client.return_value.__aenter__ = MagicMock(return_value=client_instance)
        mock_client.return_value.__aexit__ = MagicMock(return_value=None)
        yield mock_client


# ============================================================================
# Metrics/Monitoring Fixtures
# ============================================================================


@pytest.fixture
def mock_prometheus():
    """Mock Prometheus metrics for testing."""
    prometheus_mock = MagicMock()
    prometheus_mock.Counter = MagicMock(return_value=MagicMock())
    prometheus_mock.Histogram = MagicMock(return_value=MagicMock())
    prometheus_mock.Gauge = MagicMock(return_value=MagicMock())
    prometheus_mock.Summary = MagicMock(return_value=MagicMock())
    return prometheus_mock


@pytest.fixture
def mock_metrics(mock_prometheus):
    """Patch Prometheus metrics for testing."""
    with patch("app.utils.metrics.prometheus_client", mock_prometheus):
        yield mock_prometheus


# ============================================================================
# Logging Fixtures
# ============================================================================


@pytest.fixture
def mock_logger():
    """Mock logger for testing log output."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.critical = MagicMock()
    logger.exception = MagicMock()
    return logger


@pytest.fixture
def capture_logs(caplog):
    """Capture log output for assertions."""
    import logging

    caplog.set_level(logging.DEBUG)
    return caplog


# ============================================================================
# Time/Date Fixtures
# ============================================================================


@pytest.fixture
def freeze_time():
    """Fixture to freeze time for testing."""
    from datetime import datetime
    from unittest.mock import patch

    frozen_time = datetime(2025, 1, 15, 12, 0, 0)

    with patch("datetime.datetime") as mock_datetime:
        mock_datetime.now.return_value = frozen_time
        mock_datetime.utcnow.return_value = frozen_time
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        yield frozen_time


@pytest.fixture
def mock_time():
    """Mock time module for testing."""
    import time

    with patch("time.time") as mock_time_func:
        mock_time_func.return_value = 1736942400.0  # 2025-01-15 12:00:00 UTC
        yield mock_time_func


# ============================================================================
# File/IO Fixtures
# ============================================================================


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file for testing."""
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("test content")
    return file_path


@pytest.fixture
def temp_json_file(tmp_path):
    """Create a temporary JSON file for testing."""
    import json

    file_path = tmp_path / "test_data.json"
    data = {"key": "value", "nested": {"a": 1, "b": 2}}
    file_path.write_text(json.dumps(data))
    return file_path


@pytest.fixture
def temp_csv_file(tmp_path):
    """Create a temporary CSV file for testing."""
    file_path = tmp_path / "test_data.csv"
    content = "timestamp,temperature,humidity,precipitation\n"
    content += "2025-01-15T10:00:00Z,298.15,75.0,5.0\n"
    content += "2025-01-15T11:00:00Z,300.0,85.0,25.0\n"
    file_path.write_text(content)
    return file_path


# ============================================================================
# Security Testing Fixtures
# ============================================================================


@pytest.fixture
def malicious_inputs():
    """Common malicious inputs for security testing."""
    return {
        "sql_injection": [
            "'; DROP TABLE users; --",
            "1 OR 1=1",
            "UNION SELECT * FROM passwords",
            "1; DELETE FROM predictions WHERE 1=1",
        ],
        "xss": [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert(1)>",
            "javascript:alert('xss')",
            "<svg onload=alert(1)>",
        ],
        "path_traversal": ["../../../etc/passwd", "..\\..\\..\\windows\\system32", "....//....//etc/passwd"],
        "command_injection": ["; ls -la", "| cat /etc/shadow", "`id`", "$(uname -a)"],
    }


@pytest.fixture
def security_headers():
    """Expected security headers for responses."""
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
    }


# ============================================================================
# Performance Testing Fixtures
# ============================================================================


@pytest.fixture
def performance_timer():
    """Timer for performance testing."""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.perf_counter()

        def stop(self):
            self.end_time = time.perf_counter()

        @property
        def elapsed_ms(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time) * 1000
            return None

        def assert_under(self, max_ms):
            assert self.elapsed_ms is not None, "Timer not stopped"
            assert self.elapsed_ms < max_ms, f"Elapsed {self.elapsed_ms}ms exceeds {max_ms}ms"

    return Timer()


@pytest.fixture
def benchmark_requests(client, api_headers):
    """Benchmark helper for request performance."""
    import time

    def _benchmark(endpoint, method="GET", data=None, iterations=10):
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            if method == "GET":
                client.get(endpoint, headers=api_headers)
            elif method == "POST":
                client.post(endpoint, json=data, headers=api_headers)
            times.append((time.perf_counter() - start) * 1000)

        return {"min_ms": min(times), "max_ms": max(times), "avg_ms": sum(times) / len(times), "iterations": iterations}

    return _benchmark


# ============================================================================
# Database Integration Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def test_database_url():
    """Get test database URL (uses SQLite for testing)."""
    import tempfile

    temp_dir = tempfile.gettempdir()
    return f"sqlite:///{temp_dir}/test_floodingnaque.db"


@pytest.fixture(scope="function")
def db_session(app, test_database_url):
    """Create a database session for testing with automatic cleanup."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import scoped_session, sessionmaker

    # Use test database URL
    with patch.dict(os.environ, {"DATABASE_URL": test_database_url}):
        engine = create_engine(test_database_url, echo=False)

        # Import models to create tables
        try:
            from app.models.db import Base

            Base.metadata.create_all(engine)
        except ImportError:
            pass

        Session = scoped_session(sessionmaker(bind=engine))
        session = Session()

        yield session

        # Cleanup
        session.rollback()
        session.close()
        Session.remove()


@pytest.fixture
def mock_db_context():
    """Context manager for mocking database operations."""

    class DBContextMock:
        def __init__(self):
            self.session = MagicMock()
            self.queries = []

        def __enter__(self):
            return self.session

        def __exit__(self, *args):
            pass

        def record_query(self, query):
            self.queries.append(query)

    return DBContextMock()


# ============================================================================
# External API Mock Fixtures (Contract Testing)
# ============================================================================


@pytest.fixture
def mock_google_weather_response():
    """Mock Google Weather API response."""
    return {
        "currentConditions": {
            "temperature": {"value": 28.5},
            "humidity": {"value": 75},
            "precipitation": {"value": 5.0},
            "windSpeed": {"value": 15.0},
            "pressure": {"value": 1013.25},
            "uvIndex": {"value": 7},
            "cloudCover": {"value": 40},
        },
        "forecast": {
            "days": [
                {
                    "date": "2025-01-21",
                    "maxTemperature": {"value": 32.0},
                    "minTemperature": {"value": 24.0},
                    "precipitation": {"value": 10.0},
                },
                {
                    "date": "2025-01-22",
                    "maxTemperature": {"value": 30.0},
                    "minTemperature": {"value": 25.0},
                    "precipitation": {"value": 25.0},
                },
            ]
        },
    }


@pytest.fixture
def mock_meteostat_response():
    """Mock Meteostat API response."""
    return {
        "data": [
            {
                "date": "2025-01-20",
                "tavg": 27.5,
                "tmin": 24.0,
                "tmax": 31.0,
                "prcp": 5.2,
                "rhum": 78,
                "wspd": 12.5,
                "pres": 1012.0,
            },
            {
                "date": "2025-01-21",
                "tavg": 28.0,
                "tmin": 25.0,
                "tmax": 32.0,
                "prcp": 15.0,
                "rhum": 82,
                "wspd": 10.0,
                "pres": 1010.5,
            },
        ],
        "meta": {"generated": "2025-01-21T12:00:00Z", "stations": ["RPLL0"]},
    }


@pytest.fixture
def mock_worldtides_response():
    """Mock WorldTides API response."""
    return {
        "status": 200,
        "callCount": 1,
        "copyright": "WorldTides",
        "requestLat": 14.4793,
        "requestLon": 121.0198,
        "responseLat": 14.4793,
        "responseLon": 121.0198,
        "atlas": "TPXO",
        "station": "MANILA",
        "heights": [
            {"dt": 1737446400, "date": "2025-01-21T08:00+08:00", "height": 0.85},
            {"dt": 1737468000, "date": "2025-01-21T14:00+08:00", "height": 1.25},
            {"dt": 1737489600, "date": "2025-01-21T20:00+08:00", "height": 0.45},
        ],
        "extremes": [
            {"dt": 1737457200, "date": "2025-01-21T11:00+08:00", "height": 1.35, "type": "High"},
            {"dt": 1737500400, "date": "2025-01-21T23:00+08:00", "height": 0.25, "type": "Low"},
        ],
    }


@pytest.fixture
def mock_external_apis(mock_google_weather_response, mock_meteostat_response, mock_worldtides_response):
    """Mock all external API calls for integration testing."""
    with (
        patch("app.services.google_weather_service.requests.get") as mock_google,
        patch("app.services.meteostat_service.requests.get") as mock_meteostat,
        patch("app.services.worldtides_service.requests.get") as mock_tides,
    ):

        # Google Weather
        google_response = MagicMock()
        google_response.status_code = 200
        google_response.json.return_value = mock_google_weather_response
        google_response.raise_for_status = MagicMock()
        mock_google.return_value = google_response

        # Meteostat
        meteostat_response = MagicMock()
        meteostat_response.status_code = 200
        meteostat_response.json.return_value = mock_meteostat_response
        meteostat_response.raise_for_status = MagicMock()
        mock_meteostat.return_value = meteostat_response

        # WorldTides
        tides_response = MagicMock()
        tides_response.status_code = 200
        tides_response.json.return_value = mock_worldtides_response
        tides_response.raise_for_status = MagicMock()
        mock_tides.return_value = tides_response

        yield {"google": mock_google, "meteostat": mock_meteostat, "worldtides": mock_tides}


# ============================================================================
# Security Testing Fixtures (Extended)
# ============================================================================


@pytest.fixture
def sql_injection_payloads():
    """SQL injection test payloads."""
    return [
        # Basic injection
        "'; DROP TABLE users; --",
        "1 OR 1=1",
        "1' OR '1'='1",
        "1; DELETE FROM predictions WHERE 1=1",
        "UNION SELECT * FROM passwords",
        # Blind SQL injection
        "1 AND 1=1",
        "1 AND 1=2",
        "1' AND '1'='1",
        "1' AND SLEEP(5)--",
        # Second-order injection
        "admin'--",
        "' OR ''='",
        # Database-specific
        "'; EXEC xp_cmdshell('dir'); --",  # SQL Server
        "1; SELECT pg_sleep(5)--",  # PostgreSQL
    ]


@pytest.fixture
def xss_payloads():
    """XSS test payloads."""
    return [
        # Basic XSS
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert(1)>",
        "<svg onload=alert(1)>",
        # Event handlers
        "<body onload=alert(1)>",
        "<div onmouseover=alert(1)>",
        "<input onfocus=alert(1) autofocus>",
        # Protocol handlers
        "javascript:alert('xss')",
        "data:text/html,<script>alert('xss')</script>",
        # Encoded payloads
        "%3Cscript%3Ealert('xss')%3C/script%3E",
        "&#60;script&#62;alert('xss')&#60;/script&#62;",
        # DOM-based XSS
        "<img src='x' onerror='this.onerror=null;alert(1)'>",
        "<iframe src='javascript:alert(1)'></iframe>",
    ]


@pytest.fixture
def csrf_test_data():
    """CSRF test configuration."""
    return {
        "valid_token": "valid-csrf-token-12345",
        "invalid_token": "invalid-csrf-token",
        "expired_token": "expired-csrf-token",
        "missing_token": None,
        "protected_endpoints": ["/api/v1/predict", "/ingest", "/api/v1/upload", "/api/v1/export"],
    }


@pytest.fixture
def path_traversal_payloads():
    """Path traversal attack payloads."""
    return [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "....//....//....//etc/passwd",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc/passwd",
        "..%252f..%252f..%252fetc/passwd",
        "/etc/passwd%00.txt",
        "....\\....\\....\\windows\\system32",
    ]


@pytest.fixture
def command_injection_payloads():
    """Command injection test payloads."""
    return [
        "; ls -la",
        "| cat /etc/passwd",
        "& whoami",
        "`id`",
        "$(whoami)",
        "; ping -c 5 127.0.0.1",
        "|| cat /etc/passwd",
        "&& dir",
    ]


@pytest.fixture
def header_injection_payloads():
    """HTTP header injection payloads."""
    return [
        "test\r\nX-Injected: header",
        "test\r\nSet-Cookie: malicious=value",
        "test%0d%0aX-Injected:%20header",
        "test\nX-Forwarded-For: 127.0.0.1",
    ]


# ============================================================================
# Network Failure Simulation Fixtures
# ============================================================================


@pytest.fixture
def mock_network_failure():
    """Simulate network failures for negative path testing."""
    import requests.exceptions

    class NetworkFailureMock:
        def __init__(self):
            self.failure_type = None

        def timeout(self):
            """Simulate connection timeout."""
            self.failure_type = "timeout"
            raise requests.exceptions.Timeout("Connection timed out")

        def connection_error(self):
            """Simulate connection error."""
            self.failure_type = "connection"
            raise requests.exceptions.ConnectionError("Failed to connect")

        def dns_failure(self):
            """Simulate DNS failure."""
            self.failure_type = "dns"
            raise requests.exceptions.ConnectionError("DNS lookup failed")

        def ssl_error(self):
            """Simulate SSL error."""
            self.failure_type = "ssl"
            raise requests.exceptions.SSLError("SSL certificate verification failed")

        def http_error(self, status_code=500):
            """Simulate HTTP error response."""
            self.failure_type = f"http_{status_code}"
            response = MagicMock()
            response.status_code = status_code
            response.raise_for_status.side_effect = requests.exceptions.HTTPError(f"{status_code} Error")
            return response

    return NetworkFailureMock()


@pytest.fixture
def mock_slow_response():
    """Simulate slow API responses."""
    import time

    def _slow_response(delay_seconds=5):
        time.sleep(delay_seconds)
        return {"status": "ok", "delayed": True}

    return _slow_response


# ============================================================================
# Rate Limiting Test Fixtures
# ============================================================================


@pytest.fixture
def rate_limit_test_config():
    """Configuration for rate limiting tests."""
    return {
        "default_limit": "100 per minute",
        "burst_limit": "10 per second",
        "prediction_limit": "30 per minute",
        "ingest_limit": "60 per minute",
        "test_iterations": 150,  # Exceed default limit
    }


@pytest.fixture
def rapid_requests(client, api_headers):
    """Helper to make rapid requests for rate limit testing."""

    def _rapid_requests(endpoint, count=100, method="GET", data=None):
        responses = []
        for i in range(count):
            if method == "GET":
                resp = client.get(endpoint, headers=api_headers)
            else:
                resp = client.post(endpoint, json=data, headers=api_headers)
            responses.append(
                {
                    "iteration": i + 1,
                    "status_code": resp.status_code,
                    "rate_limited": resp.status_code == 429,
                    "headers": dict(resp.headers),
                }
            )
            if resp.status_code == 429:
                break
        return responses

    return _rapid_requests


# ============================================================================
# API Versioning Test Fixtures
# ============================================================================


@pytest.fixture
def api_v1_endpoints():
    """V1 API endpoints for backward compatibility testing."""
    return [
        {"path": "/api/v1/predict", "method": "POST", "required_fields": ["prediction", "flood_risk"]},
        {"path": "/api/v1/health", "method": "GET", "required_fields": ["status"]},
        {"path": "/api/v1/data", "method": "GET", "required_fields": ["data", "total"]},
        {"path": "/api/v1/models", "method": "GET", "required_fields": ["models"]},
    ]


@pytest.fixture
def deprecated_endpoints():
    """Endpoints that are deprecated but should still work."""
    return [
        {"path": "/predict", "new_path": "/api/v1/predict"},
        {"path": "/health", "new_path": "/api/v1/health"},
    ]


# ============================================================================
# Error Handling Test Fixtures
# ============================================================================


@pytest.fixture
def mock_metrics_extended():
    """Mock Prometheus metrics for testing without Prometheus installed."""
    with patch("app.utils.metrics._metrics") as mock:
        mock.predictions_total = MagicMock()
        mock.external_api_calls_total = MagicMock()
        mock.db_pool_connections = MagicMock()
        mock.cache_operations = MagicMock()
        mock.circuit_breaker_state = MagicMock()
        yield mock


@pytest.fixture
def mock_error_context():
    """Fixture for testing ErrorContext context manager."""
    from app.utils.error_handling import ErrorContext

    return ErrorContext


@pytest.fixture
def structured_error_factory():
    """Factory fixture to create StructuredError instances for testing."""
    from app.utils.error_handling import ErrorCategory, StructuredError

    def _create_error(
        error_id="test-error-id",
        category=ErrorCategory.INTERNAL,
        message="Test error message",
        exception_type="TestException",
        exception_message="Test exception",
        recoverable=False,
        retry_after_seconds=None,
        **context,
    ):
        return StructuredError(
            error_id=error_id,
            category=category,
            message=message,
            exception_type=exception_type,
            exception_message=exception_message,
            recoverable=recoverable,
            retry_after_seconds=retry_after_seconds,
            context=context,
        )

    return _create_error


@pytest.fixture
def mock_external_services():
    """Mock all external services at once for isolated testing."""
    patches = []

    # Mock weather services
    weather_patch = patch("app.services.google_weather_service.GoogleWeatherService")
    meteostat_patch = patch("app.services.meteostat_service.MeteostatService")
    worldtides_patch = patch("app.services.worldtides_service.WorldTidesService")

    mock_weather = weather_patch.start()
    mock_meteostat = meteostat_patch.start()
    mock_worldtides = worldtides_patch.start()

    patches.extend([weather_patch, meteostat_patch, worldtides_patch])

    # Configure default return values
    mock_weather.return_value.get_weather.return_value = {
        "temperature": 298.15,
        "humidity": 75.0,
        "precipitation": 5.0,
    }
    mock_meteostat.return_value.get_historical_data.return_value = []
    mock_worldtides.return_value.get_tides.return_value = {"tide_level": 1.5}

    yield {
        "weather": mock_weather,
        "meteostat": mock_meteostat,
        "worldtides": mock_worldtides,
    }

    # Cleanup
    for p in patches:
        p.stop()


@pytest.fixture
def mock_model_with_predictions():
    """Factory fixture for models with configurable prediction outcomes."""

    def _create_model(prediction=0, probabilities=None):
        model = MagicMock()
        model.predict.return_value = [prediction]
        model.predict_proba.return_value = [probabilities or [0.8, 0.2]]
        model.feature_names_in_ = ["temperature", "humidity", "precipitation"]
        return model

    return _create_model
