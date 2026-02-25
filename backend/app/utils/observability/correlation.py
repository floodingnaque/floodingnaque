"""
Correlation ID Module for Distributed Tracing.

Provides correlation ID generation and propagation across microservices
for request tracing and log aggregation.
"""

import hashlib
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Dict, Optional

# Context variable for correlation data
correlation_context: ContextVar[Optional["CorrelationContext"]] = ContextVar("correlation_context", default=None)

# Standard header names for correlation ID propagation
CORRELATION_HEADERS = {
    "X-Correlation-ID": "correlation_id",
    "X-Request-ID": "request_id",
    "X-Trace-ID": "trace_id",
    "X-Span-ID": "span_id",
    "X-Parent-Span-ID": "parent_span_id",
    "X-Session-ID": "session_id",
    "X-User-ID": "user_id",
    "X-Tenant-ID": "tenant_id",
    "X-Service-Name": "service_name",
    "X-Service-Version": "service_version",
    "traceparent": "traceparent",  # W3C Trace Context
    "tracestate": "tracestate",  # W3C Trace Context
}


def generate_correlation_id() -> str:
    """
    Generate a unique correlation ID.

    Format: <timestamp_hex>-<random_uuid_part>
    This format allows for:
    - Rough chronological ordering
    - Uniqueness across distributed systems
    - Easy identification of related requests

    Returns:
        str: A unique correlation ID
    """
    timestamp_hex = hex(int(datetime.now(timezone.utc).timestamp() * 1000))[2:]
    random_part = uuid.uuid4().hex[:16]
    return f"{timestamp_hex}-{random_part}"  # OK: has curly braces


def generate_request_id() -> str:
    """
    Generate a unique request ID (shorter format for logging).

    Returns:
        str: A unique request ID
    """
    return uuid.uuid4().hex[:12]


def generate_trace_id() -> str:
    """
    Generate a W3C compatible trace ID (32 hex chars).

    Returns:
        str: A unique trace ID
    """
    return uuid.uuid4().hex


def generate_span_id() -> str:
    """
    Generate a W3C compatible span ID (16 hex chars).

    Returns:
        str: A unique span ID
    """
    return uuid.uuid4().hex[:16]


def hash_for_sampling(trace_id: str, sample_rate: float = 1.0) -> bool:
    """
    Deterministic sampling decision based on trace ID hash.

    Args:
        trace_id: The trace ID to hash
        sample_rate: Sample rate between 0.0 and 1.0

    Returns:
        bool: Whether this trace should be sampled
    """
    if sample_rate >= 1.0:
        return True
    if sample_rate <= 0.0:
        return False

    hash_value = int(hashlib.md5(trace_id.encode(), usedforsecurity=False).hexdigest()[:8], 16)
    threshold = int(sample_rate * 0xFFFFFFFF)
    return hash_value < threshold


