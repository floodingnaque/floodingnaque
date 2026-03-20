"""
Pytest Configuration and Shared Fixtures.

Core fixtures and configuration that must remain in the root conftest.py:
- Environment setup (must run before any app import)
- Deterministic constants (UUIDs, timestamps)
- Flask application fixtures (session-scoped)
- Autouse fixtures (singleton reset, health mock, GC cleanup)
- Utility helpers

Per-feature fixtures have been split into tests/fixtures/ modules and are
registered via the ``pytest_plugins`` list below.
"""

import gc
import os
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

# ---------------------------------------------------------------------------
# Register per-feature fixture modules
# ---------------------------------------------------------------------------
pytest_plugins = [
    "tests.fixtures.mock_models",
    "tests.fixtures.mock_services",
    "tests.fixtures.database",
    "tests.fixtures.sample_data",
    "tests.fixtures.infrastructure",
    "tests.fixtures.security_performance",
]

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
os.environ.setdefault("AUTH_BYPASS_ENABLED", "false")
os.environ.setdefault("STARTUP_HEALTH_CHECK", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")
os.environ.setdefault("ENV_VALIDATION_ENABLED", "false")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")  # Disable rate limiting in tests
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")  # In-memory SQLite for tests
# PBKDF2 fallback salt – required by _hash_api_key_pbkdf2() in auth middleware.
# Without this, any call to validate_api_key / revoke / expire raises ValueError.
os.environ.setdefault(
    "API_KEY_HASH_SALT",
    "test-salt-value-for-unit-tests-at-least-32-chars!!",
)
# Set a deterministic test API key so auth middleware does not reject requests.
# Individual tests can clear this or set AUTH_BYPASS_ENABLED=true as needed.
os.environ.setdefault("VALID_API_KEYS", "xK9mR-vL2pN8qW5jT7bF4hD6cY0aG3sE")


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
    # WARNING: Tests default to in-memory SQLite, which does not support all
    # PostgreSQL features (e.g. JSON operators, array types, ON CONFLICT).
    # Set TEST_DATABASE_URL in the environment to run against a real PG instance.
    test_db_url = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")
    application.config.update(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "PRESERVE_CONTEXT_ON_EXCEPTION": False,
            "SQLALCHEMY_DATABASE_URI": test_db_url,
        }
    )

    yield application


@pytest.fixture(scope="function")
def client(app):
    """Create a test client for making HTTP requests."""
    with app.test_client() as testing_client:
        with app.app_context():
            # Recreate tables after reset_singletons disposed the engine
            from app.models.db import Base, get_engine

            Base.metadata.create_all(get_engine())
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
    # Reset database engine and session singletons to prevent stale connections
    try:
        import app.models.db as _db_mod

        if _db_mod._engine is not None:
            _db_mod._engine.dispose()
            _db_mod._engine = None
        _db_mod._Session = None
    except (ImportError, AttributeError):
        pass

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
# Auto-Mock Health Dependencies (autouse)
# ============================================================================


@pytest.fixture(scope="function")
def auto_mock_health_dependencies(request):
    """
    Mock health check dependencies for tests that need them.

    This prevents tests from failing due to:
    - Database not being available
    - Model not being loaded
    - Redis not being connected
    - External APIs being unavailable

    Usage – apply explicitly to tests that need mocked infrastructure:
        @pytest.mark.mock_health
        def test_something(self, client):
            ...

    Or request the fixture directly:
        def test_something(self, auto_mock_health_dependencies, client):
            ...
    """

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
# Utility Helpers
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
# GC Cleanup (autouse)
# ============================================================================


@pytest.fixture(autouse=True)
def cleanup_gc():
    """Run garbage collection after each test to help release file handles on Windows."""
    yield
    gc.collect()
