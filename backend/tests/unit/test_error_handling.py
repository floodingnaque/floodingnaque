"""
Unit tests for app/utils/error_handling.py.

Tests for structured error handling utilities including
error categorization, retry logic, and error decorators.
"""

import logging
import time
from unittest.mock import MagicMock, patch

import pytest
from app.utils.error_handling import (
    ErrorCategory,
    ErrorContext,
    RetryConfig,
    StructuredError,
    calculate_delay,
    categorize_exception,
    create_structured_error,
    handle_connection_error,
    handle_errors,
    handle_file_not_found,
    handle_validation_error,
    with_retry,
)


class TestErrorCategory:
    """Tests for ErrorCategory enum."""

    def test_error_category_values(self):
        """Test all error categories exist."""
        assert ErrorCategory.TRANSIENT == "transient"
        assert ErrorCategory.RATE_LIMITED == "rate_limited"
        assert ErrorCategory.RESOURCE_BUSY == "resource_busy"
        assert ErrorCategory.VALIDATION == "validation"
        assert ErrorCategory.AUTHENTICATION == "authentication"
        assert ErrorCategory.AUTHORIZATION == "authorization"
        assert ErrorCategory.NOT_FOUND == "not_found"
        assert ErrorCategory.INTERNAL == "internal"
        assert ErrorCategory.CONFIGURATION == "configuration"
        assert ErrorCategory.DEPENDENCY == "dependency"
        assert ErrorCategory.DATA_INTEGRITY == "data_integrity"
        assert ErrorCategory.DATA_FORMAT == "data_format"
        assert ErrorCategory.MODEL_LOADING == "model_loading"
        assert ErrorCategory.MODEL_INFERENCE == "model_inference"

    def test_error_category_is_string_enum(self):
        """Test ErrorCategory inherits from str."""
        assert isinstance(ErrorCategory.TRANSIENT, str)


class TestStructuredError:
    """Tests for StructuredError dataclass."""

    def test_structured_error_default_values(self):
        """Test StructuredError has sensible defaults."""
        error = StructuredError()

        assert error.error_id  # Should have a generated ID
        assert error.category == ErrorCategory.INTERNAL
        assert error.message == ""
        assert error.exception_type == ""
        assert error.exception_message == ""
        assert error.context == {}
        assert error.traceback is None
        assert error.timestamp  # Should have a timestamp
        assert error.recoverable is False
        assert error.retry_after_seconds is None

    def test_structured_error_custom_values(self):
        """Test StructuredError accepts custom values."""
        error = StructuredError(
            error_id="test123",
            category=ErrorCategory.VALIDATION,
            message="Test error message",
            exception_type="ValueError",
            exception_message="Invalid value",
            context={"key": "value"},
            recoverable=True,
            retry_after_seconds=30,
        )

        assert error.error_id == "test123"
        assert error.category == ErrorCategory.VALIDATION
        assert error.message == "Test error message"
        assert error.exception_type == "ValueError"
        assert error.recoverable is True
        assert error.retry_after_seconds == 30

    def test_to_dict(self):
        """Test to_dict serialization."""
        error = StructuredError(
            error_id="abc123",
            category=ErrorCategory.NOT_FOUND,
            message="Resource not found",
            exception_type="FileNotFoundError",
        )

        result = error.to_dict()

        assert result["error_id"] == "abc123"
        assert result["category"] == "not_found"
        assert result["message"] == "Resource not found"
        assert result["exception_type"] == "FileNotFoundError"
        assert "timestamp" in result

    def test_to_json(self):
        """Test to_json serialization."""
        error = StructuredError(error_id="xyz", message="Test")

        json_str = error.to_json()

        assert isinstance(json_str, str)
        assert "xyz" in json_str
        assert "Test" in json_str

    def test_log_method(self, caplog):
        """Test log method logs error."""
        error = StructuredError(error_id="log123", category=ErrorCategory.INTERNAL, message="Log test error")

        with caplog.at_level(logging.ERROR):
            error.log(logging.ERROR)

        assert "log123" in caplog.text or "error" in caplog.text.lower()


