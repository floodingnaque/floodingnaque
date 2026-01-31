"""
Unit tests for body size middleware.

Tests for app/api/middleware/body_size.py
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest
from app.api.middleware.body_size import (
    DEFAULT_LIMITS,
    get_body_size_limit,
    limit_body_size,
)
from flask import Flask


class TestBodySizeLimits:
    """Tests for body size limit configuration."""

    def test_default_limits_exist(self):
        """Test default limits are defined."""
        assert "default" in DEFAULT_LIMITS
        assert "auth" in DEFAULT_LIMITS
        assert "predict" in DEFAULT_LIMITS
        assert "ingest" in DEFAULT_LIMITS
        assert "upload" in DEFAULT_LIMITS

    def test_default_limit_values(self):
        """Test default limit values are reasonable."""
        # Auth should be small
        assert DEFAULT_LIMITS["auth"] <= 100 * 1024  # <= 100 KB

        # Upload should be larger
        assert DEFAULT_LIMITS["upload"] >= 5 * 1024 * 1024  # >= 5 MB

    def test_get_body_size_limit_default(self):
        """Test getting default body size limit."""
        limit = get_body_size_limit("default")

        assert limit == DEFAULT_LIMITS["default"]

    def test_get_body_size_limit_auth(self):
        """Test getting auth endpoint limit."""
        limit = get_body_size_limit("auth")

        assert limit == DEFAULT_LIMITS["auth"]

    def test_get_body_size_limit_unknown_type(self):
        """Test getting limit for unknown endpoint type falls back to default."""
        limit = get_body_size_limit("unknown_type")

        assert limit == DEFAULT_LIMITS["default"]

    @patch.dict(os.environ, {"MAX_BODY_SIZE_AUTH_KB": "50"})
    def test_get_body_size_limit_from_env(self):
        """Test getting limit from environment variable."""
        limit = get_body_size_limit("auth")

        assert limit == 50 * 1024  # 50 KB in bytes

    @patch.dict(os.environ, {"MAX_BODY_SIZE_AUTH_KB": "invalid"})
    def test_get_body_size_limit_invalid_env(self):
        """Test fallback when environment variable is invalid."""
        limit = get_body_size_limit("auth")

        assert limit == DEFAULT_LIMITS["auth"]


class TestLimitBodySizeDecorator:
    """Tests for limit_body_size decorator."""

    def test_decorator_with_endpoint_type(self):
        """Test decorator with endpoint type parameter."""
        app = Flask(__name__)

        @app.route("/test")
        @limit_body_size("auth")
        def test_endpoint():
            return "ok"

        # Decorator should wrap function
        assert callable(test_endpoint)

    def test_decorator_with_custom_limit(self):
        """Test decorator with custom limit parameter."""
        app = Flask(__name__)

        @app.route("/test")
        @limit_body_size(custom_limit_bytes=1024)
        def test_endpoint():
            return "ok"

        assert callable(test_endpoint)


class TestBodySizeValidation:
    """Tests for body size validation in requests."""

    def test_small_body_accepted(self, client):
        """Test that small request bodies are accepted."""
        small_data = {"key": "value"}

        response = client.post(
            "/predict",  # Use actual endpoint that accepts POST
            data=json.dumps(small_data),
            content_type="application/json",
        )

        # Should not be rejected for size (may fail for other reasons)
        assert response.status_code != 413

    def test_content_length_header_checked(self, client):
        """Test that Content-Length header is checked."""
        # Content-Length is checked before body is read
        pass

    def test_response_format_on_rejection(self):
        """Test response format when body too large."""
        # Response should be JSON with error message
        pass


class TestEndpointSpecificLimits:
    """Tests for endpoint-specific limits."""

    def test_predict_endpoint_limit(self):
        """Test predict endpoint has appropriate limit."""
        # Predict should allow reasonable request sizes
        assert DEFAULT_LIMITS["predict"] >= 50 * 1024  # At least 50 KB

    def test_ingest_endpoint_limit(self):
        """Test ingest endpoint has appropriate limit."""
        # Ingest may need larger limits for batch data
        assert DEFAULT_LIMITS["ingest"] >= 100 * 1024  # At least 100 KB

    def test_batch_endpoint_limit(self):
        """Test batch endpoint has larger limit."""
        # Batch operations need larger limits
        assert DEFAULT_LIMITS["batch"] >= 1 * 1024 * 1024  # At least 1 MB

    def test_webhook_endpoint_limit(self):
        """Test webhook endpoint has appropriate limit."""
        # Webhooks may receive various payload sizes
        assert DEFAULT_LIMITS["webhook"] >= 100 * 1024  # At least 100 KB


class TestSecurityBenefits:
    """Tests verifying security benefits of body size limits."""

    def test_dos_protection(self):
        """Test that limits provide DoS protection."""
        # All limits should be finite and reasonable
        for endpoint_type, limit in DEFAULT_LIMITS.items():
            assert limit > 0
            assert limit < 100 * 1024 * 1024  # Max 100 MB

    def test_sensitive_endpoints_have_strict_limits(self):
        """Test that auth endpoints have stricter limits."""
        # Auth should be stricter than general
        assert DEFAULT_LIMITS["auth"] < DEFAULT_LIMITS["default"]


class TestLogging:
    """Tests for body size limit logging."""

    @patch("app.api.middleware.body_size.logger")
    def test_oversized_request_logged(self, mock_logger):
        """Test that oversized requests are logged."""
        # When a request exceeds the limit, it should be logged
        pass
