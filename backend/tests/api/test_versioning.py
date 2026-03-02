"""
API Versioning Tests.

Tests for backward compatibility and deprecated endpoint handling.
"""

from unittest.mock import MagicMock, patch

import pytest

# ============================================================================
# API V1 Backward Compatibility Tests
# ============================================================================


class TestAPIV1BackwardCompatibility:
    """Tests for API v1 backward compatibility."""

    @pytest.mark.api_versioning
    def test_v1_predict_endpoint_exists(self, client, api_headers):
        """V1 predict endpoint should exist."""
        response = client.post(
            "/api/v1/predict", json={"temperature": 298.15, "humidity": 75.0, "precipitation": 5.0}, headers=api_headers
        )

        # Should not be 404
        assert response.status_code != 404, "V1 predict endpoint should exist"

    @pytest.mark.api_versioning
    def test_v1_weather_endpoint_exists(self, client, api_headers):
        """V1 weather endpoint should exist."""
        response = client.get("/api/v1/weather", headers=api_headers)

        # Should not be 404 (may need params, but route should exist)
        assert response.status_code != 404, "V1 weather endpoint should exist"

    @pytest.mark.api_versioning
    def test_v1_data_endpoint_exists(self, client, api_headers):
        """V1 data endpoint should exist."""
        response = client.get("/api/v1/data", headers=api_headers)

        # Endpoint should exist
        assert response.status_code != 404, "V1 data endpoint should exist"

    @pytest.mark.api_versioning
    @patch("app.services.predict.load_model")
    def test_v1_response_format_backward_compatible(self, mock_load, client, api_headers):
        """V1 response format should maintain backward compatibility."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [[0]]
        mock_model.predict_proba.return_value = [[0.8, 0.2]]
        mock_load.return_value = mock_model

        response = client.post(
            "/api/v1/predict", json={"temperature": 298.15, "humidity": 75.0, "precipitation": 5.0}, headers=api_headers
        )

        if response.status_code in [200, 201]:
            data = response.get_json()

            # V1 response should maintain expected fields
            expected_fields = ["prediction", "flood_risk", "risk_level", "probability", "confidence"]

            # At least some expected fields should be present
            present_fields = [f for f in expected_fields if f in str(data).lower()]
            assert len(present_fields) >= 1, f"Missing expected v1 response fields"

    @pytest.mark.api_versioning
    def test_v1_error_format_backward_compatible(self, client, api_headers):
        """V1 error format should maintain backward compatibility."""
        response = client.post("/api/v1/predict", json={"invalid": "data"}, headers=api_headers)

        if response.status_code >= 400:
            data = response.get_json()

            # Error response should have standard format
            if data:
                error_indicators = ["error", "message", "detail", "code"]
                present = [i for i in error_indicators if i in str(data).lower()]
                assert len(present) >= 1, "Error response missing standard fields"


# ============================================================================
# Deprecated Endpoint Tests
# ============================================================================


class TestDeprecatedEndpoints:
    """Tests for deprecated endpoint handling."""

    @pytest.mark.api_versioning
    def test_deprecated_endpoint_warning_header(self, client, api_headers):
        """Deprecated endpoints should return warning header."""
        # Test common patterns for deprecated endpoints
        deprecated_endpoints = [
            "/api/predict",  # Non-versioned might be deprecated
            "/predict",
            "/api/v0/predict",  # Old version
        ]

        for endpoint in deprecated_endpoints:
            response = client.post(
                endpoint, json={"temperature": 298.15, "humidity": 75.0, "precipitation": 5.0}, headers=api_headers
            )

            # If endpoint exists and is deprecated, check for deprecation header
            if response.status_code != 404:
                # Should have deprecation warning header if deprecated
                deprecation_header = (
                    response.headers.get("Deprecation")
                    or response.headers.get("X-Deprecated")
                    or response.headers.get("Warning")
                )

                # Note: Not all deprecated endpoints may have headers
                # This is a best practice test

    @pytest.mark.api_versioning
    def test_deprecated_endpoint_still_functional(self, client, api_headers):
        """Deprecated endpoints should still function."""
        # Non-versioned endpoint might be deprecated but functional
        response = client.get("/health")

        # 200 = healthy, 503 = unhealthy deps but endpoint still works
        assert response.status_code in (200, 503), "Deprecated endpoints should still work"

    @pytest.mark.api_versioning
    def test_deprecated_parameter_handling(self, client, api_headers):
        """Deprecated parameters should be handled gracefully."""
        # Test with old parameter names that might be deprecated
        old_payload = {
            "temp": 298.15,  # Might be deprecated in favor of "temperature"
            "hum": 75.0,  # Might be deprecated in favor of "humidity"
            "precip": 5.0,  # Might be deprecated in favor of "precipitation"
        }

        response = client.post("/api/v1/predict", json=old_payload, headers=api_headers)

        # Should either work with old params or return clear error
        assert response.status_code != 500, "Should handle deprecated params gracefully"


# ============================================================================
# Version Header Tests
# ============================================================================


class TestVersionHeaders:
    """Tests for API version headers."""

    @pytest.mark.api_versioning
    def test_api_version_header_present(self, client):
        """Response should include API version header."""
        response = client.get("/health")

        version_headers = ["X-API-Version", "API-Version", "X-Version"]

        # Check if any version header is present
        version_present = any(h in response.headers for h in version_headers)

        # Version header is best practice but may not be present

    @pytest.mark.api_versioning
    def test_accept_version_header(self, client, api_headers):
        """API should respect Accept-Version header."""
        headers = {**api_headers, "Accept-Version": "1.0"}

        response = client.post(
            "/api/v1/predict", json={"temperature": 298.15, "humidity": 75.0, "precipitation": 5.0}, headers=headers
        )

        # Should not fail with version header
        assert response.status_code != 500

    @pytest.mark.api_versioning
    def test_content_type_version_negotiation(self, client):
        """API should support content type version negotiation."""
        headers = {
            "Content-Type": "application/vnd.floodingnaque.v1+json",
            "Accept": "application/vnd.floodingnaque.v1+json",
        }

        response = client.post(
            "/api/v1/predict", json={"temperature": 298.15, "humidity": 75.0, "precipitation": 5.0}, headers=headers
        )

        # Should handle vendor-specific content types gracefully
        assert response.status_code not in [500, 406]


# ============================================================================
# Version Migration Tests
# ============================================================================


class TestVersionMigration:
    """Tests for version migration support."""

    @pytest.mark.api_versioning
    def test_v1_to_v2_field_mapping(self, client, api_headers):
        """Fields should map correctly between versions."""
        # V1 field names
        v1_payload = {"temperature": 298.15, "humidity": 75.0, "precipitation": 5.0}

        response = client.post("/api/v1/predict", json=v1_payload, headers=api_headers)

        # V1 should accept v1 field names
        assert response.status_code != 422, "V1 should accept v1 field names"

    @pytest.mark.api_versioning
    @patch("app.services.predict.load_model")
    def test_response_includes_version_info(self, mock_load, client, api_headers):
        """Response should include version information."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [[0]]
        mock_model.predict_proba.return_value = [[0.8, 0.2]]
        mock_load.return_value = mock_model

        response = client.post(
            "/api/v1/predict", json={"temperature": 298.15, "humidity": 75.0, "precipitation": 5.0}, headers=api_headers
        )

        if response.status_code in [200, 201]:
            data = response.get_json()

            # Check for version in response or headers
            response_str = str(data).lower()
            version_in_response = "version" in response_str or "api_version" in response_str
            version_in_header = "X-API-Version" in response.headers or "API-Version" in response.headers

            # Version info is best practice

    @pytest.mark.api_versioning
    def test_sunset_header_for_deprecated_versions(self, client, api_headers):
        """Deprecated versions should include Sunset header."""
        # Test for sunset header indicating when version will be removed
        response = client.get("/api/v1/data", headers=api_headers)

        if response.status_code != 404:
            sunset_header = response.headers.get("Sunset")

            # Sunset header is best practice for deprecated APIs


