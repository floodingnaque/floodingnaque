"""
Request/Response Logging Middleware.

Logs all API requests to database for analytics and debugging.

Uses a background thread pool so that slow remote-DB inserts
(common with Supabase) do not block HTTP responses.
"""

import atexit
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor

from app.models.db import APIRequest, get_db_session
from flask import current_app, g, request

logger = logging.getLogger(__name__)

# Background thread pool for non-blocking request logging.
# Keeps at most 2 workers so the DB isn't overwhelmed, with a bounded
# work queue to apply back-pressure under sustained load.
_log_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="req-log")
atexit.register(_log_executor.shutdown, wait=False)


def _is_logging_disabled():
    """Check if request logging should be disabled."""
    if os.environ.get("TESTING", "").lower() == "true":
        return True
    if current_app and current_app.config.get("TESTING"):
        return True
    return False


def _persist_request_log(log_data: dict):
    """Persist a request log entry to the database (runs in background thread)."""
    try:
        api_request = APIRequest(**log_data)
        with get_db_session() as session:
            session.add(api_request)
    except Exception as e:
        err_str = str(e)
        # Duplicate-key errors (code 23505) are expected when SSE
        # after_request and teardown_request both try to log the same
        # request_id.  Log at DEBUG to avoid polluting the log.
        if "23505" in err_str or "duplicate key" in err_str.lower():
            logger.debug("Duplicate request log ignored: %s", log_data.get("request_id"))
        else:
            logger.warning("Failed to log request to database: %s", e)


def log_request_to_db():
    """Capture request details and dispatch to background thread for persistence."""
    if _is_logging_disabled():
        return

    if not hasattr(g, "start_time") or not hasattr(g, "request_id"):
        return

    # Prevent double-logging (SSE endpoints: after_request fires on Response
    # creation, then teardown_request fires again on client disconnect).
    # Set the flag *before* any DB work so it is always visible to teardown.
    if getattr(g, "_request_logged", False):
        return
    g._request_logged = True

    try:
        response_time_ms = (time.time() - g.start_time) * 1000

        # Extract API version from path
        api_version = "v1"
        if request.path.startswith("/v"):
            parts = request.path.split("/")
            if len(parts) > 1 and parts[1].startswith("v"):
                api_version = parts[1]

        status_code = getattr(g, "response_status_code", 200)
        error_message = getattr(g, "error_message", None)

        # Snapshot all request-context data before dispatching to a
        # background thread (Flask's `g` and `request` are not accessible
        # outside the request context).
        log_data = dict(
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

        _log_executor.submit(_persist_request_log, log_data)

    except Exception as e:
        logger.warning("Failed to prepare request log data: %s", e)


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
            # GeneratorExit is the normal signal when an SSE client
            # disconnects — not an error worth recording as 500.
            if isinstance(exception, GeneratorExit):
                return
            g.response_status_code = 500
            g.error_message = str(exception)[:1000] if str(exception) else ""
            log_request_to_db()

    logger.info("Request logging middleware enabled")
