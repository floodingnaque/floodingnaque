"""
Shared authentication module for Floodingnaque microservices.

Provides JWT token creation, verification, and middleware for
inter-service authentication. All services share the same JWT secret
so tokens issued by the User Management Service are valid everywhere.
"""

import functools
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from flask import g, jsonify, request

from .config import get_secret

logger = logging.getLogger(__name__)

try:
    import jwt

    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logger.warning("PyJWT not installed - JWT auth disabled")


def _get_jwt_secret() -> str:
    """Get JWT secret key from secrets."""
    return get_secret("JWT_SECRET_KEY") or get_secret("SECRET_KEY") or "dev-secret-change-me"


def create_access_token(user_id: int, email: str, role: str = "user", expires_in: int = 3600) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User ID
        email: User email
        role: User role (user/admin/operator)
        expires_in: Token lifetime in seconds

    Returns:
        Encoded JWT token string
    """
    if not JWT_AVAILABLE:
        raise RuntimeError("PyJWT is required for authentication")

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "type": "access",
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm="HS256")


def create_refresh_token(user_id: int, expires_in: int = 2592000) -> str:
    """Create a JWT refresh token (30 days default)."""
    if not JWT_AVAILABLE:
        raise RuntimeError("PyJWT is required for authentication")

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "type": "refresh",
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm="HS256")


def verify_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Verify a JWT token.

    Returns:
        Tuple of (is_valid, payload_or_none)
    """
    if not JWT_AVAILABLE:
        return False, None

    try:
        payload = jwt.decode(token, _get_jwt_secret(), algorithms=["HS256"])
        return True, payload
    except jwt.ExpiredSignatureError:
        logger.debug("Token expired")
        return False, None
    except jwt.InvalidTokenError as e:
        logger.debug("Invalid token: %s", e)
        return False, None


def require_auth(f):
    """Decorator: require valid JWT Bearer token for a route."""

    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header.split(" ", 1)[1]
        is_valid, payload = verify_token(token)
        if not is_valid:
            return jsonify({"error": "Invalid or expired token"}), 401

        # Attach user info to request context
        g.current_user = {
            "id": int(payload.get("sub", 0)),
            "email": payload.get("email", ""),
            "role": payload.get("role", "user"),
        }
        return f(*args, **kwargs)

    return decorated


def require_role(*roles):
    """Decorator: require specific role(s) after authentication."""

    def decorator(f):
        @functools.wraps(f)
        @require_auth
        def decorated(*args, **kwargs):
            user_role = g.current_user.get("role", "user")
            if user_role not in roles:
                return jsonify({"error": "Insufficient permissions"}), 403
            return f(*args, **kwargs)

        return decorated

    return decorator


def create_service_token(service_name: str, expires_in: int = 300) -> str:
    """
    Create a short-lived service-to-service authentication token.

    Used for inter-service communication. These tokens have a
    'service' role and short expiry (5 minutes default).
    """
    if not JWT_AVAILABLE:
        raise RuntimeError("PyJWT is required")

    now = datetime.now(timezone.utc)
    payload = {
        "sub": f"service:{service_name}",
        "role": "service",
        "service": service_name,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "type": "service",
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm="HS256")