@dataclass
class CorrelationContext:
    """
    Holds all correlation identifiers for a request.

    This context is propagated across service boundaries via HTTP headers
    and injected into all log messages for distributed tracing.
    """

    # Primary identifiers
    correlation_id: str = field(default_factory=generate_correlation_id)
    request_id: str = field(default_factory=generate_request_id)
    trace_id: str = field(default_factory=generate_trace_id)
    span_id: str = field(default_factory=generate_span_id)
    parent_span_id: Optional[str] = None

    # Service metadata
    service_name: str = "floodingnaque-api"
    service_version: str = "2.0.0"

    # Session/user context
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None

    # Sampling
    sampled: bool = True

    # Timing
    start_time: datetime = field(default_factory=datetime.utcnow)

    # Baggage (additional context to propagate)
    baggage: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_headers(cls, headers: Dict[str, str], **kwargs) -> "CorrelationContext":
        """
        Extract correlation context from HTTP headers.

        Supports both custom headers and W3C Trace Context format.

        Args:
            headers: HTTP headers dictionary
            **kwargs: Additional context values

        Returns:
            CorrelationContext: Extracted or new context
        """
        # Normalize headers to lowercase for case-insensitive lookup
        normalized = {k.lower(): v for k, v in headers.items()}

        # Extract correlation ID (or generate new)
        correlation_id = (
            normalized.get("x-correlation-id") or normalized.get("x-request-id") or generate_correlation_id()
        )

        # Extract trace context from W3C traceparent header
        trace_id = None
        parent_span_id = None
        sampled = True

        traceparent = normalized.get("traceparent", "")
        if traceparent:
            parts = traceparent.split("-")
            if len(parts) >= 4:
                # Format: 00-{trace_id}-{parent_span_id}-{flags}
                trace_id = parts[1] if len(parts[1]) == 32 else None
                parent_span_id = parts[2] if len(parts[2]) == 16 else None
                sampled = parts[3] == "01" if len(parts) > 3 else True

        # Fallback to custom headers
        if not trace_id:
            trace_id = normalized.get("x-trace-id") or generate_trace_id()
        if not parent_span_id:
            parent_span_id = normalized.get("x-parent-span-id")

        request_id = normalized.get("x-request-id") or generate_request_id()

        return cls(
            correlation_id=correlation_id,
            request_id=request_id,
            trace_id=trace_id,
            span_id=generate_span_id(),
            parent_span_id=parent_span_id,
            session_id=normalized.get("x-session-id"),
            user_id=normalized.get("x-user-id"),
            tenant_id=normalized.get("x-tenant-id"),
            service_name=kwargs.get("service_name", "floodingnaque-api"),
            service_version=kwargs.get("service_version", "2.0.0"),
            sampled=sampled,
            **{k: v for k, v in kwargs.items() if k not in ["service_name", "service_version"]},
        )

    def to_headers(self) -> Dict[str, str]:
        """
        Export correlation context to HTTP headers for propagation.

        Returns:
            Dict[str, str]: Headers dictionary
        """
        # Build W3C traceparent header
        flags = "01" if self.sampled else "00"
        traceparent = f"00-{self.trace_id}-{self.span_id}-{flags}"  # OK: has curly braces

        headers = {
            "X-Correlation-ID": self.correlation_id,
            "X-Request-ID": self.request_id,
            "X-Trace-ID": self.trace_id,
            "X-Span-ID": self.span_id,
            "X-Service-Name": self.service_name,
            "X-Service-Version": self.service_version,
            "traceparent": traceparent,
        }

        # Add optional headers
        if self.parent_span_id:
            headers["X-Parent-Span-ID"] = self.parent_span_id
        if self.session_id:
            headers["X-Session-ID"] = self.session_id
        if self.user_id:
            headers["X-User-ID"] = self.user_id
        if self.tenant_id:
            headers["X-Tenant-ID"] = self.tenant_id

        # Add tracestate for baggage
        if self.baggage:
            tracestate = ",".join(f"{k}={v}" for k, v in self.baggage.items())  # OK: has curly braces
            headers["tracestate"] = tracestate

        return headers

    def to_log_context(self) -> Dict[str, Any]:
        """
        Export correlation context for log injection.

        Returns:
            Dict[str, Any]: Context dictionary for logging
        """
        ctx = {
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "service": {
                "name": self.service_name,
                "version": self.service_version,
            },
        }

        if self.parent_span_id:
            ctx["parent_span_id"] = self.parent_span_id
        if self.session_id:
            ctx["session_id"] = self.session_id
        if self.user_id:
            ctx["user_id"] = self.user_id
        if self.tenant_id:
            ctx["tenant_id"] = self.tenant_id

        return ctx

    def create_child_context(self) -> "CorrelationContext":
        """
        Create a child correlation context for downstream calls.

        Maintains correlation_id and trace_id but creates new span_id.

        Returns:
            CorrelationContext: Child context
        """
        return CorrelationContext(
            correlation_id=self.correlation_id,
            request_id=self.request_id,
            trace_id=self.trace_id,
            span_id=generate_span_id(),
            parent_span_id=self.span_id,
            session_id=self.session_id,
            user_id=self.user_id,
            tenant_id=self.tenant_id,
            service_name=self.service_name,
            service_version=self.service_version,
            sampled=self.sampled,
            baggage=self.baggage.copy(),
        )


# Context management functions
def get_correlation_context() -> Optional[CorrelationContext]:
    """Get current correlation context."""
    return correlation_context.get()


def set_correlation_context(ctx: Optional[CorrelationContext]) -> None:
    """Set current correlation context."""
    correlation_context.set(ctx)


def clear_correlation_context() -> None:
    """Clear current correlation context."""
    correlation_context.set(None)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID."""
    ctx = get_correlation_context()
    return ctx.correlation_id if ctx else None


def get_trace_id() -> Optional[str]:
    """Get current trace ID."""
    ctx = get_correlation_context()
    return ctx.trace_id if ctx else None


def get_request_id() -> Optional[str]:
    """Get current request ID."""
    ctx = get_correlation_context()
    return ctx.request_id if ctx else None


def inject_correlation_headers(headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Inject correlation headers into outgoing request headers.

    Args:
        headers: Existing headers (optional)

    Returns:
        Dict[str, str]: Headers with correlation IDs
    """
    headers = headers or {}
    ctx = get_correlation_context()

    if ctx:
        # Create child context for downstream call
        child_ctx = ctx.create_child_context()
        headers.update(child_ctx.to_headers())

    return headers


def with_correlation(func):
    """
    Decorator to ensure correlation context exists for a function.

    If no context exists, creates a new one for the duration of the call.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        ctx = get_correlation_context()
        created_new = False

        if ctx is None:
            ctx = CorrelationContext()
            set_correlation_context(ctx)
            created_new = True

        try:
            return func(*args, **kwargs)
        finally:
            if created_new:
                clear_correlation_context()

    return wrapper


class CorrelationContextManager:
    """
    Context manager for correlation context.

    Usage:
        with CorrelationContextManager(correlation_id="abc") as ctx:
            # ctx.correlation_id is available
            # All logs include correlation context
            ...
    """

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.previous_ctx = None
        self.ctx = None

    def __enter__(self) -> CorrelationContext:
        self.previous_ctx = get_correlation_context()

        if self.previous_ctx:
            # Inherit from existing context
            self.ctx = self.previous_ctx.create_child_context()
            # Apply overrides
            for key, value in self.kwargs.items():
                if hasattr(self.ctx, key):
                    setattr(self.ctx, key, value)
        else:
            self.ctx = CorrelationContext(**self.kwargs)

        set_correlation_context(self.ctx)
        return self.ctx

    def __exit__(self, exc_type, exc_val, exc_tb):
        set_correlation_context(self.previous_ctx)
        return False
