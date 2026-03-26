"""Request-scoped query counter middleware.

Tracks the number of SQL queries executed per HTTP request and adds
``X-Query-Count`` / ``X-Query-Duration-Ms`` response headers in
development mode.  Logs a warning when a single request exceeds
``QUERY_COUNT_WARN_THRESHOLD`` (default 10).
"""

import logging
import os
import time

from flask import Flask, g, request
from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

QUERY_COUNT_WARN_THRESHOLD = int(os.getenv("QUERY_COUNT_WARN_THRESHOLD", "10"))


def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Increment per-request query counter."""
    try:
        count = getattr(g, "_query_count", None)
        if count is not None:
            g._query_count += 1
    except RuntimeError:
        # Outside application/request context (e.g. scheduler jobs)
        pass


def init_query_counter(app: Flask) -> None:
    """Register before/after request hooks and SQLAlchemy event listener."""

    # Only enable in development / testing
    if os.getenv("APP_ENV", "development").lower() in ("production", "prod"):
        return

    # Attach SQLAlchemy event once
    event.listens_for(Engine, "before_cursor_execute")(_before_cursor_execute)

    @app.before_request
    def _start_counter():
        g._query_count = 0
        g._query_start = time.perf_counter()

    @app.after_request
    def _report_counter(response):
        count = getattr(g, "_query_count", None)
        if count is None:
            return response

        duration_ms = (time.perf_counter() - g._query_start) * 1000

        response.headers["X-Query-Count"] = str(count)
        response.headers["X-Query-Duration-Ms"] = f"{duration_ms:.1f}"

        if count > QUERY_COUNT_WARN_THRESHOLD:
            logger.warning(
                "HIGH QUERY COUNT: %s %s executed %d queries in %.1fms",
                request.method,
                request.path,
                count,
                duration_ms,
            )
        return response
