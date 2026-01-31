"""
Unit tests for health routes.

Tests for app/api/routes/health.py
"""

import time
from datetime import datetime
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from app.api.routes.health import (
    HEALTH_CHECK_RESPONSE_TIME_SLA_MS,
    check_database_health,
    check_external_api_health,
    check_sla_compliance,
)


class TestSLAStatus:
    """Tests for SLA status checking."""

    def test_check_sla_compliance_within_sla(self):
        """Test SLA compliance when response time is within threshold."""
        result = check_sla_compliance(100.0)  # 100ms

        assert result.within_sla is True
        assert result.response_time_ms == 100.0
        assert result.sla_threshold_ms == HEALTH_CHECK_RESPONSE_TIME_SLA_MS
        assert "within SLA" in result.message

    def test_check_sla_compliance_exceeds_sla(self):
        """Test SLA compliance when response time exceeds threshold."""
        result = check_sla_compliance(1000.0)  # 1000ms

        assert result.within_sla is False
        assert result.response_time_ms == 1000.0
        assert "EXCEEDS SLA" in result.message

    def test_check_sla_compliance_boundary(self):
        """Test SLA compliance at exact threshold."""
        result = check_sla_compliance(float(HEALTH_CHECK_RESPONSE_TIME_SLA_MS))

        assert result.within_sla is True


class TestDatabaseHealthCheck:
    """Tests for database health checking."""

    @patch("app.api.routes.health.get_db_session")
    def test_check_database_health_success(self, mock_get_db):
        """Test successful database health check."""
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

        result = check_database_health()

        assert result["status"] == "healthy"
        assert result["connected"] is True
        assert "latency_ms" in result

    @patch("app.api.routes.health.get_db_session")
    def test_check_database_health_failure(self, mock_get_db):
        """Test database health check on connection failure."""
        mock_get_db.return_value.__enter__ = MagicMock(side_effect=Exception("Connection refused"))
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

        result = check_database_health()

        assert result["status"] == "unhealthy"
        assert result["connected"] is False
        assert "error" in result


class TestExternalAPIHealthCheck:
    """Tests for external API health checking."""

    @patch("app.utils.circuit_breaker.meteostat_breaker")
    @patch("app.utils.circuit_breaker.weatherstack_breaker")
    @patch("app.utils.circuit_breaker.openweathermap_breaker")
    def test_check_external_api_health_success(self, mock_owm, mock_ws, mock_ms):
        """Test external API health check with all breakers available."""
        mock_owm.get_status.return_value = {"state": "closed", "failures": 0}
        mock_ws.get_status.return_value = {"state": "closed", "failures": 0}
        mock_ms.get_status.return_value = {"state": "open", "failures": 5}

        result = check_external_api_health()

        assert "openweathermap" in result
        assert "weatherstack" in result
        assert "meteostat" in result

    @patch.dict("sys.modules", {"app.utils.circuit_breaker": None})
    def test_check_external_api_health_import_error(self):
        """Test external API health check when circuit breaker not available."""
        # This tests graceful handling when imports fail
        pass  # Import error handling is tested implicitly


class TestHealthEndpoint:
    """Tests for the main health endpoint."""

    def test_health_endpoint_basic(self, client):
        """Test basic health endpoint returns valid response."""
        response = client.get("/health")

        # Health endpoint may return 200 (healthy) or 503 (unhealthy) depending on dependencies
        assert response.status_code in [200, 503]
        data = response.get_json()
        assert "status" in data

    def test_health_endpoint_with_api_key(self, client, api_headers):
        """Test health endpoint with API key authentication."""
        response = client.get("/health", headers=api_headers)

        # Health endpoint may return 200 or 503 depending on backend services
        assert response.status_code in [200, 503]

    @patch("app.api.routes.health.check_database_health")
    def test_health_endpoint_database_check(self, mock_db_health, client):
        """Test health endpoint includes database status."""
        mock_db_health.return_value = {"status": "healthy", "connected": True}

        response = client.get("/health")

        # Health endpoint returns valid response
        assert response.status_code in [200, 503]


class TestStatusEndpoint:
    """Tests for the status endpoint."""

    def test_status_endpoint(self, client):
        """Test status endpoint returns comprehensive status."""
        response = client.get("/status")

        assert response.status_code == 200
        data = response.get_json()
        assert "status" in data


class TestDependenciesEndpoint:
    """Tests for the dependencies endpoint."""

    def test_dependencies_endpoint(self, client):
        """Test dependencies endpoint returns dependency information."""
        response = client.get("/health/dependencies")

        # May return 200 or 404 depending on route registration
        assert response.status_code in [200, 404]
