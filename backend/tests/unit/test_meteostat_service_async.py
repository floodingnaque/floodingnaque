"""
Unit Tests for Async Meteostat Service.

Tests the AsyncMeteostatService for historical weather data retrieval
from weather stations, including:
- Initialization and configuration
- Finding nearby weather stations
- Fetching hourly and daily data
- Error handling and retry logic
- Circuit breaker integration
- Data transformation and validation
"""

import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from app.services.meteostat_service_async import (
    AsyncMeteostatService,
    WeatherObservation,
)
from app.utils.resilience.circuit_breaker import CircuitOpenError

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton instance before each test."""
    AsyncMeteostatService.reset_instance()
    yield
    AsyncMeteostatService.reset_instance()


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for the service."""
    env_vars = {
        "METEOSTAT_ENABLED": "true",
        "METEOSTAT_CACHE_MAX_AGE_DAYS": "7",
        "METEOSTAT_STATION_ID": "",
        "METEOSTAT_AS_FALLBACK": "true",
        "DEFAULT_LATITUDE": "14.4793",
        "DEFAULT_LONGITUDE": "121.0198",
        "METEOSTAT_EXECUTOR_WORKERS": "4",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


@pytest.fixture
def mock_stations_df():
    """Create a mock stations DataFrame."""
    return pd.DataFrame(
        {
            "name": ["Station A", "Station B", "Station C"],
            "country": ["PH", "PH", "PH"],
            "region": ["NCR", "NCR", "NCR"],
            "latitude": [14.48, 14.49, 14.50],
            "longitude": [121.01, 121.02, 121.03],
            "elevation": [10, 15, 20],
            "timezone": ["Asia/Manila", "Asia/Manila", "Asia/Manila"],
        },
        index=["98430", "98431", "98432"],
    )


@pytest.fixture
def mock_hourly_df():
    """Create a mock hourly weather DataFrame."""
    now = datetime.now(timezone.utc)
    dates = pd.date_range(end=now, periods=24, freq="h")
    return pd.DataFrame(
        {
            "temp": [28.5, 28.0, 27.5, 27.0] * 6,
            "rhum": [75.0, 78.0, 80.0, 82.0] * 6,
            "prcp": [0.0, 0.0, 2.5, 5.0] * 6,
            "wspd": [5.0, 4.5, 4.0, 3.5] * 6,
            "pres": [1010, 1011, 1012, 1013] * 6,
        },
        index=dates,
    )


@pytest.fixture
def mock_daily_df():
    """Create a mock daily weather DataFrame."""
    now = datetime.now(timezone.utc)
    dates = pd.date_range(end=now, periods=7, freq="D")
    return pd.DataFrame(
        {
            "tavg": [28.5, 28.0, 27.5, 29.0, 28.5, 27.0, 28.0],
            "tmin": [24.0, 23.5, 23.0, 24.5, 24.0, 23.0, 23.5],
            "tmax": [33.0, 32.5, 32.0, 33.5, 33.0, 31.0, 32.5],
            "prcp": [0.0, 5.0, 10.0, 0.0, 15.0, 20.0, 5.0],
            "snow": [0.0] * 7,
            "wdir": [180, 190, 200, 170, 180, 190, 185],
            "wspd": [5.0, 4.5, 5.5, 4.0, 6.0, 5.0, 4.5],
            "wpgt": [10.0, 9.0, 11.0, 8.0, 12.0, 10.0, 9.5],
            "pres": [1010, 1011, 1009, 1012, 1008, 1010, 1011],
        },
        index=dates,
    )


# =============================================================================
# Data Structure Tests
# =============================================================================


class TestWeatherObservationDataclass:
    """Tests for WeatherObservation dataclass."""

    def test_create_basic(self):
        """Test creating a basic WeatherObservation."""
        obs = WeatherObservation(
            timestamp=datetime.now(timezone.utc),
            temperature=28.5,
            humidity=75.0,
            precipitation=5.0,
        )

        assert obs.temperature == 28.5
        assert obs.humidity == 75.0
        assert obs.precipitation == 5.0
        assert obs.source == "meteostat"

    def test_create_with_all_fields(self):
        """Test creating WeatherObservation with all fields."""
        obs = WeatherObservation(
            timestamp=datetime.now(timezone.utc),
            temperature=28.5,
            humidity=75.0,
            precipitation=5.0,
            wind_speed=10.0,
            pressure=1013.25,
            station_id="98430",
            source="meteostat",
        )

        assert obs.wind_speed == 10.0
        assert obs.pressure == 1013.25
        assert obs.station_id == "98430"

    def test_default_values(self):
        """Test WeatherObservation default values."""
        obs = WeatherObservation(timestamp=datetime.now(timezone.utc))

        assert obs.temperature is None
        assert obs.humidity is None
        assert obs.precipitation is None
        assert obs.wind_speed is None
        assert obs.pressure is None
        assert obs.station_id is None
        assert obs.source == "meteostat"


# =============================================================================
# Service Initialization Tests
# =============================================================================


class TestAsyncMeteostatServiceInitialization:
    """Tests for AsyncMeteostatService initialization."""

    @patch.dict(os.environ, {"METEOSTAT_ENABLED": "true"}, clear=False)
    def test_service_enabled(self):
        """Test service is enabled when env var is true."""
        service = AsyncMeteostatService()
        assert service.enabled is True

    @patch.dict(os.environ, {"METEOSTAT_ENABLED": "false"}, clear=False)
    def test_service_disabled(self):
        """Test service can be disabled via environment."""
        service = AsyncMeteostatService()
        assert service.enabled is False

    @patch.dict(
        os.environ,
        {"DEFAULT_LATITUDE": "14.5", "DEFAULT_LONGITUDE": "121.0"},
        clear=False,
    )
    def test_default_coordinates_from_env(self):
        """Test default coordinates are loaded from environment."""
        service = AsyncMeteostatService()
        assert service.default_lat == 14.5
        assert service.default_lon == 121.0

    def test_singleton_pattern(self):
        """Test singleton pattern returns same instance."""
        instance1 = AsyncMeteostatService.get_instance()
        instance2 = AsyncMeteostatService.get_instance()

        assert instance1 is instance2

    def test_reset_instance(self):
        """Test reset_instance creates new instance."""
        instance1 = AsyncMeteostatService.get_instance()
        AsyncMeteostatService.reset_instance()
        instance2 = AsyncMeteostatService.get_instance()

        assert instance1 is not instance2

    @patch.dict(os.environ, {"METEOSTAT_CACHE_MAX_AGE_DAYS": "14"}, clear=False)
    def test_cache_max_age_config(self):
        """Test cache max age configuration."""
        service = AsyncMeteostatService()
        assert service.cache_max_age_days == 14

    @patch.dict(os.environ, {"METEOSTAT_AS_FALLBACK": "false"}, clear=False)
    def test_fallback_config(self):
        """Test fallback configuration."""
        service = AsyncMeteostatService()
        assert service.as_fallback is False

    @patch.dict(os.environ, {"METEOSTAT_EXECUTOR_WORKERS": "8"}, clear=False)
    def test_executor_workers_config(self):
        """Test executor workers configuration."""
        service = AsyncMeteostatService()
        assert service._executor._max_workers == 8


# =============================================================================
# Find Nearby Stations Tests
# =============================================================================


class TestFindNearbyStations:
    """Tests for find_nearby_stations method."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"METEOSTAT_ENABLED": "false"}, clear=False)
    async def test_returns_empty_when_disabled(self):
        """Test returns empty list when service is disabled."""
        service = AsyncMeteostatService()
        result = await service.find_nearby_stations()

        assert result == []

    @pytest.mark.asyncio
    @patch("app.services.meteostat_service_async.Stations")
    @patch.dict(os.environ, {"METEOSTAT_ENABLED": "true"}, clear=False)
    async def test_returns_station_list(self, mock_stations_class, mock_stations_df):
        """Test returns list of nearby stations."""
        # Setup mock
        mock_stations_instance = MagicMock()
        mock_stations_instance.nearby.return_value = mock_stations_instance
        mock_stations_instance.fetch.return_value = mock_stations_df
        mock_stations_class.return_value = mock_stations_instance

        service = AsyncMeteostatService()
        result = await service.find_nearby_stations(lat=14.4793, lon=121.0198, limit=3)

        assert len(result) == 3
        assert result[0]["name"] == "Station A"
        assert result[0]["country"] == "PH"

    @pytest.mark.asyncio
    @patch("app.services.meteostat_service_async.Stations")
    @patch.dict(os.environ, {"METEOSTAT_ENABLED": "true"}, clear=False)
    async def test_uses_default_coordinates(self, mock_stations_class):
        """Test uses default coordinates when not specified."""
        mock_stations_instance = MagicMock()
        mock_stations_instance.nearby.return_value = mock_stations_instance
        mock_stations_instance.fetch.return_value = pd.DataFrame()
        mock_stations_class.return_value = mock_stations_instance

        service = AsyncMeteostatService()
        await service.find_nearby_stations()

        mock_stations_instance.nearby.assert_called_once_with(service.default_lat, service.default_lon)


# =============================================================================
# Get Hourly Data Tests
# =============================================================================


class TestGetHourlyData:
    """Tests for get_hourly_data method."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"METEOSTAT_ENABLED": "false"}, clear=False)
    async def test_returns_empty_when_disabled(self):
        """Test returns empty list when service is disabled."""
        service = AsyncMeteostatService()
        result = await service.get_hourly_data()

        assert result == []

    @pytest.mark.asyncio
    @patch("app.services.meteostat_service_async.Hourly")
    @patch("app.services.meteostat_service_async.Point")
    @patch.dict(os.environ, {"METEOSTAT_ENABLED": "true"}, clear=False)
    async def test_returns_weather_observations(self, mock_point, mock_hourly, mock_hourly_df):
        """Test returns list of WeatherObservation objects."""
        # Setup mocks
        mock_point.return_value = MagicMock()
        mock_hourly_instance = MagicMock()
        mock_hourly_instance.fetch.return_value = mock_hourly_df
        mock_hourly.return_value = mock_hourly_instance

        service = AsyncMeteostatService()
        result = await service.get_hourly_data()

        assert len(result) == 24
        assert result[0].temperature == 28.5
        assert result[0].humidity == 75.0
        assert result[0].source == "meteostat"

    @pytest.mark.asyncio
    @patch("app.services.meteostat_service_async.Hourly")
    @patch("app.services.meteostat_service_async.Point")
    @patch.dict(os.environ, {"METEOSTAT_ENABLED": "true"}, clear=False)
    async def test_handles_empty_data(self, mock_point, mock_hourly):
        """Test handles empty DataFrame gracefully."""
        mock_point.return_value = MagicMock()
        mock_hourly_instance = MagicMock()
        mock_hourly_instance.fetch.return_value = pd.DataFrame()
        mock_hourly.return_value = mock_hourly_instance

        service = AsyncMeteostatService()
        result = await service.get_hourly_data()

        assert result == []

    @pytest.mark.asyncio
    @patch("app.services.meteostat_service_async.Hourly")
    @patch("app.services.meteostat_service_async.Point")
    @patch.dict(os.environ, {"METEOSTAT_ENABLED": "true"}, clear=False)
    async def test_uses_custom_date_range(self, mock_point, mock_hourly):
        """Test uses custom date range when specified."""
        mock_point.return_value = MagicMock()
        mock_hourly_instance = MagicMock()
        mock_hourly_instance.fetch.return_value = pd.DataFrame()
        mock_hourly.return_value = mock_hourly_instance

        service = AsyncMeteostatService()
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=3)

        await service.get_hourly_data(start=start, end=end)

        mock_hourly.assert_called_once()


