"""Security, performance, network, rate-limiting, versioning, and error-handling fixtures."""

from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# Security Testing Fixtures
# ============================================================================


@pytest.fixture
def malicious_inputs():
    """Common malicious inputs for security testing."""
    return {
        "sql_injection": [
            "'; DROP TABLE users; --",
            "1 OR 1=1",
            "UNION SELECT * FROM passwords",
            "1; DELETE FROM predictions WHERE 1=1",
        ],
        "xss": [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert(1)>",
            "javascript:alert('xss')",
            "<svg onload=alert(1)>",
        ],
        "path_traversal": ["../../../etc/passwd", "..\\..\\..\\windows\\system32", "....//....//etc/passwd"],
        "command_injection": ["; ls -la", "| cat /etc/shadow", "`id`", "$(uname -a)"],
    }


@pytest.fixture
def security_headers():
    """Expected security headers for responses."""
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
    }


# ============================================================================
# Security Testing Fixtures (Extended)
# ============================================================================


@pytest.fixture
def sql_injection_payloads():
    """SQL injection test payloads."""
    return [
        # Basic injection
        "'; DROP TABLE users; --",
        "1 OR 1=1",
        "1' OR '1'='1",
        "1; DELETE FROM predictions WHERE 1=1",
        "UNION SELECT * FROM passwords",
        # Blind SQL injection
        "1 AND 1=1",
        "1 AND 1=2",
        "1' AND '1'='1",
        "1' AND SLEEP(5)--",
        # Second-order injection
        "admin'--",
        "' OR ''='",
        # Database-specific
        "'; EXEC xp_cmdshell('dir'); --",  # SQL Server
        "1; SELECT pg_sleep(5)--",  # PostgreSQL
    ]


@pytest.fixture
def xss_payloads():
    """XSS test payloads."""
    return [
        # Basic XSS
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert(1)>",
        "<svg onload=alert(1)>",
        # Event handlers
        "<body onload=alert(1)>",
        "<div onmouseover=alert(1)>",
        "<input onfocus=alert(1) autofocus>",
        # Protocol handlers
        "javascript:alert('xss')",
        "data:text/html,<script>alert('xss')</script>",
        # Encoded payloads
        "%3Cscript%3Ealert('xss')%3C/script%3E",
        "&#60;script&#62;alert('xss')&#60;/script&#62;",
        # DOM-based XSS
        "<img src='x' onerror='this.onerror=null;alert(1)'>",
        "<iframe src='javascript:alert(1)'></iframe>",
    ]


@pytest.fixture
def csrf_test_data():
    """CSRF test configuration."""
    return {
        "valid_token": "valid-csrf-token-12345",
        "invalid_token": "invalid-csrf-token",
        "expired_token": "expired-csrf-token",
        "missing_token": None,
        "protected_endpoints": ["/api/v1/predict", "/ingest", "/api/v1/upload", "/api/v1/export"],
    }


@pytest.fixture
def path_traversal_payloads():
    """Path traversal attack payloads."""
    return [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "....//....//....//etc/passwd",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc/passwd",
        "..%252f..%252f..%252fetc/passwd",
        "/etc/passwd%00.txt",
        "....\\....\\....\\windows\\system32",
    ]


@pytest.fixture
def command_injection_payloads():
    """Command injection test payloads."""
    return [
        "; ls -la",
        "| cat /etc/passwd",
        "& whoami",
        "`id`",
        "$(whoami)",
        "; ping -c 5 127.0.0.1",
        "|| cat /etc/passwd",
        "&& dir",
    ]


@pytest.fixture
def header_injection_payloads():
    """HTTP header injection payloads."""
    return [
        "test\r\nX-Injected: header",
        "test\r\nSet-Cookie: malicious=value",
        "test%0d%0aX-Injected:%20header",
        "test\nX-Forwarded-For: 127.0.0.1",
    ]


# ============================================================================
# Network Failure Simulation Fixtures
# ============================================================================


@pytest.fixture
def mock_network_failure():
    """Simulate network failures for negative path testing."""
    import requests.exceptions

    class NetworkFailureMock:
        def __init__(self):
            self.failure_type = None

        def timeout(self):
            """Simulate connection timeout."""
            self.failure_type = "timeout"
            raise requests.exceptions.Timeout("Connection timed out")

        def connection_error(self):
            """Simulate connection error."""
            self.failure_type = "connection"
            raise requests.exceptions.ConnectionError("Failed to connect")

        def dns_failure(self):
            """Simulate DNS failure."""
            self.failure_type = "dns"
            raise requests.exceptions.ConnectionError("DNS lookup failed")

        def ssl_error(self):
            """Simulate SSL error."""
            self.failure_type = "ssl"
            raise requests.exceptions.SSLError("SSL certificate verification failed")

        def http_error(self, status_code=500):
            """Simulate HTTP error response."""
            self.failure_type = f"http_{status_code}"
            response = MagicMock()
            response.status_code = status_code
            response.raise_for_status.side_effect = requests.exceptions.HTTPError(f"{status_code} Error")
            return response

    return NetworkFailureMock()


@pytest.fixture
def mock_slow_response():
    """Simulate slow API responses."""
    import time

    def _slow_response(delay_seconds=5):
        time.sleep(delay_seconds)
        return {"status": "ok", "delayed": True}

    return _slow_response


# ============================================================================
# Rate Limiting Test Fixtures
# ============================================================================


@pytest.fixture
def rate_limit_test_config():
    """Configuration for rate limiting tests."""
    return {
        "default_limit": "100 per minute",
        "burst_limit": "10 per second",
        "prediction_limit": "30 per minute",
        "ingest_limit": "60 per minute",
        "test_iterations": 150,  # Exceed default limit
    }


