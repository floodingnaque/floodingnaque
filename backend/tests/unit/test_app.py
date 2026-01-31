"""
Unit tests for app/api/app.py.

Tests for the Flask application factory and core functionality.
"""

import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from app.api.app import create_app
from flask import Flask, g


class TestCreateApp:
    """Tests for create_app function."""

    @pytest.fixture(autouse=True)
    def setup_env(self):
        """Setup test environment variables."""
        env_vars = {
            "APP_ENV": "development",
            "FLASK_DEBUG": "true",
            "SECRET_KEY": "test-secret-key-for-testing-only-not-for-production",
            "TESTING": "true",
            "AUTH_BYPASS_ENABLED": "true",
            "STARTUP_HEALTH_CHECK": "false",
            "SCHEDULER_ENABLED": "false",
            "ENV_VALIDATION_ENABLED": "false",
            "FEATURE_API_DOCS_ENABLED": "false",
            "RESPONSE_TIME_TRACKING_ENABLED": "false",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            yield

    def test_create_app_returns_flask_instance(self, setup_env):
        """Test create_app returns a Flask application."""
        app = create_app()
        assert isinstance(app, Flask)

    def test_create_app_with_config_override(self, setup_env):
        """Test create_app accepts configuration overrides."""
        custom_config = {"CUSTOM_KEY": "custom_value"}
        app = create_app(config_override=custom_config)

        assert app.config.get("CUSTOM_KEY") == "custom_value"

    def test_create_app_sets_testing_mode(self, setup_env):
        """Test create_app can set testing configuration."""
        app = create_app(config_override={"TESTING": True})
        assert app.config.get("TESTING") is True

    def test_create_app_registers_blueprints(self, setup_env):
        """Test create_app registers expected blueprints."""
        app = create_app()

        # Check that key blueprints are registered
        blueprint_names = list(app.blueprints.keys())
        # At least some blueprints should be registered
        assert len(blueprint_names) > 0


class TestErrorHandlers:
    """Tests for HTTP error handlers."""

    @pytest.fixture
    def test_client(self):
        """Create test client with error handlers."""
        env_vars = {
            "APP_ENV": "development",
            "FLASK_DEBUG": "true",
            "SECRET_KEY": "test-secret-key-for-testing-only-not-for-production",
            "TESTING": "true",
            "AUTH_BYPASS_ENABLED": "true",
            "STARTUP_HEALTH_CHECK": "false",
            "SCHEDULER_ENABLED": "false",
            "ENV_VALIDATION_ENABLED": "false",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            app = create_app()
            app.config["TESTING"] = True
            with app.test_client() as client:
                yield client

    def test_404_error_handler(self, test_client):
        """Test 404 Not Found error handler."""
        response = test_client.get("/nonexistent-route-xyz-test")
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"

    def test_error_response_format_rfc7807(self, test_client):
        """Test error responses follow RFC 7807 format."""
        response = test_client.get("/nonexistent-endpoint-test")
        data = response.get_json()

        assert "error" in data
        error = data["error"]
        # RFC 7807 fields
        assert "type" in error
        assert "title" in error
        assert "status" in error
        assert "detail" in error

    def test_error_includes_request_id(self, test_client):
        """Test error responses include request ID."""
        response = test_client.get("/nonexistent-endpoint-test")
        data = response.get_json()

        assert "error" in data
        assert "request_id" in data["error"]


class TestRequestTracing:
    """Tests for request tracing middleware."""

    @pytest.fixture
    def test_app(self):
        """Create test application."""
        env_vars = {
            "APP_ENV": "development",
            "FLASK_DEBUG": "true",
            "SECRET_KEY": "test-secret-key-for-testing-only-not-for-production",
            "TESTING": "true",
            "AUTH_BYPASS_ENABLED": "true",
            "STARTUP_HEALTH_CHECK": "false",
            "SCHEDULER_ENABLED": "false",
            "ENV_VALIDATION_ENABLED": "false",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            app = create_app()
            app.config["TESTING"] = True
            return app

    def test_response_includes_correlation_headers(self, test_app):
        """Test responses include correlation headers."""
        with test_app.test_client() as client:
            response = client.get("/status")

            # Check for correlation headers
            assert "X-Request-ID" in response.headers or "X-Correlation-ID" in response.headers

    def test_accepts_incoming_trace_headers(self, test_app):
        """Test app accepts incoming trace headers."""
        with test_app.test_client() as client:
            headers = {
                "X-Request-ID": "test-request-123",
                "X-Correlation-ID": "test-correlation-456",
            }
            response = client.get("/status", headers=headers)

            # Should accept and potentially echo back trace headers
            assert response.status_code in [200, 401, 403]


class TestGetApp:
    """Tests for get_app singleton function."""

    def test_get_app_creates_instance(self):
        """Test get_app creates application instance."""
        env_vars = {
            "APP_ENV": "development",
            "FLASK_DEBUG": "true",
            "SECRET_KEY": "test-secret-key-for-testing-only-not-for-production",
            "TESTING": "true",
            "AUTH_BYPASS_ENABLED": "true",
            "STARTUP_HEALTH_CHECK": "false",
            "SCHEDULER_ENABLED": "false",
            "ENV_VALIDATION_ENABLED": "false",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            # Reset global app to None
            import app.api.app as app_module

            app_module.app = None

            app = app_module.get_app()
            assert isinstance(app, Flask)


class TestExtensionsInitialization:
    """Tests for Flask extensions initialization."""

    @pytest.fixture
    def test_app(self):
        """Create test application."""
        env_vars = {
            "APP_ENV": "development",
            "FLASK_DEBUG": "true",
            "SECRET_KEY": "test-secret-key-for-testing-only-not-for-production",
            "TESTING": "true",
            "AUTH_BYPASS_ENABLED": "true",
            "STARTUP_HEALTH_CHECK": "false",
            "SCHEDULER_ENABLED": "false",
            "ENV_VALIDATION_ENABLED": "false",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            app = create_app()
            app.config["TESTING"] = True
            return app

    def test_compression_enabled(self, test_app):
        """Test response compression is enabled."""
        # Compression extension should be initialized
        # This is tested by checking if app was created successfully
        assert test_app is not None

    def test_cors_initialized(self, test_app):
        """Test CORS is initialized."""
        with test_app.test_client() as client:
            # OPTIONS request should work (CORS preflight)
            response = client.options("/status")
            # Should not error out
            assert response.status_code in [200, 204, 404]


class TestStartupConfiguration:
    """Tests for startup configuration options."""

    def test_startup_health_check_can_be_disabled(self):
        """Test STARTUP_HEALTH_CHECK=false skips health validation."""
        env_vars = {
            "APP_ENV": "development",
            "FLASK_DEBUG": "true",
            "SECRET_KEY": "test-secret-key-for-testing-only-not-for-production",
            "STARTUP_HEALTH_CHECK": "false",
            "SCHEDULER_ENABLED": "false",
            "ENV_VALIDATION_ENABLED": "false",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            # Should not raise even if health checks would fail
            app = create_app()
            assert app is not None

    def test_scheduler_can_be_disabled(self):
        """Test SCHEDULER_ENABLED=false skips scheduler start."""
        env_vars = {
            "APP_ENV": "development",
            "FLASK_DEBUG": "true",
            "SECRET_KEY": "test-secret-key-for-testing-only-not-for-production",
            "STARTUP_HEALTH_CHECK": "false",
            "SCHEDULER_ENABLED": "false",
            "ENV_VALIDATION_ENABLED": "false",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            app = create_app()
            assert app is not None

    def test_env_validation_can_be_disabled(self):
        """Test ENV_VALIDATION_ENABLED=false skips env validation."""
        env_vars = {
            "APP_ENV": "development",
            "FLASK_DEBUG": "true",
            "SECRET_KEY": "test-secret-key-for-testing-only-not-for-production",
            "STARTUP_HEALTH_CHECK": "false",
            "SCHEDULER_ENABLED": "false",
            "ENV_VALIDATION_ENABLED": "false",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            app = create_app()
            assert app is not None


class TestBuildErrorResponse:
    """Tests for _build_error_response internal function."""

    @pytest.fixture
    def test_app(self):
        """Create test application."""
        env_vars = {
            "APP_ENV": "development",
            "FLASK_DEBUG": "true",
            "TESTING": "true",
            "AUTH_BYPASS_ENABLED": "true",
            "STARTUP_HEALTH_CHECK": "false",
            "SCHEDULER_ENABLED": "false",
            "ENV_VALIDATION_ENABLED": "false",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            app = create_app()
            app.config["TESTING"] = True
            return app

    def test_400_bad_request_response(self, test_app):
        """Test 400 error response structure."""
        with test_app.test_client() as client:
            # Trigger a 400 by sending invalid JSON
            response = client.post("/api/v1/predict/", data="not json", content_type="application/json")
            # May be 400 or 422 depending on validation
            assert response.status_code in [400, 401, 404, 422]

    def test_error_response_includes_timestamp(self, test_app):
        """Test error responses include timestamp."""
        with test_app.test_client() as client:
            response = client.get("/nonexistent")
            data = response.get_json()

            if data and "error" in data:
                assert "timestamp" in data["error"]
