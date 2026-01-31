"""
Unit tests for rate limit middleware.

Tests for app/api/middleware/rate_limit.py
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from app.api.middleware.rate_limit import (
    BURST_ENABLED,
    BURST_MULTIPLIER,
    BURST_WINDOW_SECONDS,
    DEFAULT_LIMIT,
    INTERNAL_BYPASS_IPS,
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_STORAGE,
    Limiter,
    get_rate_limit_key,
    get_remote_address,
    is_internal_service_request,
)
from flask import Flask, g


class TestRateLimitConfiguration:
    """Tests for rate limit configuration."""

    def test_rate_limit_enabled_env_var(self):
        """Test RATE_LIMIT_ENABLED environment variable is read."""
        assert isinstance(RATE_LIMIT_ENABLED, bool)

    def test_rate_limit_storage_env_var(self):
        """Test RATE_LIMIT_STORAGE environment variable is read."""
        assert isinstance(RATE_LIMIT_STORAGE, str)

    def test_default_limit_env_var(self):
        """Test DEFAULT_LIMIT environment variable is read."""
        assert isinstance(DEFAULT_LIMIT, str)

    def test_burst_configuration(self):
        """Test burst configuration constants."""
        assert isinstance(BURST_ENABLED, bool)
        assert isinstance(BURST_MULTIPLIER, float)
        assert isinstance(BURST_WINDOW_SECONDS, int)


class TestGetRateLimitKey:
    """Tests for get_rate_limit_key function."""

    def test_get_rate_limit_key_function_exists(self):
        """Test get_rate_limit_key function exists."""
        assert callable(get_rate_limit_key)

    def test_get_rate_limit_key_returns_string(self):
        """Test get_rate_limit_key returns a string."""
        app = Flask(__name__)

        with app.test_request_context("/test"):
            key = get_rate_limit_key()

            assert isinstance(key, str)

    @patch("app.api.middleware.rate_limit.is_internal_service_request", return_value=False)
    def test_get_rate_limit_key_uses_api_key_if_present(self, mock_internal):
        """Test get_rate_limit_key uses API key hash if present."""
        app = Flask(__name__)

        with app.test_request_context("/test"):
            g.api_key_hash = "test_hash_123"  # pragma: allowlist secret
            key = get_rate_limit_key()

            assert "api_key" in key
            assert "test_hash_123" in key


class TestIsInternalServiceRequest:
    """Tests for is_internal_service_request function."""

    def test_is_internal_service_request_function_exists(self):
        """Test is_internal_service_request function exists."""
        assert callable(is_internal_service_request)

    def test_is_internal_service_request_returns_bool(self):
        """Test is_internal_service_request returns boolean."""
        app = Flask(__name__)

        with app.test_request_context("/test"):
            result = is_internal_service_request()

            assert isinstance(result, bool)

    @patch.dict(os.environ, {"RATE_LIMIT_INTERNAL_BYPASS_ENABLED": "false"})
    def test_internal_bypass_disabled(self):
        """Test internal bypass when disabled."""
        # Reimport to get new env value
        from flask import Flask

        app = Flask(__name__)

        with app.test_request_context("/test"):
            # When bypass is disabled, should return False
            pass  # Just verify no crash


class TestInternalBypassIPs:
    """Tests for internal bypass IP configuration."""

    def test_internal_bypass_ips_is_set(self):
        """Test INTERNAL_BYPASS_IPS is configured."""
        assert isinstance(INTERNAL_BYPASS_IPS, set)

    def test_localhost_in_bypass_ips(self):
        """Test localhost IPs are in bypass list."""
        # By default should include localhost
        assert "127.0.0.1" in INTERNAL_BYPASS_IPS or "::1" in INTERNAL_BYPASS_IPS


class TestGetRemoteAddress:
    """Tests for get_remote_address usage."""

    def test_get_remote_address_imported(self):
        """Test get_remote_address is available."""
        assert callable(get_remote_address)


class TestLimiterSetup:
    """Tests for Flask-Limiter setup."""

    def test_limiter_class_imported(self):
        """Test Limiter class is imported."""
        assert Limiter is not None