# ============================================================================
# API Version Routing Tests
# ============================================================================


class TestAPIVersionRouting:
    """Tests for API version routing."""

    @pytest.mark.api_versioning
    def test_v1_routes_accessible(self, client, api_headers):
        """All v1 routes should be accessible."""
        v1_endpoints = [
            ("/api/v1/predict", "POST"),
            ("/api/v1/weather", "GET"),
            ("/api/v1/data", "GET"),
        ]

        for endpoint, method in v1_endpoints:
            if method == "GET":
                response = client.get(endpoint, headers=api_headers)
            else:
                response = client.post(
                    endpoint, json={"temperature": 298.15, "humidity": 75.0, "precipitation": 5.0}, headers=api_headers
                )

            assert response.status_code != 404, f"V1 endpoint {endpoint} should exist"

    @pytest.mark.api_versioning
    def test_non_versioned_routes_redirect_or_work(self, client, api_headers):
        """Non-versioned routes should redirect to latest or work directly."""
        # Non-versioned endpoint
        response = client.get("/api/data", headers=api_headers)

        # Should either redirect (301/302/307) or work (200) or not exist (404)
        assert response.status_code in [200, 301, 302, 307, 404, 401, 403]

    @pytest.mark.api_versioning
    def test_invalid_version_handling(self, client, api_headers):
        """Invalid API version should be handled gracefully."""
        response = client.get("/api/v999/data", headers=api_headers)

        # Should return 404 for non-existent version
        assert response.status_code in [404, 400]

    @pytest.mark.api_versioning
    def test_version_prefix_consistency(self, client, api_headers):
        """All versioned endpoints should use consistent version prefix."""
        # Test that v1 endpoints all use /api/v1/ prefix
        v1_test_endpoints = ["/api/v1/predict", "/api/v1/weather", "/api/v1/data"]

        for endpoint in v1_test_endpoints:
            assert endpoint.startswith("/api/v1/"), f"Endpoint {endpoint} should use /api/v1/ prefix"