# =============================================================================
# Get Daily Data Tests
# =============================================================================


class TestGetDailyData:
    """Tests for get_daily_data method."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"METEOSTAT_ENABLED": "false"}, clear=False)
    async def test_returns_empty_when_disabled(self):
        """Test returns empty list when service is disabled."""
        service = AsyncMeteostatService()
        result = await service.get_daily_data()

        assert result == []

    @pytest.mark.asyncio
    @patch("app.services.meteostat_service_async.Daily")
    @patch("app.services.meteostat_service_async.Point")
    @patch.dict(os.environ, {"METEOSTAT_ENABLED": "true"}, clear=False)
    async def test_returns_daily_data(self, mock_point, mock_daily, mock_daily_df):
        """Test returns list of daily weather data."""
        mock_point.return_value = MagicMock()
        mock_daily_instance = MagicMock()
        mock_daily_instance.fetch.return_value = mock_daily_df
        mock_daily.return_value = mock_daily_instance

        service = AsyncMeteostatService()
        result = await service.get_daily_data()

        assert len(result) == 7
        assert result[0]["tavg"] == 28.5
        assert result[0]["source"] == "meteostat"

    @pytest.mark.asyncio
    @patch("app.services.meteostat_service_async.Daily")
    @patch("app.services.meteostat_service_async.Point")
    @patch.dict(os.environ, {"METEOSTAT_ENABLED": "true"}, clear=False)
    async def test_handles_empty_daily_data(self, mock_point, mock_daily):
        """Test handles empty daily DataFrame gracefully."""
        mock_point.return_value = MagicMock()
        mock_daily_instance = MagicMock()
        mock_daily_instance.fetch.return_value = pd.DataFrame()
        mock_daily.return_value = mock_daily_instance

        service = AsyncMeteostatService()
        result = await service.get_daily_data()

        assert result == []


# =============================================================================
# Get Latest Observation Tests
# =============================================================================


class TestGetLatestObservation:
    """Tests for get_latest_observation method."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"METEOSTAT_ENABLED": "false"}, clear=False)
    async def test_returns_none_when_disabled(self):
        """Test returns None when service is disabled."""
        service = AsyncMeteostatService()
        result = await service.get_latest_observation()

        assert result is None


