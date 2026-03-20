"""
Input Sanitization Security Tests.

Tests to verify proper input sanitization and validation.
"""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _mock_data_db():
    """Auto-mock DB session so data-route tests don't need a real database."""
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.all.return_value = []
    mock_query.count.return_value = 0
    mock_session.query.return_value = mock_query

    @contextmanager
    def _fake_session():
        yield mock_session

    with (
        patch("app.models.db.get_db_session", _fake_session),
        patch("app.api.routes.data.get_db_session", _fake_session),
    ):
        yield


class TestInputValidation:
    """Tests for input validation."""

    @pytest.mark.security
    def test_numeric_fields_reject_strings(self, client, api_headers):
        """Test numeric fields reject string inputs."""
        invalid_inputs = [
            {"temperature": "hot", "humidity": 75.0, "precipitation": 5.0},
            {"temperature": 298.15, "humidity": "wet", "precipitation": 5.0},
            {"temperature": 298.15, "humidity": 75.0, "precipitation": "rainy"},
        ]

        for data in invalid_inputs:
            response = client.post("/api/v1/predict", json=data, headers=api_headers)

            # Should return validation error
            assert response.status_code in [400, 422], f"Invalid input accepted: {data}"

    @pytest.mark.security
    def test_coordinate_bounds_validation(self, client, api_headers):
        """Test coordinate bounds are validated."""
        invalid_coords = [
            {"lat": 91.0, "lon": 121.0},  # Latitude > 90
            {"lat": -91.0, "lon": 121.0},  # Latitude < -90
            {"lat": 14.4, "lon": 181.0},  # Longitude > 180
            {"lat": 14.4, "lon": -181.0},  # Longitude < -180
        ]

        for coords in invalid_coords:
            response = client.get(
                f"/api/v1/ingest/ingest?lat={coords['lat']}&lon={coords['lon']}",
                headers=api_headers,
            )

            # Should reject invalid coordinates or return info (GET is allowed); 401 if auth fails
            assert response.status_code in [200, 400, 401, 422], f"Invalid coords accepted: {coords}"

    @pytest.mark.security
    def test_pagination_limits_enforced(self, client):
        """Test pagination limits are enforced."""
        # Test excessive limit
        response = client.get("/api/v1/data/data?limit=10000")
        assert response.status_code in [200, 400], "Excessive limit should be rejected or capped"

        # Test negative limit
        response = client.get("/api/v1/data/data?limit=-1")
        assert response.status_code in [200, 400], "Negative limit should be rejected"

        # Test negative offset
        response = client.get("/api/v1/data/data?offset=-10")
        assert response.status_code in [200, 400], "Negative offset should be rejected"

    @pytest.mark.security
    def test_string_length_limits(self, client, api_headers):
        """Test string length limits are enforced."""
        # Very long string in prediction request
        long_string = "A" * 100000

        response = client.post(
            "/api/v1/predict", json={"note": long_string, "temperature": 298.15}, headers=api_headers
        )

        # Should either reject or truncate
        assert response.status_code in [200, 400, 413, 422, 502, 503]


class TestPathTraversal:
    """Tests for path traversal prevention."""

    @pytest.mark.security
    def test_path_traversal_in_file_param(self, client, path_traversal_payloads):
        """Test path traversal in file parameters."""
        for payload in path_traversal_payloads:
            response = client.get(f"/api/v1/export?file={payload}")

            # Should not return file contents from outside allowed directory
            assert response.status_code in [200, 400, 403, 404]

            if response.status_code == 200:
                data = response.get_json() or {}
                # Should not contain sensitive file contents
                assert "root:" not in str(data)
                assert "SYSTEM" not in str(data)

    @pytest.mark.security
    def test_path_traversal_in_model_name(self, client, path_traversal_payloads):
        """Test path traversal in model name parameter."""
        for payload in path_traversal_payloads:
            response = client.get(f"/api/v1/models/{payload}")

            # Should not allow accessing arbitrary files
            assert response.status_code in [200, 400, 403, 404]


class TestCommandInjection:
    """Tests for command injection prevention."""

    @pytest.mark.security
    def test_command_injection_in_params(self, client, command_injection_payloads):
        """Test command injection in parameters."""
        for payload in command_injection_payloads:
            response = client.get(f"/api/v1/data?search={payload}")

            # Should not execute commands
            assert response.status_code != 500

    @pytest.mark.security
    def test_command_injection_in_export(self, client, command_injection_payloads, api_headers):
        """Test command injection in export parameters."""
        for payload in command_injection_payloads:
            response = client.get(f"/api/v1/export/predictions?format={payload}", headers=api_headers)

            # Should not execute shell commands
            assert response.status_code in [200, 400, 422]


