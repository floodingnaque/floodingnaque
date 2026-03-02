"""
Integration tests for authentication middleware.

These tests exercise the real auth middleware flow (F1),
unlike unit tests that run with AUTH_BYPASS_ENABLED=true.
"""

import os
import secrets
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_strong_api_key() -> str:
    """Generate an API key that passes entropy / format checks."""
    return secrets.token_urlsafe(48)  # ~64 chars, high entropy


# ---------------------------------------------------------------------------
# Fixtures: auth-enabled Flask app
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def auth_app():
    """Flask app with authentication ENABLED (not bypassed)."""
    # Temporarily override env BEFORE importing the app
    saved = {
        k: os.environ.get(k)
        for k in (
            "AUTH_BYPASS_ENABLED",
            "VALID_API_KEYS",
            "RATE_LIMIT_ENABLED",
            "STARTUP_HEALTH_CHECK",
            "SCHEDULER_ENABLED",
            "ENV_VALIDATION_ENABLED",
            "TESTING",
            "APP_ENV",
            "SECRET_KEY",
            "FLASK_DEBUG",
            "API_KEY_HASH_SALT",
        )
    }

    os.environ["API_KEY_HASH_SALT"] = "test-salt-value-for-integration-tests-at-least-32-chars!!"

    test_key = _generate_strong_api_key()

    os.environ["AUTH_BYPASS_ENABLED"] = "false"
    os.environ["VALID_API_KEYS"] = test_key
    os.environ["RATE_LIMIT_ENABLED"] = "false"
    os.environ["STARTUP_HEALTH_CHECK"] = "false"
    os.environ["SCHEDULER_ENABLED"] = "false"
    os.environ["ENV_VALIDATION_ENABLED"] = "false"
    os.environ["TESTING"] = "true"
    os.environ["APP_ENV"] = "development"
    os.environ["SECRET_KEY"] = "test-secret-key-for-auth-integration"
    os.environ["FLASK_DEBUG"] = "true"

    # Invalidate cached keys so the new VALID_API_KEYS is picked up
    from app.api.middleware.auth import invalidate_api_key_cache

    invalidate_api_key_cache()

    from app.api.app import create_app

    application = create_app()
    application.config["TESTING"] = True

    yield application, test_key

    # Restore original env
    invalidate_api_key_cache()
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    invalidate_api_key_cache()


@pytest.fixture()
def auth_client(auth_app):
    """Test client with auth turned on."""
    application, _key = auth_app
    with application.test_client() as c:
        with application.app_context():
            yield c


@pytest.fixture()
def valid_api_key(auth_app):
    """The legitimate API key configured for auth_app."""
    return auth_app[1]


# ---------------------------------------------------------------------------
# Tests: missing / invalid key → 401
# ---------------------------------------------------------------------------


class TestAuthMissingKey:
    """Requests without an API key should be rejected."""

    def test_predict_without_key_returns_401(self, auth_client):
        """POST /api/v1/predict/ without X-API-Key header → 401."""
        resp = auth_client.post(
            "/api/v1/predict/",
            json={
                "latitude": 14.48,
                "longitude": 121.02,
            },
        )
        assert resp.status_code == 401
        data = resp.get_json()
        assert data.get("error") in ("API key required", "Authentication required")

    def test_ingest_without_key_returns_401(self, auth_client):
        """POST /api/v1/ingest/ingest without X-API-Key header → 401."""
        resp = auth_client.post("/api/v1/ingest/ingest")
        assert resp.status_code == 401


class TestAuthInvalidKey:
    """Requests with a wrong API key should be rejected."""

    def test_predict_with_invalid_key_returns_401(self, auth_client):
        """POST /api/v1/predict/ with wrong X-API-Key → 401."""
        resp = auth_client.post(
            "/api/v1/predict/",
            headers={"X-API-Key": _generate_strong_api_key()},  # random wrong key
            json={"latitude": 14.48, "longitude": 121.02},
        )
        assert resp.status_code == 401
        data = resp.get_json()
        assert data.get("error") in ("Invalid API key", "Authentication required")


