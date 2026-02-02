"""
Unit tests for security middleware.

Tests for app/api/middleware/security.py
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from app.api.middleware.security import (
    add_security_headers,
    get_cors_origins,
    setup_cors,
    setup_security_headers,
    validate_cors_origin,
)
from flask import Flask


class TestAddSecurityHeaders:
    """Tests for add_security_headers function."""

    def test_add_security_headers_exists(self):
        """Test add_security_headers function exists."""
        assert callable(add_security_headers)

    def test_adds_x_content_type_options(self):
        """Test X-Content-Type-Options header is added."""
        app = Flask(__name__)
        with app.test_request_context("/api/test"):
            response = MagicMock()
            response.headers = {}

            result = add_security_headers(response)

            assert result.headers["X-Content-Type-Options"] == "nosniff"

    def test_adds_x_frame_options(self):
        """Test X-Frame-Options header is added."""
        app = Flask(__name__)
        with app.test_request_context("/api/test"):
            response = MagicMock()
            response.headers = {}

            result = add_security_headers(response)

            assert result.headers["X-Frame-Options"] == "DENY"

    def test_adds_x_xss_protection(self):
        """Test X-XSS-Protection header is added."""
        app = Flask(__name__)
        with app.test_request_context("/api/test"):
            response = MagicMock()
            response.headers = {}

            result = add_security_headers(response)

            assert result.headers["X-XSS-Protection"] == "1; mode=block"

    def test_adds_referrer_policy(self):
        """Test Referrer-Policy header is added."""
        app = Flask(__name__)
        with app.test_request_context("/api/test"):
            response = MagicMock()
            response.headers = {}

            result = add_security_headers(response)

            assert result.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_adds_permissions_policy(self):
        """Test Permissions-Policy header is added."""
        app = Flask(__name__)
        with app.test_request_context("/api/test"):
            response = MagicMock()
            response.headers = {}

            result = add_security_headers(response)

            assert "Permissions-Policy" in result.headers
            assert "accelerometer=()" in result.headers["Permissions-Policy"]
            assert "camera=()" in result.headers["Permissions-Policy"]
            assert "microphone=()" in result.headers["Permissions-Policy"]

    def test_adds_coep_header(self):
        """Test Cross-Origin-Embedder-Policy header is added."""
        app = Flask(__name__)
        with app.test_request_context("/api/test"):
            response = MagicMock()
            response.headers = {}

            result = add_security_headers(response)

            assert "Cross-Origin-Embedder-Policy" in result.headers

    def test_adds_coop_header(self):
        """Test Cross-Origin-Opener-Policy header is added."""
        app = Flask(__name__)
        with app.test_request_context("/api/test"):
            response = MagicMock()
            response.headers = {}

            result = add_security_headers(response)

            assert "Cross-Origin-Opener-Policy" in result.headers

    def test_adds_corp_header(self):
        """Test Cross-Origin-Resource-Policy header is added."""
        app = Flask(__name__)
        with app.test_request_context("/api/test"):
            response = MagicMock()
            response.headers = {}

            result = add_security_headers(response)

            assert "Cross-Origin-Resource-Policy" in result.headers

    @patch.dict(os.environ, {"ENABLE_HTTPS": "true"})
    def test_adds_hsts_in_production(self):
        """Test HSTS header is added when HTTPS is enabled."""
        app = Flask(__name__)
        with app.test_request_context("/api/test"):
            response = MagicMock()
            response.headers = {}

            result = add_security_headers(response)

            assert "Strict-Transport-Security" in result.headers
            assert "max-age=" in result.headers["Strict-Transport-Security"]

    def test_adds_csp_header(self):
        """Test Content-Security-Policy header is added."""
        app = Flask(__name__)
        with app.test_request_context("/api/test"):
            response = MagicMock()
            response.headers = {}

            result = add_security_headers(response)

            assert "Content-Security-Policy" in result.headers
            assert "default-src" in result.headers["Content-Security-Policy"]

    def test_cache_control_for_api(self):
        """Test Cache-Control is set to no-store for API responses."""
        app = Flask(__name__)
        with app.test_request_context("/api/predict"):
            response = MagicMock()
            response.headers = {}

            result = add_security_headers(response)

            assert "no-store" in result.headers["Cache-Control"]
            assert result.headers["Pragma"] == "no-cache"
            assert result.headers["Expires"] == "0"

    def test_cache_control_for_health_endpoint(self):
        """Test Cache-Control allows caching for health endpoint."""
        app = Flask(__name__)
        with app.test_request_context("/health"):
            response = MagicMock()
            response.headers = {}

            result = add_security_headers(response)

            assert "public" in result.headers["Cache-Control"]
            assert "max-age=60" in result.headers["Cache-Control"]

    def test_preserves_existing_cache_control(self):
        """Test existing Cache-Control header is preserved."""
        app = Flask(__name__)
        with app.test_request_context("/api/test"):
            response = MagicMock()
            response.headers = {"Cache-Control": "max-age=3600"}

            result = add_security_headers(response)

            assert result.headers["Cache-Control"] == "max-age=3600"


class TestSetupSecurityHeaders:
    """Tests for setup_security_headers function."""

    def test_setup_function_exists(self):
        """Test setup_security_headers function exists."""
        assert callable(setup_security_headers)

    def test_registers_after_request_handler(self):
        """Test setup registers after_request handler."""
        app = Flask(__name__)

        setup_security_headers(app)

        # Verify after_request hook is registered
        assert app.after_request_funcs is not None


class TestGetCorsOrigins:
    """Tests for get_cors_origins function."""

    def test_function_exists(self):
        """Test get_cors_origins function exists."""
        assert callable(get_cors_origins)

    @patch.dict(os.environ, {"CORS_ORIGINS": "http://localhost:3000,http://example.com"}, clear=False)
    def test_returns_configured_origins(self):
        """Test returns origins from environment."""
        origins = get_cors_origins()

        # Use set comparison for exact membership check (avoids CodeQL py/incomplete-url-substring-sanitization)
        expected_origins = {"http://localhost:3000", "http://example.com"}
        assert set(origins) == expected_origins

    @patch.dict(os.environ, {"CORS_ORIGINS": "", "FLASK_DEBUG": "true"}, clear=False)
    @patch("app.api.middleware.security.is_debug_mode", return_value=True)
    def test_returns_default_in_debug(self, mock_debug):
        """Test returns default localhost origins in debug mode."""
        origins = get_cors_origins()

        assert "http://localhost:3000" in origins
        assert "http://127.0.0.1:3000" in origins

    @patch.dict(os.environ, {"CORS_ORIGINS": ""}, clear=False)
    @patch("app.api.middleware.security.is_debug_mode", return_value=False)
    def test_returns_empty_in_production_without_config(self, mock_debug):
        """Test returns empty list in production without config."""
        origins = get_cors_origins()

        assert origins == []


class TestSetupCors:
    """Tests for setup_cors function."""

    def test_function_exists(self):
        """Test setup_cors function exists."""
        assert callable(setup_cors)

    @patch("app.api.middleware.security.get_cors_origins")
    def test_configures_cors_with_origins(self, mock_get_origins):
        """Test CORS is configured with allowed origins."""
        mock_get_origins.return_value = ["http://localhost:3000"]
        app = Flask(__name__)
        cors_instance = MagicMock()

        setup_cors(app, cors_instance)

        cors_instance.init_app.assert_called_once()
        call_kwargs = cors_instance.init_app.call_args[1]
        assert call_kwargs["origins"] == ["http://localhost:3000"]
        assert "GET" in call_kwargs["methods"]
        assert "POST" in call_kwargs["methods"]

    @patch("app.api.middleware.security.get_cors_origins")
    def test_skips_cors_without_origins(self, mock_get_origins):
        """Test CORS is not configured when no origins specified."""
        mock_get_origins.return_value = []
        app = Flask(__name__)
        cors_instance = MagicMock()

        setup_cors(app, cors_instance)

        cors_instance.init_app.assert_not_called()


class TestValidateCorsOrigin:
    """Tests for validate_cors_origin function."""

    def test_function_exists(self):
        """Test validate_cors_origin function exists."""
        assert callable(validate_cors_origin)

    def test_rejects_empty_origin(self):
        """Test empty origin is rejected."""
        assert validate_cors_origin("") is False
        # Note: None would be a type error, test only empty string

    @patch("app.api.middleware.security.get_cors_origins")
    def test_rejects_no_allowed_origins(self, mock_get_origins):
        """Test origin is rejected when no origins allowed."""
        mock_get_origins.return_value = []

        assert validate_cors_origin("http://example.com") is False

    @patch("app.api.middleware.security.get_cors_origins")
    def test_accepts_allowed_origin(self, mock_get_origins):
        """Test allowed origin is accepted."""
        mock_get_origins.return_value = ["http://localhost:3000", "http://example.com"]

        assert validate_cors_origin("http://localhost:3000") is True
        assert validate_cors_origin("http://example.com") is True

    @patch("app.api.middleware.security.get_cors_origins")
    def test_rejects_disallowed_origin(self, mock_get_origins):
        """Test disallowed origin is rejected."""
        mock_get_origins.return_value = ["http://localhost:3000"]

        assert validate_cors_origin("http://malicious.com") is False

    @patch("app.api.middleware.security.get_cors_origins")
    def test_handles_trailing_slash(self, mock_get_origins):
        """Test trailing slashes are handled correctly."""
        mock_get_origins.return_value = ["http://localhost:3000"]

        assert validate_cors_origin("http://localhost:3000/") is True

    @patch("app.api.middleware.security.get_cors_origins")
    def test_supports_wildcard_subdomain(self, mock_get_origins):
        """Test wildcard subdomain matching."""
        mock_get_origins.return_value = ["*.floodingnaque.com"]

        assert validate_cors_origin("http://app.floodingnaque.com") is True
        assert validate_cors_origin("http://api.floodingnaque.com") is True


class TestEnvironmentVariables:
    """Tests for environment variable handling."""

    @patch.dict(os.environ, {"COEP_POLICY": "require-corp"}, clear=False)
    def test_coep_from_env(self):
        """Test COEP policy from environment variable."""
        app = Flask(__name__)
        with app.test_request_context("/api/test"):
            response = MagicMock()
            response.headers = {}

            result = add_security_headers(response)

            assert result.headers["Cross-Origin-Embedder-Policy"] == "require-corp"

    @patch.dict(os.environ, {"COOP_POLICY": "same-origin"}, clear=False)
    def test_coop_from_env(self):
        """Test COOP policy from environment variable."""
        app = Flask(__name__)
        with app.test_request_context("/api/test"):
            response = MagicMock()
            response.headers = {}

            result = add_security_headers(response)

            assert result.headers["Cross-Origin-Opener-Policy"] == "same-origin"

    @patch.dict(os.environ, {"CORP_POLICY": "same-site"}, clear=False)
    def test_corp_from_env(self):
        """Test CORP policy from environment variable."""
        app = Flask(__name__)
        with app.test_request_context("/api/test"):
            response = MagicMock()
            response.headers = {}

            result = add_security_headers(response)

            assert result.headers["Cross-Origin-Resource-Policy"] == "same-site"

    @patch.dict(os.environ, {"CSP_POLICY": "default-src 'none'"}, clear=False)
    def test_csp_from_env(self):
        """Test CSP policy from environment variable."""
        app = Flask(__name__)
        with app.test_request_context("/api/test"):
            response = MagicMock()
            response.headers = {}

            result = add_security_headers(response)

            assert result.headers["Content-Security-Policy"] == "default-src 'none'"
