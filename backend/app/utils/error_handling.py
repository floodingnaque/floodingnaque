"""
Structured Error Handling Utilities for Floodingnaque.

Provides enhanced error handling with:
- Specific exception types for different error categories
- Structured JSON logging with context
- Automatic retry logic for transient failures
- Error categorization (recoverable vs fatal)

Usage:
    from app.utils.error_handling import (
        handle_errors,
        with_retry,
        ErrorCategory,
        StructuredError
    )

    @handle_errors(default_return=None)
    def risky_operation():
        ...

    @with_retry(max_attempts=3, retry_on=(ConnectionError, TimeoutError))
    def external_api_call():
        ...
"""

import functools
import json
import logging
import time
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar

logger = logging.getLogger(__name__)


# =============================================================================
# ERROR CATEGORIES
# =============================================================================


class ErrorCategory(str, Enum):
    """Error categories for classification."""

    # Recoverable errors - can retry or handle gracefully
    TRANSIENT = "transient"  # Network timeouts, temporary DB issues
    RATE_LIMITED = "rate_limited"  # API rate limits hit
    RESOURCE_BUSY = "resource_busy"  # Resource temporarily unavailable

    # Client errors - user/input issues
    VALIDATION = "validation"  # Input validation failures
    AUTHENTICATION = "authentication"  # Auth failures
    AUTHORIZATION = "authorization"  # Permission denied
    NOT_FOUND = "not_found"  # Resource not found

    # Server/system errors - internal issues
    INTERNAL = "internal"  # Unexpected internal errors
    CONFIGURATION = "configuration"  # Misconfiguration
    DEPENDENCY = "dependency"  # External service failures

    # Data errors
    DATA_INTEGRITY = "data_integrity"  # Data corruption/inconsistency
    DATA_FORMAT = "data_format"  # Malformed data

    # ML-specific errors
    MODEL_LOADING = "model_loading"  # Model file issues
    MODEL_INFERENCE = "model_inference"  # Prediction failures


# Map exception types to categories
EXCEPTION_CATEGORY_MAP: Dict[Type[Exception], ErrorCategory] = {
    FileNotFoundError: ErrorCategory.NOT_FOUND,
    PermissionError: ErrorCategory.AUTHORIZATION,
    ValueError: ErrorCategory.VALIDATION,
    TypeError: ErrorCategory.DATA_FORMAT,
    KeyError: ErrorCategory.DATA_FORMAT,
    ConnectionError: ErrorCategory.TRANSIENT,
    TimeoutError: ErrorCategory.TRANSIENT,
    OSError: ErrorCategory.INTERNAL,
    MemoryError: ErrorCategory.INTERNAL,
}


# =============================================================================
# STRUCTURED ERROR CLASS
# =============================================================================


@dataclass
class StructuredError:
    """
    Structured error information for logging and reporting.
    """

    error_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    category: ErrorCategory = ErrorCategory.INTERNAL
    message: str = ""
    exception_type: str = ""
    exception_message: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    traceback: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    recoverable: bool = False
    retry_after_seconds: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "error_id": self.error_id,
            "category": self.category.value,
            "message": self.message,
            "exception_type": self.exception_type,
            "exception_message": self.exception_message,
            "context": self.context,
            "traceback": self.traceback,
            "timestamp": self.timestamp,
            "recoverable": self.recoverable,
            "retry_after_seconds": self.retry_after_seconds,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    def log(self, level: int = logging.ERROR) -> None:
        """Log the structured error."""
        log_data = {
            "event": "error",
            "error_id": self.error_id,
            "category": self.category.value,
            "message": self.message,
            "exception_type": self.exception_type,
            "recoverable": self.recoverable,
            **self.context,
        }
        logger.log(level, json.dumps(log_data))

        # Log traceback separately at debug level
        if self.traceback:
            logger.debug(f"Error {self.error_id} traceback:\n{self.traceback}")


