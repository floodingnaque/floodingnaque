"""
User Authentication Routes.

Provides endpoints for user registration, login, logout, token refresh,
and password reset functionality.
"""

import logging
import os
import re
from datetime import datetime, timedelta, timezone

from app.api.middleware.rate_limit import limiter
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    is_bcrypt_available,
    is_jwt_available,
    is_secure_password,
    verify_password,
    verify_password_reset_token,
)
from app.models.db import User, get_db_session
from app.utils.api_constants import (
    HTTP_BAD_REQUEST,
    HTTP_CONFLICT,
    HTTP_CREATED,
    HTTP_FORBIDDEN,
    HTTP_INTERNAL_ERROR,
    HTTP_NOT_FOUND,
    HTTP_OK,
    HTTP_UNAUTHORIZED,
)
from app.utils.api_responses import api_error
from flask import Blueprint, g, jsonify, request

logger = logging.getLogger(__name__)

users_bp = Blueprint("users", __name__)

# Configuration
MAX_FAILED_LOGIN_ATTEMPTS = int(os.getenv("MAX_FAILED_LOGIN_ATTEMPTS", "5"))
ACCOUNT_LOCKOUT_MINUTES = int(os.getenv("ACCOUNT_LOCKOUT_MINUTES", "15"))
# Development-only auth bypass flag.
# When AUTH_BYPASS_ENABLED=true, the /login endpoint will skip password
# verification and log in any existing active user by email. This is
# intended purely for local development and should NEVER be enabled
# in production.
AUTH_BYPASS_ENABLED = os.getenv("AUTH_BYPASS_ENABLED", "false").lower() == "true"
if AUTH_BYPASS_ENABLED and os.getenv("APP_ENV", "").lower() == "production":
    raise RuntimeError("AUTH_BYPASS_ENABLED must not be set in production")


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def get_client_ip() -> str:
    """Get client IP address from request."""
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    return request.remote_addr or "unknown"


@users_bp.route("/register", methods=["POST"])
@limiter.limit("5 per hour")
def register():
    """
    Register a new user account.

    Request Body:
    {
        "email": "user@example.com",
        "password": "SecurePassword123!",
        "full_name": "John Doe",
        "phone_number": "+639123456789"
    }

    Returns:
        201: User registered successfully
        400: Invalid request data
        409: Email already exists
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
          properties:
            email:
              type: string
              format: email
            password:
              type: string
              minLength: 12
            full_name:
              type: string
            phone_number:
              type: string
    responses:
      201:
        description: User registered successfully
      400:
        description: Invalid request data
      409:
        description: Email already exists
    """
    request_id = getattr(g, "request_id", "unknown")

    # Check dependencies
    if not is_jwt_available() or not is_bcrypt_available():
        return api_error(
            "ServiceUnavailable", "Authentication service not properly configured", HTTP_INTERNAL_ERROR, request_id
        )

    try:
        data = request.get_json()
        if not data:
            return api_error("InvalidRequest", "No data provided", HTTP_BAD_REQUEST, request_id)

        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        # Accept both 'full_name' and 'name' from the frontend
        full_name = (data.get("full_name") or data.get("name") or "").strip()
        phone_number = data.get("phone_number", "").strip()

        # Validate email
        if not email or not validate_email(email):
            return api_error("ValidationError", "Invalid email format", HTTP_BAD_REQUEST, request_id)

        # Validate password
        if not password:
            return api_error("ValidationError", "Password is required", HTTP_BAD_REQUEST, request_id)

        is_valid, password_errors = is_secure_password(password)
        if not is_valid:
            return api_error("ValidationError", "; ".join(password_errors), HTTP_BAD_REQUEST, request_id)

        with get_db_session() as session:
            # Check if email already exists
            existing_user = session.query(User).filter(User.email == email, User.is_deleted.is_(False)).first()

            if existing_user:
                return api_error("EmailExists", "An account with this email already exists", HTTP_CONFLICT, request_id)

            # Create new user
            user = User(
                email=email,
                password_hash=hash_password(password),
                full_name=full_name or None,
                phone_number=phone_number or None,
                role="user",
                is_active=True,
                is_verified=False,  # Require email verification in production
            )

            session.add(user)
            session.flush()  # Get the user ID

            user_data = user.to_dict()

        logger.info(f"User registered: {email} [{request_id}]")

        return (
            jsonify(
                {
                    "success": True,
                    "message": "User registered successfully",
                    "user": user_data,
                    "request_id": request_id,
                }
            ),
            HTTP_CREATED,
        )

    except Exception as e:
        logger.error(f"Registration error [{request_id}]: {str(e)}", exc_info=True)
        return api_error("RegistrationFailed", "Failed to register user", HTTP_INTERNAL_ERROR, request_id)


