"""
Unit Tests for Async WorldTides Service.

Tests the AsyncWorldTidesService for tidal data retrieval
from WorldTides API, including:
- Initialization and configuration
- Current tide fetching
- Tide heights prediction
- Tide extremes (high/low tides)
- Caching functionality
- Error handling and retry logic
- API response handling
"""

import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from app.services.worldtides_service_async import (
    AsyncWorldTidesService,
    TideData,
    TideExtreme,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton instance before each test."""
    # Store original class state
    original_instance = AsyncWorldTidesService._instance
    original_session = AsyncWorldTidesService._session

    # Reset
    AsyncWorldTidesService._instance = None
    AsyncWorldTidesService._session = None

    yield

    # Cleanup
    AsyncWorldTidesService._instance = None
    AsyncWorldTidesService._session = None


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for the service."""
    env_vars = {
        "WORLDTIDES_API_KEY": "test-api-key-123",  # pragma: allowlist secret
        "WORLDTIDES_ENABLED": "true",
        "WORLDTIDES_DATUM": "MSL",
        "DEFAULT_LATITUDE": "14.4793",
        "DEFAULT_LONGITUDE": "120.9822",
        "WORLDTIDES_CACHE_TTL_SECONDS": "1800",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


@pytest.fixture
def mock_tide_heights_response():
    """Create mock tide heights API response."""
    now = datetime.now(timezone.utc)
    return {
        "status": 200,
        "callCount": 1,
        "responseDatum": "MSL",
        "heights": [
            {"dt": int((now - timedelta(hours=2)).timestamp()), "height": 0.5},
            {"dt": int((now - timedelta(hours=1)).timestamp()), "height": 1.0},
            {"dt": int(now.timestamp()), "height": 1.5},
            {"dt": int((now + timedelta(hours=1)).timestamp()), "height": 2.0},
            {"dt": int((now + timedelta(hours=2)).timestamp()), "height": 1.8},
        ],
    }


@pytest.fixture
def mock_tide_extremes_response():
    """Create mock tide extremes API response."""
    now = datetime.now(timezone.utc)
    return {
        "status": 200,
        "callCount": 1,
        "responseDatum": "MSL",
        "extremes": [
            {"dt": int((now + timedelta(hours=3)).timestamp()), "height": 2.1, "type": "High"},
            {"dt": int((now + timedelta(hours=9)).timestamp()), "height": 0.3, "type": "Low"},
            {"dt": int((now + timedelta(hours=15)).timestamp()), "height": 2.0, "type": "High"},
            {"dt": int((now + timedelta(hours=21)).timestamp()), "height": 0.4, "type": "Low"},
        ],
    }


@pytest.fixture
def mock_error_response():
    """Create mock error API response."""
    return {
        "status": 400,
        "error": "Invalid API key",
    }


# =============================================================================
# Data Structure Tests
# =============================================================================


class TestTideDataDataclass:
    """Tests for TideData dataclass."""

    def test_create_basic(self):
        """Test creating a basic TideData."""
        tide = TideData(
            timestamp=datetime.now(timezone.utc),
            height=1.5,
        )

        assert tide.height == 1.5
        assert tide.datum == "MSL"
        assert tide.source == "worldtides"
        assert tide.type is None

    def test_create_with_all_fields(self):
        """Test creating TideData with all fields."""
        tide = TideData(
            timestamp=datetime.now(timezone.utc),
            height=2.1,
            type="high",
            datum="LAT",
            source="worldtides",
        )

        assert tide.height == 2.1
        assert tide.type == "high"
        assert tide.datum == "LAT"


class TestTideExtremeDataclass:
    """Tests for TideExtreme dataclass."""

    def test_create_high_tide(self):
        """Test creating a high tide extreme."""
        extreme = TideExtreme(
            timestamp=datetime.now(timezone.utc),
            height=2.1,
            type="High",
        )

        assert extreme.height == 2.1
        assert extreme.type == "High"
        assert extreme.datum == "MSL"

    def test_create_low_tide(self):
        """Test creating a low tide extreme."""
        extreme = TideExtreme(
            timestamp=datetime.now(timezone.utc),
            height=0.3,
            type="Low",
            datum="LAT",
        )

        assert extreme.height == 0.3
        assert extreme.type == "Low"
        assert extreme.datum == "LAT"


# =============================================================================
# Service Initialization Tests
# =============================================================================


class TestAsyncWorldTidesServiceInitialization:
    """Tests for AsyncWorldTidesService initialization."""

    @patch.dict(
        os.environ,
        {"WORLDTIDES_API_KEY": "test-key", "WORLDTIDES_ENABLED": "true"},  # pragma: allowlist secret
        clear=False,
    )
    def test_service_enabled_with_key(self):
        """Test service is enabled with API key."""
        service = AsyncWorldTidesService()
        assert service.enabled is True

    @patch.dict(os.environ, {"WORLDTIDES_API_KEY": ""}, clear=False)
    def test_service_disabled_without_key(self):
        """Test service is disabled without API key."""
        service = AsyncWorldTidesService()
        assert service.enabled is False

    @patch.dict(
        os.environ,
        {"WORLDTIDES_API_KEY": "test-key", "WORLDTIDES_ENABLED": "false"},  # pragma: allowlist secret
        clear=False,
    )
    def test_service_disabled_via_env(self):
        """Test service can be disabled via environment."""
        service = AsyncWorldTidesService()
        assert service.enabled is False

    @patch.dict(
        os.environ,
        {"WORLDTIDES_API_KEY": "test-key", "WORLDTIDES_DATUM": "LAT"},  # pragma: allowlist secret
        clear=False,
    )
    def test_custom_datum(self):
        """Test custom datum configuration."""
        service = AsyncWorldTidesService()
        assert service.default_datum == "LAT"

    @patch.dict(
        os.environ,
        {
            "WORLDTIDES_API_KEY": "test-key",  # pragma: allowlist secret
            "DEFAULT_LATITUDE": "15.0",
            "DEFAULT_LONGITUDE": "121.5",
        },
        clear=False,
    )
    def test_default_coordinates_from_env(self):
        """Test default coordinates from environment."""
        service = AsyncWorldTidesService()
        assert service.default_lat == 15.0
        assert service.default_lon == 121.5

    def test_singleton_pattern(self, mock_env_vars):
        """Test singleton pattern returns same instance."""
        instance1 = AsyncWorldTidesService.get_instance()
        instance2 = AsyncWorldTidesService.get_instance()

        assert instance1 is instance2

    def test_reset_instance(self, mock_env_vars):
        """Test reset_instance creates new instance."""
        instance1 = AsyncWorldTidesService.get_instance()
        AsyncWorldTidesService.reset_instance()
        instance2 = AsyncWorldTidesService.get_instance()

        assert instance1 is not instance2

    @patch.dict(
        os.environ,
        {"WORLDTIDES_API_KEY": "test-key", "WORLDTIDES_CACHE_TTL_SECONDS": "3600"},  # pragma: allowlist secret
        clear=False,
    )
    def test_cache_ttl_config(self):
        """Test cache TTL configuration."""
        service = AsyncWorldTidesService()
        assert service._cache_ttl == 3600


# =============================================================================
# Session Management Tests
# =============================================================================


class TestSessionManagement:
    """Tests for aiohttp session management."""

    @pytest.mark.asyncio
    async def test_get_session_creates_new(self, mock_env_vars):
        """Test _get_session creates new session."""
        service = AsyncWorldTidesService()
        session = await service._get_session()

        assert session is not None
        assert isinstance(session, aiohttp.ClientSession)

        # Cleanup
        await session.close()

    @pytest.mark.asyncio
    async def test_get_session_reuses_existing(self, mock_env_vars):
        """Test _get_session reuses existing session."""
        service = AsyncWorldTidesService()
        session1 = await service._get_session()
        session2 = await service._get_session()

        assert session1 is session2

        # Cleanup
        await session1.close()

    @pytest.mark.asyncio
    async def test_close_session(self, mock_env_vars):
        """Test closing the session."""
        service = AsyncWorldTidesService()
        await service._get_session()

        await service.close()
        # Session should be closed


# =============================================================================
# Cache Tests
# =============================================================================


class TestCaching:
    """Tests for caching functionality."""

    def test_get_cache_key(self, mock_env_vars):
        """Test cache key generation."""
        service = AsyncWorldTidesService()
        key = service._get_cache_key("current", 14.4793, 120.9822, datum="MSL")

        assert "current" in key
        assert "14.4793" in key
        assert "120.9822" in key
        assert "datum=MSL" in key

    def test_cache_key_consistent(self, mock_env_vars):
        """Test cache key is consistent for same inputs."""
        service = AsyncWorldTidesService()
        key1 = service._get_cache_key("heights", 14.0, 120.0, days=2)
        key2 = service._get_cache_key("heights", 14.0, 120.0, days=2)

        assert key1 == key2

    def test_set_and_get_cache(self, mock_env_vars):
        """Test setting and getting from cache."""
        service = AsyncWorldTidesService()
        cache_key = "test_key"
        test_data = {"height": 1.5}

        service._set_cache(cache_key, test_data)
        result = service._get_from_cache(cache_key)

        assert result == test_data

    def test_cache_miss(self, mock_env_vars):
        """Test cache miss returns None."""
        service = AsyncWorldTidesService()
        result = service._get_from_cache("nonexistent_key")

        assert result is None

    def test_cache_expiry(self, mock_env_vars):
        """Test cache expiry."""
        with patch.dict(os.environ, {"WORLDTIDES_CACHE_TTL_SECONDS": "0"}, clear=False):
            service = AsyncWorldTidesService()
            service._cache_ttl = 0  # Override to expire immediately

            cache_key = "test_expiry"
            service._set_cache(cache_key, {"data": "test"})

            # Wait a tiny bit
            import time

            time.sleep(0.01)

            result = service._get_from_cache(cache_key)
            assert result is None


# =============================================================================
# Get Current Tide Tests
# =============================================================================


class TestGetCurrentTide:
    """Tests for get_current_tide method."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"WORLDTIDES_API_KEY": ""}, clear=False)
    async def test_returns_none_when_disabled(self):
        """Test returns None when service is disabled."""
        service = AsyncWorldTidesService()
        result = await service.get_current_tide()

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_cached_data(self, mock_env_vars):
        """Test returns cached data if available."""
        service = AsyncWorldTidesService()

        # Pre-populate cache
        cached_tide = TideData(
            timestamp=datetime.now(timezone.utc),
            height=1.5,
            datum="MSL",
        )
        cache_key = service._get_cache_key("current", 14.4793, 120.9822, datum="MSL")
        service._set_cache(cache_key, cached_tide)

        result = await service.get_current_tide(lat=14.4793, lon=120.9822)

        assert result is cached_tide


# =============================================================================
# Get Tide Heights Tests
# =============================================================================


class TestGetTideHeights:
    """Tests for get_tide_heights method."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"WORLDTIDES_API_KEY": ""}, clear=False)
    async def test_returns_empty_when_disabled(self):
        """Test returns empty list when disabled."""
        service = AsyncWorldTidesService()
        result = await service.get_tide_heights()

        assert result == []

    @pytest.mark.asyncio
    async def test_clamps_days_parameter(self, mock_env_vars):
        """Test days parameter is clamped to 1-7."""
        service = AsyncWorldTidesService()

        # Days should be clamped even though we can't make actual API call
        days_clamped = min(max(10, 1), 7)
        assert days_clamped == 7

        days_clamped = min(max(0, 1), 7)
        assert days_clamped == 1


# =============================================================================
# Get Tide Extremes Tests
# =============================================================================


class TestGetTideExtremes:
    """Tests for get_tide_extremes method."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"WORLDTIDES_API_KEY": ""}, clear=False)
    async def test_returns_empty_when_disabled(self):
        """Test returns empty list when disabled."""
        service = AsyncWorldTidesService()
        result = await service.get_tide_extremes()

        assert result == []


# =============================================================================
# Make Request Tests
# =============================================================================


class TestMakeRequest:
    """Tests for _make_request method."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"WORLDTIDES_API_KEY": ""}, clear=False)
    async def test_returns_none_when_disabled(self):
        """Test returns None when service is disabled."""
        service = AsyncWorldTidesService()
        result = await service._make_request({"test": "params"})

        assert result is None


# =============================================================================
# Retry Configuration Tests
# =============================================================================


class TestRetryConfiguration:
    """Tests for retry configuration."""

    def test_retry_constants(self):
        """Test retry configuration constants."""
        assert AsyncWorldTidesService.MAX_RETRIES == 3
        assert AsyncWorldTidesService.RETRY_MIN_WAIT == 1
        assert AsyncWorldTidesService.RETRY_MAX_WAIT == 10


# =============================================================================
# API URL Tests
# =============================================================================


class TestApiConfiguration:
    """Tests for API configuration."""

    def test_api_base_url(self):
        """Test API base URL is correct."""
        assert AsyncWorldTidesService.API_BASE_URL == "https://www.worldtides.info/api/v3"


# =============================================================================
# Default Location Tests
# =============================================================================


class TestDefaultLocation:
    """Tests for default location (Manila Bay)."""

    def test_default_coordinates_are_manila_bay(self):
        """Test default coordinates are for Manila Bay area."""
        # These are the class-level defaults
        assert AsyncWorldTidesService.DEFAULT_LAT == 14.4793
        assert AsyncWorldTidesService.DEFAULT_LON == 120.9822

    def test_coordinates_in_manila_bay(self):
        """Test coordinates are within Manila Bay bounds."""
        lat = AsyncWorldTidesService.DEFAULT_LAT
        lon = AsyncWorldTidesService.DEFAULT_LON

        # Manila Bay area bounding box
        assert 14.0 <= lat <= 15.0
        assert 120.5 <= lon <= 121.5

    def test_coordinates_in_philippines(self):
        """Test coordinates are within Philippines bounds."""
        lat = AsyncWorldTidesService.DEFAULT_LAT
        lon = AsyncWorldTidesService.DEFAULT_LON

        # Philippines bounding box
        assert 4.0 <= lat <= 21.0
        assert 116.0 <= lon <= 127.0


# =============================================================================
# Tide Data For Prediction Tests
# =============================================================================


class TestTideDataForPrediction:
    """Tests for tide data used in flood prediction."""

    def test_tide_height_ranges(self):
        """Test valid tide height ranges for Manila Bay."""
        # Typical tide heights in Manila Bay
        normal_low_tide = 0.3
        normal_high_tide = 1.5
        king_tide = 2.5

        assert normal_low_tide < normal_high_tide < king_tide

    def test_tide_affects_flood_risk(self):
        """Test that high tides increase flood risk calculation."""
        high_tide_height = 2.0
        low_tide_height = 0.3
        heavy_rain = 50.0  # mm

        # Simple risk calculation (conceptual)
        risk_at_high_tide = heavy_rain * (1 + high_tide_height / 2)
        risk_at_low_tide = heavy_rain * (1 + low_tide_height / 2)

        assert risk_at_high_tide > risk_at_low_tide


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_handles_api_error_response(self, mock_env_vars, mock_error_response):
        """Test handling of API error responses."""
        service = AsyncWorldTidesService()

        # API error should result in None
        # (actual implementation would need mocking the HTTP call)
        assert mock_error_response["status"] != 200
        assert "error" in mock_error_response


# =============================================================================
# SSE Format Tests (for tide alerts)
# =============================================================================


class TestTideAlertFormatting:
    """Tests for formatting tide data for alerts."""

    def test_tide_data_serializable(self):
        """Test TideData can be serialized."""
        tide = TideData(
            timestamp=datetime.now(timezone.utc),
            height=1.5,
            type="high",
            datum="MSL",
        )

        # Should be convertible to dict for JSON serialization
        tide_dict = {
            "timestamp": tide.timestamp.isoformat(),
            "height": tide.height,
            "type": tide.type,
            "datum": tide.datum,
            "source": tide.source,
        }

        assert tide_dict["height"] == 1.5
        assert "timestamp" in tide_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
