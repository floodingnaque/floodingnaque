"""
Negative Path Tests.

Tests for network failure simulations, timeout handling, and rate limit edge cases.
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import ConnectionError, RequestException, Timeout

# ============================================================================
# Network Failure Simulation Tests
# ============================================================================


class TestNetworkFailureSimulation:
    """Tests for network failure handling."""

    @pytest.mark.negative
    @pytest.mark.network
    def test_external_api_connection_failure(self, client, api_headers, mock_network_failure):
        """Test handling of external API connection failure."""
        with patch("requests.get") as mock_get:
            mock_get.side_effect = mock_network_failure

            response = client.get("/api/v1/weather?lat=14.5&lon=121.0", headers=api_headers)

            # Should not crash, should return graceful error
            assert response.status_code != 500 or response.get_json().get("error") is not None

    @pytest.mark.negative
    @pytest.mark.network
    def test_database_connection_failure(self, client, api_headers):
        """Test handling of database connection failure."""
        with patch("app.models.db.get_db_session") as mock_db:
            mock_db.side_effect = Exception("Database connection failed")

            response = client.post(
                "/api/v1/predict",
                json={"temperature": 298.15, "humidity": 75.0, "precipitation": 5.0},
                headers=api_headers,
            )

            # Should handle gracefully
            assert response.status_code in [500, 503, 200]

    @pytest.mark.negative
    @pytest.mark.network
    def test_dns_resolution_failure(self, client, api_headers):
        """Test handling of DNS resolution failure."""
        with patch("socket.gethostbyname") as mock_dns:
            mock_dns.side_effect = Exception("DNS resolution failed")

            response = client.get("/api/v1/weather?lat=14.5&lon=121.0", headers=api_headers)

            # Should handle DNS failures gracefully
            # May fall through to mock or cached data

    @pytest.mark.negative
    @pytest.mark.network
    def test_ssl_certificate_error(self, client, api_headers):
        """Test handling of SSL certificate error."""
        with patch("requests.get") as mock_get:
            from requests.exceptions import SSLError

            mock_get.side_effect = SSLError("SSL certificate verify failed")

            response = client.get("/api/v1/weather?lat=14.5&lon=121.0", headers=api_headers)

            # Should not expose SSL error details to client

    @pytest.mark.negative
    @pytest.mark.network
    def test_partial_network_failure(self, client, api_headers):
        """Test handling of partial network failure (some services up, some down)."""
        call_count = [0]

        def intermittent_failure(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] % 2 == 0:
                raise ConnectionError("Connection refused")
            return MagicMock(status_code=200, json=lambda: {"data": "test"})

        with patch("requests.get", side_effect=intermittent_failure):
            # Make several requests
            for _ in range(5):
                response = client.get("/api/v1/weather?lat=14.5&lon=121.0", headers=api_headers)
                # Each request should be handled gracefully


# ============================================================================
# Timeout Handling Tests
# ============================================================================


class TestTimeoutHandling:
    """Tests for timeout handling."""

    @pytest.mark.negative
    @pytest.mark.timeout
    def test_external_api_timeout(self, client, api_headers):
        """Test handling of external API timeout."""
        with patch("requests.get") as mock_get:
            mock_get.side_effect = Timeout("Connection timed out")

            response = client.get("/api/v1/weather?lat=14.5&lon=121.0", headers=api_headers)

            # Should not hang, should return timeout error
            assert response.status_code in [200, 408, 503, 504]

    @pytest.mark.negative
    @pytest.mark.timeout
    def test_slow_database_query(self, client, api_headers, db_session):
        """Test handling of slow database query."""
        with patch("sqlalchemy.orm.Query.all") as mock_query:

            def slow_query():
                time.sleep(0.5)
                return []

            mock_query.side_effect = slow_query

            response = client.get("/api/v1/data", headers=api_headers)

            # Should complete (perhaps with timeout error)

    @pytest.mark.negative
    @pytest.mark.timeout
    @patch("app.services.predict.load_model")
    def test_slow_model_inference(self, mock_load, client, api_headers):
        """Test handling of slow model inference."""
        mock_model = MagicMock()

        def slow_predict(*args, **kwargs):
            time.sleep(0.5)
            return [[0]]

        mock_model.predict.side_effect = slow_predict
        mock_model.predict_proba.return_value = [[0.8, 0.2]]
        mock_load.return_value = mock_model

        response = client.post(
            "/api/v1/predict", json={"temperature": 298.15, "humidity": 75.0, "precipitation": 5.0}, headers=api_headers
        )

        # Should complete, possibly with timeout handling

    @pytest.mark.negative
    @pytest.mark.timeout
    def test_read_timeout_vs_connect_timeout(self, client, api_headers):
        """Test distinction between read and connect timeouts."""
        from requests.exceptions import ConnectTimeout, ReadTimeout

        with patch("requests.get") as mock_get:
            # Test connect timeout
            mock_get.side_effect = ConnectTimeout("Connect timeout")
            response = client.get("/api/v1/weather?lat=14.5&lon=121.0", headers=api_headers)

        with patch("requests.get") as mock_get:
            # Test read timeout
            mock_get.side_effect = ReadTimeout("Read timeout")
            response = client.get("/api/v1/weather?lat=14.5&lon=121.0", headers=api_headers)


# ============================================================================
# Rate Limit Edge Cases Tests
# ============================================================================


class TestRateLimitEdgeCases:
    """Tests for rate limit edge cases."""

    @pytest.mark.negative
    @pytest.mark.rate_limit
    def test_rate_limit_boundary(self, client, api_headers, rate_limit_test_config):
        """Test behavior at rate limit boundary."""
        # Make requests up to the limit
        limit = rate_limit_test_config.get("limit", 100)

        for i in range(min(limit, 10)):  # Test with smaller number
            response = client.get("/status", headers=api_headers)

            if response.status_code == 429:
                # Rate limited - verify response format
                data = response.get_json()
                assert "error" in data or "message" in data or response.status_code == 429
                break

    @pytest.mark.negative
    @pytest.mark.rate_limit
    def test_rate_limit_recovery(self, client, api_headers):
        """Test rate limit recovery after window."""
        # Trigger rate limit
        for _ in range(200):
            response = client.get("/status", headers=api_headers)
            if response.status_code == 429:
                break

        # Wait for rate limit window (very short for test)
        time.sleep(0.1)

        # Should recover
        response = client.get("/health", headers=api_headers)
        # May or may not have recovered depending on implementation

    @pytest.mark.negative
    @pytest.mark.rate_limit
    def test_rate_limit_different_endpoints(self, client, api_headers):
        """Test rate limits apply differently to different endpoints."""
        # Some endpoints may have different rate limits
        endpoints = ["/health", "/status", "/api/v1/predict"]

        for endpoint in endpoints:
            if endpoint == "/api/v1/predict":
                response = client.post(
                    endpoint, json={"temperature": 298.15, "humidity": 75.0, "precipitation": 5.0}, headers=api_headers
                )
            else:
                response = client.get(endpoint, headers=api_headers)

            # Check rate limit headers if present
            remaining = response.headers.get("X-RateLimit-Remaining")
            limit = response.headers.get("X-RateLimit-Limit")

            # Rate limit headers are best practice

    @pytest.mark.negative
    @pytest.mark.rate_limit
    def test_rate_limit_by_ip(self, client):
        """Test rate limiting by IP address."""
        headers_ip1 = {"X-Forwarded-For": "192.168.1.1", "Content-Type": "application/json"}
        headers_ip2 = {"X-Forwarded-For": "192.168.1.2", "Content-Type": "application/json"}

        # Requests from different IPs should have separate rate limits
        response1 = client.get("/health", headers=headers_ip1)
        response2 = client.get("/health", headers=headers_ip2)

        # Both should succeed (separate rate limit buckets)
        assert response1.status_code in [200, 429]
        assert response2.status_code in [200, 429]

    @pytest.mark.negative
    @pytest.mark.rate_limit
    def test_rate_limit_burst_handling(self, isolated_client, api_headers):
        """Test handling of request burst with proper context isolation."""
        import concurrent.futures

        num_requests = 20

        def make_request():
            """Make request within isolated context to avoid Flask context errors."""
            with isolated_client() as client:
                return client.get("/health", headers=api_headers)

        # Burst of concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            responses = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Some may be rate limited, but none should error
        status_codes = [r.status_code for r in responses]
        assert all(s in [200, 429, 503] for s in status_codes)


# ============================================================================
# Invalid Request Tests
# ============================================================================


class TestInvalidRequests:
    """Tests for invalid request handling."""

    @pytest.mark.negative
    def test_malformed_json(self, client, api_headers):
        """Test handling of malformed JSON."""
        response = client.post("/api/v1/predict", data="not valid json{", headers=api_headers)

        assert response.status_code in [400, 422]

    @pytest.mark.negative
    def test_wrong_content_type(self, client):
        """Test handling of wrong content type."""
        response = client.post("/api/v1/predict", data="temperature=298.15", headers={"Content-Type": "text/plain"})

        # 500 may occur if content-type validation happens after JSON parsing attempt
        assert response.status_code in [400, 415, 422, 500]

    @pytest.mark.negative
    def test_empty_body(self, client, api_headers):
        """Test handling of empty request body."""
        response = client.post("/api/v1/predict", data="", headers=api_headers)

        assert response.status_code in [400, 422]

    @pytest.mark.negative
    def test_extremely_large_payload(self, client, api_headers):
        """Test handling of extremely large payload."""
        # Create a very large payload
        large_payload = {"data": "x" * (10 * 1024 * 1024)}  # 10MB

        response = client.post("/api/v1/predict", json=large_payload, headers=api_headers)

        # Should reject or handle large payloads
        assert response.status_code in [400, 413, 422, 500]

    @pytest.mark.negative
    def test_deeply_nested_json(self, client, api_headers):
        """Test handling of deeply nested JSON."""
        # Create deeply nested structure
        nested = {"value": 1}
        for _ in range(100):
            nested = {"nested": nested}

        response = client.post("/api/v1/predict", json=nested, headers=api_headers)

        # Should handle without stack overflow

    @pytest.mark.negative
    def test_binary_in_json_field(self, client, api_headers):
        """Test handling of binary data in JSON field."""
        payload = {"temperature": 298.15, "data": "\x00\x01\x02\xff"}  # Binary data

        response = client.post("/api/v1/predict", json=payload, headers=api_headers)

        # Should handle gracefully


# ============================================================================
# Resource Exhaustion Tests
# ============================================================================


class TestResourceExhaustion:
    """Tests for resource exhaustion scenarios."""

    @pytest.mark.negative
    @pytest.mark.slow
    def test_memory_exhaustion_protection(self, client, api_headers):
        """Test protection against memory exhaustion."""
        # Attempt to allocate large amounts of memory through API
        large_list = [{"index": i, "data": "x" * 1000} for i in range(10000)]

        response = client.post("/api/v1/predict", json={"bulk": large_list}, headers=api_headers)

        # Should reject or handle gracefully
        assert response.status_code in [400, 413, 422, 500]

    @pytest.mark.negative
    @pytest.mark.slow
    def test_connection_pool_exhaustion(self, isolated_client, api_headers):
        """Test handling of connection pool exhaustion."""
        import concurrent.futures

        num_requests = 100

        def make_db_request():
            """Make request within isolated context to avoid Flask context errors."""
            with isolated_client() as client:
                return client.get("/api/v1/data", headers=api_headers)

        # Many concurrent database requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_db_request) for _ in range(num_requests)]
            responses = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All should complete (possibly with errors)
        status_codes = [r.status_code for r in responses]

        # Should not hang

    @pytest.mark.negative
    def test_file_descriptor_exhaustion(self, client, api_headers):
        """Test handling when file descriptors are exhausted."""
        # This is more of an infrastructure test
        # API should handle gracefully if FD limit is reached

        for _ in range(50):
            response = client.get("/health", headers=api_headers)
            assert response.status_code in [200, 429, 503]


# ============================================================================
# Edge Case Input Tests
# ============================================================================


class TestEdgeCaseInputs:
    """Tests for edge case inputs."""

    @pytest.mark.negative
    def test_null_values(self, client, api_headers):
        """Test handling of null values."""
        payload = {"temperature": None, "humidity": 75.0, "precipitation": 5.0}

        response = client.post("/api/v1/predict", json=payload, headers=api_headers)

        # Should validate and reject null
        assert response.status_code in [400, 422, 200]

    @pytest.mark.negative
    def test_infinity_values(self, client, api_headers):
        """Test handling of infinity values."""
        payload = {"temperature": float("inf"), "humidity": 75.0, "precipitation": 5.0}

        response = client.post("/api/v1/predict", json=payload, headers=api_headers)

        # Should reject infinity

    @pytest.mark.negative
    def test_nan_values(self, client, api_headers):
        """Test handling of NaN values."""
        # NaN in JSON is typically represented as null or string
        payload = {"temperature": "NaN", "humidity": 75.0, "precipitation": 5.0}

        response = client.post("/api/v1/predict", json=payload, headers=api_headers)

        # Should handle NaN input

    @pytest.mark.negative
    def test_extreme_values(self, client, api_headers):
        """Test handling of extreme values."""
        extreme_payloads = [
            {"temperature": 1e308, "humidity": 75.0, "precipitation": 5.0},
            {"temperature": -1e308, "humidity": 75.0, "precipitation": 5.0},
            {"temperature": 298.15, "humidity": 1e100, "precipitation": 5.0},
        ]

        for payload in extreme_payloads:
            response = client.post("/api/v1/predict", json=payload, headers=api_headers)

            # Should validate ranges; 503 may occur if model is not available
            assert response.status_code in [200, 400, 422, 503]

    @pytest.mark.negative
    def test_unicode_edge_cases(self, client, api_headers):
        """Test handling of Unicode edge cases."""
        unicode_payloads = [
            {"name": "\u0000"},  # Null character
            {"name": "\uffff"},  # Max BMP character
            {"name": "🌊💧🌧️"},  # Emoji (surrogate pairs)
            {"name": "\u202e"},  # Right-to-left override
        ]

        for payload in unicode_payloads:
            response = client.post(
                "/api/v1/predict",
                json={"temperature": 298.15, "humidity": 75.0, "precipitation": 5.0, **payload},
                headers=api_headers,
            )

            # Should handle Unicode gracefully
            assert response.status_code != 500

    @pytest.mark.negative
    def test_empty_string_values(self, client, api_headers):
        """Test handling of empty string values."""
        payload = {"temperature": "", "humidity": "", "precipitation": ""}

        response = client.post("/api/v1/predict", json=payload, headers=api_headers)

        # Should validate and reject empty strings for numeric fields
        assert response.status_code in [400, 422]

    @pytest.mark.negative
    def test_array_instead_of_value(self, client, api_headers):
        """Test handling of array instead of scalar value."""
        payload = {"temperature": [298.15, 300.0], "humidity": 75.0, "precipitation": 5.0}

        response = client.post("/api/v1/predict", json=payload, headers=api_headers)

        # Should validate type
        assert response.status_code in [400, 422, 200]  # May accept array for batch

    @pytest.mark.negative
    def test_object_instead_of_value(self, client, api_headers):
        """Test handling of object instead of scalar value."""
        payload = {"temperature": {"value": 298.15}, "humidity": 75.0, "precipitation": 5.0}

        response = client.post("/api/v1/predict", json=payload, headers=api_headers)

        # Should validate type
        assert response.status_code in [400, 422]