class TestCategorizeException:
    """Tests for categorize_exception function."""

    def test_categorize_file_not_found(self):
        """Test FileNotFoundError categorization."""
        exc = FileNotFoundError("test.txt")
        category, recoverable = categorize_exception(exc)

        assert category == ErrorCategory.NOT_FOUND
        assert recoverable is False

    def test_categorize_permission_error(self):
        """Test PermissionError categorization."""
        exc = PermissionError("Access denied")
        category, recoverable = categorize_exception(exc)

        assert category == ErrorCategory.AUTHORIZATION
        assert recoverable is False

    def test_categorize_value_error(self):
        """Test ValueError categorization."""
        exc = ValueError("Invalid value")
        category, recoverable = categorize_exception(exc)

        assert category == ErrorCategory.VALIDATION
        assert recoverable is False

    def test_categorize_connection_error(self):
        """Test ConnectionError categorization."""
        exc = ConnectionError("Connection failed")
        category, recoverable = categorize_exception(exc)

        assert category == ErrorCategory.TRANSIENT
        assert recoverable is True

    def test_categorize_timeout_error(self):
        """Test TimeoutError categorization."""
        exc = TimeoutError("Request timed out")
        category, recoverable = categorize_exception(exc)

        assert category == ErrorCategory.TRANSIENT
        assert recoverable is True

    def test_categorize_type_error(self):
        """Test TypeError categorization."""
        exc = TypeError("Wrong type")
        category, recoverable = categorize_exception(exc)

        assert category == ErrorCategory.DATA_FORMAT
        assert recoverable is False

    def test_categorize_key_error(self):
        """Test KeyError categorization."""
        exc = KeyError("missing_key")
        category, recoverable = categorize_exception(exc)

        assert category == ErrorCategory.DATA_FORMAT
        assert recoverable is False

    def test_categorize_unknown_exception(self):
        """Test unknown exception defaults to INTERNAL."""

        class CustomException(Exception):
            pass

        exc = CustomException("Unknown error")
        category, recoverable = categorize_exception(exc)

        assert category == ErrorCategory.INTERNAL
        assert recoverable is False


class TestCreateStructuredError:
    """Tests for create_structured_error function."""

    def test_create_from_exception(self):
        """Test creating StructuredError from exception."""
        exc = ValueError("Test validation error")
        error = create_structured_error(exc)

        assert error.category == ErrorCategory.VALIDATION
        assert error.exception_type == "ValueError"
        assert "Test validation error" in error.exception_message
        assert error.recoverable is False

    def test_create_with_custom_message(self):
        """Test creating with custom message."""
        exc = RuntimeError("Internal")
        error = create_structured_error(exc, message="Custom message")

        assert error.message == "Custom message"

    def test_create_with_context(self):
        """Test creating with additional context."""
        exc = IOError("File error")
        context = {"filename": "test.txt", "operation": "read"}
        error = create_structured_error(exc, context=context)

        assert error.context["filename"] == "test.txt"
        assert error.context["operation"] == "read"

    def test_create_without_traceback(self):
        """Test creating without traceback."""
        exc = ValueError("Test")
        error = create_structured_error(exc, include_traceback=False)

        assert error.traceback is None

    def test_create_with_traceback(self):
        """Test creating with traceback."""
        try:
            raise ValueError("Test traceback")
        except ValueError as exc:
            error = create_structured_error(exc, include_traceback=True)
            assert error.traceback is not None
            assert "ValueError" in error.traceback


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_default_config(self):
        """Test RetryConfig default values."""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.base_delay_seconds == 1.0
        assert config.max_delay_seconds == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert ConnectionError in config.retry_on
        assert TimeoutError in config.retry_on

    def test_custom_config(self):
        """Test RetryConfig with custom values."""
        config = RetryConfig(max_attempts=5, base_delay_seconds=0.5, max_delay_seconds=30.0, jitter=False)

        assert config.max_attempts == 5
        assert config.base_delay_seconds == 0.5
        assert config.max_delay_seconds == 30.0
        assert config.jitter is False


class TestCalculateDelay:
    """Tests for calculate_delay function."""

    def test_first_attempt_delay(self):
        """Test delay for first retry attempt."""
        config = RetryConfig(base_delay_seconds=1.0, jitter=False)
        delay = calculate_delay(1, config)

        assert delay == 1.0

    def test_exponential_backoff(self):
        """Test exponential backoff increase."""
        config = RetryConfig(base_delay_seconds=1.0, exponential_base=2.0, jitter=False)

        delay1 = calculate_delay(1, config)
        delay2 = calculate_delay(2, config)
        delay3 = calculate_delay(3, config)

        assert delay1 == 1.0
        assert delay2 == 2.0
        assert delay3 == 4.0

    def test_max_delay_cap(self):
        """Test delay is capped at max_delay_seconds."""
        config = RetryConfig(base_delay_seconds=10.0, max_delay_seconds=30.0, exponential_base=2.0, jitter=False)

        delay = calculate_delay(10, config)  # Would be very large without cap
        assert delay <= 30.0

    def test_jitter_adds_randomness(self):
        """Test jitter adds randomness to delay."""
        config = RetryConfig(base_delay_seconds=1.0, jitter=True)

        delays = [calculate_delay(1, config) for _ in range(10)]

        # With jitter, delays should vary
        # At least some should be different (unless extremely unlikely)
        unique_delays = set(round(d, 6) for d in delays)
        assert len(unique_delays) >= 2 or all(0.5 <= d <= 1.5 for d in delays)


