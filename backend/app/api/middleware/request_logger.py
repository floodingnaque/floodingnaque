"""
Request/Response Logging Middleware.

Logs all API requests to database for analytics and debugging.
"""

import logging
import os
import time

from app.models.db import APIRequest, get_db_session
from flask import current_app, g, request

logger = logging.getLogger(__name__)


def _is_logging_disabled():
    """Check if request logging should be disabled."""
    # Disable in testing environment to avoid SQLite thread safety issues
    if os.environ.get("TESTING", "").lower() == "true":
        return True
    # Also check Flask app testing flag
    if current_app and current_app.config.get("TESTING"):
        return True
    return False


def log_request_to_db():
    """Log request details to database after response is sent."""
    # Skip logging in test environment
    if _is_logging_disabled():
        return

    if not hasattr(g, "start_time") or not hasattr(g, "request_id"):
        return

    try:
        response_time_ms = (time.time() - g.start_time) * 1000

        # Extract API version from path
        api_version = "v1"
        if request.path.startswith("/v"):
            parts = request.path.split("/")
            if len(parts) > 1 and parts[1].startswith("v"):
                api_version = parts[1]

        # Get status code from response
        status_code = getattr(g, "response_status_code", 200)
        error_message = getattr(g, "error_message", None)

        # Create log entry
        api_request = APIRequest(
            request_id=g.request_id,
            endpoint=request.path,
            method=request.method,
            status_code=status_code,
            response_time_ms=response_time_ms,
            user_agent=request.headers.get("User-Agent", "")[:500],
            ip_address=request.remote_addr or "unknown",
            api_version=api_version,
            error_message=error_message,
        )

        with get_db_session() as session:
            session.add(api_request)
            session.commit()

    except Exception as e:
        logger.error(f"Failed to log request to database: {e}")


def setup_request_logging_middleware(app):
    """Setup request logging middleware."""

    @app.before_request
    def before_request():
        """Record request start time."""
        g.start_time = time.time()

    @app.after_request
    def after_request(response):
        """Log request after response is ready."""
        if hasattr(g, "request_id"):
            g.response_status_code = response.status_code
            log_request_to_db()
        return response

    @app.teardown_request
    def teardown_request(exception=None):
        """Log request even if there was an exception."""
        if exception and hasattr(g, "request_id"):
            g.response_status_code = 500
            g.error_message = str(exception)[:1000]
            log_request_to_db()

    logger.info("Request logging middleware enabled")
