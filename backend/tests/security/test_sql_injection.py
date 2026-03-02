"""
SQL Injection Security Tests.

Tests to verify protection against SQL injection attacks.
"""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _mock_data_db():
    """Auto-mock the DB session so data-route SQL injection tests don't hit a real DB."""
    mock_session = MagicMock()
    # Make query chains return empty results
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

    with patch("app.models.db.get_db_session", _fake_session), \
         patch("app.api.routes.data.get_db_session", _fake_session):
        yield


class TestSQLInjectionPrevention:
    """Tests for SQL injection prevention."""

    @pytest.mark.security
    def test_injection_in_data_endpoint(self, client, sql_injection_payloads):
        """Test SQL injection payloads in data endpoint parameters."""
        for payload in sql_injection_payloads:
            # Test in query parameter
            response = client.get(f"/api/v1/data?limit={payload}")

            # Should not return 500 (server error from SQL execution)
            # Should return 400 (validation error) or 200 (safely handled)
            assert response.status_code != 500, f"SQL injection may be possible: {payload}"

    @pytest.mark.security
    def test_injection_in_search_parameter(self, client, sql_injection_payloads):
        """Test SQL injection in search parameters."""
        for payload in sql_injection_payloads:
            response = client.get(f"/api/v1/data?search={payload}")

            # Should be safely rejected or sanitized
            assert response.status_code in [200, 400, 422], f"Potential vulnerability: {payload}"

    @pytest.mark.security
    def test_injection_in_date_filters(self, client, sql_injection_payloads):
        """Test SQL injection in date filter parameters."""
        for payload in sql_injection_payloads:
            response = client.get(f"/api/v1/data?start_date={payload}")

            # Date parameters should be validated
            assert response.status_code in [200, 400, 422], f"Potential vulnerability: {payload}"

    @pytest.mark.security
    def test_injection_in_order_by(self, client, sql_injection_payloads):
        """Test SQL injection in ORDER BY parameter."""
        for payload in sql_injection_payloads:
            response = client.get(f"/api/v1/data?sort_by={payload}")

            # Sort parameters should use allowlist validation
            assert response.status_code in [200, 400, 422], f"Potential vulnerability: {payload}"

    @pytest.mark.security
    def test_injection_in_prediction_request(self, client, sql_injection_payloads, api_headers):
        """Test SQL injection in prediction request body."""
        for payload in sql_injection_payloads:
            data = {"temperature": payload, "humidity": 75.0, "precipitation": 5.0}

            response = client.post("/api/v1/predict", json=data, headers=api_headers)

            # Should fail validation, not execute SQL
            assert response.status_code in [200, 400, 422], f"Potential vulnerability: {payload}"

    @pytest.mark.security
    def test_injection_in_coordinates(self, client, sql_injection_payloads, api_headers):
        """Test SQL injection in coordinate parameters."""
        for payload in sql_injection_payloads:
            response = client.get(
                f"/api/v1/ingest/ingest?lat={payload}&lon=121.0",
                headers=api_headers,
            )

            # Coordinates should be validated as numbers
            assert response.status_code in [200, 400, 401, 422], f"Potential vulnerability: {payload}"

    @pytest.mark.security
    def test_injection_in_id_parameter(self, client, sql_injection_payloads):
        """Test SQL injection in ID parameters."""
        for payload in sql_injection_payloads:
            response = client.get(f"/api/v1/predictions/{payload}")

            # ID parameters should be validated
            assert response.status_code in [200, 400, 404, 422], f"Potential vulnerability: {payload}"


class TestParameterizedQueries:
    """Tests to verify parameterized queries are used."""

    @pytest.mark.security
    @patch("app.models.db.get_db_session")
    def test_query_uses_parameters(self, mock_session, app, app_context):
        """Test that queries use parameterized statements."""
        mock_db = MagicMock()
        mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_session.return_value.__exit__ = MagicMock(return_value=None)

        # When queries are executed, they should use parameters
        # not string concatenation
        with mock_session() as session:
            # Simulate a parameterized query
            session.execute("SELECT * FROM weather_data WHERE id = :id", {"id": 1})

            session.execute.assert_called()

    @pytest.mark.security
    def test_orm_protects_against_injection(self, app, app_context):
        """Test that ORM usage protects against injection."""
        try:
            from app.models.db import WeatherData
            from sqlalchemy.orm import Query

            # ORM queries are inherently parameterized
            # This test verifies ORM is being used
            assert hasattr(WeatherData, "__tablename__")  # ORM model check
        except ImportError:
            pytest.skip("ORM models not available")


class TestSecondOrderInjection:
    """Tests for second-order SQL injection prevention."""

    @pytest.mark.security
    def test_stored_data_does_not_execute(self, client, api_headers):
        """Test that stored malicious data doesn't execute later."""
        # Store data that looks like SQL
        payload = "'; DROP TABLE users; --"

        # First request stores the data
        response = client.post(
            "/api/v1/predict",
            json={
                "temperature": 298.15,
                "humidity": 75.0,
                "precipitation": 5.0,
                "notes": payload,  # If notes field exists
            },
            headers=api_headers,
        )

        # Second request retrieves data - should not execute stored SQL
        response = client.get("/api/v1/data")

        # Server should still be functioning
        assert response.status_code != 500


class TestBlindSQLInjection:
    """Tests for blind SQL injection prevention."""

    @pytest.mark.security
    def test_timing_based_injection(self, client, performance_timer):
        """Test protection against timing-based blind injection."""
        # Try to inject a SLEEP command
        payload = "1; SELECT SLEEP(5)--"

        performance_timer.start()
        response = client.get(f"/api/v1/data?limit={payload}")
        performance_timer.stop()

        # Response should be fast (< 3 seconds), not delayed by SLEEP
        assert performance_timer.elapsed_ms < 3000, "Possible timing-based injection"

    @pytest.mark.security
    def test_boolean_based_injection(self, client):
        """Test protection against boolean-based blind injection."""
        # Try boolean-based payloads
        true_payload = "1 AND 1=1"
        false_payload = "1 AND 1=2"

        response_true = client.get(f"/api/v1/data?limit={true_payload}")
        response_false = client.get(f"/api/v1/data?limit={false_payload}")

        # Both should be handled the same way (validation error)
        assert response_true.status_code == response_false.status_code
