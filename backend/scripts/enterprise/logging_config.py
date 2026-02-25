"""
Structured Logging Module
=========================

This module provides enterprise-grade logging with:
- JSON structured logging
- Correlation IDs for request tracing
- Context managers for operation tracking
- Performance timing

.. module:: enterprise.logging_config
   :synopsis: Structured logging with correlation IDs and timing.

.. moduleauthor:: Floodingnaque Team

Features
--------
- JSON-formatted log output for log aggregation
- Correlation IDs for distributed tracing
- Operation timing with context managers
- Training-specific logging events
- Structured event logging

Dependencies
------------
Optional: structlog>=23.0.0

Example
-------
::

    >>> from enterprise.logging_config import TrainingLogger, new_correlation_id
    >>> new_correlation_id()  # Start new trace
    >>> logger = TrainingLogger("training", json_format=True)
    >>> with logger.operation("model_training", version=1):
    ...     # Training code here
    ...     logger.log_metrics({'accuracy': 0.95})
"""

import functools
import json
import logging
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

try:
    import structlog

    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False
    structlog = None


# Thread-local storage for correlation ID
import threading

_context = threading.local()


def get_correlation_id() -> str:
    """Get current correlation ID or generate new one."""
    if not hasattr(_context, "correlation_id"):
        _context.correlation_id = uuid.uuid4().hex[:12]
    return _context.correlation_id


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for current thread."""
    _context.correlation_id = correlation_id


def new_correlation_id() -> str:
    """Generate and set a new correlation ID."""
    correlation_id = uuid.uuid4().hex[:12]
    set_correlation_id(correlation_id)
    return correlation_id


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": get_correlation_id(),
        }

        # Add location info
        log_data["location"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "exc_info",
                "exc_text",
                "thread",
                "threadName",
                "message",
                "asctime",
            ]:
                try:
                    json.dumps(value)
                    log_data[key] = value
                except (TypeError, ValueError):
                    log_data[key] = str(value)

        return json.dumps(log_data, default=str)


class TrainingLogger:
    """
    Specialized logger for ML training operations.

    Provides:
    - Structured logging with context
    - Training progress tracking
    - Metrics logging
    - Performance timing
    """

    def __init__(
        self,
        name: str = "floodingnaque.training",
        log_level: str = "INFO",
        log_file: Optional[Path] = None,
        json_format: bool = True,
    ):
        """
        Initialize training logger.

        Args:
            name: Logger name
            log_level: Logging level
            log_file: Optional file path for log output
            json_format: Whether to use JSON formatting
        """
        self.name = name
        self.json_format = json_format

        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        self.logger.handlers = []  # Clear existing handlers

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        if json_format:
            console_handler.setFormatter(JSONFormatter())
        else:
            console_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)-8s | %(correlation_id)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
                )
            )
        self.logger.addHandler(console_handler)

        # File handler (always JSON)
        if log_file:
            log_file = Path(log_file)
            log_file.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(JSONFormatter())
            self.logger.addHandler(file_handler)

        # Bind correlation ID to log records
        self._add_correlation_filter()

    def _add_correlation_filter(self):
        """Add filter to include correlation ID in all records."""

        class CorrelationFilter(logging.Filter):
            def filter(self, record):
                record.correlation_id = get_correlation_id()
                return True

        self.logger.addFilter(CorrelationFilter())

    def _log(self, level: str, message: str, **kwargs) -> None:
        """Internal logging method."""
        extra = {"extra_data": kwargs} if kwargs else {}
        getattr(self.logger, level.lower())(message, extra=extra)

    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self._log("info", message, **kwargs)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self._log("debug", message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self._log("warning", message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self._log("error", message, **kwargs)

    def exception(self, message: str, **kwargs) -> None:
        """Log exception with traceback."""
        self.logger.exception(message, extra={"extra_data": kwargs})

    def training_started(self, version: int, features: int, samples: int, **kwargs) -> None:
        """Log training start event."""
        self.info(
            "Training started",
            event="training_started",
            version=version,
            n_features=features,
            n_samples=samples,
            **kwargs,
        )

    def training_completed(self, version: int, metrics: Dict[str, float], duration_seconds: float, **kwargs) -> None:
        """Log training completion event."""
        self.info(
            "Training completed",
            event="training_completed",
            version=version,
            metrics=metrics,
            duration_seconds=round(duration_seconds, 2),
            **kwargs,
        )

    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None) -> None:
        """Log metrics update."""
        self.info("Metrics update", event="metrics", metrics=metrics, step=step)

    def log_hyperparameters(self, params: Dict[str, Any]) -> None:
        """Log hyperparameters."""
        self.info("Hyperparameters", event="hyperparameters", params=params)

    def validation_error(self, error_type: str, details: Dict[str, Any]) -> None:
        """Log data validation error."""
        self.warning(
            f"Validation error: {error_type}", event="validation_error", error_type=error_type, details=details
        )

    def model_saved(self, path: str, version: int, metrics: Dict[str, float]) -> None:
        """Log model save event."""
        self.info("Model saved", event="model_saved", path=path, version=version, metrics=metrics)

    @contextmanager
    def operation(self, operation_name: str, **context):
        """
        Context manager for tracking operations.

        Usage:
            with logger.operation("training", version=1):
                # training code
        """
        start_time = time.time()
        self.info(f"{operation_name} started", event=f"{operation_name}_started", **context)

        try:
            yield
            duration = time.time() - start_time
            self.info(
                f"{operation_name} completed",
                event=f"{operation_name}_completed",
                duration_seconds=round(duration, 2),
                **context,
            )
        except Exception as e:
            duration = time.time() - start_time
            self.error(
                f"{operation_name} failed",
                event=f"{operation_name}_failed",
                duration_seconds=round(duration, 2),
                error=str(e),
                error_type=type(e).__name__,
                **context,
            )
            raise


def timed(logger: Optional[TrainingLogger] = None):
    """
    Decorator to time function execution.

    Usage:
        @timed(logger)
        def train_model():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                if logger:
                    logger.info(
                        f"{func.__name__} completed",
                        event="function_completed",
                        function=func.__name__,
                        duration_seconds=round(duration, 2),
                    )
                return result
            except Exception as e:
                duration = time.time() - start_time
                if logger:
                    logger.error(
                        f"{func.__name__} failed",
                        event="function_failed",
                        function=func.__name__,
                        duration_seconds=round(duration, 2),
                        error=str(e),
                    )
                raise

        return wrapper

    return decorator


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None, json_format: bool = True) -> TrainingLogger:
    """
    Setup and return configured logger.

    Args:
        log_level: Logging level
        log_file: Optional log file path
        json_format: Whether to use JSON format

    Returns:
        Configured TrainingLogger instance
    """
    log_path = Path(log_file) if log_file else None
    return TrainingLogger(log_level=log_level, log_file=log_path, json_format=json_format)


# Default logger instance
_default_logger: Optional[TrainingLogger] = None


def get_logger() -> TrainingLogger:
    """Get or create default logger."""
    global _default_logger
    if _default_logger is None:
        _default_logger = setup_logging()
    return _default_logger
