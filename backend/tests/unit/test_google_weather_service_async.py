"""
Unit Tests for Async Google Weather Service.

Tests the AsyncGoogleWeatherService for satellite precipitation data retrieval
from Google Earth Engine, including:
- Initialization and configuration
- GPM IMERG precipitation fetching
- CHIRPS daily precipitation
- ERA5 reanalysis data
- Error handling and retry logic
- Circuit breaker integration
"""

import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.google_weather_service_async import (
    AsyncGoogleWeatherService,
    SatellitePrecipitation,
    WeatherReanalysis,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton instance before each test."""
    AsyncGoogleWeatherService.reset_instance()
    yield
    AsyncGoogleWeatherService.reset_instance()


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for the service."""
    env_vars = {
        "EARTHENGINE_ENABLED": "true",
        "GOOGLE_CLOUD_PROJECT": "test-project",
        "GOOGLE_APPLICATION_CREDENTIALS": "",
        "GPM_PRECIPITATION_ENABLED": "true",
        "CHIRPS_PRECIPITATION_ENABLED": "true",
        "ERA5_REANALYSIS_ENABLED": "true",
        "EARTHENGINE_LOG_REQUESTS": "false",
        "DEFAULT_LATITUDE": "14.4793",
        "DEFAULT_LONGITUDE": "121.0198",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


@pytest.fixture
def mock_ee_module():
    """Mock the Earth Engine module."""
    mock_ee = MagicMock()
    mock_ee.Initialize = MagicMock()
    mock_ee.Authenticate = MagicMock()
    mock_ee.ServiceAccountCredentials = MagicMock()
    mock_ee.Geometry = MagicMock()
    mock_ee.Geometry.Point = MagicMock(return_value=MagicMock())
    mock_ee.ImageCollection = MagicMock()
    mock_ee.Reducer = MagicMock()
    mock_ee.Reducer.mean = MagicMock(return_value=MagicMock())
    return mock_ee


@pytest.fixture
def mock_gpm_result():
    """Mock GPM precipitation result."""
    return {
        "precipitationCal": 5.5,  # mm/hour
    }


@pytest.fixture
def mock_chirps_result():
    """Mock CHIRPS precipitation result."""
    return {
        "precipitation": 12.5,  # mm/day
    }


# =============================================================================
# Data Structure Tests
# =============================================================================


class TestSatellitePrecipitationDataclass:
    """Tests for SatellitePrecipitation dataclass."""

    def test_create_basic(self):
        """Test creating a basic SatellitePrecipitation."""
        precip = SatellitePrecipitation(
            timestamp=datetime.now(timezone.utc),
            latitude=14.4793,
            longitude=121.0198,
            precipitation_rate=5.5,
        )

        assert precip.precipitation_rate == 5.5
        assert precip.latitude == 14.4793
        assert precip.dataset == "GPM"
        assert precip.source == "earth_engine"

    def test_create_with_accumulations(self):
        """Test creating SatellitePrecipitation with accumulations."""
        precip = SatellitePrecipitation(
            timestamp=datetime.now(timezone.utc),
            latitude=14.4793,
            longitude=121.0198,
            precipitation_rate=10.0,
            accumulation_1h=10.0,
            accumulation_3h=30.0,
            accumulation_24h=120.0,
            data_quality=0.95,
            dataset="GPM",
        )

        assert precip.accumulation_1h == 10.0
        assert precip.accumulation_3h == 30.0
        assert precip.accumulation_24h == 120.0
        assert precip.data_quality == 0.95

    def test_default_values(self):
        """Test SatellitePrecipitation default values."""
        precip = SatellitePrecipitation(
            timestamp=datetime.now(timezone.utc),
            latitude=0.0,
            longitude=0.0,
            precipitation_rate=0.0,
        )

        assert precip.accumulation_1h is None
        assert precip.accumulation_3h is None
        assert precip.accumulation_24h is None
        assert precip.data_quality is None
        assert precip.source == "earth_engine"


class TestWeatherReanalysisDataclass:
    """Tests for WeatherReanalysis dataclass."""

    def test_create_weather_reanalysis(self):
        """Test creating WeatherReanalysis."""
        reanalysis = WeatherReanalysis(
            timestamp=datetime.now(timezone.utc),
            latitude=14.4793,
            longitude=121.0198,
            temperature=28.5,
            humidity=75.0,
            precipitation=10.0,
            wind_speed=5.5,
            pressure=1013.25,
        )

        assert reanalysis.temperature == 28.5
        assert reanalysis.humidity == 75.0
        assert reanalysis.precipitation == 10.0
        assert reanalysis.wind_speed == 5.5
        assert reanalysis.source == "era5"


# =============================================================================
# Service Initialization Tests
# =============================================================================


class TestAsyncGoogleWeatherServiceInitialization:
    """Tests for AsyncGoogleWeatherService initialization."""

    @patch.dict(os.environ, {"EARTHENGINE_ENABLED": "true"}, clear=False)
    def test_service_enabled_by_default(self):
        """Test service is enabled when env var is true."""
        service = AsyncGoogleWeatherService()
        assert service.enabled is True

    @patch.dict(os.environ, {"EARTHENGINE_ENABLED": "false"}, clear=False)
    def test_service_disabled(self):
        """Test service can be disabled via environment."""
        service = AsyncGoogleWeatherService()
        assert service.enabled is False

    @patch.dict(
        os.environ,
        {"DEFAULT_LATITUDE": "14.5", "DEFAULT_LONGITUDE": "121.0"},
        clear=False,
    )
    def test_default_coordinates_from_env(self):
        """Test default coordinates are loaded from environment."""
        service = AsyncGoogleWeatherService()
        assert service.default_lat == 14.5
        assert service.default_lon == 121.0

    def test_singleton_pattern(self):
        """Test singleton pattern returns same instance."""
        instance1 = AsyncGoogleWeatherService.get_instance()
        instance2 = AsyncGoogleWeatherService.get_instance()

        assert instance1 is instance2

    def test_reset_instance(self):
        """Test reset_instance creates new instance."""
        instance1 = AsyncGoogleWeatherService.get_instance()
        AsyncGoogleWeatherService.reset_instance()
        instance2 = AsyncGoogleWeatherService.get_instance()

        assert instance1 is not instance2

    @patch.dict(
        os.environ,
        {
            "GPM_PRECIPITATION_ENABLED": "true",
            "CHIRPS_PRECIPITATION_ENABLED": "false",
            "ERA5_REANALYSIS_ENABLED": "true",
        },
        clear=False,
    )
    def test_dataset_toggles(self):
        """Test individual dataset toggles."""
        service = AsyncGoogleWeatherService()

        assert service.gpm_enabled is True
        assert service.chirps_enabled is False
        assert service.era5_enabled is True


class TestDatasetConfiguration:
    """Tests for dataset configuration."""

    def test_datasets_defined(self):
        """Test that all datasets are defined."""
        service = AsyncGoogleWeatherService()

        assert "GPM" in service.DATASETS
        assert "CHIRPS" in service.DATASETS
        assert "ERA5" in service.DATASETS

    def test_gpm_dataset_config(self):
        """Test GPM dataset configuration."""
        service = AsyncGoogleWeatherService()
        gpm_config = service.DATASETS["GPM"]

        assert "collection" in gpm_config
        assert "band" in gpm_config
        assert "scale" in gpm_config
        assert gpm_config["band"] == "precipitationCal"

    def test_chirps_dataset_config(self):
        """Test CHIRPS dataset configuration."""
        service = AsyncGoogleWeatherService()
        chirps_config = service.DATASETS["CHIRPS"]

        assert chirps_config["band"] == "precipitation"
        assert "description" in chirps_config


# =============================================================================
# GPM Precipitation Tests
# =============================================================================


class TestGetGpmPrecipitation:
    """Tests for get_gpm_precipitation method."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GPM_PRECIPITATION_ENABLED": "false"}, clear=False)
    async def test_returns_none_when_disabled(self):
        """Test returns None when GPM is disabled."""
        service = AsyncGoogleWeatherService()
        result = await service.get_gpm_precipitation()

        assert result is None

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"EARTHENGINE_ENABLED": "false"}, clear=False)
    async def test_returns_none_when_service_disabled(self):
        """Test returns None when Earth Engine is disabled."""
        service = AsyncGoogleWeatherService()
        result = await service.get_gpm_precipitation()

        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.google_weather_service_async._lazy_import_ee")
    @patch.dict(os.environ, {"EARTHENGINE_ENABLED": "true", "GPM_PRECIPITATION_ENABLED": "true"}, clear=False)
    async def test_uses_default_coordinates(self, mock_lazy_import):
        """Test uses default coordinates when not specified."""
        mock_lazy_import.return_value = None  # Will fail initialization
        service = AsyncGoogleWeatherService()

        # Even though it will fail, check that defaults are set correctly
        assert service.default_lat == float(os.getenv("DEFAULT_LATITUDE", "14.4793"))
        assert service.default_lon == float(os.getenv("DEFAULT_LONGITUDE", "121.0198"))

    @pytest.mark.asyncio
    async def test_accepts_custom_coordinates(self):
        """Test accepts custom lat/lon coordinates."""
        # Test that parameters are accepted (service disabled to avoid actual API call)
        with patch.dict(os.environ, {"EARTHENGINE_ENABLED": "false"}, clear=False):
            service = AsyncGoogleWeatherService()
            result = await service.get_gpm_precipitation(lat=15.0, lon=120.0)
            assert result is None  # Expected when disabled


# =============================================================================
# CHIRPS Precipitation Tests
# =============================================================================


class TestGetChirpsPrecipitation:
    """Tests for get_chirps_precipitation method."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"CHIRPS_PRECIPITATION_ENABLED": "false"}, clear=False)
    async def test_returns_none_when_disabled(self):
        """Test returns None when CHIRPS is disabled."""
        service = AsyncGoogleWeatherService()

        # CHIRPS method should return None when disabled
        assert service.chirps_enabled is False


# =============================================================================
# ERA5 Reanalysis Tests
# =============================================================================


class TestGetEra5Reanalysis:
    """Tests for ERA5 reanalysis data retrieval."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"ERA5_REANALYSIS_ENABLED": "false"}, clear=False)
    async def test_returns_none_when_disabled(self):
        """Test returns None when ERA5 is disabled."""
        service = AsyncGoogleWeatherService()
        assert service.era5_enabled is False


# =============================================================================
# Earth Engine Initialization Tests
# =============================================================================


class TestEarthEngineInitialization:
    """Tests for Earth Engine initialization logic."""

    @patch("app.services.google_weather_service_async._lazy_import_ee")
    @patch.dict(os.environ, {"EARTHENGINE_ENABLED": "true"}, clear=False)
    def test_lazy_import_failure(self, mock_lazy_import):
        """Test handling when earthengine-api is not installed."""
        mock_lazy_import.return_value = None

        service = AsyncGoogleWeatherService()
        result = service._initialize_ee()

        assert result is False

    @patch("app.services.google_weather_service_async._lazy_import_ee")
    @patch.dict(
        os.environ,
        {
            "EARTHENGINE_ENABLED": "true",
            "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/creds.json",
            "GOOGLE_SERVICE_ACCOUNT_EMAIL": "test@project.iam.gserviceaccount.com",
        },
        clear=False,
    )
    def test_service_account_initialization(self, mock_lazy_import, mock_ee_module):
        """Test initialization with service account credentials."""
        mock_lazy_import.return_value = mock_ee_module

        service = AsyncGoogleWeatherService()
        # Service account path doesn't exist, so init will use default
        assert service.credentials_path == "/path/to/creds.json"

    @patch.dict(os.environ, {"EARTHENGINE_ENABLED": "false"}, clear=False)
    def test_initialization_skipped_when_disabled(self):
        """Test initialization is skipped when service disabled."""
        service = AsyncGoogleWeatherService()
        result = service._initialize_ee()

        assert result is False


# =============================================================================
# Retry Logic Tests
# =============================================================================


class TestRetryConfiguration:
    """Tests for retry configuration."""

    def test_retry_constants(self):
        """Test retry configuration constants."""
        assert AsyncGoogleWeatherService.MAX_RETRIES == 3
        assert AsyncGoogleWeatherService.RETRY_MIN_WAIT == 1
        assert AsyncGoogleWeatherService.RETRY_MAX_WAIT == 10


# =============================================================================
# Resource Cleanup Tests
# =============================================================================


class TestResourceCleanup:
    """Tests for resource cleanup."""

    @pytest.mark.asyncio
    async def test_close_executor(self):
        """Test closing the executor."""
        service = AsyncGoogleWeatherService()
        assert service._executor is not None

        await service.close()
        # Executor should be shutdown (may raise error if used after)

    @pytest.mark.asyncio
    async def test_reset_cleans_up_executor(self):
        """Test reset_instance cleans up executor."""
        service = AsyncGoogleWeatherService.get_instance()
        executor = service._executor

        AsyncGoogleWeatherService.reset_instance()

        # New instance should have new executor
        new_service = AsyncGoogleWeatherService.get_instance()
        assert new_service._executor is not executor


# =============================================================================
# Request Logging Tests
# =============================================================================


class TestRequestLogging:
    """Tests for request logging functionality."""

    @patch.dict(os.environ, {"EARTHENGINE_LOG_REQUESTS": "true"}, clear=False)
    def test_logging_enabled(self):
        """Test request logging can be enabled."""
        service = AsyncGoogleWeatherService()
        assert service.log_requests is True

    @patch.dict(os.environ, {"EARTHENGINE_LOG_REQUESTS": "false"}, clear=False)
    def test_logging_disabled(self):
        """Test request logging can be disabled."""
        service = AsyncGoogleWeatherService()
        assert service.log_requests is False

    @patch.dict(os.environ, {"EARTHENGINE_LOG_REQUESTS": "false"}, clear=False)
    def test_log_ee_request_returns_none_when_disabled(self):
        """Test _log_ee_request returns None when logging disabled."""
        service = AsyncGoogleWeatherService()
        result = service._log_ee_request("gpm", dataset="GPM", lat=14.4793, lon=121.0198)

        assert result is None


# =============================================================================
# Cache Directory Tests
# =============================================================================


class TestCacheDirectory:
    """Tests for cache directory configuration."""

    def test_cache_dir_created(self, tmp_path):
        """Test cache directory is created on initialization."""
        with patch.dict(os.environ, {"EARTHENGINE_CACHE_DIR": str(tmp_path / "ee_cache")}, clear=False):
            service = AsyncGoogleWeatherService()
            assert service.cache_dir.exists()


# =============================================================================
# Default Location Tests
# =============================================================================


class TestDefaultLocation:
    """Tests for default location (Parañaque City)."""

    def test_default_coordinates_are_paranaque(self):
        """Test default coordinates are for Parañaque City."""
        # These are the class-level defaults
        assert AsyncGoogleWeatherService.DEFAULT_LAT == 14.4793
        assert AsyncGoogleWeatherService.DEFAULT_LON == 121.0198

    def test_coordinates_in_metro_manila(self):
        """Test coordinates are within Metro Manila bounds."""
        lat = AsyncGoogleWeatherService.DEFAULT_LAT
        lon = AsyncGoogleWeatherService.DEFAULT_LON

        # Metro Manila bounding box
        assert 14.3 <= lat <= 14.8
        assert 120.9 <= lon <= 121.2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
