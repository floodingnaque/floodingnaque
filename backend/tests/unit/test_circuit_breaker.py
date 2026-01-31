"""
Unit tests for circuit breaker utility.

Tests for app/utils/circuit_breaker.py
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from app.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    meteostat_breaker,
    openweathermap_breaker,
    retry_with_backoff,
    weatherstack_breaker,
)


class TestCircuitState:
    """Tests for circuit breaker states."""

    def test_circuit_states_exist(self):
        """Test all circuit states are defined."""
        assert CircuitState.CLOSED is not None
        assert CircuitState.OPEN is not None
        assert CircuitState.HALF_OPEN is not None

    def test_circuit_state_values(self):
        """Test circuit state values."""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half-open"


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initializes in closed state."""
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30, name="test")

        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_threshold == 5
        assert breaker.recovery_timeout == 30
        assert breaker.name == "test"
        assert breaker._failures == 0

    def test_circuit_breaker_default_values(self):
        """Test circuit breaker default initialization values."""
        breaker = CircuitBreaker()

        assert breaker.failure_threshold == 5
        assert breaker.recovery_timeout == 30
        assert breaker.name == "default"

    def test_circuit_breaker_record_success(self):
        """Test recording success resets failure count."""
        breaker = CircuitBreaker()
        breaker._failures = 3

        breaker.record_success()

        assert breaker._failures == 0
        assert breaker.state == CircuitState.CLOSED

    def test_circuit_breaker_record_failure(self):
        """Test recording failure increments count."""
        breaker = CircuitBreaker(failure_threshold=5)

        breaker.record_failure()

        assert breaker._failures == 1

    def test_circuit_breaker_opens_at_threshold(self):
        """Test circuit opens when failure threshold reached."""
        breaker = CircuitBreaker(failure_threshold=3)

        for _ in range(3):
            breaker.record_failure()

        assert breaker.state == CircuitState.OPEN

    def test_circuit_breaker_is_open_property(self):
        """Test is_open property."""
        breaker = CircuitBreaker(failure_threshold=2)

        assert breaker.is_open is False

        breaker.record_failure()
        breaker.record_failure()

        assert breaker.is_open is True

    def test_circuit_breaker_half_open_after_timeout(self):
        """Test circuit enters half-open state after recovery timeout."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0)  # 0 second timeout

        breaker.record_failure()
        assert breaker._state == CircuitState.OPEN

        # After timeout, should be half-open when checked
        time.sleep(0.1)
        state = breaker.state  # This triggers the check

        assert state == CircuitState.HALF_OPEN

    def test_circuit_breaker_closes_after_success_in_half_open(self):
        """Test circuit closes after success in half-open state."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0)

        breaker.record_failure()
        time.sleep(0.1)
        _ = breaker.state  # Trigger half-open

        breaker.record_success()

        assert breaker.state == CircuitState.CLOSED

    def test_circuit_breaker_reopens_after_failure_in_half_open(self):
        """Test circuit reopens after failure in half-open state."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=60)  # Long timeout to prevent auto-recovery

        # First failure opens the circuit
        breaker.record_failure()
        assert breaker._state == CircuitState.OPEN

        # Manually set to HALF_OPEN to test the transition
        breaker._state = CircuitState.HALF_OPEN

        # Record another failure which should reopen the circuit
        breaker.record_failure()

        # Check internal state directly to avoid property's recovery check
        assert breaker._state == CircuitState.OPEN


class TestCircuitBreakerCall:
    """Tests for circuit breaker call method."""

    def test_call_success(self):
        """Test successful call through circuit breaker."""
        breaker = CircuitBreaker()

        def success_func():
            return "success"

        result = breaker.call(success_func)

        assert result == "success"
        assert breaker._failures == 0

    def test_call_failure(self):
        """Test failed call records failure."""
        breaker = CircuitBreaker()

        def fail_func():
            raise ValueError("error")

        with pytest.raises(ValueError):
            breaker.call(fail_func)

        assert breaker._failures == 1

    def test_call_blocked_when_open(self):
        """Test calls are blocked when circuit is open."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=60)

        breaker.record_failure()  # Opens circuit

        def success_func():
            return "success"

        with pytest.raises(CircuitOpenError):
            breaker.call(success_func)


class TestCircuitBreakerDecorator:
    """Tests for circuit breaker as decorator."""

    def test_decorator_wraps_function(self):
        """Test decorator properly wraps function."""
        breaker = CircuitBreaker()

        @breaker
        def my_function():
            return "result"

        assert callable(my_function)
        result = my_function()
        assert result == "result"

    def test_decorator_preserves_function_name(self):
        """Test decorator preserves function metadata."""
        breaker = CircuitBreaker()

        @breaker
        def my_named_function():
            """My docstring."""
            return "result"

        assert my_named_function.__name__ == "my_named_function"
        assert my_named_function.__doc__ is not None and "docstring" in my_named_function.__doc__


class TestCircuitBreakerReset:
    """Tests for circuit breaker reset functionality."""

    def test_reset_clears_state(self):
        """Test reset returns circuit to initial state."""
        breaker = CircuitBreaker(failure_threshold=2)

        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        # Reset
        breaker.reset()

        assert breaker.state == CircuitState.CLOSED
        assert breaker._failures == 0
        assert breaker._last_failure_time is None


class TestCircuitBreakerStatus:
    """Tests for circuit breaker status reporting."""

    def test_get_status(self):
        """Test getting circuit breaker status."""
        breaker = CircuitBreaker(name="test_breaker", failure_threshold=5, recovery_timeout=30)
        breaker.record_failure()

        status = breaker.get_status()

        assert status["name"] == "test_breaker"
        assert status["state"] == "closed"
        assert status["failures"] == 1
        assert status["failure_threshold"] == 5
        assert status["recovery_timeout"] == 30


class TestCircuitOpenError:
    """Tests for CircuitOpenError exception."""

    def test_circuit_open_error(self):
        """Test CircuitOpenError exception."""
        error = CircuitOpenError("Circuit is open")

        assert str(error) == "Circuit is open"
        assert isinstance(error, Exception)


class TestRetryWithBackoff:
    """Tests for retry with backoff decorator."""

    def test_retry_success_first_try(self):
        """Test retry succeeds on first try."""
        call_count = 0

        @retry_with_backoff(max_retries=3)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = success_func()

        assert result == "success"
        assert call_count == 1

    def test_retry_succeeds_after_failures(self):
        """Test retry succeeds after some failures."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("temporary error")
            return "success"

        result = flaky_func()

        assert result == "success"
        assert call_count == 2

    def test_retry_exhausted(self):
        """Test retry raises after max retries."""

        @retry_with_backoff(max_retries=2, base_delay=0.01)
        def always_fail():
            raise ValueError("always fails")

        with pytest.raises(ValueError):
            always_fail()


class TestPredefinedBreakers:
    """Tests for predefined circuit breakers."""

    def test_openweathermap_breaker_exists(self):
        """Test OpenWeatherMap breaker is defined."""
        assert openweathermap_breaker is not None
        assert openweathermap_breaker.name == "openweathermap"

    def test_weatherstack_breaker_exists(self):
        """Test Weatherstack breaker is defined."""
        assert weatherstack_breaker is not None
        assert weatherstack_breaker.name == "weatherstack"

    def test_meteostat_breaker_exists(self):
        """Test Meteostat breaker is defined."""
        assert meteostat_breaker is not None
        assert meteostat_breaker.name == "meteostat"
