"""Utility functions and helpers.

Sub-packages:
    - observability: logging, metrics, tracing, correlation, sentry
    - resilience: circuit breakers, caching
    - ml: ML version checking
"""

from app.utils.api_errors import (  # Backward compatibility aliases
    AppException,
    AuthenticationError,
    AuthorizationError,
    BadRequestError,
    ConfigurationError,
    ConflictError,
    DatabaseError,
    ExternalAPIError,
    ExternalServiceError,
    ForbiddenError,
    InternalServerError,
    ModelError,
    NotFoundError,
    RateLimitError,
    RateLimitExceededError,
    ServiceUnavailableError,
    UnauthorizedError,
    ValidationError,
)
from app.utils.api_responses import (
    api_accepted,
    api_created,
    api_error,
    api_error_from_exception,
    api_no_content,
    api_paginated,
    api_success,
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
from app.utils.resilience.cache import (
    cache_delete,
    cache_get,
    cache_set,
    cached,
    get_cache_stats,
    is_cache_enabled,
)
from app.utils.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    meteostat_breaker,
    openweathermap_breaker,
    retry_with_backoff,
    weatherstack_breaker,
)
from app.utils.secrets import (
    get_secret,
    get_secret_or_env,
    mask_secret,
    read_secret_file,
    validate_secrets,
)
from app.utils.validation import validate_coordinates, validate_weather_data

__all__ = [
    # Circuit breaker
    "CircuitBreaker",
    "CircuitOpenError",
    "CircuitState",
    "openweathermap_breaker",
    "weatherstack_breaker",
    "meteostat_breaker",
    "retry_with_backoff",
    # Validation
    "validate_coordinates",
    "validate_weather_data",
    # Caching
    "cached",
    "cache_get",
    "cache_set",
    "cache_delete",
    "get_cache_stats",
    "is_cache_enabled",
    # Metrics
    "init_prometheus_metrics",
    "get_metrics",
    "record_prediction",
    "record_external_api_call",
    "record_alert_sent",
    # Secrets
    "get_secret",
    "get_secret_or_env",
    "read_secret_file",
    "mask_secret",
    "validate_secrets",
    # Sentry
    "init_sentry",
    "capture_exception",
    "capture_message",
    "add_breadcrumb",
    "set_user_context",
    "set_tag",
    "is_sentry_enabled",
    # API Responses
    "api_success",
    "api_error",
    "api_error_from_exception",
    "api_created",
    "api_accepted",
    "api_no_content",
    "api_paginated",
    # API Errors
    "AppException",
    "ValidationError",
    "NotFoundError",
    "UnauthorizedError",
    "ForbiddenError",
    "ConflictError",
    "RateLimitExceededError",
    "InternalServerError",
    "ServiceUnavailableError",
    "BadRequestError",
    "ModelError",
    "ExternalServiceError",
    "AuthenticationError",
    "AuthorizationError",
    "RateLimitError",
    "ExternalAPIError",
    "DatabaseError",
    "ConfigurationError",
    # Logging
    "setup_logging",
    "get_logger",
    "set_request_context",
    "clear_request_context",
    "get_request_context",
    "log_with_context",
    "LogContext",
    "log_function_call",
    # Tracing
    "TraceContext",
    "Span",
    "get_current_trace",
    "set_current_trace",
    "clear_current_trace",
    "trace_operation",
    "trace_operation_async",
    "SpanContext",
    "inject_trace_headers",
]
