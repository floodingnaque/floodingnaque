"""
Circuit Breaker Pattern Implementation.

Prevents cascading failures when external services are unavailable.
Implements retry with exponential backoff.
"""

import logging
import time
from enum import Enum
from functools import wraps
from threading import Lock
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests allowed
    OPEN = "open"  # Failure threshold exceeded, requests blocked
    HALF_OPEN = "half-open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker for external API calls.

    Prevents repeated calls to failing services, allowing them time to recover.
    Implements the circuit breaker pattern with three states:
    - CLOSED: Normal operation, all requests pass through
    - OPEN: After failure threshold, all requests are blocked
    - HALF_OPEN: After recovery timeout, one test request is allowed

    Example:
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30)

        @breaker
        def call_external_api():
            return requests.get(url)
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30, name: str = "default"):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before testing recovery
            name: Name for logging purposes
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name

        self._failures = 0
        self._last_failure_time: Optional[float] = None
        self._state = CircuitState.CLOSED
        self._lock = Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for recovery."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._last_failure_time and time.time() - self._last_failure_time > self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit breaker '{self.name}' entering half-open state")
            return self._state

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)."""
        return self.state == CircuitState.OPEN

    def record_success(self) -> None:
        """Record a successful call, resetting failure count."""
        with self._lock:
            self._failures = 0
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                logger.info(f"Circuit breaker '{self.name}' closed after recovery")

    def record_failure(self) -> None:
        """Record a failed call, potentially opening the circuit."""
        with self._lock:
            self._failures += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                # Failed during recovery test, reopen circuit
                self._state = CircuitState.OPEN
                logger.warning(f"Circuit breaker '{self.name}' reopened after failed recovery")
            elif self._failures >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(f"Circuit breaker '{self.name}' opened after {self._failures} failures")

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to call
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Result from the function call

        Raises:
            CircuitOpenError: If circuit is open
            Exception: Any exception from the function
        """
        if self.is_open:
            raise CircuitOpenError(
                f"Circuit breaker '{self.name}' is open. " f"Retry after {self.recovery_timeout} seconds."
            )

        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise

    def __call__(self, func: Callable) -> Callable:
        """
        Decorator to wrap a function with circuit breaker.

        Example:
            @circuit_breaker
            def call_api():
                return requests.get(url)
        """

        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)

        return wrapper

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        with self._lock:
            self._failures = 0
            self._last_failure_time = None
            self._state = CircuitState.CLOSED
            logger.info(f"Circuit breaker '{self.name}' reset to closed state")

    def get_status(self) -> dict:
        """Get circuit breaker status for monitoring."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failures": self._failures,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure": self._last_failure_time,
        }


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable:
    """
    Decorator for retry with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff calculation
        exceptions: Tuple of exceptions to retry on

    Returns:
        Decorated function

    Example:
        @retry_with_backoff(max_retries=3, base_delay=1.0)
        def flaky_api_call():
            return requests.get(url)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries + 1} attempts")
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base**attempt), max_delay)

                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {delay:.1f}s: {str(e)}"
                    )
                    time.sleep(delay)

            raise last_exception

        return wrapper

    return decorator


# Pre-configured circuit breakers for external services
openweathermap_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60, name="openweathermap")

weatherstack_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60, name="weatherstack")

meteostat_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60, name="meteostat")
