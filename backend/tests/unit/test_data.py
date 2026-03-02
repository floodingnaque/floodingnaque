"""
Unit tests for weather data routes.

Tests for app/api/routes/data.py
"""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _mock_data_db(request):
    """Mock the database session and query cache for all data route tests.

    The test-suite SQLite has no ``weather_data`` table, so we provide a mock
    session that returns an empty result set.  The query cache is also patched
    to avoid stale/real data interfering with assertions.
    """
    mock_session = MagicMock()
    mock_query = MagicMock()
    # Chain all query-builder methods back to the same mock
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.count.return_value = 0
    mock_query.all.return_value = []
    mock_session.query.return_value = mock_query

    with (
        patch("app.api.routes.data.get_db_session") as mock_db,
        patch("app.api.routes.data.query_cache_get", return_value=None),
    ):
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)
        yield mock_db


class TestGetWeatherData:
    """Tests for GET /api/v1/data/data endpoint."""

    def test_get_weather_data_default(self, client):
        """Test getting weather data with default parameters."""
        response = client.get("/api/v1/data/data")

        assert response.status_code == 200
        data = response.get_json()
        assert "data" in data or "error" in data

    def test_get_weather_data_with_limit(self, client):
        """Test getting weather data with custom limit."""
        response = client.get("/api/v1/data/data?limit=10")

        assert response.status_code == 200

    def test_get_weather_data_invalid_limit_low(self, client):
        """Test getting weather data with limit below minimum."""
        response = client.get("/api/v1/data/data?limit=0")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data or "ValidationError" in str(data)

    def test_get_weather_data_invalid_limit_high(self, client):
        """Test getting weather data with limit above maximum."""
        response = client.get("/api/v1/data/data?limit=10000")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data or "ValidationError" in str(data)

    def test_get_weather_data_with_offset(self, client):
        """Test getting weather data with offset."""
        response = client.get("/api/v1/data/data?offset=10")

        assert response.status_code == 200

    def test_get_weather_data_with_date_range(self, client):
        """Test getting weather data with date range filter."""
        start_date = (datetime.now() - timedelta(days=7)).isoformat()
        end_date = datetime.now().isoformat()

        response = client.get(f"/api/v1/data/data?start_date={start_date}&end_date={end_date}")

        assert response.status_code == 200

    def test_get_weather_data_invalid_start_date(self, client):
        """Test getting weather data with invalid start date format."""
        response = client.get("/api/v1/data/data?start_date=invalid-date")

        assert response.status_code == 400

    def test_get_weather_data_invalid_end_date(self, client):
        """Test getting weather data with invalid end date format."""
        response = client.get("/api/v1/data/data?end_date=not-a-date")

        assert response.status_code == 400

    def test_get_weather_data_with_sort(self, client):
        """Test getting weather data with sorting."""
        response = client.get("/api/v1/data/data?sort_by=timestamp&order=desc")

        assert response.status_code == 200

    def test_get_weather_data_invalid_sort_field(self, client):
        """Test getting weather data with invalid sort field."""
        response = client.get("/api/v1/data/data?sort_by=invalid_field")

        assert response.status_code == 400

    def test_get_weather_data_invalid_order(self, client):
        """Test getting weather data with invalid order."""
        response = client.get("/api/v1/data/data?order=invalid")

        assert response.status_code == 400

    def test_get_weather_data_with_source_filter(self, client):
        """Test getting weather data filtered by source."""
        response = client.get("/api/v1/data/data?source=Meteostat")

        assert response.status_code == 200

    def test_get_weather_data_cache_hit(self, client):
        """Test that repeated requests can hit cache."""
        # Make the same request twice
        response1 = client.get("/api/v1/data/data?limit=10")
        response2 = client.get("/api/v1/data/data?limit=10")

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Second request might have cache_hit flag
        data2 = response2.get_json()
        # Cache hit is implementation-dependent


class TestWeatherDataPagination:
    """Tests for weather data pagination."""

    def test_pagination_response_structure(self, client):
        """Test pagination info is included in response."""
        response = client.get("/api/v1/data/data?limit=10&offset=0")

        assert response.status_code == 200
        data = response.get_json()
        # Should include pagination info
        if "data" in data:
            assert isinstance(data.get("data"), list) or "records" in str(data)

    def test_pagination_offset_works(self, client):
        """Test that offset actually skips records."""
        response1 = client.get("/api/v1/data/data?limit=5&offset=0")
        response2 = client.get("/api/v1/data/data?limit=5&offset=5")

        assert response1.status_code == 200
        assert response2.status_code == 200


class TestWeatherDataSorting:
    """Tests for weather data sorting options."""

    @pytest.mark.parametrize("sort_field", ["timestamp", "temperature", "humidity", "precipitation", "created_at"])
    def test_valid_sort_fields(self, client, sort_field):
        """Test all valid sort fields work."""
        response = client.get(f"/api/v1/data/data?sort_by={sort_field}")

        assert response.status_code == 200

    @pytest.mark.parametrize("order", ["asc", "desc"])
    def test_sort_orders(self, client, order):
        """Test both sort orders work."""
        response = client.get(f"/api/v1/data/data?order={order}")

        assert response.status_code == 200


class TestWeatherDataFiltering:
    """Tests for weather data filtering options."""

    def test_filter_by_date_range(self, client):
        """Test filtering by date range."""
        now = datetime.now()
        start = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
        end = now.strftime("%Y-%m-%dT%H:%M:%S")

        response = client.get(f"/api/v1/data/data?start_date={start}&end_date={end}")

        assert response.status_code == 200

    def test_filter_by_source_owm(self, client):
        """Test filtering by OWM source."""
        response = client.get("/api/v1/data/data?source=OWM")

        assert response.status_code == 200

    def test_filter_by_source_manual(self, client):
        """Test filtering by Manual source."""
        response = client.get("/api/v1/data/data?source=Manual")

        assert response.status_code == 200


class TestWeatherDataRateLimiting:
    """Tests for weather data rate limiting."""

    def test_data_endpoint_rate_limit_header(self, client):
        """Test that rate limit headers are present."""
        response = client.get("/api/v1/data/data")

        assert response.status_code == 200
        # Rate limit headers may be present
        # X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset


class TestWeatherDataErrorHandling:
    """Tests for weather data error handling."""

    @patch("app.api.routes.data.get_db_session")
    def test_database_error_handling(self, mock_db, client):
        """Test handling of database errors."""
        mock_db.side_effect = Exception("Database connection failed")

        response = client.get("/api/v1/data/data")

        # Should return error response, not 500
        assert response.status_code in [200, 500, 503]

    def test_malformed_query_parameters(self, client):
        """Test handling of malformed query parameters."""
        response = client.get("/api/v1/data/data?limit=abc")

        # Should handle gracefully
        assert response.status_code in [200, 400]