def categorize_exception(exc: Exception) -> Tuple[ErrorCategory, bool]:
    """
    Categorize an exception and determine if it's recoverable.

    Args:
        exc: The exception to categorize

    Returns:
        Tuple of (category, is_recoverable)
    """
    exc_type = type(exc)

    # Check direct mapping first
    if exc_type in EXCEPTION_CATEGORY_MAP:
        category = EXCEPTION_CATEGORY_MAP[exc_type]
        recoverable = category in (
            ErrorCategory.TRANSIENT,
            ErrorCategory.RATE_LIMITED,
            ErrorCategory.RESOURCE_BUSY,
        )
        return category, recoverable

    # Check inheritance chain
    for base_type, category in EXCEPTION_CATEGORY_MAP.items():
        if isinstance(exc, base_type):
            recoverable = category in (
                ErrorCategory.TRANSIENT,
                ErrorCategory.RATE_LIMITED,
                ErrorCategory.RESOURCE_BUSY,
            )
            return category, recoverable

    # Default to internal error
    return ErrorCategory.INTERNAL, False


def create_structured_error(
    exc: Exception,
    message: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    include_traceback: bool = True,
) -> StructuredError:
    """
    Create a StructuredError from an exception.

    Args:
        exc: The exception
        message: Optional custom message
        context: Additional context dictionary
        include_traceback: Whether to include traceback

    Returns:
        StructuredError instance
    """
    category, recoverable = categorize_exception(exc)

    return StructuredError(
        category=category,
        message=message or str(exc),
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        context=context or {},
        traceback=traceback.format_exc() if include_traceback else None,
        recoverable=recoverable,
    )


# =============================================================================
# RETRY LOGIC
# =============================================================================


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on: Tuple[Type[Exception], ...] = (ConnectionError, TimeoutError)


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    Calculate delay before next retry using exponential backoff.

    Args:
        attempt: Current attempt number (1-indexed)
        config: Retry configuration

    Returns:
        Delay in seconds
    """
    delay = config.base_delay_seconds * (config.exponential_base ** (attempt - 1))
    delay = min(delay, config.max_delay_seconds)

    if config.jitter:
        import random

        delay = delay * (0.5 + random.random())  # nosec B311

    return delay


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retry_on: Tuple[Type[Exception], ...] = (ConnectionError, TimeoutError),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
):
    """
    Decorator to add retry logic to a function.

    Args:
        max_attempts: Maximum number of attempts
        base_delay: Base delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        retry_on: Tuple of exception types to retry on
        on_retry: Optional callback called before each retry

    Example:
        @with_retry(max_attempts=3, retry_on=(ConnectionError, TimeoutError))
        def fetch_weather_data():
            return requests.get(API_URL).json()
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay_seconds=base_delay,
        max_delay_seconds=max_delay,
        retry_on=retry_on,
    )

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e

                    if attempt < config.max_attempts:
                        delay = calculate_delay(attempt, config)

                        structured_error = create_structured_error(
                            e,
                            message=f"Attempt {attempt}/{config.max_attempts} failed, retrying in {delay:.2f}s",
                            context={
                                "function": func.__name__,
                                "attempt": attempt,
                                "max_attempts": config.max_attempts,
                                "delay_seconds": delay,
                            },
                            include_traceback=False,
                        )
                        structured_error.log(logging.WARNING)

                        if on_retry:
                            on_retry(e, attempt)

                        time.sleep(delay)
                    else:
                        # Final attempt failed
                        structured_error = create_structured_error(
                            e,
                            message=f"All {config.max_attempts} attempts failed",
                            context={
                                "function": func.__name__,
                                "final_attempt": attempt,
                            },
                        )
                        structured_error.log(logging.ERROR)

            # Raise the last exception if all retries failed
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


# =============================================================================
# ERROR HANDLING DECORATOR
# =============================================================================

T = TypeVar("T")


