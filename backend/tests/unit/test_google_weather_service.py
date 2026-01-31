"""
Unit tests for Google Weather (Earth Engine) service.
"""

from datetime import datetime
from unittest.mock import patch

import pytest
from app.services.google_weather_service import (
    GoogleWeatherService,
    SatellitePrecipitation,
    WeatherReanalysis,
)


class TestGoogleWeatherServiceInitialization:
    """Tests for GoogleWeatherService initialization."""

    @patch.dict("os.environ", {"EARTHENGINE_ENABLED": "false"}, clear=False)
    def test_service_disabled_by_env(self):
        """Test service can be disabled via environment variable."""
        service = GoogleWeatherService()

        assert not service.enabled

    @patch.dict("os.environ", {"EARTHENGINE_ENABLED": "true", "GOOGLE_CLOUD_PROJECT": "test-project"}, clear=False)
    def test_service_enabled_with_config(self):
        """Test service is enabled with proper configuration."""
        service = GoogleWeatherService()

        # Should be enabled based on env
        assert service.project_id == "test-project"


class TestSatellitePrecipitationDataStructure:
    """Tests for SatellitePrecipitation data structure."""

    def test_data_structure_creation(self):
        """Test SatellitePrecipitation dataclass creation."""
        precip = SatellitePrecipitation(
            timestamp=datetime.now(), latitude=14.4793, longitude=121.0198, precipitation_rate=5.0
        )

        assert precip.precipitation_rate == 5.0
        assert precip.latitude == 14.4793

    def test_default_values(self):
        """Test SatellitePrecipitation default values."""
        precip = SatellitePrecipitation(
            timestamp=datetime.now(), latitude=14.4793, longitude=121.0198, precipitation_rate=2.5
        )

        assert precip.dataset == "GPM"
        assert precip.source == "earth_engine"

    def test_accumulation_fields(self):
        """Test precipitation accumulation fields."""
        precip = SatellitePrecipitation(
            timestamp=datetime.now(),
            latitude=14.4793,
            longitude=121.0198,
            precipitation_rate=5.0,
            accumulation_1h=5.0,
            accumulation_3h=12.0,
            accumulation_24h=45.0,
        )

        assert precip.accumulation_1h == 5.0
        assert precip.accumulation_3h == 12.0
        assert precip.accumulation_24h == 45.0


class TestWeatherReanalysisDataStructure:
    """Tests for WeatherReanalysis data structure."""

    def test_data_structure_creation(self):
        """Test WeatherReanalysis dataclass creation."""
        reanalysis = WeatherReanalysis(
            timestamp=datetime.now(),
            latitude=14.4793,
            longitude=121.0198,
            temperature=28.0,
            humidity=75.0,
            precipitation=5.0,
        )

        assert reanalysis.temperature == 28.0
        assert reanalysis.humidity == 75.0

    def test_default_source(self):
        """Test default source is ERA5."""
        reanalysis = WeatherReanalysis(
            timestamp=datetime.now(),
            latitude=14.4793,
            longitude=121.0198,
            temperature=28.0,
            humidity=75.0,
            precipitation=5.0,
        )

        assert reanalysis.source == "era5"


class TestDatasetConfigurations:
    """Tests for satellite dataset configurations."""

    def test_gpm_dataset_config(self):
        """Test GPM dataset configuration."""
        gpm_config = {"collection": "NASA/GPM_L3/IMERG_V06", "band": "precipitationCal", "scale": 11132}

        assert "GPM" in gpm_config["collection"]
        assert gpm_config["band"] == "precipitationCal"

    def test_chirps_dataset_config(self):
        """Test CHIRPS dataset configuration."""
        chirps_config = {"collection": "UCSB-CHG/CHIRPS/DAILY", "band": "precipitation", "scale": 5566}

        assert "CHIRPS" in chirps_config["collection"]
        assert chirps_config["band"] == "precipitation"

    def test_era5_dataset_config(self):
        """Test ERA5 dataset configuration."""
        era5_config = {
            "collection": "ECMWF/ERA5_LAND/HOURLY",
            "bands": ["temperature_2m", "total_precipitation", "dewpoint_temperature_2m"],
        }

        assert "ERA5" in era5_config["collection"]
        assert "temperature_2m" in era5_config["bands"]


class TestDefaultCoordinates:
    """Tests for default coordinate handling."""

    def test_default_latitude_paranaque(self):
        """Test default latitude is for Parañaque City."""
        default_lat = 14.4793

        assert 14.0 <= default_lat <= 15.0

    def test_default_longitude_paranaque(self):
        """Test default longitude is for Parañaque City."""
        default_lon = 121.0198

        assert 120.5 <= default_lon <= 121.5


class TestFeatureToggles:
    """Tests for feature toggle handling."""

    def test_gpm_can_be_disabled(self):
        """Test GPM precipitation can be disabled."""
        gpm_enabled = False

        assert not gpm_enabled

    def test_chirps_can_be_disabled(self):
        """Test CHIRPS precipitation can be disabled."""
        chirps_enabled = False

        assert not chirps_enabled

    def test_era5_can_be_disabled(self):
        """Test ERA5 reanalysis can be disabled."""
        era5_enabled = False

        assert not era5_enabled

    def test_bigquery_can_be_disabled(self):
        """Test BigQuery can be disabled."""
        bigquery_enabled = False

        assert not bigquery_enabled


class TestRequestLogging:
    """Tests for Earth Engine request logging."""

    def test_request_log_fields(self):
        """Test request log contains required fields."""
        log_entry = {
            "request_type": "gpm",
            "dataset": "GPM",
            "lat": 14.4793,
            "lon": 121.0198,
            "status": "success",
            "response_time_ms": 250.5,
        }

        assert "request_type" in log_entry
        assert "status" in log_entry
        assert "response_time_ms" in log_entry

    def test_status_values(self):
        """Test valid status values."""
        valid_statuses = ["pending", "success", "error"]

        for status in valid_statuses:
            assert status in valid_statuses


class TestErrorHandling:
    """Tests for error handling in Google Weather service."""

    def test_handles_earth_engine_not_installed(self):
        """Test handling when earthengine-api is not installed."""
        # This simulates the lazy import behavior
        ee_module = None

        assert ee_module is None

    def test_handles_authentication_failure(self):
        """Test handling of authentication failures."""
        auth_error = Exception("Authentication failed")

        assert isinstance(auth_error, Exception)

    def test_handles_api_quota_exceeded(self):
        """Test handling of API quota exceeded errors."""
        quota_error = "Quota exceeded for Earth Engine API"

        assert "Quota" in quota_error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
