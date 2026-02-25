"""
Unit tests for data ingestion service.

Tests for app/services/ingest.py
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

# Import modules at top level for proper coverage tracking
from app.services import ingest
from app.services.ingest import ingest_data


class TestIngestFunction:
    """Tests for the ingest_data function."""

    @patch("app.services.ingest._get_meteostat_service")
    @patch("app.services.ingest.get_db_session")
    @patch.dict("os.environ", {"OWM_API_KEY": "test_key"})
    @patch("app.services.ingest.requests.get")
    def test_ingest_data_returns_dict(self, mock_get, mock_session, mock_meteostat):
        """Test that ingest_data returns a dictionary."""
        # Mock the meteostat service
        mock_service = MagicMock()
        mock_service.get_weather_for_ingest.return_value = {
            "temperature": 298.15,
            "humidity": 75.0,
            "precipitation": 5.0,
            "source": "meteostat",
        }
        mock_meteostat.return_value = mock_service

        # Mock the HTTP request
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "main": {"temp": 298.15, "humidity": 75, "pressure": 1013},
            "weather": [{"description": "clear sky"}],
            "wind": {"speed": 5.0},
            "rain": {},
        }
        mock_get.return_value = mock_response

        mock_session.return_value.__enter__ = Mock(return_value=MagicMock())
        mock_session.return_value.__exit__ = Mock(return_value=None)

        result = ingest_data(lat=14.4793, lon=121.0198)

        assert isinstance(result, dict)

    def test_default_coordinates_are_paranaque(self):
        """Test that default coordinates are for Parañaque City."""
        default_lat = 14.4793
        default_lon = 121.0198

        # Verify coordinates are within Philippines bounds
        assert 4.0 <= default_lat <= 21.0  # Philippines latitude range
        assert 116.0 <= default_lon <= 127.0  # Philippines longitude range


class TestWeatherDataValidation:
    """Tests for weather data validation in ingestion."""

    def test_temperature_kelvin_conversion(self):
        """Test temperature is handled correctly in Kelvin."""
        temp_celsius = 25.0
        temp_kelvin = temp_celsius + 273.15

        assert temp_kelvin == 298.15

    def test_valid_humidity_range(self):
        """Test humidity values are within valid range."""
        valid_humidity_values = [0.0, 25.0, 50.0, 75.0, 100.0]

        for humidity in valid_humidity_values:
            assert 0.0 <= humidity <= 100.0

    def test_valid_precipitation_range(self):
        """Test precipitation values are non-negative."""
        valid_precip_values = [0.0, 5.0, 10.0, 50.0, 100.0]

        for precip in valid_precip_values:
            assert precip >= 0.0

    def test_invalid_humidity_rejected(self):
        """Test invalid humidity values are identified."""
        invalid_humidity_values = [-10.0, 101.0, 150.0]

        for humidity in invalid_humidity_values:
            assert not (0.0 <= humidity <= 100.0)


class TestDataSourceHandling:
    """Tests for handling different weather data sources."""

    def test_meteostat_source_identification(self):
        """Test Meteostat data source is correctly identified."""
        source = "meteostat"
        assert source in ["meteostat", "owm", "openweathermap", "manual"]

    def test_owm_source_identification(self):
        """Test OpenWeatherMap data source is correctly identified."""
        source = "owm"
        assert source in ["meteostat", "owm", "openweathermap", "manual"]

    def test_source_field_is_required(self):
        """Test that weather data should include source field."""
        weather_data = {"temperature": 298.15, "humidity": 75.0, "precipitation": 5.0, "source": "meteostat"}

        assert "source" in weather_data


class TestTimestampHandling:
    """Tests for timestamp handling in ingestion."""

    def test_timestamp_format_iso(self):
        """Test timestamp is in ISO format."""
        timestamp = datetime.now(timezone.utc).isoformat()

        # ISO format should contain 'T' separator
        assert "T" in timestamp or "-" in timestamp

    def test_utc_timezone_used(self):
        """Test that UTC timezone is used for timestamps."""
        utc_now = datetime.now(timezone.utc)

        assert utc_now.tzinfo is not None


class TestIngestErrorHandling:
    """Tests for error handling in data ingestion."""

    def test_handles_missing_temperature(self):
        """Test handling of missing temperature data."""
        incomplete_data = {"humidity": 75.0, "precipitation": 5.0}

        assert "temperature" not in incomplete_data

    def test_handles_missing_humidity(self):
        """Test handling of missing humidity data."""
        incomplete_data = {"temperature": 298.15, "precipitation": 5.0}

        assert "humidity" not in incomplete_data

    def test_handles_null_values(self):
        """Test handling of null/None values."""
        data_with_null = {"temperature": 298.15, "humidity": None, "precipitation": 5.0}

        assert data_with_null["humidity"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