@pytest.fixture
def rapid_requests(client, api_headers):
    """Helper to make rapid requests for rate limit testing."""

    def _rapid_requests(endpoint, count=100, method="GET", data=None):
        responses = []
        for i in range(count):
            if method == "GET":
                resp = client.get(endpoint, headers=api_headers)
            else:
                resp = client.post(endpoint, json=data, headers=api_headers)
            responses.append(
                {
                    "iteration": i + 1,
                    "status_code": resp.status_code,
                    "rate_limited": resp.status_code == 429,
                    "headers": dict(resp.headers),
                }
            )
            if resp.status_code == 429:
                break
        return responses

    return _rapid_requests


# ============================================================================
# Performance Testing Fixtures
# ============================================================================


@pytest.fixture
def performance_timer():
    """Timer for performance testing."""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.perf_counter()

        def stop(self):
            self.end_time = time.perf_counter()

        @property
        def elapsed_ms(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time) * 1000
            return None

        def assert_under(self, max_ms):
            assert self.elapsed_ms is not None, "Timer not stopped"
            assert self.elapsed_ms < max_ms, f"Elapsed {self.elapsed_ms}ms exceeds {max_ms}ms"

    return Timer()


@pytest.fixture
def benchmark_requests(client, api_headers):
    """Benchmark helper for request performance."""
    import time

    def _benchmark(endpoint, method="GET", data=None, iterations=10):
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            if method == "GET":
                client.get(endpoint, headers=api_headers)
            elif method == "POST":
                client.post(endpoint, json=data, headers=api_headers)
            times.append((time.perf_counter() - start) * 1000)

        return {"min_ms": min(times), "max_ms": max(times), "avg_ms": sum(times) / len(times), "iterations": iterations}

    return _benchmark


# ============================================================================
# API Versioning Test Fixtures
# ============================================================================


@pytest.fixture
def api_v1_endpoints():
    """V1 API endpoints for backward compatibility testing."""
    return [
        {"path": "/api/v1/predict", "method": "POST", "required_fields": ["prediction", "flood_risk"]},
        {"path": "/api/v1/health", "method": "GET", "required_fields": ["status"]},
        {"path": "/api/v1/data", "method": "GET", "required_fields": ["data", "total"]},
        {"path": "/api/v1/models", "method": "GET", "required_fields": ["models"]},
    ]


@pytest.fixture
def deprecated_endpoints():
    """Endpoints that are deprecated but should still work."""
    return [
        {"path": "/predict", "new_path": "/api/v1/predict"},
        {"path": "/health", "new_path": "/api/v1/health"},
    ]


# ============================================================================
# Error Handling Test Fixtures
# ============================================================================


@pytest.fixture
def mock_metrics_extended():
    """Mock Prometheus metrics for testing without Prometheus installed."""
    with patch("app.utils.metrics._metrics") as mock:
        mock.predictions_total = MagicMock()
        mock.external_api_calls_total = MagicMock()
        mock.db_pool_connections = MagicMock()
        mock.cache_operations = MagicMock()
        mock.circuit_breaker_state = MagicMock()
        yield mock


@pytest.fixture
def mock_error_context():
    """Fixture for testing ErrorContext context manager."""
    from app.utils.error_handling import ErrorContext

    return ErrorContext


@pytest.fixture
def structured_error_factory():
    """Factory fixture to create StructuredError instances for testing."""
    from app.utils.error_handling import ErrorCategory, StructuredError

    def _create_error(
        error_id="test-error-id",
        category=ErrorCategory.INTERNAL,
        message="Test error message",
        exception_type="TestException",
        exception_message="Test exception",
        recoverable=False,
        retry_after_seconds=None,
        **context,
    ):
        return StructuredError(
            error_id=error_id,
            category=category,
            message=message,
            exception_type=exception_type,
            exception_message=exception_message,
            recoverable=recoverable,
            retry_after_seconds=retry_after_seconds,
            context=context,
        )

    return _create_error


@pytest.fixture
def mock_external_services():
    """Mock all external services at once for isolated testing."""
    patches = []

    # Mock weather services
    weather_patch = patch("app.services.google_weather_service.GoogleWeatherService")
    meteostat_patch = patch("app.services.meteostat_service.MeteostatService")
    worldtides_patch = patch("app.services.worldtides_service.WorldTidesService")

    mock_weather = weather_patch.start()
    mock_meteostat = meteostat_patch.start()
    mock_worldtides = worldtides_patch.start()

    patches.extend([weather_patch, meteostat_patch, worldtides_patch])

    # Configure default return values
    mock_weather.return_value.get_weather.return_value = {
        "temperature": 298.15,
        "humidity": 75.0,
        "precipitation": 5.0,
    }
    mock_meteostat.return_value.get_historical_data.return_value = []
    mock_worldtides.return_value.get_tides.return_value = {"tide_level": 1.5}

    yield {
        "weather": mock_weather,
        "meteostat": mock_meteostat,
        "worldtides": mock_worldtides,
    }

    # Cleanup
    for p in patches:
        p.stop()


@pytest.fixture
def mock_model_with_predictions():
    """Factory fixture for models with configurable prediction outcomes."""

    def _create_model(prediction=0, probabilities=None):
        model = MagicMock()
        model.predict.return_value = [prediction]
        model.predict_proba.return_value = [probabilities or [0.8, 0.2]]
        model.feature_names_in_ = ["temperature", "humidity", "precipitation"]
        return model

    return _create_model
