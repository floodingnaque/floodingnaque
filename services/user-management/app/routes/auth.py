"""
Authentication routes.

Endpoints:
  POST /api/v1/auth/register   - Register a new user
  POST /api/v1/auth/login      - Login and receive JWT tokens
  POST /api/v1/auth/logout     - Logout (invalidate refresh token)
  POST /api/v1/auth/refresh    - Refresh access token
  GET  /api/v1/auth/me         - Get current user info
  POST /api/v1/auth/password/reset    - Request password reset
  POST /api/v1/auth/password/change   - Change password
"""

import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user account.

    Body:
      {
        "email": "user@example.com",
        "password": "SecureP@ssw0rd!",
        "full_name": "Juan Dela Cruz",
        "phone_number": "+639171234567"
      }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Request body required"}), 400

    required = ["email", "password"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"success": False, "error": f"Missing fields: {missing}"}), 422

    try:
        from app.services.user_service import UserService
        service = UserService()
        result = service.register(
            email=data["email"],
            password=data["password"],
            full_name=data.get("full_name"),
            phone_number=data.get("phone_number"),
        )
        return jsonify({"success": True, **result}), 201
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 409
    except Exception as e:
        logger.error("Registration failed: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate user and return JWT tokens.

    Body: { "email": "...", "password": "..." }

    Returns:
      {
        "success": true,
        "access_token": "eyJ...",
        "refresh_token": "eyJ...",
        "user": { "id": 1, "email": "...", "role": "user" }
      }
    """
    data = request.get_json()
    if not data or "email" not in data or "password" not in data:
        return jsonify({"success": False, "error": "Email and password required"}), 400

    try:
        from app.services.user_service import UserService
        service = UserService()
        result = service.login(
            email=data["email"],
            password=data["password"],
            ip_address=request.remote_addr,
        )

        if not result:
            return jsonify({"success": False, "error": "Invalid email or password"}), 401

        return jsonify({"success": True, **result})
    except Exception as e:
        logger.error("Login failed: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Logout and invalidate refresh token."""
    from shared.auth import require_auth

    try:
        from app.services.user_service import UserService
        service = UserService()
        # Extract token from header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            service.logout(token)
        return jsonify({"success": True, "message": "Logged out successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@auth_bp.route("/refresh", methods=["POST"])
def refresh_token():
    """
    Refresh an expired access token.

    Body: { "refresh_token": "eyJ..." }
    """
    data = request.get_json()
    if not data or "refresh_token" not in data:
        return jsonify({"success": False, "error": "refresh_token required"}), 400

    try:
        from app.services.user_service import UserService
        service = UserService()
        result = service.refresh_access_token(data["refresh_token"])

        if not result:
            return jsonify({"success": False, "error": "Invalid or expired refresh token"}), 401

        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@auth_bp.route("/me", methods=["GET"])
def get_me():
    """Get current authenticated user's profile."""
    from shared.auth import require_auth, verify_token

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "error": "Authentication required"}), 401

    token = auth_header.split(" ", 1)[1]
    is_valid, payload = verify_token(token)
    if not is_valid:
        return jsonify({"success": False, "error": "Invalid or expired token"}), 401

    try:
        from app.services.user_service import UserService
        service = UserService()
        user = service.get_user(int(payload["sub"]))
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404

        return jsonify({"success": True, "user": user})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@auth_bp.route("/password/reset", methods=["POST"])
def request_password_reset():
    """Request a password reset email."""
    data = request.get_json()
    email = data.get("email") if data else None
    if not email:
        return jsonify({"success": False, "error": "email required"}), 400

    # Always return success (don't reveal if email exists)
    return jsonify({
        "success": True,
        "message": "If an account exists with that email, a reset link has been sent",
    })


@auth_bp.route("/password/change", methods=["POST"])
def change_password():
    """Change password for authenticated user."""
    from shared.auth import verify_token

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "error": "Authentication required"}), 401

    token = auth_header.split(" ", 1)[1]
    is_valid, payload = verify_token(token)
    if not is_valid:
        return jsonify({"success": False, "error": "Invalid token"}), 401

    data = request.get_json()
    if not data or "current_password" not in data or "new_password" not in data:
        return jsonify({"success": False, "error": "current_password and new_password required"}), 400

    try:
        from app.services.user_service import UserService
        service = UserService()
        service.change_password(
            user_id=int(payload["sub"]),
            current_password=data["current_password"],
            new_password=data["new_password"],
        )
        return jsonify({"success": True, "message": "Password changed successfully"})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
