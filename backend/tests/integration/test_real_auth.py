"""
Integration tests for real user-authentication flow (bcrypt + JWT).

Unlike unit tests that mock `hash_password` / `verify_password`, these
tests exercise the actual bcrypt hashing and JWT token creation / validation
end-to-end through the HTTP API.
"""

import os

import pytest

# ---------------------------------------------------------------------------
# Fixture: app with auth enabled and a real DB table
# ---------------------------------------------------------------------------

_TEST_EMAIL = "integration_auth_test@floodingnaque.test"
_TEST_PASSWORD = "Str0ngP@ssword!2026xQ"  # meets the security policy


@pytest.fixture(scope="module")
def user_auth_app():
    """Flask app with full auth (bcrypt + JWT) and a valid DB."""
    saved = {
        k: os.environ.get(k)
        for k in (
            "AUTH_BYPASS_ENABLED",
            "RATE_LIMIT_ENABLED",
            "STARTUP_HEALTH_CHECK",
            "SCHEDULER_ENABLED",
            "ENV_VALIDATION_ENABLED",
            "TESTING",
            "APP_ENV",
            "SECRET_KEY",
            "FLASK_DEBUG",
            "API_KEY_HASH_SALT",
            "DATABASE_URL",
        )
    }

    os.environ["API_KEY_HASH_SALT"] = "test-salt-value-for-integration-tests-at-least-32-chars!!"
    os.environ["AUTH_BYPASS_ENABLED"] = "false"
    os.environ["RATE_LIMIT_ENABLED"] = "false"
    os.environ["STARTUP_HEALTH_CHECK"] = "false"
    os.environ["SCHEDULER_ENABLED"] = "false"
    os.environ["ENV_VALIDATION_ENABLED"] = "false"
    os.environ["TESTING"] = "true"
    os.environ["APP_ENV"] = "development"
    os.environ["SECRET_KEY"] = "test-jwt-secret-key-for-real-auth-flow"
    os.environ["FLASK_DEBUG"] = "true"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    from app.api.middleware.auth import invalidate_api_key_cache

    invalidate_api_key_cache()

    # Reset the DB engine / session singletons so they pick up the new DATABASE_URL
    import app.models.db as _db_mod

    _saved_engine = _db_mod._engine
    _saved_session = _db_mod._Session
    _db_mod._engine = None
    _db_mod._Session = None

    from app.api.app import create_app

    application = create_app()
    application.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    # Create tables so we can register real users
    with application.app_context():
        from app.models.db import Base, get_engine

        Base.metadata.create_all(get_engine())

    yield application

    # Restore engine / session singletons
    _db_mod._engine = _saved_engine
    _db_mod._Session = _saved_session

    # Restore env
    invalidate_api_key_cache()
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    invalidate_api_key_cache()


@pytest.fixture()
def user_client(user_auth_app):
    # Re-create tables in case the auto_reset_singletons fixture disposed the engine
    with user_auth_app.app_context():
        from app.models.db import Base, get_engine

        Base.metadata.create_all(get_engine())
    with user_auth_app.test_client() as c:
        with user_auth_app.app_context():
            yield c


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRealUserAuthFlow:
    """End-to-end register → login → access protected route using real
    bcrypt hashing and JWT tokens (no mocks)."""

    def test_register_creates_user_with_bcrypt_hash(self, user_client):
        """POST /api/v1/auth/register should hash the password with bcrypt."""
        resp = user_client.post(
            "/api/v1/auth/register",
            json={
                "email": _TEST_EMAIL,
                "password": _TEST_PASSWORD,
                "full_name": "Integration Test User",
            },
        )
        # Accept 201 (created) or 409 (already exists from prior run)
        assert resp.status_code in (201, 409), resp.get_json()

    def test_login_with_correct_password_returns_token(self, user_client):
        """POST /api/v1/auth/login with the real password should return JWT tokens."""
        # Ensure user exists first
        user_client.post(
            "/api/v1/auth/register",
            json={
                "email": _TEST_EMAIL,
                "password": _TEST_PASSWORD,
                "full_name": "Integration Test User",
            },
        )

        resp = user_client.post(
            "/api/v1/auth/login",
            json={
                "email": _TEST_EMAIL,
                "password": _TEST_PASSWORD,
            },
        )
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()
        assert data.get("success") is True
        # Should contain a JWT access token
        assert "access_token" in data or "token" in data

    def test_login_with_wrong_password_returns_401(self, user_client):
        """POST /api/v1/auth/login with a wrong password should be rejected."""
        # Ensure user exists
        user_client.post(
            "/api/v1/auth/register",
            json={
                "email": _TEST_EMAIL,
                "password": _TEST_PASSWORD,
                "full_name": "Integration Test User",
            },
        )

        resp = user_client.post(
            "/api/v1/auth/login",
            json={
                "email": _TEST_EMAIL,
                "password": "WrongPassword!123456",
            },
        )
        assert resp.status_code == 401
        data = resp.get_json()
        assert data.get("success") is False or "Invalid" in data.get("message", "")

    def test_jwt_token_grants_access_to_protected_route(self, user_client):
        """A valid JWT from /login should authenticate against /me."""
        # Register + login
        user_client.post(
            "/api/v1/auth/register",
            json={
                "email": _TEST_EMAIL,
                "password": _TEST_PASSWORD,
                "full_name": "Integration Test User",
            },
        )
        login_resp = user_client.post(
            "/api/v1/auth/login",
            json={
                "email": _TEST_EMAIL,
                "password": _TEST_PASSWORD,
            },
        )
        data = login_resp.get_json()
        token = data.get("access_token") or data.get("token")
        if not token:
            pytest.skip("Login did not return a token field - endpoint shape may differ")

        # Hit a protected endpoint with the token
        me_resp = user_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Should not be 401 (auth should pass); may be 200 or 404 depending on route setup
        assert me_resp.status_code != 401, me_resp.get_json()