# =============================================================================
# Retry Configuration Tests
# =============================================================================


class TestRetryConfiguration:
    """Tests for retry configuration."""

    def test_retry_constants(self):
        """Test retry configuration constants."""
        assert AsyncMeteostatService.MAX_RETRIES == 3
        assert AsyncMeteostatService.RETRY_MIN_WAIT == 1
        assert AsyncMeteostatService.RETRY_MAX_WAIT == 10


# =============================================================================
# Circuit Breaker Tests
# =============================================================================


class TestCircuitBreakerIntegration:
    """Tests for circuit breaker integration."""

    @pytest.mark.asyncio
    @patch("app.services.meteostat_service_async.Stations")
    @patch.dict(os.environ, {"METEOSTAT_ENABLED": "true"}, clear=False)
    async def test_handles_circuit_open_error(self, mock_stations_class):
        """Test handles CircuitOpenError gracefully."""
        mock_stations_instance = MagicMock()
        mock_stations_instance.nearby.side_effect = CircuitOpenError("Circuit is open")
        mock_stations_class.return_value = mock_stations_instance

        service = AsyncMeteostatService()
        result = await service.find_nearby_stations()

        assert result == []


# =============================================================================
# Resource Cleanup Tests
# =============================================================================


class TestResourceCleanup:
    """Tests for resource cleanup."""

    @pytest.mark.asyncio
    async def test_close_executor(self):
        """Test closing the executor."""
        service = AsyncMeteostatService()
        assert service._executor is not None

        await service.close()
        # Executor should be shutdown

    @pytest.mark.asyncio
    async def test_reset_cleans_up_executor(self):
        """Test reset_instance cleans up executor."""
        service = AsyncMeteostatService.get_instance()
        executor = service._executor

        AsyncMeteostatService.reset_instance()

        new_service = AsyncMeteostatService.get_instance()
        assert new_service._executor is not executor