@users_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def login():
    """
    Authenticate user and return tokens.

    Request Body:
    {
        "email": "user@example.com",
        "password": "SecurePassword123!"
    }

    Returns:
        200: Login successful with tokens
        401: Invalid credentials
        423: Account locked
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
          properties:
            email:
              type: string
            password:
              type: string
    responses:
      200:
        description: Login successful
      401:
        description: Invalid credentials
      423:
        description: Account locked
    """
    request_id = getattr(g, "request_id", "unknown")

    if not is_jwt_available() or not is_bcrypt_available():
        return api_error(
            "ServiceUnavailable", "Authentication service not properly configured", HTTP_INTERNAL_ERROR, request_id
        )

    try:
        data = request.get_json()
        if not data:
            return api_error("InvalidRequest", "No data provided", HTTP_BAD_REQUEST, request_id)

        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        if not email or not password:
            return api_error("ValidationError", "Email and password are required", HTTP_BAD_REQUEST, request_id)

        with get_db_session() as session:
            user = session.query(User).filter(User.email == email, User.is_deleted.is_(False)).first()

            # User not found - use generic message to prevent enumeration
            if not user:
                logger.warning(f"Login attempt for non-existent user: {email} [{request_id}]")
                return api_error("InvalidCredentials", "Invalid email or password", HTTP_UNAUTHORIZED, request_id)

            # Optional development bypass: skip password verification entirely.
            if AUTH_BYPASS_ENABLED:
                logger.warning(
                    "AUTH_BYPASS_ENABLED is TRUE - bypassing password verification for user '%s' [%s]",
                    email,
                    request_id,
                )
            else:
                # Check if account is locked
                if user.is_locked():
                    remaining = (user.locked_until - datetime.now(timezone.utc)).total_seconds()
                    logger.warning(f"Login attempt for locked account: {email} [{request_id}]")
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "AccountLocked",
                                "message": f"Account is locked. Try again in {int(remaining / 60)} minutes",
                                "retry_after": int(remaining),
                                "request_id": request_id,
                            }
                        ),
                        423,
                    )

                # Check if account is active
                if not user.is_active:
                    return api_error("AccountDisabled", "Account is disabled", HTTP_FORBIDDEN, request_id)

                # Verify password
                if not verify_password(password, user.password_hash):
                    # Increment failed attempts
                    user.failed_login_attempts += 1

                    if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
                        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=ACCOUNT_LOCKOUT_MINUTES)
                        logger.warning(f"Account locked due to failed attempts: {email} [{request_id}]")

                    logger.warning(
                        f"Failed login attempt for {email} (attempt {user.failed_login_attempts}) [{request_id}]"
                    )
                    return api_error("InvalidCredentials", "Invalid email or password", HTTP_UNAUTHORIZED, request_id)

            # Successful login - reset failed attempts and update login info
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login_at = datetime.now(timezone.utc)
            user.last_login_ip = get_client_ip()

            # Generate tokens
            access_token = create_access_token(user.id, user.email, user.role)
            refresh_token, refresh_hash = create_refresh_token(user.id)

            # Store refresh token hash
            user.refresh_token_hash = refresh_hash
            user.refresh_token_expires = datetime.now(timezone.utc) + timedelta(days=7)

            user_data = user.to_dict()

        logger.info(f"User logged in: {email} [{request_id}]")

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Login successful",
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "Bearer",
                    "expires_in": 15 * 60,  # 15 minutes in seconds
                    "user": user_data,
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Login error [{request_id}]: {str(e)}", exc_info=True)
        return api_error("LoginFailed", "Failed to process login", HTTP_INTERNAL_ERROR, request_id)