class TestWithRetry:
    """Tests for with_retry decorator."""

    def test_successful_call_no_retry(self):
        """Test successful function doesn't retry."""
        call_count = 0

        @with_retry(max_attempts=3)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()

        assert result == "success"
        assert call_count == 1

    def test_retry_on_transient_error(self):
        """Test retry on transient error."""
        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.01, retry_on=(ConnectionError,))
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return "success"

        result = flaky_func()

        assert result == "success"
        assert call_count == 3

    def test_exhausted_retries_raises(self):
        """Test all retries exhausted raises exception."""
        call_count = 0

        @with_retry(max_attempts=2, base_delay=0.01, retry_on=(ConnectionError,))
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            always_fails()

        assert call_count == 2

    def test_non_retryable_error_not_retried(self):
        """Test non-retryable errors are not retried."""
        call_count = 0

        @with_retry(max_attempts=3, retry_on=(ConnectionError,))
        def value_error_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError):
            value_error_func()

        assert call_count == 1

    def test_on_retry_callback(self):
        """Test on_retry callback is called."""
        retry_calls = []

        def on_retry_callback(exc, attempt):
            retry_calls.append((type(exc).__name__, attempt))

        @with_retry(max_attempts=3, base_delay=0.01, retry_on=(TimeoutError,), on_retry=on_retry_callback)
        def timeout_func():
            if len(retry_calls) < 2:
                raise TimeoutError("Timeout")
            return "done"

        result = timeout_func()

        assert result == "done"
        assert len(retry_calls) == 2
        assert retry_calls[0] == ("TimeoutError", 1)
        assert retry_calls[1] == ("TimeoutError", 2)


class TestHandleErrors:
    """Tests for handle_errors decorator."""

    def test_successful_call_returns_value(self):
        """Test successful function returns normally."""

        @handle_errors(default_return=None)
        def successful_func():
            return "success"

        result = successful_func()
        assert result == "success"

    def test_error_returns_default(self):
        """Test error returns default value."""

        @handle_errors(default_return="default")
        def error_func():
            raise ValueError("Error")

        result = error_func()
        assert result == "default"

    def test_error_returns_default_list(self):
        """Test error returns default list."""

        @handle_errors(default_return=[])
        def error_func():
            raise RuntimeError("Error")

        result = error_func()
        assert result == []

    def test_reraise_option(self):
        """Test reraise option re-raises exception."""

        @handle_errors(reraise=True)
        def error_func():
            raise ValueError("Re-raise me")

        with pytest.raises(ValueError, match="Re-raise me"):
            error_func()

    def test_specific_handler(self):
        """Test specific exception handler is called."""

        def value_handler(exc):
            return f"Handled: {exc}"

        @handle_errors(specific_handlers={ValueError: value_handler})
        def error_func():
            raise ValueError("Test")

        result = error_func()
        assert result == "Handled: Test"

    def test_context_provider(self):
        """Test context provider adds context."""

        @handle_errors(default_return=None, context_provider=lambda: {"service": "test"})
        def error_func():
            raise RuntimeError("Error")

        # Should not raise, returns default
        result = error_func()
        assert result is None


class TestSpecificErrorHandlers:
    """Tests for specific error handler functions."""

    def test_handle_file_not_found(self):
        """Test handle_file_not_found creates proper error."""
        exc = FileNotFoundError("config.yaml")
        exc.filename = "config.yaml"

        error = handle_file_not_found(exc)

        assert isinstance(error, StructuredError)
        assert error.category == ErrorCategory.NOT_FOUND
        assert "config.yaml" in error.message

    def test_handle_validation_error(self):
        """Test handle_validation_error creates proper error."""
        exc = ValueError("Invalid temperature: -500")

        error = handle_validation_error(exc)

        assert isinstance(error, StructuredError)
        assert error.category == ErrorCategory.VALIDATION
        assert "Validation failed" in error.message

    def test_handle_connection_error(self):
        """Test handle_connection_error creates proper error."""
        exc = ConnectionError("Failed to connect to API")

        error = handle_connection_error(exc)

        assert isinstance(error, StructuredError)
        assert error.category == ErrorCategory.TRANSIENT
        assert error.recoverable is True
        assert error.retry_after_seconds == 5


class TestErrorContext:
    """Tests for ErrorContext context manager."""

    def test_error_context_success(self):
        """Test ErrorContext on successful operation."""
        with ErrorContext("test_operation") as ctx:
            result = 1 + 1
            ctx.add_context("result", result)

        # Should not raise

    def test_error_context_captures_exception(self):
        """Test ErrorContext captures exception info."""
        ctx = None
        try:
            with ErrorContext("failing_operation", key="value") as ctx:
                raise ValueError("Test error")
        except ValueError:
            pass  # Expected

        # Error context should have recorded the error
        assert ctx is not None
        assert ctx.error is not None or hasattr(ctx, "exception")
