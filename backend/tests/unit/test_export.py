"""
Unit tests for export routes.

Tests data export functionality for weather and predictions.

Auth note: @require_api_key is applied at import time, so patching the
module-level name has no effect.  Instead, each request sends the test
API key via the ``api_headers`` fixture (provided by sample_data.py).
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestExportWeather:
    """Tests for weather data export endpoint."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        with patch("app.api.routes.export.get_db_session") as mock:
            session = MagicMock()
            mock.return_value.__enter__ = Mock(return_value=session)
            mock.return_value.__exit__ = Mock(return_value=False)
            yield session

    @pytest.fixture
    def mock_weather_data(self):
        """Create mock weather data records."""
        records = []
        for i in range(3):
            record = MagicMock()
            record.id = i + 1
            record.timestamp = datetime(2025, 1, 10, 12, 0, 0)
            record.temperature = 298.15 + i
            record.humidity = 75.0
            record.precipitation = 5.0
            record.wind_speed = 10.0
            record.pressure = 1013.25
            record.latitude = 14.4793
            record.longitude = 121.0198
            record.location = "Paranaque City"
            records.append(record)
        return records

    def test_export_weather_json_format(self, client, api_headers, mock_db_session, mock_weather_data):
        """Test weather export in JSON format."""
        mock_query = MagicMock()
        mock_query.filter_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_weather_data
        mock_db_session.query.return_value = mock_query

        response = client.get("/api/export/weather?format=json", headers=api_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert "data" in data
        assert "count" in data
        assert data["format"] == "json"

    def test_export_weather_csv_format(self, client, api_headers, mock_db_session, mock_weather_data):
        """Test weather export in CSV format."""
        mock_query = MagicMock()
        mock_query.filter_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_weather_data
        mock_db_session.query.return_value = mock_query

        response = client.get("/api/export/weather?format=csv", headers=api_headers)

        assert response.status_code == 200
        assert response.content_type == "text/csv; charset=utf-8"

    def test_export_weather_invalid_format(self, client, api_headers):
        """Test weather export with invalid format returns error."""
        response = client.get("/api/export/weather?format=xml", headers=api_headers)

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "Invalid format" in data["error"]

    def test_export_weather_limit_exceeded(self, client, api_headers):
        """Test weather export with limit exceeding max."""
        response = client.get("/api/export/weather?limit=15000", headers=api_headers)

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "Limit exceeds maximum" in data["error"]

    def test_export_weather_invalid_start_date(self, client, api_headers):
        """Test weather export with invalid start date format."""
        with patch("app.api.routes.export.get_db_session") as mock_session:
            session = MagicMock()
            mock_session.return_value.__enter__ = Mock(return_value=session)
            mock_session.return_value.__exit__ = Mock(return_value=False)

            mock_query = MagicMock()
            mock_query.filter_by.return_value = mock_query
            session.query.return_value = mock_query

            response = client.get("/api/export/weather?start_date=invalid", headers=api_headers)

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_export_weather_no_data(self, client, api_headers, mock_db_session):
        """Test weather export with no data found."""
        mock_query = MagicMock()
        mock_query.filter_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db_session.query.return_value = mock_query

        response = client.get("/api/export/weather", headers=api_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 0


class TestExportPredictions:
    """Tests for predictions data export endpoint."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        with patch("app.api.routes.export.get_db_session") as mock:
            session = MagicMock()
            mock.return_value.__enter__ = Mock(return_value=session)
            mock.return_value.__exit__ = Mock(return_value=False)
            yield session

    @pytest.fixture
    def mock_predictions(self):
        """Create mock prediction records."""
        records = []
        for i in range(3):
            record = Mock()
            record.id = i + 1
            record.created_at = datetime(2025, 1, 10, 12, 0, 0)
            record.prediction = 0
            record.risk_level = 0
            record.confidence = 0.85
            record.temperature = 298.15
            record.humidity = 75.0
            record.precipitation = 5.0
            record.model_version = "1.0.0"
            record.is_deleted = False
            records.append(record)
        return records

    def test_export_predictions_json_format(self, client, api_headers, mock_db_session, mock_predictions):
        """Test predictions export in JSON format."""
        mock_query = MagicMock()
        mock_query.filter_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_predictions
        mock_db_session.query.return_value = mock_query

        response = client.get("/api/export/predictions?format=json", headers=api_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert "data" in data
        assert "count" in data

    def test_export_predictions_csv_format(self, client, api_headers, mock_db_session, mock_predictions):
        """Test predictions export in CSV format."""
        mock_query = MagicMock()
        mock_query.filter_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_predictions
        mock_db_session.query.return_value = mock_query

        response = client.get("/api/export/predictions?format=csv", headers=api_headers)

        assert response.status_code == 200
        assert response.content_type == "text/csv; charset=utf-8"

    def test_export_predictions_with_risk_level_filter(self, client, api_headers, mock_db_session, mock_predictions):
        """Test predictions export with risk level filter."""
        mock_query = MagicMock()
        mock_query.filter_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_predictions
        mock_db_session.query.return_value = mock_query

        response = client.get("/api/export/predictions?risk_level=0", headers=api_headers)

        assert response.status_code == 200

    def test_export_predictions_invalid_format(self, client, api_headers):
        """Test predictions export with invalid format returns error."""
        response = client.get("/api/export/predictions?format=xml", headers=api_headers)

        assert response.status_code == 400


class TestExportDateFilters:
    """Tests for date filtering in export endpoints."""

    def test_valid_date_range(self, client, api_headers):
        """Test export with valid date range."""
        with patch("app.api.routes.export.get_db_session") as mock_session:
            session = MagicMock()
            mock_session.return_value.__enter__ = Mock(return_value=session)
            mock_session.return_value.__exit__ = Mock(return_value=False)

            mock_query = MagicMock()
            mock_query.filter_by.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all.return_value = []
            session.query.return_value = mock_query

            response = client.get(
                "/api/export/weather?start_date=2025-01-01&end_date=2025-01-31",
                headers=api_headers,
            )

        assert response.status_code == 200

    def test_invalid_end_date(self, client, api_headers):
        """Test export with invalid end date format."""
        with patch("app.api.routes.export.get_db_session") as mock_session:
            session = MagicMock()
            mock_session.return_value.__enter__ = Mock(return_value=session)
            mock_session.return_value.__exit__ = Mock(return_value=False)

            mock_query = MagicMock()
            mock_query.filter_by.return_value = mock_query
            mock_query.filter.return_value = mock_query
            session.query.return_value = mock_query

            response = client.get(
                "/api/export/weather?start_date=2025-01-01&end_date=invalid",
                headers=api_headers,
            )

        assert response.status_code == 400


class TestExportErrorHandling:
    """Tests for error handling in export endpoints."""

    def test_export_database_error(self, client, api_headers):
        """Test export handles database errors gracefully."""
        with patch("app.api.routes.export.get_db_session") as mock_session:
            mock_session.side_effect = Exception("Database error")

            response = client.get("/api/export/weather", headers=api_headers)

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
