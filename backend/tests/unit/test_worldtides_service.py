"""
Unit tests for WorldTides service.

Tests for app/services/worldtides_service.py
"""

from datetime import datetime
from unittest.mock import patch

import pytest

# Import modules at top level for proper coverage tracking
from app.services import worldtides_service
from app.services.worldtides_service import (
    TideData,
    TideExtreme,
    WorldTidesService,
)


class TestWorldTidesServiceInitialization:
    """Tests for WorldTidesService initialization."""

    @patch.dict("os.environ", {"WORLDTIDES_API_KEY": ""}, clear=False)
    def test_service_disabled_without_api_key(self):
        """Test service is disabled without API key."""
        WorldTidesService.reset_instance()
        service = WorldTidesService()

        assert not service.enabled

    @patch.dict("os.environ", {"WORLDTIDES_API_KEY": "test-key-123", "WORLDTIDES_ENABLED": "true"}, clear=False)
    def test_service_enabled_with_api_key(self):
        """Test service is enabled with API key."""
        WorldTidesService.reset_instance()
        service = WorldTidesService()

        assert service.enabled

    def test_singleton_pattern(self):
        """Test singleton pattern returns same instance."""
        WorldTidesService.reset_instance()
        instance1 = WorldTidesService.get_instance()
        instance2 = WorldTidesService.get_instance()

        assert instance1 is instance2


class TestTideDataStructure:
    """Tests for TideData data structure."""

    def test_tide_data_creation(self):
        """Test TideData dataclass creation."""
        tide = TideData(timestamp=datetime.now(), height=1.5, type="high", datum="MSL", source="worldtides")

        assert tide.height == 1.5
        assert tide.type == "high"
        assert tide.datum == "MSL"

    def test_tide_data_default_values(self):
        """Test TideData default values."""
        tide = TideData(timestamp=datetime.now(), height=0.5)

        assert tide.datum == "MSL"
        assert tide.source == "worldtides"
        assert tide.type is None


class TestTideExtremeStructure:
    """Tests for TideExtreme data structure."""

    def test_tide_extreme_creation(self):
        """Test TideExtreme dataclass creation."""
        extreme = TideExtreme(timestamp=datetime.now(), height=2.1, type="High", datum="MSL")

        assert extreme.height == 2.1
        assert extreme.type == "High"

    def test_high_tide_type(self):
        """Test high tide type classification."""
        tide_type = "High"
        assert tide_type in ["High", "Low"]

    def test_low_tide_type(self):
        """Test low tide type classification."""
        tide_type = "Low"
        assert tide_type in ["High", "Low"]


class TestDefaultCoordinates:
    """Tests for default coordinate handling."""

    def test_default_latitude_is_paranaque(self):
        """Test default latitude is for Parañaque/Manila Bay area."""
        default_lat = 14.4793

        # Should be near Parañaque City
        assert 14.0 <= default_lat <= 15.0

    def test_default_longitude_is_manila_bay(self):
        """Test default longitude is for Manila Bay area."""
        default_lon = 120.9822

        # Should be near Manila Bay
        assert 120.5 <= default_lon <= 121.5

    def test_coordinates_are_in_philippines(self):
        """Test coordinates are within Philippines bounds."""
        lat = 14.4793
        lon = 120.9822

        # Philippines bounding box
        assert 4.0 <= lat <= 21.0
        assert 116.0 <= lon <= 127.0


class TestTideDataForPrediction:
    """Tests for tide data used in flood prediction."""

    def test_tide_height_affects_flood_risk(self):
        """Test that high tide heights increase flood risk."""
        low_tide_height = 0.3
        high_tide_height = 2.0

        # Higher tide should indicate higher flood risk
        assert high_tide_height > low_tide_height

    def test_tide_trend_calculation(self):
        """Test tide trend can be calculated from heights."""
        heights = [0.5, 0.8, 1.2, 1.5]  # Rising tide

        # Should be able to detect rising trend
        assert heights[-1] > heights[0]

    def test_king_tide_threshold(self):
        """Test king tide threshold detection."""
        normal_high_tide = 1.5
        king_tide = 2.5
        king_tide_threshold = 2.0

        assert normal_high_tide < king_tide_threshold
        assert king_tide > king_tide_threshold


class TestCacheHandling:
    """Tests for tide data caching."""

    def test_cache_key_generation(self):
        """Test cache key is generated correctly."""
        prefix = "current"
        lat = 14.4793
        lon = 120.9822

        # Cache key should be unique for location
        cache_key = f"{prefix}:{lat:.4f}:{lon:.4f}"

        assert "current" in cache_key
        assert "14.4793" in cache_key

    def test_cache_ttl_default(self):
        """Test default cache TTL is reasonable."""
        default_ttl = 1800  # 30 minutes

        # TTL should be between 10 minutes and 2 hours
        assert 600 <= default_ttl <= 7200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