@users_bp.route("/refresh", methods=["POST"])
@limiter.limit("30 per hour")
def refresh_token():
    """
    Refresh access token using refresh token.

    Request Body:
    {
        "refresh_token": "eyJ..."
    }

    Returns:
        200: New access token
        401: Invalid or expired refresh token
    ---
    tags:
      - Authentication
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        data = request.get_json()
        if not data or "refresh_token" not in data:
            return api_error("InvalidRequest", "Refresh token is required", HTTP_BAD_REQUEST, request_id)

        token = data.get("refresh_token")

        # Decode and validate refresh token
        payload, error = decode_token(token)
        if error:
            return api_error("InvalidToken", error, HTTP_UNAUTHORIZED, request_id)

        if payload.get("type") != "refresh":
            return api_error("InvalidToken", "Not a refresh token", HTTP_UNAUTHORIZED, request_id)

        user_id = int(payload.get("sub"))

        with get_db_session() as session:
            user = (
                session.query(User)
                .filter(User.id == user_id, User.is_deleted.is_(False), User.is_active.is_(True))
                .first()
            )

            if not user:
                return api_error("UserNotFound", "User not found", HTTP_UNAUTHORIZED, request_id)

            # Verify refresh token hash matches stored hash
            import hashlib

            token_hash = hashlib.sha256(token.encode()).hexdigest()
            if user.refresh_token_hash != token_hash:
                return api_error("InvalidToken", "Token has been revoked", HTTP_UNAUTHORIZED, request_id)

            # Check if refresh token has expired in database
            if user.refresh_token_expires and datetime.now(timezone.utc) > user.refresh_token_expires:
                return api_error("TokenExpired", "Refresh token has expired", HTTP_UNAUTHORIZED, request_id)

            # Generate new access token
            access_token = create_access_token(user.id, user.email, user.role)

        return (
            jsonify(
                {
                    "success": True,
                    "access_token": access_token,
                    "token_type": "Bearer",
                    "expires_in": 15 * 60,
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Token refresh error [{request_id}]: {str(e)}", exc_info=True)
        return api_error("RefreshFailed", "Failed to refresh token", HTTP_INTERNAL_ERROR, request_id)


@users_bp.route("/logout", methods=["POST"])
@limiter.limit("30 per hour")
def logout():
    """
    Logout user and invalidate refresh token.

    Headers:
        Authorization: Bearer <access_token>

    Returns:
        200: Logged out successfully
    ---
    tags:
      - Authentication
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return api_error("InvalidRequest", "Authorization header required", HTTP_UNAUTHORIZED, request_id)

        token = auth_header.split(" ", 1)[1]
        payload, error = decode_token(token)

        if error:
            # Token might be expired but we still want to logout
            logger.debug(f"Logout with invalid/expired token [{request_id}]: {error}")
            return jsonify({"success": True, "message": "Logged out successfully", "request_id": request_id}), HTTP_OK

        user_id = int(payload.get("sub"))

        with get_db_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                # Invalidate refresh token
                user.refresh_token_hash = None
                user.refresh_token_expires = None

        logger.info(f"User logged out: {payload.get('email')} [{request_id}]")

        return jsonify({"success": True, "message": "Logged out successfully", "request_id": request_id}), HTTP_OK

    except Exception as e:
        logger.error(f"Logout error [{request_id}]: {str(e)}", exc_info=True)
        return jsonify({"success": True, "message": "Logged out successfully", "request_id": request_id}), HTTP_OK