def handle_errors(
    default_return: Any = None,
    log_level: int = logging.ERROR,
    reraise: bool = False,
    specific_handlers: Optional[Dict[Type[Exception], Callable[[Exception], Any]]] = None,
    context_provider: Optional[Callable[[], Dict[str, Any]]] = None,
):
    """
    Decorator for structured error handling.

    Args:
        default_return: Value to return if an error occurs
        log_level: Logging level for errors
        reraise: Whether to re-raise the exception after handling
        specific_handlers: Dict mapping exception types to handler functions
        context_provider: Optional callable that returns context dict

    Example:
        @handle_errors(default_return=[], context_provider=lambda: {"service": "weather"})
        def get_weather_data():
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Build context
                context = {
                    "function": func.__name__,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys()),
                }
                if context_provider:
                    context.update(context_provider())

                # Check for specific handlers
                if specific_handlers:
                    for exc_type, handler in specific_handlers.items():
                        if isinstance(e, exc_type):
                            try:
                                return handler(e)
                            except Exception as handler_error:
                                logger.error(f"Error handler failed: {handler_error}")

                # Create and log structured error
                structured_error = create_structured_error(e, context=context)
                structured_error.log(log_level)

                if reraise:
                    raise

                return default_return

        return wrapper

    return decorator


# =============================================================================
# SPECIFIC ERROR HANDLERS
# =============================================================================


def handle_file_not_found(exc: FileNotFoundError) -> StructuredError:
    """Handle FileNotFoundError with enhanced context."""
    return create_structured_error(
        exc,
        message=f"Required file not found: {exc.filename or exc}",
        context={"filename": str(exc.filename) if exc.filename else None},
    )


def handle_validation_error(exc: ValueError) -> StructuredError:
    """Handle ValueError with validation context."""
    return create_structured_error(
        exc,
        message=f"Validation failed: {exc}",
        context={"validation_type": "value_error"},
    )


def handle_connection_error(exc: ConnectionError) -> StructuredError:
    """Handle ConnectionError with retry guidance."""
    error = create_structured_error(
        exc,
        message=f"Connection failed: {exc}",
        context={"retryable": True},
    )
    error.recoverable = True
    error.retry_after_seconds = 5
    return error


# =============================================================================
# CONTEXT MANAGERS
# =============================================================================


class ErrorContext:
    """
    Context manager for structured error handling.

    Example:
        with ErrorContext("loading_model", model_path=path) as ctx:
            model = load_model(path)
            ctx.add_context("model_version", model.version)
    """

    def __init__(self, operation: str, reraise: bool = True, log_level: int = logging.ERROR, **context):
        self.operation = operation
        self.reraise = reraise
        self.log_level = log_level
        self.context = context
        self.error: Optional[StructuredError] = None

    def add_context(self, key: str, value: Any) -> None:
        """Add additional context."""
        self.context[key] = value

    def __enter__(self) -> "ErrorContext":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_val is not None:
            self.context["operation"] = self.operation
            self.error = create_structured_error(
                exc_val,
                message=f"Error during {self.operation}",
                context=self.context,
            )
            self.error.log(self.log_level)

            if not self.reraise:
                return True  # Suppress exception

        return False  # Propagate exception


# =============================================================================
# ERROR AGGREGATOR FOR BATCH OPERATIONS
# =============================================================================


class ErrorAggregator:
    """
    Collect errors during batch operations.

    Example:
        aggregator = ErrorAggregator("batch_predictions")
        for item in items:
            try:
                process(item)
            except Exception as e:
                aggregator.add_error(e, item_id=item.id)

        if aggregator.has_errors:
            aggregator.log_summary()
    """

    def __init__(self, operation: str):
        self.operation = operation
        self.errors: List[StructuredError] = []
        self.total_processed: int = 0

    def add_error(self, exc: Exception, **context) -> None:
        """Add an error to the aggregator."""
        error = create_structured_error(exc, context=context)
        self.errors.append(error)

    def increment_processed(self) -> None:
        """Increment the processed count."""
        self.total_processed += 1

    @property
    def has_errors(self) -> bool:
        """Check if any errors were collected."""
        return len(self.errors) > 0

    @property
    def error_count(self) -> int:
        """Get the number of errors."""
        return len(self.errors)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_processed == 0:
            return 0.0
        return (self.total_processed - len(self.errors)) / self.total_processed

    def get_summary(self) -> Dict[str, Any]:
        """Get error summary."""
        by_category = {}
        for error in self.errors:
            cat = error.category.value
            by_category[cat] = by_category.get(cat, 0) + 1

        return {
            "operation": self.operation,
            "total_processed": self.total_processed,
            "error_count": len(self.errors),
            "success_rate": self.success_rate,
            "errors_by_category": by_category,
            "recoverable_errors": sum(1 for e in self.errors if e.recoverable),
        }

    def log_summary(self) -> None:
        """Log error summary."""
        summary = self.get_summary()
        logger.warning(f"Batch operation '{self.operation}' completed with errors: " f"{json.dumps(summary)}")