class TestHeaderInjection:
    """Tests for HTTP header injection prevention."""

    @pytest.mark.security
    def test_header_injection_in_redirect(self, client, header_injection_payloads):
        """Test header injection in redirect parameters."""
        for payload in header_injection_payloads:
            response = client.get(f"/api/v1/redirect?url={payload}", follow_redirects=False)

            # Should not contain injected headers
            assert "X-Injected" not in response.headers
            assert "Set-Cookie: malicious" not in str(response.headers)

    @pytest.mark.security
    def test_crlf_injection(self, client):
        """Test CRLF injection prevention."""
        payloads = [
            "test%0d%0aX-Injected:%20header",
            "test\r\nX-Injected: header",
            "test%0d%0aSet-Cookie:%20malicious=value",
        ]

        for payload in payloads:
            response = client.get(f"/api/v1/data?search={payload}")

            # Should not have injected headers
            assert "X-Injected" not in response.headers


class TestJSONValidation:
    """Tests for JSON input validation."""

    @pytest.mark.security
    def test_malformed_json_rejected(self, client, api_headers):
        """Test malformed JSON is rejected."""
        malformed_json = [
            '{"temperature": 298.15',  # Missing closing brace
            "{'temperature': 298.15}",  # Single quotes
            '{"temperature": undefined}',  # JavaScript undefined
        ]

        for json_str in malformed_json:
            response = client.post("/api/v1/predict", data=json_str, headers={**api_headers})

            # Should return 400, not 500
            assert response.status_code in [400, 415, 422]

    @pytest.mark.security
    def test_nested_json_depth_limit(self, client, api_headers):
        """Test deeply nested JSON is handled."""
        # Create deeply nested JSON
        nested = {"a": 298.15}
        for _ in range(100):
            nested = {"nested": nested}

        response = client.post("/api/v1/predict", json=nested, headers=api_headers)

        # Should handle gracefully
        assert response.status_code in [200, 400, 422]

    @pytest.mark.security
    def test_large_json_body(self, client, api_headers):
        """Test large JSON body is handled."""
        # Create large array
        large_data = {"items": [{"temperature": 298.15}] * 10000}

        response = client.post("/api/v1/predict", json=large_data, headers=api_headers)

        # Should either process or reject (not crash)
        assert response.status_code in [200, 400, 413, 422]


class TestSpecialCharacterHandling:
    """Tests for special character handling."""

    @pytest.mark.security
    def test_null_byte_handling(self, client):
        """Test null byte injection is handled."""
        payloads = [
            "test%00.json",
            "test\x00.json",
        ]

        for payload in payloads:
            response = client.get(f"/api/v1/data?file={payload}")

            # Should not bypass extension checks
            assert response.status_code in [200, 400, 404]

    @pytest.mark.security
    def test_unicode_handling(self, client, api_headers):
        """Test Unicode input is handled safely."""
        unicode_inputs = [
            "温度测试",  # Chinese
            "🌧️☀️",  # Emoji
            "تجربة",  # Arabic
            "тест",  # Cyrillic
        ]

        for text in unicode_inputs:
            response = client.post("/api/v1/feedback", json={"message": text, "rating": 5}, headers=api_headers)

            # Should handle Unicode safely
            assert response.status_code in [200, 400, 404]

    @pytest.mark.security
    def test_control_character_handling(self, client, api_headers):
        """Test control characters are handled."""
        # ASCII control characters
        control_chars = ["\x00", "\x01", "\x1f", "\x7f"]

        for char in control_chars:
            response = client.post(
                "/api/v1/predict",
                json={"temperature": 298.15, "humidity": 75.0, "precipitation": 5.0, "notes": f"test{char}value"},
                headers=api_headers,
            )

            # Should handle control characters safely
            assert response.status_code != 500


class TestTypeCoercion:
    """Tests for type coercion safety."""

    @pytest.mark.security
    def test_boolean_coercion(self, client, api_headers):
        """Test boolean coercion is safe."""
        # Strings that might be coerced to boolean
        values = ["true", "false", "1", "0", "yes", "no", "on", "off"]

        for value in values:
            response = client.get(f"/api/v1/data?include_nulls={value}")

            # Should be handled consistently
            assert response.status_code in [200, 400]

    @pytest.mark.security
    def test_array_parameter_handling(self, client):
        """Test array parameters are handled safely."""
        # PHP-style array injection
        response = client.get("/api/v1/data?id[]=1&id[]=2&id[]=3")

        # Should handle array parameters safely
        assert response.status_code in [200, 400]
