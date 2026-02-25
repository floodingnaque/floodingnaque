"""Observability utilities: logging, metrics, tracing, correlation, and Sentry integration."""

from app.utils.observability.correlation import (
    CorrelationContext,
    clear_correlation_context,
    get_correlation_context,
    inject_correlation_headers,
    set_correlation_context,
)
from app.utils.observability.logging import (
    LogContext,
    clear_request_context,
    get_logger,
    get_request_context,
    log_function_call,
    log_with_context,
    set_request_context,
    setup_logging,
)
from app.utils.observability.metrics import (
    get_metrics,
    init_prometheus_metrics,
    record_alert_sent,
    record_external_api_call,
    record_prediction,
)
from app.utils.observability.sentry import (
    add_breadcrumb,
    capture_exception,
    capture_message,
    init_sentry,
    is_sentry_enabled,
    set_tag,
    set_user_context,
)
from app.utils.observability.tracing import (
    Span,
    SpanContext,
    TraceContext,
    clear_current_trace,
    get_current_trace,
    inject_trace_headers,
    set_current_trace,
    trace_operation,
    trace_operation_async,
)

__all__ = [
    # Correlation
    "CorrelationContext",
    "clear_correlation_context",
    "get_correlation_context",
    "inject_correlation_headers",
    "set_correlation_context",
    # Logging
    "LogContext",
    "clear_request_context",
    "get_logger",
    "get_request_context",
    "log_function_call",
    "log_with_context",
    "set_request_context",
    "setup_logging",
    # Metrics
    "get_metrics",
    "init_prometheus_metrics",
    "record_alert_sent",
    "record_external_api_call",
    "record_prediction",
    # Sentry
    "add_breadcrumb",
    "capture_exception",
    "capture_message",
    "init_sentry",
    "is_sentry_enabled",
    "set_tag",
    "set_user_context",
    # Tracing
    "Span",
    "SpanContext",
    "TraceContext",
    "clear_current_trace",
    "get_current_trace",
    "inject_trace_headers",
    "set_current_trace",
    "trace_operation",
    "trace_operation_async",
]
