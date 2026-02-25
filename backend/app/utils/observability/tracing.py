"""
Request Tracing Module.

Provides distributed tracing capabilities with trace/span ID propagation
for observability across services.
"""

import logging
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Context variable for current trace
current_trace: ContextVar[Optional["TraceContext"]] = ContextVar("current_trace", default=None)


@dataclass
class Span:
    """Represents a single span in a trace."""

    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: list = field(default_factory=list)
    status: str = "OK"
    error: Optional[str] = None

    @property
    def duration_ms(self) -> Optional[float]:
        """Get span duration in milliseconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000

    def set_tag(self, key: str, value: Any) -> "Span":
        """Add a tag to the span."""
        self.tags[key] = value
        return self

    def log_event(self, event: str, **fields) -> "Span":
        """Log an event within the span."""
        self.logs.append({"timestamp": datetime.now(timezone.utc).isoformat() + "Z", "event": event, **fields})
        return self

    def set_error(self, error: Exception) -> "Span":
        """Mark span as errored."""
        self.status = "ERROR"
        self.error = str(error)
        self.set_tag("error.type", type(error).__name__)
        self.set_tag("error.message", str(error))
        return self

    def finish(self) -> "Span":
        """Mark span as finished."""
        self.end_time = time.perf_counter()
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary."""
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "tags": self.tags,
            "logs": self.logs,
            "status": self.status,
            "error": self.error,
        }


@dataclass
class TraceContext:
    """Manages trace context for a request."""

    trace_id: str
    request_id: str
    spans: list = field(default_factory=list)
    active_span: Optional[Span] = None
    baggage: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def new(cls, request_id: str = None, trace_id: str = None) -> "TraceContext":
        """Create a new trace context."""
        return cls(trace_id=trace_id or str(uuid.uuid4()).replace("-", ""), request_id=request_id or str(uuid.uuid4()))

    @classmethod
    def from_headers(cls, headers: Dict[str, str]) -> "TraceContext":
        """Extract trace context from HTTP headers (W3C Trace Context compatible)."""
        trace_id = headers.get("X-Trace-ID")
        request_id = headers.get("X-Request-ID")
        parent_span_id = headers.get("X-Span-ID")

        # Support W3C traceparent header
        traceparent = headers.get("traceparent", "")
        if traceparent and not trace_id:
            parts = traceparent.split("-")
            if len(parts) >= 2:
                trace_id = parts[1]

        ctx = cls.new(request_id=request_id, trace_id=trace_id)

        if parent_span_id:
            ctx.baggage["parent_span_id"] = parent_span_id

        return ctx

    def to_headers(self) -> Dict[str, str]:
        """Export trace context to HTTP headers."""
        headers = {
            "X-Trace-ID": self.trace_id,
            "X-Request-ID": self.request_id,
        }
        if self.active_span:
            headers["X-Span-ID"] = self.active_span.span_id
            # W3C Trace Context format
            headers["traceparent"] = f"00-{self.trace_id}-{self.active_span.span_id}-01"
        return headers

    def start_span(self, operation_name: str, parent_span_id: str = None, tags: Dict[str, Any] = None) -> Span:
        """Start a new span."""
        if parent_span_id is None and self.active_span:
            parent_span_id = self.active_span.span_id
        elif parent_span_id is None:
            parent_span_id = self.baggage.get("parent_span_id")

        span = Span(
            span_id=str(uuid.uuid4())[:16],
            trace_id=self.trace_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=time.perf_counter(),
            tags=tags or {},
        )

        self.spans.append(span)
        self.active_span = span
        return span

    def finish_span(self, span: Span = None) -> None:
        """Finish a span."""
        span = span or self.active_span
        if span:
            span.finish()
            # Set active span to parent if available
            if span == self.active_span:
                parent_spans = [s for s in self.spans if s.span_id == span.parent_span_id]
                self.active_span = parent_spans[0] if parent_spans else None

    def get_summary(self) -> Dict[str, Any]:
        """Get trace summary for logging."""
        return {
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "span_count": len(self.spans),
            "total_duration_ms": sum(s.duration_ms or 0 for s in self.spans),
            "spans": [s.to_dict() for s in self.spans],
        }


def get_current_trace() -> Optional[TraceContext]:
    """Get current trace context."""
    return current_trace.get()


def set_current_trace(ctx: TraceContext) -> None:
    """Set current trace context."""
    current_trace.set(ctx)


def clear_current_trace() -> None:
    """Clear current trace context."""
    current_trace.set(None)


def trace_operation(operation_name: str = None, tags: Dict[str, Any] = None):
    """
    Decorator to trace a function/method.

    Usage:
        @trace_operation("fetch_weather_data")
        def fetch_weather():
            ...
    """

    def decorator(func: Callable) -> Callable:
        op_name = operation_name or f"{func.__module__}.{func.__name__}"

        @wraps(func)
        def wrapper(*args, **kwargs):
            ctx = get_current_trace()

            if ctx is None:
                return func(*args, **kwargs)

            span = ctx.start_span(op_name, tags=tags)
            try:
                result = func(*args, **kwargs)
                span.set_tag("result.success", True)
                return result
            except Exception as e:
                span.set_error(e)
                raise
            finally:
                ctx.finish_span(span)

        return wrapper

    return decorator


def trace_operation_async(operation_name: str = None, tags: Dict[str, Any] = None):
    """
    Async decorator to trace a function/method.

    Usage:
        @trace_operation_async("fetch_weather_data")
        async def fetch_weather():
            ...
    """

    def decorator(func: Callable) -> Callable:
        op_name = operation_name or f"{func.__module__}.{func.__name__}"

        @wraps(func)
        async def wrapper(*args, **kwargs):
            ctx = get_current_trace()

            if ctx is None:
                return await func(*args, **kwargs)

            span = ctx.start_span(op_name, tags=tags)
            try:
                result = await func(*args, **kwargs)
                span.set_tag("result.success", True)
                return result
            except Exception as e:
                span.set_error(e)
                raise
            finally:
                ctx.finish_span(span)

        return wrapper

    return decorator


class SpanContext:
    """
    Context manager for creating spans.

    Usage:
        with SpanContext("database_query") as span:
            span.set_tag("db.type", "postgresql")
            result = db.query(...)
    """

    def __init__(self, operation_name: str, tags: Dict[str, Any] = None):
        self.operation_name = operation_name
        self.tags = tags or {}
        self.span: Optional[Span] = None

    def __enter__(self) -> Optional[Span]:
        ctx = get_current_trace()
        if ctx:
            self.span = ctx.start_span(self.operation_name, tags=self.tags)
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.span:
            if exc_val:
                self.span.set_error(exc_val)
            ctx = get_current_trace()
            if ctx:
                ctx.finish_span(self.span)
        return False


def inject_trace_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """
    Inject trace headers for outgoing HTTP requests.

    Usage:
        headers = inject_trace_headers({'Content-Type': 'application/json'})
        requests.get(url, headers=headers)
    """
    ctx = get_current_trace()
    if ctx:
        headers.update(ctx.to_headers())
    return headers