# ---------------------------------------------------------------------------
# Tests: valid key → passes auth (endpoint may still 4xx/5xx for other reasons)
# ---------------------------------------------------------------------------


class TestAuthValidKey:
    """Requests with a legitimate API key pass the auth layer."""

    def test_health_does_not_require_key(self, auth_client):
        """GET /health should not require auth at all."""
        resp = auth_client.get("/health")
        # Health endpoint is not decorated with @require_api_key
        assert resp.status_code in (200, 503)

    def test_predict_with_valid_key_passes_auth(self, auth_client, valid_api_key):
        """POST /api/v1/predict/ with valid key should pass the auth layer.

        The endpoint itself may return a 400/422/500 because no model
        is loaded - but the status should NOT be 401.
        """
        resp = auth_client.post(
            "/api/v1/predict/",
            headers={"X-API-Key": valid_api_key},
            json={"latitude": 14.48, "longitude": 121.02},
        )
        # Anything except 401 means auth passed
        assert resp.status_code != 401


# ---------------------------------------------------------------------------
# Tests: IP lockout after repeated failures
# ---------------------------------------------------------------------------


class TestAuthLockout:
    """IP lockout after too many failed attempts."""

    def test_lockout_after_max_failed_attempts(self, auth_client):
        """After MAX_FAILED_ATTEMPTS consecutive bad keys the IP is locked out."""
        from app.api.middleware.auth import (
            MAX_FAILED_ATTEMPTS,
            _clear_failed_attempts,
        )

        # Reset tracking for 127.0.0.1 (test client remote_addr)
        _clear_failed_attempts("127.0.0.1")

        wrong_key = _generate_strong_api_key()
        for _ in range(MAX_FAILED_ATTEMPTS):
            auth_client.post(
                "/api/v1/predict/",
                headers={"X-API-Key": wrong_key},
                json={"latitude": 14.48, "longitude": 121.02},
            )

        # Next request should be locked out → 429
        resp = auth_client.post(
            "/api/v1/predict/",
            headers={"X-API-Key": wrong_key},
            json={"latitude": 14.48, "longitude": 121.02},
        )
        assert resp.status_code == 429
        data = resp.get_json()
        assert "Too many failed attempts" in data.get("error", "")

        # Cleanup
        _clear_failed_attempts("127.0.0.1")


# ---------------------------------------------------------------------------
# Tests: key expiration & revocation
# ---------------------------------------------------------------------------


class TestAuthKeyLifecycle:
    """Expiration and revocation checks during real request flow."""

    def test_revoked_key_is_rejected(self, auth_client, valid_api_key):
        """A revoked key should return 401 even though it is otherwise valid."""
        from app.api.middleware.auth import (
            _clear_failed_attempts,
            _revoked_api_keys,
            invalidate_api_key_cache,
            revoke_api_key,
        )

        _clear_failed_attempts("127.0.0.1")

        revoke_api_key(valid_api_key)

        resp = auth_client.post(
            "/api/v1/predict/",
            headers={"X-API-Key": valid_api_key},
            json={"latitude": 14.48, "longitude": 121.02},
        )
        assert resp.status_code == 401

        # Cleanup - un-revoke so other tests still work
        _revoked_api_keys.clear()
        _clear_failed_attempts("127.0.0.1")

    def test_expired_key_is_rejected(self, auth_client, valid_api_key):
        """An expired key should return 401."""
        import time

        from app.api.middleware.auth import (
            _api_key_expirations,
            _clear_failed_attempts,
            set_api_key_expiration,
        )

        _clear_failed_attempts("127.0.0.1")

        # Expire the key 10 seconds in the past
        set_api_key_expiration(valid_api_key, time.time() - 10)

        resp = auth_client.post(
            "/api/v1/predict/",
            headers={"X-API-Key": valid_api_key},
            json={"latitude": 14.48, "longitude": 121.02},
        )
        assert resp.status_code == 401

        # Cleanup
        _api_key_expirations.clear()
        _clear_failed_attempts("127.0.0.1")