@users_bp.route("/password-reset/request", methods=["POST"])
@limiter.limit("3 per hour")
def request_password_reset():
    """
    Request a password reset token.

    Request Body:
    {
        "email": "user@example.com"
    }

    Returns:
        200: Reset token sent (always returns success to prevent enumeration)
    ---
    tags:
      - Authentication
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        data = request.get_json()
        email = data.get("email", "").strip().lower() if data else ""

        # Always return success to prevent email enumeration
        success_response = jsonify(
            {
                "success": True,
                "message": "If an account exists with this email, a password reset link has been sent",
                "request_id": request_id,
            }
        )

        if not email or not validate_email(email):
            return success_response, HTTP_OK

        with get_db_session() as session:
            user = (
                session.query(User)
                .filter(User.email == email, User.is_deleted.is_(False), User.is_active.is_(True))
                .first()
            )

            if user:
                # Generate reset token
                token, expires = create_password_reset_token()
                user.password_reset_token = token
                user.password_reset_expires = expires

                # In production, send email with reset link
                logger.info(f"Password reset requested [{request_id}]")
                # Note: Never log reset tokens - send via secure email channel only

                # TODO: Integrate email service to send reset link
                # send_password_reset_email(email, token)

        return success_response, HTTP_OK

    except Exception as e:
        logger.error(f"Password reset request error [{request_id}]: {str(e)}", exc_info=True)
        return (
            jsonify(
                {
                    "success": True,
                    "message": "If an account exists with this email, a password reset link has been sent",
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )


@users_bp.route("/password-reset/confirm", methods=["POST"])
@limiter.limit("5 per hour")
def confirm_password_reset():
    """
    Confirm password reset with token.

    Request Body:
    {
        "email": "user@example.com",
        "token": "reset_token_here",
        "new_password": "NewSecurePassword123!"
    }

    Returns:
        200: Password reset successful
        400: Invalid token or password
    ---
    tags:
      - Authentication
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        data = request.get_json()
        if not data:
            return api_error("InvalidRequest", "No data provided", HTTP_BAD_REQUEST, request_id)

        email = data.get("email", "").strip().lower()
        token = data.get("token", "")
        new_password = data.get("new_password", "")

        if not email or not token or not new_password:
            return api_error(
                "ValidationError", "Email, token, and new password are required", HTTP_BAD_REQUEST, request_id
            )

        # Validate new password
        is_valid, password_errors = is_secure_password(new_password)
        if not is_valid:
            return api_error("ValidationError", "; ".join(password_errors), HTTP_BAD_REQUEST, request_id)

        with get_db_session() as session:
            user = session.query(User).filter(User.email == email, User.is_deleted.is_(False)).first()

            if not user:
                return api_error("InvalidToken", "Invalid or expired reset token", HTTP_BAD_REQUEST, request_id)

            # Verify reset token
            if not verify_password_reset_token(user.password_reset_token, token, user.password_reset_expires):
                return api_error("InvalidToken", "Invalid or expired reset token", HTTP_BAD_REQUEST, request_id)

            # Update password
            user.password_hash = hash_password(new_password)
            user.password_reset_token = None
            user.password_reset_expires = None

            # Invalidate all refresh tokens (force re-login)
            user.refresh_token_hash = None
            user.refresh_token_expires = None

            # Reset failed login attempts
            user.failed_login_attempts = 0
            user.locked_until = None

        logger.info(f"Password reset completed for {email} [{request_id}]")

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Password reset successful. Please login with your new password.",
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Password reset confirm error [{request_id}]: {str(e)}", exc_info=True)
        return api_error("ResetFailed", "Failed to reset password", HTTP_INTERNAL_ERROR, request_id)


@users_bp.route("/me", methods=["GET"])
def get_current_user():
    """
    Get current authenticated user profile.

    Headers:
        Authorization: Bearer <access_token>

    Returns:
        200: User profile
        401: Not authenticated
    ---
    tags:
      - Authentication
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return api_error("Unauthorized", "Authorization header required", HTTP_UNAUTHORIZED, request_id)

        token = auth_header.split(" ", 1)[1]
        payload, error = decode_token(token)

        if error:
            return api_error("InvalidToken", error, HTTP_UNAUTHORIZED, request_id)

        user_id = int(payload.get("sub"))

        with get_db_session() as session:
            user = session.query(User).filter(User.id == user_id, User.is_deleted.is_(False)).first()

            if not user:
                return api_error("UserNotFound", "User not found", HTTP_NOT_FOUND, request_id)

            user_data = user.to_dict(include_sensitive=True)

        return jsonify({"success": True, "user": user_data, "request_id": request_id}), HTTP_OK

    except Exception as e:
        logger.error(f"Get user error [{request_id}]: {str(e)}", exc_info=True)
        return api_error("UserFetchFailed", "Failed to fetch user profile", HTTP_INTERNAL_ERROR, request_id)
