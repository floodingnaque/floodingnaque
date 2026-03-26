"""
User Authentication Routes.

Provides endpoints for user registration, login, logout, token refresh,
and password reset functionality.
"""

import logging
import os
import re
from datetime import date, datetime, timedelta, timezone

from app.api.middleware.rate_limit import limiter
from app.core.security import (
    JWT_ACCESS_TOKEN_EXPIRES,
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
from app.models.db import ResidentProfile, User, get_db_session
from app.services.email import send_password_reset_email
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
        phone_number = (data.get("phone_number") or data.get("contact_number") or "").strip()

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

            # Create resident profile if extended registration data is present
            has_profile_data = any(
                data.get(f) is not None
                for f in ("date_of_birth", "barangay", "household_members", "sex", "civil_status")
            )
            if has_profile_data:
                dob = None
                raw_dob = data.get("date_of_birth")
                if raw_dob:
                    try:
                        dob = date.fromisoformat(str(raw_dob)[:10])
                    except (ValueError, TypeError):
                        pass

                profile = ResidentProfile(
                    user_id=user.id,
                    date_of_birth=dob,
                    sex=data.get("sex"),
                    civil_status=data.get("civil_status"),
                    contact_number=data.get("contact_number", "").strip() or None,
                    alt_contact_number=data.get("alt_contact_number", "").strip() if data.get("alt_contact_number") else None,
                    alt_contact_name=data.get("alt_contact_name", "").strip() if data.get("alt_contact_name") else None,
                    alt_contact_relationship=data.get("alt_contact_relationship"),
                    is_pwd=bool(data.get("is_pwd", False)),
                    is_senior_citizen=bool(data.get("is_senior_citizen", False)),
                    household_members=data.get("household_members"),
                    children_count=data.get("children_count", 0),
                    senior_count=data.get("senior_count", 0),
                    pwd_count=data.get("pwd_count", 0),
                    barangay=data.get("barangay"),
                    purok=data.get("purok"),
                    street_address=data.get("street_address"),
                    nearest_landmark=data.get("nearest_landmark"),
                    home_type=data.get("home_type"),
                    floor_level=data.get("floor_level"),
                    has_flood_experience=bool(data.get("has_flood_experience", False)),
                    most_recent_flood_year=data.get("most_recent_flood_year"),
                    sms_alerts=bool(data.get("sms_alerts", True)),
                    email_alerts=bool(data.get("email_alerts", True)),
                    push_notifications=bool(data.get("push_notifications", False)),
                    preferred_language=data.get("preferred_language", "Filipino"),
                    data_privacy_consent=bool(data.get("data_privacy_consent", False)),
                )
                session.add(profile)

            # Auto-login: generate tokens so the user is signed in immediately
            access_token = create_access_token(user.id, user.email, user.role)
            refresh_token, refresh_hash = create_refresh_token(user.id)

            user.refresh_token_hash = refresh_hash
            user.refresh_token_expires = datetime.now(timezone.utc) + timedelta(days=7)

            user_data = user.to_dict()

        logger.info(f"User registered: {email} [{request_id}]")

        return (
            jsonify(
                {
                    "success": True,
                    "message": "User registered successfully",
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "Bearer",
                    "expires_in": JWT_ACCESS_TOKEN_EXPIRES * 60,
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
                assert (  # nosec B101 - intentional dev-only guard
                    os.getenv("APP_ENV", "").lower() != "production"
                ), "AUTH_BYPASS must never be active in production"
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
                    "expires_in": JWT_ACCESS_TOKEN_EXPIRES * 60,
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
                    "expires_in": JWT_ACCESS_TOKEN_EXPIRES * 60,
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
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            payload, error = decode_token(token)

            if not error:
                user_id = int(payload.get("sub"))

                with get_db_session() as session:
                    user = session.query(User).filter(User.id == user_id).first()
                    if user:
                        # Invalidate refresh token
                        user.refresh_token_hash = None
                        user.refresh_token_expires = None

                logger.info(f"User logged out: {payload.get('email')} [{request_id}]")
            else:
                # Token expired or invalid — still succeed (user is logging out)
                logger.debug(f"Logout with invalid/expired token [{request_id}]: {error}")
        else:
            # No Authorization header — still succeed (client-side already cleared)
            logger.debug(f"Logout without token [{request_id}]")

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

            if not user:
                # In development, let the caller know the email was not found
                # so they don't waste time waiting for a token that will never come.
                from app.core.config import is_debug_mode

                if is_debug_mode():
                    return (
                        jsonify(
                            {
                                "success": False,
                                "message": "No account found with this email address (development only).",
                                "email_found": False,
                                "request_id": request_id,
                            }
                        ),
                        HTTP_NOT_FOUND,
                    )
                return success_response, HTTP_OK

            # Generate reset token and store its hash (never store plain text)
            token, expires = create_password_reset_token()
            import hashlib as _hashlib

            user.password_reset_token = _hashlib.sha256(token.encode()).hexdigest()
            user.password_reset_expires = expires

            # In production, send email with reset link
            logger.info(f"Password reset requested [{request_id}]")
            # Note: Never log reset tokens - send via secure email channel only

            email_sent = send_password_reset_email(email, token)

            # In development, if SMTP is not configured, return the token
            # directly so developers can still test the reset flow.
            if not email_sent:
                from app.core.config import is_debug_mode

                if is_debug_mode():
                    logger.warning(f"SMTP not configured - returning reset token in response (dev mode) [{request_id}]")
                    return (
                        jsonify(
                            {
                                "success": True,
                                "message": "SMTP not configured. Token returned in response (development only).",
                                "dev_token": token,
                                "request_id": request_id,
                            }
                        ),
                        HTTP_OK,
                    )

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

            # Verify reset token (compare hash since we stored hashed)
            import hashlib as _hashlib

            token_hash = _hashlib.sha256(token.encode()).hexdigest()
            if not verify_password_reset_token(user.password_reset_token, token_hash, user.password_reset_expires):
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


@users_bp.route("/me/change-password", methods=["POST"])
@limiter.limit("5 per hour")
def change_password():
    """
    Change the current authenticated user's password.

    Requires the current password for verification and a new password
    that meets the security policy.

    Headers:
        Authorization: Bearer <access_token>

    Request Body:
    {
        "current_password": "OldPassword123!",
        "new_password": "NewSecurePassword456!"
    }

    Returns:
        200: Password changed successfully
        400: Invalid request / weak password
        401: Not authenticated / wrong current password
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

        data = request.get_json()
        if not data:
            return api_error("InvalidRequest", "No data provided", HTTP_BAD_REQUEST, request_id)

        current_password = data.get("current_password", "")
        new_password = data.get("new_password", "")

        if not current_password or not new_password:
            return api_error(
                "ValidationError",
                "Current password and new password are required",
                HTTP_BAD_REQUEST,
                request_id,
            )

        # Validate new password meets security policy
        is_valid, password_errors = is_secure_password(new_password)
        if not is_valid:
            return api_error("ValidationError", "; ".join(password_errors), HTTP_BAD_REQUEST, request_id)

        with get_db_session() as session:
            user = session.query(User).filter(User.id == user_id, User.is_deleted.is_(False)).first()

            if not user:
                return api_error("UserNotFound", "User not found", HTTP_NOT_FOUND, request_id)

            # Verify current password
            if not verify_password(current_password, user.password_hash):
                return api_error(
                    "InvalidPassword",
                    "Current password is incorrect",
                    HTTP_UNAUTHORIZED,
                    request_id,
                )

            # Update password
            user.password_hash = hash_password(new_password)

            # Invalidate all refresh tokens (force re-login on other devices)
            user.refresh_token_hash = None
            user.refresh_token_expires = None

        logger.info(f"Password changed for user_id={user_id} [{request_id}]")

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Password changed successfully.",
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Password change error [{request_id}]: {str(e)}", exc_info=True)
        return api_error("PasswordChangeFailed", "Failed to change password", HTTP_INTERNAL_ERROR, request_id)


@users_bp.route("/me", methods=["GET"])
@limiter.limit("60 per minute")
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


@users_bp.route("/me", methods=["PATCH"])
@limiter.limit("10 per hour")
def update_current_user():
    """
    Update current authenticated user profile.

    Headers:
        Authorization: Bearer <access_token>

    Body (all optional):
        name: str — Full name (2-255 chars)
        email: str — Valid email address

    Returns:
        200: Updated user profile
        400: Validation error
        401: Not authenticated
        409: Email already in use
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
        data = request.get_json(silent=True) or {}

        with get_db_session() as session:
            user = session.query(User).filter(User.id == user_id, User.is_deleted.is_(False)).first()

            if not user:
                return api_error("UserNotFound", "User not found", HTTP_NOT_FOUND, request_id)

            # Update name
            if "name" in data:
                name = str(data["name"]).strip()
                if len(name) < 2 or len(name) > 255:
                    return api_error(
                        "ValidationError", "Name must be between 2 and 255 characters", HTTP_BAD_REQUEST, request_id
                    )
                user.full_name = name

            # Update email
            if "email" in data:
                email = str(data["email"]).strip().lower()
                if not validate_email(email):
                    return api_error("ValidationError", "Invalid email address", HTTP_BAD_REQUEST, request_id)
                if email != user.email:
                    existing = (
                        session.query(User)
                        .filter(User.email == email, User.id != user_id, User.is_deleted.is_(False))
                        .first()
                    )
                    if existing:
                        return api_error("EmailConflict", "Email address is already in use", HTTP_CONFLICT, request_id)
                    user.email = email

            # Update notification preferences
            if "sms_alerts_enabled" in data:
                user.sms_alerts_enabled = bool(data["sms_alerts_enabled"])
            if "email_alerts_enabled" in data:
                user.email_alerts_enabled = bool(data["email_alerts_enabled"])

            session.commit()
            user_data = user.to_dict(include_sensitive=True)

        logger.info(f"Profile updated [{request_id}]: user_id={user_id}")
        return jsonify({"success": True, "user": user_data, "request_id": request_id}), HTTP_OK

    except Exception as e:
        logger.error(f"Profile update error [{request_id}]: {str(e)}", exc_info=True)
        return api_error("ProfileUpdateFailed", "Failed to update profile", HTTP_INTERNAL_ERROR, request_id)


@users_bp.route("/me", methods=["DELETE"])
@limiter.limit("5 per hour")
def delete_current_user():
    """
    Delete the current authenticated user's account (GDPR right to erasure).

    Performs a soft-delete so that referential integrity is maintained
    while personal data is scrubbed.  Tokens are invalidated immediately.

    Headers:
        Authorization: Bearer <access_token>

    Returns:
        200: Account deleted
        401: Not authenticated
    ---
    tags:
      - Privacy & GDPR
    responses:
      200:
        description: Account deleted successfully
      401:
        description: Not authenticated
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

            email = user.email

            # Soft-delete the account
            user.soft_delete()

            # Scrub PII fields
            user.full_name = None
            user.phone_number = None
            user.last_login_ip = None

            # Invalidate all tokens
            user.refresh_token_hash = None
            user.refresh_token_expires = None
            user.password_reset_token = None
            user.password_reset_expires = None

        logger.info(f"User account deleted (GDPR erasure): {email} [{request_id}]")

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Your account has been deleted and personal data erased.",
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Account deletion error [{request_id}]: {str(e)}", exc_info=True)
        return api_error("DeletionFailed", "Failed to delete account", HTTP_INTERNAL_ERROR, request_id)


@users_bp.route("/me/profile", methods=["GET"])
@limiter.limit("60 per minute")
def get_resident_profile():
    """
    Get the current user's resident/household profile.

    Headers:
        Authorization: Bearer <access_token>

    Returns:
        200: Resident profile data
        401: Not authenticated
    ---
    tags:
      - Resident Profile
    responses:
      200:
        description: Resident profile
      401:
        description: Not authenticated
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

            profile = session.query(ResidentProfile).filter(ResidentProfile.user_id == user_id).first()
            if not profile:
                # Auto-create an empty profile for the user
                profile = ResidentProfile(user_id=user_id)
                session.add(profile)
                session.commit()
                session.refresh(profile)

            return jsonify({"success": True, "data": profile.to_dict(), "request_id": request_id}), HTTP_OK

    except Exception as e:
        logger.error(f"Get resident profile error [{request_id}]: {str(e)}", exc_info=True)
        return api_error("ProfileFetchFailed", "Failed to fetch resident profile", HTTP_INTERNAL_ERROR, request_id)


@users_bp.route("/me/profile", methods=["PATCH"])
@limiter.limit("20 per hour")
def update_resident_profile():
    """
    Update the current user's resident/household profile.

    Headers:
        Authorization: Bearer <access_token>

    Body (all optional):
        contact_number, alt_contact_number, alt_contact_name,
        alt_contact_relationship, is_pwd, is_senior_citizen,
        household_members, children_count, senior_count, pwd_count,
        barangay, purok, street_address, nearest_landmark,
        home_type, floor_level, has_flood_experience,
        most_recent_flood_year, sms_alerts, email_alerts,
        push_notifications, preferred_language, date_of_birth,
        sex, civil_status, data_privacy_consent

    Returns:
        200: Updated resident profile
        400: Validation error
        401: Not authenticated
    ---
    tags:
      - Resident Profile
    responses:
      200:
        description: Updated resident profile
      400:
        description: Validation error
      401:
        description: Not authenticated
    """
    request_id = getattr(g, "request_id", "unknown")

    ALLOWED_FIELDS = {
        "date_of_birth", "sex", "civil_status",
        "contact_number", "alt_contact_number", "alt_contact_name", "alt_contact_relationship",
        "is_pwd", "is_senior_citizen",
        "household_members", "children_count", "senior_count", "pwd_count",
        "barangay", "purok", "street_address", "nearest_landmark",
        "home_type", "floor_level",
        "has_flood_experience", "most_recent_flood_year",
        "sms_alerts", "email_alerts", "push_notifications", "preferred_language",
        "data_privacy_consent",
    }

    VALID_SEX = {"Male", "Female", "Prefer not to say"}
    VALID_CIVIL_STATUS = {"Single", "Married", "Widowed", "Separated"}
    VALID_HOME_TYPE = {"Concrete", "Semi-Concrete", "Wood", "Makeshift"}
    VALID_FLOOR_LEVEL = {"Ground Floor", "2nd Floor", "3rd Floor or higher"}
    VALID_LANGUAGE = {"Filipino", "English"}

    try:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return api_error("Unauthorized", "Authorization header required", HTTP_UNAUTHORIZED, request_id)

        token = auth_header.split(" ", 1)[1]
        payload, error = decode_token(token)

        if error:
            return api_error("InvalidToken", error, HTTP_UNAUTHORIZED, request_id)

        user_id = int(payload.get("sub"))
        data = request.get_json(silent=True) or {}

        # Filter to allowed fields only
        updates = {k: v for k, v in data.items() if k in ALLOWED_FIELDS}
        if not updates:
            return api_error("ValidationError", "No valid fields to update", HTTP_BAD_REQUEST, request_id)

        # Validate enum fields
        if "sex" in updates and updates["sex"] is not None and updates["sex"] not in VALID_SEX:
            return api_error("ValidationError", f"sex must be one of: {', '.join(VALID_SEX)}", HTTP_BAD_REQUEST, request_id)
        if "civil_status" in updates and updates["civil_status"] is not None and updates["civil_status"] not in VALID_CIVIL_STATUS:
            return api_error("ValidationError", f"civil_status must be one of: {', '.join(VALID_CIVIL_STATUS)}", HTTP_BAD_REQUEST, request_id)
        if "home_type" in updates and updates["home_type"] is not None and updates["home_type"] not in VALID_HOME_TYPE:
            return api_error("ValidationError", f"home_type must be one of: {', '.join(VALID_HOME_TYPE)}", HTTP_BAD_REQUEST, request_id)
        if "floor_level" in updates and updates["floor_level"] is not None and updates["floor_level"] not in VALID_FLOOR_LEVEL:
            return api_error("ValidationError", f"floor_level must be one of: {', '.join(VALID_FLOOR_LEVEL)}", HTTP_BAD_REQUEST, request_id)
        if "preferred_language" in updates and updates["preferred_language"] not in VALID_LANGUAGE:
            return api_error("ValidationError", f"preferred_language must be one of: {', '.join(VALID_LANGUAGE)}", HTTP_BAD_REQUEST, request_id)

        # Parse date_of_birth if provided as string
        if "date_of_birth" in updates and isinstance(updates["date_of_birth"], str):
            try:
                updates["date_of_birth"] = date.fromisoformat(updates["date_of_birth"])
            except ValueError:
                return api_error("ValidationError", "date_of_birth must be ISO date (YYYY-MM-DD)", HTTP_BAD_REQUEST, request_id)

        with get_db_session() as session:
            user = session.query(User).filter(User.id == user_id, User.is_deleted.is_(False)).first()
            if not user:
                return api_error("UserNotFound", "User not found", HTTP_NOT_FOUND, request_id)

            profile = session.query(ResidentProfile).filter(ResidentProfile.user_id == user_id).first()
            if not profile:
                profile = ResidentProfile(user_id=user_id)
                session.add(profile)

            for field, value in updates.items():
                setattr(profile, field, value)

            session.commit()
            session.refresh(profile)

            logger.info(f"Resident profile updated [{request_id}]: user_id={user_id}, fields={list(updates.keys())}")
            return jsonify({"success": True, "data": profile.to_dict(), "request_id": request_id}), HTTP_OK

    except Exception as e:
        logger.error(f"Resident profile update error [{request_id}]: {str(e)}", exc_info=True)
        return api_error("ProfileUpdateFailed", "Failed to update resident profile", HTTP_INTERNAL_ERROR, request_id)


@users_bp.route("/me/export", methods=["GET"])
@limiter.limit("5 per hour")
def export_current_user_data():
    """
    Export all personal data for the current authenticated user (GDPR right of access / data portability).

    Returns a JSON document containing every piece of personal data
    the system stores for this user.

    Headers:
        Authorization: Bearer <access_token>

    Returns:
        200: JSON with all user data
        401: Not authenticated
    ---
    tags:
      - Privacy & GDPR
    responses:
      200:
        description: User data export
      401:
        description: Not authenticated
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

            export_data = {
                "export_generated_at": datetime.now(timezone.utc).isoformat(),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "phone_number": user.phone_number,
                    "role": user.role,
                    "is_active": user.is_active,
                    "is_verified": user.is_verified,
                    "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                    "last_login_ip": user.last_login_ip,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                },
            }

        logger.info(f"User data exported (GDPR portability): user_id={user_id} [{request_id}]")

        response = jsonify({"success": True, "data": export_data, "request_id": request_id})
        response.headers["Content-Disposition"] = "attachment; filename=user_data_export.json"
        return response, HTTP_OK

    except Exception as e:
        logger.error(f"Data export error [{request_id}]: {str(e)}", exc_info=True)
        return api_error("ExportFailed", "Failed to export user data", HTTP_INTERNAL_ERROR, request_id)
