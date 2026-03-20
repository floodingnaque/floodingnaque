"""
Unit tests for users/auth routes.

Tests user authentication, registration, login, logout, and password reset.
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestUserRegistration:
    """Tests for user registration endpoint."""

    @pytest.fixture
    def valid_registration_data(self):
        """Create valid registration data."""
        return {
            "email": "test@example.com",
            "password": "SecurePassword123!@#",
            "full_name": "Test User",
            "phone_number": "+639123456789",
        }

    def test_register_success(self, client, valid_registration_data):
        """Test successful user registration."""
        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.users.is_jwt_available", return_value=True):
                with patch("app.api.routes.users.is_bcrypt_available", return_value=True):
                    with patch("app.api.routes.users.is_secure_password", return_value=(True, [])):
                        with patch("app.api.routes.users.hash_password", return_value="hashed"):
                            with patch("app.api.routes.users.get_db_session") as mock_session:
                                session = MagicMock()
                                mock_session.return_value.__enter__ = Mock(return_value=session)
                                mock_session.return_value.__exit__ = Mock(return_value=False)

                                mock_query = MagicMock()
                                mock_query.filter.return_value = mock_query
                                mock_query.first.return_value = None  # No existing user
                                session.query.return_value = mock_query

                                mock_user = MagicMock()
                                mock_user.id = 1
                                mock_user.email = valid_registration_data["email"]
                                mock_user.role = "user"
                                mock_user.to_dict.return_value = {"id": 1, "email": valid_registration_data["email"]}

                                with patch("app.api.routes.users.User", return_value=mock_user):
                                    with patch(
                                        "app.api.routes.users.create_access_token", return_value="mock_access_token"
                                    ):
                                        with patch(
                                            "app.api.routes.users.create_refresh_token",
                                            return_value=("mock_refresh_token", "mock_hash"),
                                        ):
                                            response = client.post(
                                                "/api/v1/auth/register",
                                                data=json.dumps(valid_registration_data),
                                                content_type="application/json",
                                            )

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert "user" in data

    def test_register_missing_email(self, client):
        """Test registration with missing email."""
        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.users.is_jwt_available", return_value=True):
                with patch("app.api.routes.users.is_bcrypt_available", return_value=True):
                    response = client.post(
                        "/api/v1/auth/register",
                        data=json.dumps({"password": "SecurePassword123!@#"}),
                        content_type="application/json",
                    )

        assert response.status_code == 400

    def test_register_invalid_email(self, client):
        """Test registration with invalid email format."""
        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.users.is_jwt_available", return_value=True):
                with patch("app.api.routes.users.is_bcrypt_available", return_value=True):
                    response = client.post(
                        "/api/v1/auth/register",
                        data=json.dumps({"email": "invalid-email", "password": "SecurePassword123!@#"}),
                        content_type="application/json",
                    )

        assert response.status_code == 400

    def test_register_missing_password(self, client):
        """Test registration with missing password."""
        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.users.is_jwt_available", return_value=True):
                with patch("app.api.routes.users.is_bcrypt_available", return_value=True):
                    response = client.post(
                        "/api/v1/auth/register",
                        data=json.dumps({"email": "test@example.com"}),
                        content_type="application/json",
                    )

        assert response.status_code == 400

    def test_register_weak_password(self, client):
        """Test registration with weak password."""
        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.users.is_jwt_available", return_value=True):
                with patch("app.api.routes.users.is_bcrypt_available", return_value=True):
                    with patch("app.api.routes.users.is_secure_password", return_value=(False, ["Password too weak"])):
                        response = client.post(
                            "/api/v1/auth/register",
                            data=json.dumps({"email": "test@example.com", "password": "weak"}),
                            content_type="application/json",
                        )

        assert response.status_code == 400

    def test_register_email_exists(self, client, valid_registration_data):
        """Test registration with existing email."""
        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.users.is_jwt_available", return_value=True):
                with patch("app.api.routes.users.is_bcrypt_available", return_value=True):
                    with patch("app.api.routes.users.is_secure_password", return_value=(True, [])):
                        with patch("app.api.routes.users.get_db_session") as mock_session:
                            session = MagicMock()
                            mock_session.return_value.__enter__ = Mock(return_value=session)
                            mock_session.return_value.__exit__ = Mock(return_value=False)

                            mock_query = MagicMock()
                            mock_query.filter.return_value = mock_query
                            mock_query.first.return_value = MagicMock()  # Existing user
                            session.query.return_value = mock_query

                            response = client.post(
                                "/api/v1/auth/register",
                                data=json.dumps(valid_registration_data),
                                content_type="application/json",
                            )

        assert response.status_code == 409

    def test_register_service_unavailable(self, client):
        """Test registration when auth service unavailable."""
        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.users.is_jwt_available", return_value=False):
                response = client.post(
                    "/api/v1/auth/register",
                    data=json.dumps({"email": "test@example.com", "password": "pwd"}),
                    content_type="application/json",
                )

        assert response.status_code == 500


class TestUserLogin:
    """Tests for user login endpoint."""

    @pytest.fixture
    def valid_login_data(self):
        """Create valid login data."""
        return {"email": "test@example.com", "password": "SecurePassword123!@#"}

    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = MagicMock()
        user.id = 1
        user.email = "test@example.com"
        user.password_hash = "hashed_password"
        user.role = "user"
        user.is_active = True
        user.failed_login_attempts = 0
        user.is_locked = Mock(return_value=False)
        user.to_dict.return_value = {"id": 1, "email": "test@example.com"}
        return user

    def test_login_success(self, client, valid_login_data, mock_user):
        """Test successful login."""
        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.users.is_jwt_available", return_value=True):
                with patch("app.api.routes.users.is_bcrypt_available", return_value=True):
                    with patch("app.api.routes.users.verify_password", return_value=True):
                        with patch("app.api.routes.users.create_access_token", return_value="access_token"):
                            with patch(
                                "app.api.routes.users.create_refresh_token", return_value=("refresh_token", "hash")
                            ):
                                with patch("app.api.routes.users.get_db_session") as mock_session:
                                    session = MagicMock()
                                    mock_session.return_value.__enter__ = Mock(return_value=session)
                                    mock_session.return_value.__exit__ = Mock(return_value=False)

                                    mock_query = MagicMock()
                                    mock_query.filter.return_value = mock_query
                                    mock_query.first.return_value = mock_user
                                    session.query.return_value = mock_query

                                    response = client.post(
                                        "/api/v1/auth/login",
                                        data=json.dumps(valid_login_data),
                                        content_type="application/json",
                                    )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_missing_email(self, client):
        """Test login with missing email."""
        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.users.is_jwt_available", return_value=True):
                with patch("app.api.routes.users.is_bcrypt_available", return_value=True):
                    response = client.post(
                        "/api/v1/auth/login",
                        data=json.dumps({"password": "password123"}),
                        content_type="application/json",
                    )

        assert response.status_code == 400

    def test_login_user_not_found(self, client, valid_login_data):
        """Test login with non-existent user."""
        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.users.is_jwt_available", return_value=True):
                with patch("app.api.routes.users.is_bcrypt_available", return_value=True):
                    with patch("app.api.routes.users.get_db_session") as mock_session:
                        session = MagicMock()
                        mock_session.return_value.__enter__ = Mock(return_value=session)
                        mock_session.return_value.__exit__ = Mock(return_value=False)

                        mock_query = MagicMock()
                        mock_query.filter.return_value = mock_query
                        mock_query.first.return_value = None
                        session.query.return_value = mock_query

                        response = client.post(
                            "/api/v1/auth/login", data=json.dumps(valid_login_data), content_type="application/json"
                        )

        assert response.status_code == 401

    def test_login_wrong_password(self, client, valid_login_data, mock_user):
        """Test login with wrong password."""
        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.users.is_jwt_available", return_value=True):
                with patch("app.api.routes.users.is_bcrypt_available", return_value=True):
                    with patch("app.api.routes.users.verify_password", return_value=False):
                        with patch("app.api.routes.users.get_db_session") as mock_session:
                            session = MagicMock()
                            mock_session.return_value.__enter__ = Mock(return_value=session)
                            mock_session.return_value.__exit__ = Mock(return_value=False)

                            mock_query = MagicMock()
                            mock_query.filter.return_value = mock_query
                            mock_query.first.return_value = mock_user
                            session.query.return_value = mock_query

                            response = client.post(
                                "/api/v1/auth/login", data=json.dumps(valid_login_data), content_type="application/json"
                            )

        assert response.status_code == 401

    def test_login_account_locked(self, client, valid_login_data, mock_user):
        """Test login with locked account."""
        mock_user.is_locked = Mock(return_value=True)
        mock_user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)

        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.users.is_jwt_available", return_value=True):
                with patch("app.api.routes.users.is_bcrypt_available", return_value=True):
                    with patch("app.api.routes.users.get_db_session") as mock_session:
                        session = MagicMock()
                        mock_session.return_value.__enter__ = Mock(return_value=session)
                        mock_session.return_value.__exit__ = Mock(return_value=False)

                        mock_query = MagicMock()
                        mock_query.filter.return_value = mock_query
                        mock_query.first.return_value = mock_user
                        session.query.return_value = mock_query

                        response = client.post(
                            "/api/v1/auth/login", data=json.dumps(valid_login_data), content_type="application/json"
                        )

        assert response.status_code == 423

    def test_login_account_disabled(self, client, valid_login_data, mock_user):
        """Test login with disabled account."""
        mock_user.is_active = False

        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.users.is_jwt_available", return_value=True):
                with patch("app.api.routes.users.is_bcrypt_available", return_value=True):
                    with patch("app.api.routes.users.get_db_session") as mock_session:
                        session = MagicMock()
                        mock_session.return_value.__enter__ = Mock(return_value=session)
                        mock_session.return_value.__exit__ = Mock(return_value=False)

                        mock_query = MagicMock()
                        mock_query.filter.return_value = mock_query
                        mock_query.first.return_value = mock_user
                        session.query.return_value = mock_query

                        response = client.post(
                            "/api/v1/auth/login", data=json.dumps(valid_login_data), content_type="application/json"
                        )

        assert response.status_code == 403


class TestTokenRefresh:
    """Tests for token refresh endpoint."""

    def test_refresh_success(self, client):
        """Test successful token refresh."""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.role = "user"
        mock_user.refresh_token_hash = "token_hash"
        mock_user.refresh_token_expires = datetime.now(timezone.utc) + timedelta(days=7)

        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.users.decode_token", return_value=({"sub": "1", "type": "refresh"}, None)):
                with patch("app.api.routes.users.create_access_token", return_value="new_access_token"):
                    with patch("app.api.routes.users.get_db_session") as mock_session:
                        session = MagicMock()
                        mock_session.return_value.__enter__ = Mock(return_value=session)
                        mock_session.return_value.__exit__ = Mock(return_value=False)

                        mock_query = MagicMock()
                        mock_query.filter.return_value = mock_query
                        mock_query.first.return_value = mock_user
                        session.query.return_value = mock_query

                        with patch("hashlib.sha256") as mock_hash:
                            mock_hash.return_value.hexdigest.return_value = "token_hash"

                            response = client.post(
                                "/api/v1/auth/refresh",
                                data=json.dumps({"refresh_token": "valid_token"}),
                                content_type="application/json",
                            )

        assert response.status_code == 200
        data = response.get_json()
        assert "access_token" in data

    def test_refresh_missing_token(self, client):
        """Test refresh with missing token."""
        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            response = client.post("/api/v1/auth/refresh", data=json.dumps({}), content_type="application/json")

        assert response.status_code == 400

    def test_refresh_invalid_token(self, client):
        """Test refresh with invalid token."""
        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.users.decode_token", return_value=(None, "Invalid token")):
                response = client.post(
                    "/api/v1/auth/refresh",
                    data=json.dumps({"refresh_token": "invalid_token"}),
                    content_type="application/json",
                )

        assert response.status_code == 401


class TestLogout:
    """Tests for logout endpoint."""

    def test_logout_success(self, client):
        """Test successful logout."""
        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            with patch(
                "app.api.routes.users.decode_token", return_value=({"sub": "1", "email": "test@example.com"}, None)
            ):
                with patch("app.api.routes.users.get_db_session") as mock_session:
                    session = MagicMock()
                    mock_session.return_value.__enter__ = Mock(return_value=session)
                    mock_session.return_value.__exit__ = Mock(return_value=False)

                    mock_user = MagicMock()
                    mock_query = MagicMock()
                    mock_query.filter.return_value = mock_query
                    mock_query.first.return_value = mock_user
                    session.query.return_value = mock_query

                    response = client.post("/api/v1/auth/logout", headers={"Authorization": "Bearer valid_token"})

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_logout_without_token(self, client):
        """Test logout without authorization header."""
        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            response = client.post("/api/v1/auth/logout")

        assert response.status_code == 401

    def test_logout_with_expired_token(self, client):
        """Test logout with expired token still succeeds."""
        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.users.decode_token", return_value=(None, "Token expired")):
                response = client.post("/api/v1/auth/logout", headers={"Authorization": "Bearer expired_token"})

        assert response.status_code == 200


class TestPasswordReset:
    """Tests for password reset endpoints."""

    def test_request_password_reset(self, client):
        """Test password reset request."""
        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.users.get_db_session") as mock_session:
                session = MagicMock()
                mock_session.return_value.__enter__ = Mock(return_value=session)
                mock_session.return_value.__exit__ = Mock(return_value=False)

                mock_user = MagicMock()
                mock_query = MagicMock()
                mock_query.filter.return_value = mock_query
                mock_query.first.return_value = mock_user
                session.query.return_value = mock_query

                with patch(
                    "app.api.routes.users.create_password_reset_token",
                    return_value=("token", datetime.now(timezone.utc)),
                ):
                    response = client.post(
                        "/api/v1/auth/password-reset/request",
                        data=json.dumps({"email": "test@example.com"}),
                        content_type="application/json",
                    )

        assert response.status_code == 200
        # Always returns success to prevent email enumeration
        data = response.get_json()
        assert data["success"] is True

    def test_request_password_reset_invalid_email(self, client):
        """Test password reset request with invalid email still returns success."""
        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            response = client.post(
                "/api/v1/auth/password-reset/request",
                data=json.dumps({"email": "invalid"}),
                content_type="application/json",
            )

        # Always returns success to prevent enumeration
        assert response.status_code == 200

    def test_confirm_password_reset_success(self, client):
        """Test successful password reset confirmation."""
        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.users.is_secure_password", return_value=(True, [])):
                with patch("app.api.routes.users.verify_password_reset_token", return_value=True):
                    with patch("app.api.routes.users.hash_password", return_value="new_hash"):
                        with patch("app.api.routes.users.get_db_session") as mock_session:
                            session = MagicMock()
                            mock_session.return_value.__enter__ = Mock(return_value=session)
                            mock_session.return_value.__exit__ = Mock(return_value=False)

                            mock_user = MagicMock()
                            mock_user.password_reset_token = "token"
                            mock_user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)

                            mock_query = MagicMock()
                            mock_query.filter.return_value = mock_query
                            mock_query.first.return_value = mock_user
                            session.query.return_value = mock_query

                            response = client.post(
                                "/api/v1/auth/password-reset/confirm",
                                data=json.dumps(
                                    {
                                        "email": "test@example.com",
                                        "token": "reset_token",
                                        "new_password": "NewSecurePassword123!@#",
                                    }
                                ),
                                content_type="application/json",
                            )

        assert response.status_code == 200

    def test_confirm_password_reset_missing_fields(self, client):
        """Test password reset confirmation with missing fields."""
        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            response = client.post(
                "/api/v1/auth/password-reset/confirm",
                data=json.dumps({"email": "test@example.com"}),
                content_type="application/json",
            )

        assert response.status_code == 400

    def test_confirm_password_reset_invalid_token(self, client):
        """Test password reset confirmation with invalid token."""
        with patch("app.api.routes.users.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.users.is_secure_password", return_value=(True, [])):
                with patch("app.api.routes.users.verify_password_reset_token", return_value=False):
                    with patch("app.api.routes.users.get_db_session") as mock_session:
                        session = MagicMock()
                        mock_session.return_value.__enter__ = Mock(return_value=session)
                        mock_session.return_value.__exit__ = Mock(return_value=False)

                        mock_user = MagicMock()
                        mock_query = MagicMock()
                        mock_query.filter.return_value = mock_query
                        mock_query.first.return_value = mock_user
                        session.query.return_value = mock_query

                        response = client.post(
                            "/api/v1/auth/password-reset/confirm",
                            data=json.dumps(
                                {
                                    "email": "test@example.com",
                                    "token": "invalid_token",
                                    "new_password": "NewSecurePassword123!@#",
                                }
                            ),
                            content_type="application/json",
                        )

        assert response.status_code == 400


class TestGetCurrentUser:
    """Tests for get current user endpoint."""

    def test_get_current_user_success(self, client):
        """Test successful retrieval of current user."""
        mock_user = MagicMock()
        mock_user.to_dict.return_value = {"id": 1, "email": "test@example.com"}

        with patch("app.api.routes.users.decode_token", return_value=({"sub": "1"}, None)):
            with patch("app.api.routes.users.get_db_session") as mock_session:
                session = MagicMock()
                mock_session.return_value.__enter__ = Mock(return_value=session)
                mock_session.return_value.__exit__ = Mock(return_value=False)

                mock_query = MagicMock()
                mock_query.filter.return_value = mock_query
                mock_query.first.return_value = mock_user
                session.query.return_value = mock_query

                response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer valid_token"})

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "user" in data

    def test_get_current_user_unauthorized(self, client):
        """Test get current user without authorization."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client):
        """Test get current user with invalid token."""
        with patch("app.api.routes.users.decode_token", return_value=(None, "Invalid token")):
            response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token"})

        assert response.status_code == 401

    def test_get_current_user_not_found(self, client):
        """Test get current user when user doesn't exist."""
        with patch("app.api.routes.users.decode_token", return_value=({"sub": "1"}, None)):
            with patch("app.api.routes.users.get_db_session") as mock_session:
                session = MagicMock()
                mock_session.return_value.__enter__ = Mock(return_value=session)
                mock_session.return_value.__exit__ = Mock(return_value=False)

                mock_query = MagicMock()
                mock_query.filter.return_value = mock_query
                mock_query.first.return_value = None
                session.query.return_value = mock_query

                response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer valid_token"})

        assert response.status_code == 404


class TestEmailValidation:
    """Tests for email validation helper."""

    def test_valid_emails(self):
        """Test valid email formats."""
        from app.api.routes.users import validate_email

        valid_emails = [
            "test@example.com",
            "user.name@example.com",
            "user+tag@example.com",
            "user@subdomain.example.com",
        ]

        for email in valid_emails:
            assert validate_email(email) is True

    def test_invalid_emails(self):
        """Test invalid email formats."""
        from app.api.routes.users import validate_email

        invalid_emails = ["invalid", "invalid@", "@example.com", "user@.com", "user@com"]

        for email in invalid_emails:
            assert validate_email(email) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
