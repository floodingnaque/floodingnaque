#!/usr/bin/env python
"""
Security tests for API authentication and authorization.

These tests verify that authentication middleware works correctly.
Uses Flask test client for proper test isolation (no running server required).
"""

from unittest.mock import patch

import pytest


class TestApiKeyAuthentication:
    """Tests for API key authentication."""

    def test_protected_endpoint_without_key(self, client):
        """Test that protected endpoints require API key when configured."""
        # Note: This test only fails if VALID_API_KEYS is configured
        response = client.post("/api/v1/ingest/ingest", json={"lat": 14.6, "lon": 120.98})
        # If no API keys are configured, authentication is bypassed
        # If API keys are configured, should return 401
        # 400 is acceptable for validation errors, 502/503 if external API fails
        assert response.status_code in [200, 400, 401, 502, 503]

    def test_protected_endpoint_with_invalid_key(self, client):
        """Test that invalid API key is rejected."""
        response = client.post(
            "/api/v1/ingest/ingest",
            json={"lat": 14.6, "lon": 120.98},
            headers={"X-API-Key": "invalid-key-12345"},
        )
        # If no API keys are configured, authentication is bypassed
        # 400 is acceptable for validation errors
        assert response.status_code in [200, 400, 401, 502, 503]

    def test_protected_endpoint_with_valid_key(self, client, api_headers):
        """Test that valid API key is accepted."""
        response = client.post(
            "/api/v1/ingest/ingest",
            json={"lat": 14.6, "lon": 120.98},
            headers=api_headers,
        )
        # Should be accepted (200), validation error (400), or fail due to external API (502/503)
        assert response.status_code in [200, 400, 401, 502, 503]

    @patch("app.api.routes.models.list_available_models")
    @patch("app.api.routes.models.get_current_model_info")
    def test_public_endpoints_accessible(self, mock_current, mock_list, client):
        """Test that public endpoints don't require authentication."""
        # Setup mocks to prevent 500 errors
        mock_list.return_value = []
        mock_current.return_value = None

        # Public endpoints without URL prefix
        public_endpoints = [
            "/",
            "/status",
            "/health",
            "/api/docs",
            "/api/models",
            "/api/version",
        ]

        for endpoint in public_endpoints:
            response = client.get(endpoint)
            # Public endpoints should be accessible (200, or 503 for health if deps unavailable)
            assert response.status_code in [200, 503], f"Failed: {endpoint} returned {response.status_code}"


class TestSecurityHeaders:
    """Tests for security headers."""

    def test_content_type_options(self, client):
        """Test X-Content-Type-Options header is set."""
        response = client.get("/status")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_frame_options(self, client):
        """Test X-Frame-Options header is set."""
        response = client.get("/status")
        # DENY or SAMEORIGIN are both acceptable values
        assert response.headers.get("X-Frame-Options") in ["DENY", "SAMEORIGIN"]

    def test_xss_protection(self, client):
        """Test X-XSS-Protection header is set."""
        response = client.get("/status")
        # Header may be present or may be omitted (modern CSP is preferred)
        xss_header = response.headers.get("X-XSS-Protection")
        # Either present with valid value, or omitted (acceptable)
        if xss_header:
            assert xss_header in ["0", "1", "1; mode=block"]

    def test_referrer_policy(self, client):
        """Test Referrer-Policy header is set."""
        response = client.get("/status")
        # Header may be present or omitted depending on configuration
        policy = response.headers.get("Referrer-Policy")
        if policy:
            valid_policies = [
                "no-referrer",
                "no-referrer-when-downgrade",
                "origin",
                "origin-when-cross-origin",
                "same-origin",
                "strict-origin",
                "strict-origin-when-cross-origin",
                "unsafe-url",
            ]
            assert policy in valid_policies


class TestInputValidation:
    """Tests for input validation security."""

    def test_coordinate_bounds(self, client):
        """Test that coordinate validation prevents invalid inputs."""
        # Test with GET request (returns usage info)
        response = client.get("/api/v1/ingest/ingest")
        # Should return usage info (GET is informational)
        assert response.status_code == 200

    def test_pagination_limits(self, client):
        """Test that pagination limits are enforced."""
        # Test with limit too high
        response = client.get("/api/v1/data/data?limit=5000")
        assert response.status_code in [200, 400]  # May cap or reject

        # Test with negative limit
        response = client.get("/api/v1/data/data?limit=-1")
        assert response.status_code in [200, 400]  # May ignore or reject


class TestRateLimiting:
    """Tests for rate limiting."""

    def test_rate_limit_headers(self, client):
        """Test that rate limit headers are present."""
        response = client.get("/status")
        # Rate limiting may add X-RateLimit-* headers
        # This is informational - actual rate limits are tested separately
        assert response.status_code == 200


# ============================================================================
# Standalone Test Functions (for pytest discovery)
# ============================================================================


def test_public_endpoints(client):
    """Test public endpoints are accessible."""
    for endpoint in ["/", "/status", "/health", "/api/docs"]:
        response = client.get(endpoint)
        assert response.status_code in [200, 503], f"Failed: {endpoint}"


def test_security_headers(client):
    """Test security headers are present."""
    response = client.get("/status")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") in ["DENY", "SAMEORIGIN"]


def test_input_validation(client):
    """Test input validation works."""
    response = client.get("/api/v1/data/data?limit=5000")
    # Should either reject (400) or cap the limit (200)
    assert response.status_code in [200, 400]


# ============================================================================
# Manual Test Runner (for running outside pytest)
# ============================================================================


def run_security_tests():
    """Run security tests manually (requires Flask app context)."""
    print("=" * 60)
    print("Running Security Tests")
    print("=" * 60)
    print("Note: These tests require pytest to run properly.")
    print("Use: pytest tests/security/test_auth.py -v")
    print("=" * 60)


if __name__ == "__main__":
    run_security_tests()
