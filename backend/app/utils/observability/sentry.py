"""
Sentry Error Tracking Integration.

Provides centralized error tracking and performance monitoring using Sentry.
Automatically captures exceptions, logs, and performance metrics.
"""

import logging
import os
from typing import Optional

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

logger = logging.getLogger(__name__)


def init_sentry(app=None) -> bool:
    """
    Initialize Sentry SDK for error tracking and performance monitoring.

    Features:
    - Automatic exception capture
    - Performance monitoring (transactions and spans)
    - Breadcrumb tracking for debugging context
    - Release tracking for deployment monitoring
    - Environment-based configuration

    Args:
        app: Flask application instance (optional, for Flask integration)

    Returns:
        bool: True if Sentry was initialized successfully, False otherwise
    """
    sentry_dsn = os.getenv("SENTRY_DSN", "").strip()

    # Skip initialization if DSN not configured
    if not sentry_dsn:
        logger.info("Sentry not configured (SENTRY_DSN not set)")
        return False

    # Get configuration from environment
    environment = os.getenv("SENTRY_ENVIRONMENT") or os.getenv("APP_ENV", "development")
    release = os.getenv("SENTRY_RELEASE") or os.getenv("APP_VERSION", "2.0.0")
    traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
    profiles_sample_rate = float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1"))

    # Configure logging integration
    # Capture logs at ERROR level and above
    sentry_logging = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR,  # Send errors and above as events
    )

    # Build integrations list
    integrations = [
        FlaskIntegration(transaction_style="url"),  # Use URL patterns for transaction names
        SqlalchemyIntegration(),
        RedisIntegration(),
        sentry_logging,
    ]

    try:
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=integrations,
            # Environment and release tracking
            environment=environment,
            release=f"floodingnaque@{release}",
            # Performance monitoring
            traces_sample_rate=traces_sample_rate,
            profiles_sample_rate=profiles_sample_rate,
            # Additional options
            send_default_pii=False,  # Don't send personally identifiable information
            attach_stacktrace=True,  # Include stack traces in messages
            max_breadcrumbs=50,  # Keep last 50 breadcrumbs for context
            # Before send hook for filtering/modifying events
            before_send=before_send_hook,
        )

        logger.info(
            f"Sentry initialized successfully " f"(env={environment}, release={release}, traces={traces_sample_rate})"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
        return False


def before_send_hook(event, hint):
    """
    Hook called before sending events to Sentry.

    Use this to:
    - Filter out certain errors
    - Scrub sensitive data
    - Add custom tags or context

    Args:
        event: The event dictionary
        hint: Additional context about the event

    Returns:
        Modified event or None to drop the event
    """
    # Filter out specific exceptions if needed
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]

        # Example: Don't send 404 errors to Sentry
        if exc_type.__name__ == "NotFound":
            return None

    # Scrub sensitive data from request headers
    if "request" in event:
        headers = event["request"].get("headers", {})
        # Remove sensitive headers
        for sensitive_header in ["Authorization", "X-API-Key", "Cookie"]:
            if sensitive_header in headers:
                headers[sensitive_header] = "[Filtered]"

    return event


def capture_exception(error: Exception, context: Optional[dict] = None) -> Optional[str]:
    """
    Manually capture an exception and send to Sentry.

    Args:
        error: The exception to capture
        context: Additional context dictionary (tags, extra data, etc.)

    Returns:
        Event ID if sent successfully, None otherwise
    """
    if context:
        with sentry_sdk.push_scope() as scope:
            # Add tags
            if "tags" in context:
                for key, value in context["tags"].items():
                    scope.set_tag(key, value)

            # Add extra context
            if "extra" in context:
                for key, value in context["extra"].items():
                    scope.set_extra(key, value)

            # Add user context
            if "user" in context:
                scope.set_user(context["user"])

            return sentry_sdk.capture_exception(error)
    else:
        return sentry_sdk.capture_exception(error)


def capture_message(message: str, level: str = "info", context: Optional[dict] = None) -> Optional[str]:
    """
    Manually capture a message and send to Sentry.

    Args:
        message: The message to capture
        level: Severity level (debug, info, warning, error, fatal)
        context: Additional context dictionary

    Returns:
        Event ID if sent successfully, None otherwise
    """
    if context:
        with sentry_sdk.push_scope() as scope:
            if "tags" in context:
                for key, value in context["tags"].items():
                    scope.set_tag(key, value)
            if "extra" in context:
                for key, value in context["extra"].items():
                    scope.set_extra(key, value)

            return sentry_sdk.capture_message(message, level=level)
    else:
        return sentry_sdk.capture_message(message, level=level)


def add_breadcrumb(message: str, category: str = "default", level: str = "info", data: Optional[dict] = None):
    """
    Add a breadcrumb for debugging context.

    Breadcrumbs are kept in memory and sent with error events to provide context.

    Args:
        message: Breadcrumb message
        category: Category (e.g., 'http', 'db', 'auth')
        level: Severity level
        data: Additional data dictionary
    """
    sentry_sdk.add_breadcrumb(message=message, category=category, level=level, data=data or {})


def set_user_context(user_id: str, email: Optional[str] = None, username: Optional[str] = None):
    """
    Set user context for error tracking.

    Args:
        user_id: Unique user identifier
        email: User email (optional)
        username: Username (optional)
    """
    sentry_sdk.set_user({"id": user_id, "email": email, "username": username})


def set_tag(key: str, value: str):
    """
    Set a tag for the current scope.

    Tags are searchable in Sentry and useful for filtering errors.

    Args:
        key: Tag key
        value: Tag value
    """
    sentry_sdk.set_tag(key, value)


def set_context(name: str, context: dict):
    """
    Set additional context for error events.

    Args:
        name: Context name
        context: Context dictionary
    """
    sentry_sdk.set_context(name, context)


def start_transaction(name: str, op: str = "http.server") -> sentry_sdk.tracing.Transaction:
    """
    Start a performance monitoring transaction.

    Args:
        name: Transaction name
        op: Operation type

    Returns:
        Transaction object (use as context manager)
    """
    return sentry_sdk.start_transaction(name=name, op=op)


def is_sentry_enabled() -> bool:
    """
    Check if Sentry is enabled and initialized.

    Returns:
        bool: True if Sentry is active
    """
    return sentry_sdk.Hub.current.client is not None