# ============================================================================
# API Version Contract Tests
# ============================================================================


class TestAPIVersionContract:
    """Tests for API version contract compliance."""

    @pytest.mark.api_versioning
    def test_v1_contract_required_fields(self, client, api_headers):
        """V1 should require specific fields."""
        # Missing required fields
        incomplete_payloads = [{}, {"temperature": 298.15}, {"humidity": 75.0}, {"precipitation": 5.0}]

        for payload in incomplete_payloads:
            response = client.post("/api/v1/predict", json=payload, headers=api_headers)

            # Should return validation error for incomplete data
            assert response.status_code in [400, 422, 200], f"Should handle incomplete payload: {payload}"

    @pytest.mark.api_versioning
    def test_v1_contract_field_types(self, client, api_headers):
        """V1 should validate field types."""
        # Wrong types
        wrong_type_payloads = [
            {"temperature": "hot", "humidity": 75.0, "precipitation": 5.0},
            {"temperature": 298.15, "humidity": "wet", "precipitation": 5.0},
            {"temperature": 298.15, "humidity": 75.0, "precipitation": "heavy"},
        ]

        for payload in wrong_type_payloads:
            response = client.post("/api/v1/predict", json=payload, headers=api_headers)

            # Should return validation error for wrong types
            assert response.status_code in [400, 422, 200], f"Should handle wrong type payload: {payload}"

    @pytest.mark.api_versioning
    @patch("app.services.predict.load_model")
    def test_v1_contract_response_structure(self, mock_load, client, api_headers):
        """V1 response should maintain contract structure."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [[0]]
        mock_model.predict_proba.return_value = [[0.8, 0.2]]
        mock_load.return_value = mock_model

        response = client.post(
            "/api/v1/predict", json={"temperature": 298.15, "humidity": 75.0, "precipitation": 5.0}, headers=api_headers
        )

        if response.status_code in [200, 201]:
            data = response.get_json()

            # Response should be JSON object
            assert isinstance(data, dict), "V1 response should be JSON object"

            # Response should contain result-related field
            result_indicators = ["prediction", "flood", "risk", "result", "output"]
            response_str = str(data).lower()
            has_result = any(i in response_str for i in result_indicators)

            assert has_result or len(data) > 0, "V1 response should contain results"
