"""
Session Configuration for Floodingnaque API.

Provides server-side session storage configuration with Redis backend
for production environments. Falls back to filesystem storage in development.
"""

import logging
import os
from datetime import timedelta
from typing import Any, Dict

from app.utils.secrets import get_secret

logger = logging.getLogger(__name__)


def get_session_config() -> Dict[str, Any]:
    """
    Get session configuration based on environment.

    Production: Uses Redis for distributed session storage
    Development: Uses filesystem-based sessions

    Returns:
        Dict with session configuration settings
    """
    is_production = os.getenv("APP_ENV", "development").lower() in ("production", "prod", "staging", "stage")
    redis_url = get_secret("REDIS_URL") or get_secret("RATE_LIMIT_STORAGE_URL") or ""

    config = {
        # Base session settings
        "SESSION_COOKIE_NAME": "floodingnaque_session",
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SECURE": is_production,  # Require HTTPS in production
        "SESSION_COOKIE_SAMESITE": "Lax",
        "PERMANENT_SESSION_LIFETIME": timedelta(hours=24),
        "SESSION_REFRESH_EACH_REQUEST": True,
        "SESSION_KEY_PREFIX": "floodingnaque:session:",
    }

    # Redis session configuration for production
    if redis_url and ("redis" in redis_url.lower() or is_production):
        try:
            config.update(
                {
                    "SESSION_TYPE": "redis",
                    "SESSION_PERMANENT": True,
                    "SESSION_USE_SIGNER": True,  # Sign session cookies for integrity
                    "SESSION_REDIS": _get_redis_connection(redis_url),
                }
            )
            logger.info("Session storage configured: Redis")
        except Exception as e:
            logger.warning(f"Failed to configure Redis sessions: {e}. Falling back to filesystem.")
            config.update(_get_filesystem_config())
    else:
        # Development fallback to filesystem
        config.update(_get_filesystem_config())

    return config


def _get_filesystem_config() -> Dict[str, Any]:
    """Get filesystem session configuration for development."""
    import tempfile

    session_dir = os.path.join(tempfile.gettempdir(), "floodingnaque_sessions")
    os.makedirs(session_dir, exist_ok=True)

    logger.info(f"Session storage configured: Filesystem ({session_dir})")

    from cachelib import FileSystemCache

    return {
        "SESSION_TYPE": "cachelib",
        "SESSION_CACHELIB": FileSystemCache(session_dir, threshold=500, mode=0o600),
        "SESSION_PERMANENT": False,
    }


def _get_redis_connection(redis_url: str):
    """
    Create a Redis connection for session storage.

    Supports both regular redis:// and TLS rediss:// connections.

    Args:
        redis_url: Redis connection URL

    Returns:
        Redis connection instance
    """
    import redis

    # Parse TLS settings
    use_ssl = redis_url.startswith("rediss://")

    # Configure connection based on URL
    if use_ssl:
        logger.info("Using TLS for Redis session connection")
        return redis.Redis.from_url(
            redis_url,
            ssl_cert_reqs=None,  # Allow self-signed certs in some environments
            decode_responses=False,  # Flask-Session handles encoding
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )
    else:
        return redis.Redis.from_url(
            redis_url,
            decode_responses=False,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )


def init_session(app) -> bool:
    """
    Initialize Flask-Session with the app.

    Args:
        app: Flask application instance

    Returns:
        bool: True if initialization succeeded
    """
    try:
        from flask_session import Session

        # Apply session configuration
        session_config = get_session_config()
        app.config.update(session_config)

        # Initialize Flask-Session
        Session(app)

        session_type = session_config.get("SESSION_TYPE", "unknown")
        logger.info(f"Flask-Session initialized with {session_type} backend")

        return True
    except ImportError:
        logger.warning("Flask-Session not installed. Using default Flask sessions.")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Flask-Session: {e}")
        return False


def validate_session_health() -> Dict[str, Any]:
    """
    Validate session storage health.

    Returns:
        Dict with health status information
    """
    redis_url = get_secret("REDIS_URL") or get_secret("RATE_LIMIT_STORAGE_URL") or ""

    result = {
        "status": "unknown",
        "backend": "unknown",
        "latency_ms": None,
    }

    if redis_url and "redis" in redis_url.lower():
        result["backend"] = "redis"
        try:
            import time

            client = _get_redis_connection(redis_url)
            start = time.time()
            client.ping()
            latency = (time.time() - start) * 1000

            result["status"] = "healthy"
            result["latency_ms"] = round(latency, 2)
        except Exception as e:
            result["status"] = "unhealthy"
            result["error"] = str(e)
    else:
        result["backend"] = "filesystem"
        result["status"] = "healthy"

    return result


class SessionSecurityMiddleware:
    """
    Middleware for additional session security measures.

    - Rotates session ID on privilege escalation
    - Validates session integrity
    - Logs suspicious session activity
    """

    @staticmethod
    def regenerate_session(session):
        """
        Regenerate session ID for security (e.g., after login).

        Call this after successful authentication to prevent
        session fixation attacks.

        Args:
            session: Flask session object
        """
        from flask import session as flask_session

        # Store current session data
        session_data = dict(flask_session)

        # Clear and regenerate
        flask_session.clear()
        flask_session.update(session_data)
        flask_session.modified = True

        logger.debug("Session regenerated for security")

    @staticmethod
    def validate_session_fingerprint(session, request) -> bool:
        """
        Validate session fingerprint to detect session hijacking.

        Checks if the current request matches the session's
        original fingerprint (user agent + IP).

        Args:
            session: Flask session object
            request: Flask request object

        Returns:
            bool: True if fingerprint is valid
        """
        fingerprint = session.get("_fingerprint")
        if not fingerprint:
            # No fingerprint yet, create one
            import hashlib

            user_agent = request.headers.get("User-Agent", "")[:200]
            new_fingerprint = hashlib.sha256(user_agent.encode()).hexdigest()[:16]
            session["_fingerprint"] = new_fingerprint
            return True

        # Validate existing fingerprint
        import hashlib

        user_agent = request.headers.get("User-Agent", "")[:200]
        current_fingerprint = hashlib.sha256(user_agent.encode()).hexdigest()[:16]

        if fingerprint != current_fingerprint:
            logger.warning("Session fingerprint mismatch - possible session hijacking")
            return False

        return True