# =============================================================================
# Safe Float Conversion Tests
# =============================================================================


class TestSafeFloatConversion:
    """Tests for _safe_float helper method."""

    @patch.dict(os.environ, {"METEOSTAT_ENABLED": "true"}, clear=False)
    def test_converts_valid_float(self):
        """Test converting valid float value."""
        service = AsyncMeteostatService()
        result = service._safe_float(28.5)
        assert result == 28.5

    @patch.dict(os.environ, {"METEOSTAT_ENABLED": "true"}, clear=False)
    def test_returns_none_for_none(self):
        """Test returns None for None input."""
        service = AsyncMeteostatService()
        result = service._safe_float(None)
        assert result is None

    @patch.dict(os.environ, {"METEOSTAT_ENABLED": "true"}, clear=False)
    def test_returns_default_for_none(self):
        """Test returns default value for None input."""
        service = AsyncMeteostatService()
        result = service._safe_float(None, default=0.0)
        assert result == 0.0


# =============================================================================
# Default Location Tests
# =============================================================================


class TestDefaultLocation:
    """Tests for default location (Parañaque City)."""

    @patch.dict(
        os.environ,
        {"DEFAULT_LATITUDE": "14.4793", "DEFAULT_LONGITUDE": "121.0198"},
        clear=False,
    )
    def test_default_coordinates_are_paranaque(self):
        """Test default coordinates are for Parañaque City."""
        service = AsyncMeteostatService()
        assert service.default_lat == 14.4793
        assert service.default_lon == 121.0198

    def test_coordinates_in_metro_manila(self):
        """Test coordinates are within Metro Manila bounds."""
        lat = 14.4793
        lon = 121.0198

        # Metro Manila bounding box
        assert 14.3 <= lat <= 14.8
        assert 120.9 <= lon <= 121.2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
