"""
WorldTides Service for Tidal Data.

Provides access to global tidal data from WorldTides API for flood prediction.
Tide levels are critical for coastal flood risk assessment in areas like Parañaque City.

Features:
- Fetch current and predicted tide heights
- Get tide extremes (high/low tide times)
- Integrate with flood prediction model
- Cache results to minimize API credits usage

API Documentation: https://www.worldtides.info/apidocs
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
from app.core.constants import DEFAULT_LATITUDE, DEFAULT_LONGITUDE
from app.services.worldtides_types import TideData, TideExtreme
from app.utils.secrets import get_secret

logger = logging.getLogger(__name__)


class WorldTidesService:
    """
    Service for fetching tidal data from WorldTides API.

    Tidal data is essential for coastal flood prediction because:
    - High tides reduce drainage capacity
    - King tides combined with rain cause severe flooding
    - Storm surge effects are amplified at high tide

    Parañaque City is a coastal city where tides significantly
    impact flood risk.
    """

    _instance: Optional["WorldTidesService"] = None

    # WorldTides API v3 endpoint
    API_BASE_URL = "https://www.worldtides.info/api/v3"

    # Default location (Parañaque City, Philippines - Manila Bay)
    DEFAULT_LAT = DEFAULT_LATITUDE
    DEFAULT_LON = 120.9822  # Slightly adjusted for Manila Bay coastline

    def __init__(self):
        """Initialize the WorldTides service."""
        self.api_key = get_secret("WORLDTIDES_API_KEY", default="")
        self.enabled = bool(self.api_key) and os.getenv("WORLDTIDES_ENABLED", "True").lower() == "true"
        self.default_datum = os.getenv("WORLDTIDES_DATUM", "MSL")  # Mean Sea Level

        # Default location (from environment or central config)
        self.default_lat = float(os.getenv("DEFAULT_LATITUDE", str(DEFAULT_LATITUDE)))
        self.default_lon = float(os.getenv("DEFAULT_LONGITUDE", str(self.DEFAULT_LON)))

        # Cache settings
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = int(os.getenv("WORLDTIDES_CACHE_TTL_SECONDS", "1800"))  # 30 min default

        if self.enabled:
            logger.info("WorldTidesService initialized with API key")
        else:
            logger.warning("WorldTidesService disabled - no WORLDTIDES_API_KEY configured")

    @classmethod
    def get_instance(cls) -> "WorldTidesService":
        """Get the singleton instance of WorldTidesService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        cls._instance = None

    def _make_request(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Make a request to the WorldTides API.

        Args:
            params: Query parameters for the API

        Returns:
            JSON response dict or None on error
        """
        if not self.enabled:
            logger.warning("WorldTides API is disabled")
            return None

        params["key"] = self.api_key

        try:
            response = requests.get(self.API_BASE_URL, params=params, timeout=30)

            data = response.json()

            if data.get("status") != 200:
                error_msg = data.get("error", "Unknown error")
                logger.error(f"WorldTides API error: {error_msg}")
                return None

            # Log credit usage
            call_count = data.get("callCount", 0)
            logger.debug(f"WorldTides API call used {call_count} credit(s)")

            return data

        except requests.exceptions.Timeout:
            logger.error("WorldTides API request timed out")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"WorldTides API request failed: {e}")
            return None
        except ValueError as e:
            logger.error(f"Failed to parse WorldTides API response: {e}")
            return None

    def _get_cache_key(self, prefix: str, lat: float, lon: float, **kwargs) -> str:
        """Generate a cache key for a request."""
        key_parts = [prefix, f"{lat:.4f}", f"{lon:.4f}"]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        return ":".join(key_parts)

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get data from cache if valid."""
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if datetime.now() - cached_time < timedelta(seconds=self._cache_ttl):
                logger.debug(f"Cache hit for {cache_key}")
                return cached_data
            else:
                del self._cache[cache_key]
        return None

    def _set_cache(self, cache_key: str, data: Any) -> None:
        """Store data in cache."""
        self._cache[cache_key] = (data, datetime.now())

    def get_current_tide(
        self, lat: Optional[float] = None, lon: Optional[float] = None, datum: Optional[str] = None
    ) -> Optional[TideData]:
        """
        Get the current tide height for a location.

        Args:
            lat: Latitude
            lon: Longitude
            datum: Vertical reference level (default: MSL)

        Returns:
            TideData for current time or None
        """
        lat = lat or self.default_lat
        lon = lon or self.default_lon
        datum = datum or self.default_datum

        cache_key = self._get_cache_key("current", lat, lon, datum=datum)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        params = {
            "lat": lat,
            "lon": lon,
            "heights": "",  # Request heights
            "datum": datum,
            "length": 3600,  # 1 hour of data
            "step": 1800,  # 30 min intervals
        }

        data = self._make_request(params)
        if not data or "heights" not in data:
            return None

        heights = data.get("heights", [])
        if not heights:
            return None

        # Get the most recent height
        latest = heights[-1]
        result = TideData(
            timestamp=datetime.fromtimestamp(latest["dt"]),
            height=latest["height"],
            datum=data.get("responseDatum", datum),
            source="worldtides",
        )

        self._set_cache(cache_key, result)
        return result

    def get_tide_heights(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        days: int = 1,
        datum: Optional[str] = None,
        step: int = 1800,  # 30 minutes
    ) -> List[TideData]:
        """
        Get tide height predictions for a location.

        Args:
            lat: Latitude
            lon: Longitude
            days: Number of days of predictions (1-7)
            datum: Vertical reference level
            step: Time step in seconds (min 60)

        Returns:
            List of TideData predictions
        """
        lat = lat or self.default_lat
        lon = lon or self.default_lon
        datum = datum or self.default_datum
        days = min(max(days, 1), 7)  # Clamp to 1-7 days

        cache_key = self._get_cache_key("heights", lat, lon, days=days, datum=datum)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        params = {
            "lat": lat,
            "lon": lon,
            "heights": "",
            "datum": datum,
            "date": "today",
            "days": days,
            "step": step,
            "localtime": "",
            "timezone": "",
        }

        data = self._make_request(params)
        if not data or "heights" not in data:
            return []

        results = []
        response_datum = data.get("responseDatum", datum)

        for height_data in data.get("heights", []):
            results.append(
                TideData(
                    timestamp=datetime.fromtimestamp(height_data["dt"]),
                    height=height_data["height"],
                    datum=response_datum,
                    source="worldtides",
                )
            )

        self._set_cache(cache_key, results)
        logger.info(f"Retrieved {len(results)} tide height predictions")
        return results

    def get_tide_extremes(
        self, lat: Optional[float] = None, lon: Optional[float] = None, days: int = 2, datum: Optional[str] = None
    ) -> List[TideExtreme]:
        """
        Get tide extremes (high and low tides) for a location.

        Args:
            lat: Latitude
            lon: Longitude
            days: Number of days of data (default: 2)
            datum: Vertical reference level

        Returns:
            List of TideExtreme (high/low tides)
        """
        lat = lat or self.default_lat
        lon = lon or self.default_lon
        datum = datum or self.default_datum

        cache_key = self._get_cache_key("extremes", lat, lon, days=days, datum=datum)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        params = {
            "lat": lat,
            "lon": lon,
            "extremes": "",
            "datum": datum,
            "date": "today",
            "days": days,
            "localtime": "",
            "timezone": "",
        }

        data = self._make_request(params)
        if not data or "extremes" not in data:
            return []

        results = []
        response_datum = data.get("responseDatum", datum)

        for extreme_data in data.get("extremes", []):
            results.append(
                TideExtreme(
                    timestamp=datetime.fromtimestamp(extreme_data["dt"]),
                    height=extreme_data["height"],
                    type=extreme_data.get("type", "Unknown"),
                    datum=response_datum,
                )
            )

        self._set_cache(cache_key, results)
        logger.info(f"Retrieved {len(results)} tide extremes")
        return results

    def get_nearby_stations(
        self, lat: Optional[float] = None, lon: Optional[float] = None, distance_km: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get nearby tidal stations.

        Args:
            lat: Latitude
            lon: Longitude
            distance_km: Maximum distance in kilometers

        Returns:
            List of station information dicts
        """
        lat = lat or self.default_lat
        lon = lon or self.default_lon

        params = {
            "lat": lat,
            "lon": lon,
            "stations": "",
            "stationDistance": distance_km,
        }

        data = self._make_request(params)
        if not data or "stations" not in data:
            return []

        return data.get("stations", [])

    def get_tide_data_for_prediction(
        self, lat: Optional[float] = None, lon: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get tide data formatted for flood prediction model.

        Returns tide information that can enhance flood prediction:
        - Current tide height
        - Next high/low tide info
        - Hours until next high tide
        - Tide trend (rising/falling)

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Dict with tide features for prediction, or None
        """
        lat = lat or self.default_lat
        lon = lon or self.default_lon

        current = self.get_current_tide(lat, lon)
        extremes = self.get_tide_extremes(lat, lon, days=2)

        if not current:
            return None

        result = {
            "tide_height": current.height,
            "tide_datum": current.datum,
            "tide_timestamp": current.timestamp.isoformat(),
            "source": "worldtides",
            "latitude": lat,
            "longitude": lon,
        }

        # Analyze extremes to determine trend and next high tide
        if extremes:
            now = datetime.now()
            future_extremes = [e for e in extremes if e.timestamp > now]

            if future_extremes:
                next_extreme = future_extremes[0]
                result["next_extreme_type"] = next_extreme.type
                result["next_extreme_height"] = next_extreme.height
                result["next_extreme_time"] = next_extreme.timestamp.isoformat()

                hours_until = (next_extreme.timestamp - now).total_seconds() / 3600
                result["hours_until_next_extreme"] = round(hours_until, 2)

                # Determine if tide is rising or falling
                if next_extreme.type == "High":
                    result["tide_trend"] = "rising"
                else:
                    result["tide_trend"] = "falling"

                # Find next high tide specifically
                next_high = next((e for e in future_extremes if e.type == "High"), None)
                if next_high:
                    hours_to_high = (next_high.timestamp - now).total_seconds() / 3600
                    result["hours_until_high_tide"] = round(hours_to_high, 2)
                    result["next_high_tide_height"] = next_high.height

        # Calculate tide risk factor (0-1 scale)
        # Higher tide = higher flood risk when combined with rain
        result["tide_risk_factor"] = self._calculate_tide_risk_factor(current.height, extremes)

        return result

    def _calculate_tide_risk_factor(self, current_height: float, extremes: List[TideExtreme]) -> float:
        """
        Calculate a tide risk factor for flood prediction.

        The risk factor is 0-1 where:
        - 0 = Low tide (minimal flood contribution)
        - 0.5 = Mean tide level
        - 1 = High tide (maximum flood contribution)

        Args:
            current_height: Current tide height
            extremes: List of recent tide extremes

        Returns:
            Risk factor between 0 and 1
        """
        if not extremes:
            # No extreme data, estimate based on absolute height
            # Assume typical tidal range of ~1m around MSL
            return max(0, min(1, (current_height + 0.5) / 1.0))

        # Find min and max from extremes
        heights = [e.height for e in extremes]
        min_height = min(heights)
        max_height = max(heights)

        range_height = max_height - min_height
        if range_height <= 0:
            return 0.5

        # Normalize current height to 0-1 scale
        risk = (current_height - min_height) / range_height
        return max(0, min(1, risk))

    def get_datums_info(self, lat: Optional[float] = None, lon: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Get available vertical datums for a location.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Dict with datum information
        """
        lat = lat or self.default_lat
        lon = lon or self.default_lon

        params = {
            "lat": lat,
            "lon": lon,
            "datums": "",
        }

        data = self._make_request(params)
        if not data:
            return None

        return {
            "datums": data.get("datums", []),
            "station": data.get("station"),
            "atlas": data.get("atlas"),
            "copyright": data.get("copyright"),
        }

    def is_available(self) -> bool:
        """Check if the WorldTides service is available and configured."""
        return self.enabled

    def get_service_status(self) -> Dict[str, Any]:
        """Get the current status of the WorldTides service."""
        return {
            "enabled": self.enabled,
            "api_key_configured": bool(self.api_key),
            "default_location": {"lat": self.default_lat, "lon": self.default_lon},
            "default_datum": self.default_datum,
            "cache_entries": len(self._cache),
            "cache_ttl_seconds": self._cache_ttl,
        }


# Module-level convenience functions
def get_worldtides_service() -> WorldTidesService:
    """Get the WorldTidesService singleton instance."""
    return WorldTidesService.get_instance()


def get_current_tide(lat: Optional[float] = None, lon: Optional[float] = None) -> Optional[TideData]:
    """
    Convenience function to get current tide height.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        TideData or None
    """
    service = get_worldtides_service()
    return service.get_current_tide(lat, lon)


def get_tide_for_prediction(lat: Optional[float] = None, lon: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """
    Get tide data formatted for flood prediction.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Dict with tide features or None
    """
    service = get_worldtides_service()
    return service.get_tide_data_for_prediction(lat, lon)


def get_tide_extremes(lat: Optional[float] = None, lon: Optional[float] = None, days: int = 2) -> List[TideExtreme]:
    """
    Get upcoming high and low tides.

    Args:
        lat: Latitude
        lon: Longitude
        days: Number of days

    Returns:
        List of TideExtreme
    """
    service = get_worldtides_service()
    return service.get_tide_extremes(lat, lon, days)
