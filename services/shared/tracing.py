"""
Distributed tracing module for Floodingnaque microservices.

Implements W3C Trace Context propagation across service boundaries.
Each service forwards the traceparent/tracestate headers so that
the entire request chain can be traced in observability tools.
"""

import logging
import os
import time
import uuid
from typing import Dict, Optional

from flask import g, request

logger = logging.getLogger(__name__)


def generate_trace_id() -> str:
    """Generate a 32-character hex trace ID."""
    return uuid.uuid4().hex


def generate_span_id() -> str:
    """Generate a 16-character hex span ID."""
    return uuid.uuid4().hex[:16]


def setup_tracing_middleware(app, service_name: str):
    """
    Register before/after request hooks for distributed tracing.

    Extracts or creates trace context from incoming request headers
    and propagates it in response headers.
    """

    @app.before_request
    def trace_before_request():
        g.request_start_time = time.perf_counter()

        # Extract W3C traceparent if present
        traceparent = request.headers.get("traceparent", "")
        if traceparent:
            parts = traceparent.split("-")
            if len(parts) >= 4:
                g.trace_id = parts[1]
                g.parent_span_id = parts[2]
            else:
                g.trace_id = generate_trace_id()
                g.parent_span_id = None
        else:
            g.trace_id = generate_trace_id()
            g.parent_span_id = None

        g.span_id = generate_span_id()
        g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        g.correlation_id = request.headers.get("X-Correlation-ID", g.trace_id)
        g.service_name = service_name

    @app.after_request
    def trace_after_request(response):
        # Add tracing headers to response
        if hasattr(g, "trace_id"):
            response.headers["X-Trace-ID"] = g.trace_id
        if hasattr(g, "request_id"):
            response.headers["X-Request-ID"] = g.request_id
        if hasattr(g, "correlation_id"):
            response.headers["X-Correlation-ID"] = g.correlation_id
        if hasattr(g, "span_id"):
            response.headers["X-Span-ID"] = g.span_id

        # Build W3C traceparent for downstream propagation
        if hasattr(g, "trace_id") and hasattr(g, "span_id"):
            traceparent = f"00-{g.trace_id}-{g.span_id}-01"
            response.headers["traceparent"] = traceparent

        # Log request completion with timing
        if hasattr(g, "request_start_time"):
            duration_ms = (time.perf_counter() - g.request_start_time) * 1000
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            logger.info(
                "%s %s %d %.2fms [trace=%s]",
                request.method,
                request.path,
                response.status_code,
                duration_ms,
                getattr(g, "trace_id", "?"),
            )

        return response
