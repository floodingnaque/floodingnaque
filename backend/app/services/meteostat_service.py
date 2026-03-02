"""
Meteostat Service for Historical Weather Data.

Provides access to historical weather data from weather stations using the Meteostat library.
Meteostat is free and does not require an API key.

Features:
- Fetch historical hourly and daily weather data
- Find nearby weather stations
- Get current weather observations from nearby stations
- Automatic station selection based on coordinates
"""

import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
from app.core.constants import DEFAULT_LATITUDE, DEFAULT_LONGITUDE
from app.services.meteostat_types import WeatherObservation
from app.utils.circuit_breaker import CircuitOpenError, meteostat_breaker
from meteostat import Daily, Hourly, Point, Stations

logger = logging.getLogger(__name__)

# Default timeout (seconds) for Meteostat upstream requests.
# Prevents a hung upstream from blocking a Gunicorn worker indefinitely.
METEOSTAT_REQUEST_TIMEOUT = int(os.getenv("METEOSTAT_REQUEST_TIMEOUT", "30"))


class MeteostatService:
    """
    Service for fetching weather data from Meteostat.

    Meteostat provides free access to historical weather data from
    weather stations worldwide. It's particularly useful for:
    - Historical data analysis for ML training
    - Fallback data source when APIs are unavailable
    - Validation of API data against station observations
    """

    _instance: Optional["MeteostatService"] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self):
        """Initialize the Meteostat service."""
        self.enabled = os.getenv("METEOSTAT_ENABLED", "True").lower() == "true"
        self.cache_max_age_days = int(os.getenv("METEOSTAT_CACHE_MAX_AGE_DAYS", "7"))
        self.default_station_id = os.getenv("METEOSTAT_STATION_ID", "")
        self.as_fallback = os.getenv("METEOSTAT_AS_FALLBACK", "True").lower() == "true"
        self.request_timeout = METEOSTAT_REQUEST_TIMEOUT

        # Default location (Parañaque City, Philippines)
        self.default_lat = float(os.getenv("DEFAULT_LATITUDE", str(DEFAULT_LATITUDE)))
        self.default_lon = float(os.getenv("DEFAULT_LONGITUDE", str(DEFAULT_LONGITUDE)))

        # Configure Meteostat cache directory
        cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "meteostat_cache")
        os.makedirs(cache_dir, exist_ok=True)

        logger.info(f"MeteostatService initialized (enabled={self.enabled}, fallback={self.as_fallback})")

    @classmethod
    def get_instance(cls) -> "MeteostatService":
        """Get the singleton instance of MeteostatService (thread-safe)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        with cls._lock:
            cls._instance = None

    def _call_with_timeout(self, func, *args, **kwargs):
        """
        Execute *func* in a thread-pool and enforce ``self.request_timeout``.

        Prevents an upstream Meteostat hang from blocking the calling
        Gunicorn worker indefinitely.
        """
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            try:
                return future.result(timeout=self.request_timeout)
            except FuturesTimeoutError:
                logger.error(
                    f"Meteostat request timed out after {self.request_timeout}s"
                )
                raise TimeoutError(
                    f"Meteostat upstream did not respond within {self.request_timeout}s"
                )

    def find_nearby_stations(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radius: int = 100000,  # 100km default radius
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Find nearby weather stations.

        Args:
            lat: Latitude (default: configured default)
            lon: Longitude (default: configured default)
            radius: Search radius in meters (default: 100km)
            limit: Maximum number of stations to return

        Returns:
            List of station dictionaries with id, name, distance, etc.
        """
        if not self.enabled:
            logger.warning("Meteostat is disabled")
            return []

        lat = lat or self.default_lat
        lon = lon or self.default_lon

        try:

            def _fetch_stations():
                stations = Stations()
                nearby = stations.nearby(lat, lon)
                df = nearby.fetch(limit)

                results = []
                for station_id, row in df.iterrows():
                    results.append(
                        {
                            "id": station_id,
                            "name": row.get("name", "Unknown"),
                            "country": row.get("country", ""),
                            "region": row.get("region", ""),
                            "latitude": row.get("latitude"),
                            "longitude": row.get("longitude"),
                            "elevation": row.get("elevation"),
                            "timezone": row.get("timezone", ""),
                        }
                    )
                return results

            return self._call_with_timeout(meteostat_breaker.call, _fetch_stations)

        except CircuitOpenError as e:
            logger.warning(f"Meteostat circuit breaker open: {e}")
            return []
        except (TimeoutError, Exception) as e:
            logger.error(f"Error finding nearby stations: {e}")
            return []

    def get_hourly_data(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        station_id: Optional[str] = None,
    ) -> List[WeatherObservation]:
        """
        Fetch hourly weather data for a location.

        Args:
            lat: Latitude (default: configured default)
            lon: Longitude (default: configured default)
            start: Start datetime (default: 7 days ago)
            end: End datetime (default: now)
            station_id: Specific station ID (optional)

        Returns:
            List of WeatherObservation objects
        """
        if not self.enabled:
            logger.warning("Meteostat is disabled")
            return []

        lat = lat or self.default_lat
        lon = lon or self.default_lon
        end = end or datetime.now()
        start = start or (end - timedelta(days=7))

        try:

            def _fetch_hourly():
                # Create a Point for the location
                location = Point(lat, lon)

                # Fetch hourly data
                data = Hourly(location, start, end)
                df = data.fetch()

                if df.empty:
                    logger.warning(f"No hourly data available for lat={lat}, lon={lon}")
                    return []

                observations = []
                for idx, row in df.iterrows():
                    obs = WeatherObservation(
                        timestamp=idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx,
                        temperature=self._safe_float(row.get("temp")),
                        humidity=self._safe_float(row.get("rhum")),
                        precipitation=self._safe_float(row.get("prcp"), default=0.0),
                        wind_speed=self._safe_float(row.get("wspd")),
                        pressure=self._safe_float(row.get("pres")),
                        station_id=station_id,
                        source="meteostat",
                    )
                    observations.append(obs)

                return observations

            return self._call_with_timeout(meteostat_breaker.call, _fetch_hourly)

        except CircuitOpenError as e:
            logger.warning(f"Meteostat circuit breaker open: {e}")
            return []
        except (TimeoutError, Exception) as e:
            logger.error(f"Error fetching hourly data: {e}")
            return []

    def get_daily_data(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        station_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch daily weather data for a location.

        Args:
            lat: Latitude (default: configured default)
            lon: Longitude (default: configured default)
            start: Start datetime (default: 30 days ago)
            end: End datetime (default: now)
            station_id: Specific station ID (optional)

        Returns:
            List of daily weather data dictionaries
        """
        if not self.enabled:
            logger.warning("Meteostat is disabled")
            return []

        lat = lat or self.default_lat
        lon = lon or self.default_lon
        end = end or datetime.now()
        start = start or (end - timedelta(days=30))

        try:

            def _fetch_daily():
                location = Point(lat, lon)
                data = Daily(location, start, end)
                df = data.fetch()

                if df.empty:
                    logger.warning(f"No daily data available for lat={lat}, lon={lon}")
                    return []

                results = []
                for idx, row in df.iterrows():
                    date = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx
                    results.append(
                        {
                            "date": date.isoformat() if hasattr(date, "isoformat") else str(date),
                            "tavg": self._safe_float(row.get("tavg")),  # Average temperature
                            "tmin": self._safe_float(row.get("tmin")),  # Min temperature
                            "tmax": self._safe_float(row.get("tmax")),  # Max temperature
                            "prcp": self._safe_float(row.get("prcp"), default=0.0),  # Precipitation
                            "snow": self._safe_float(row.get("snow"), default=0.0),  # Snowfall
                            "wdir": self._safe_float(row.get("wdir")),  # Wind direction
                            "wspd": self._safe_float(row.get("wspd")),  # Wind speed
                            "wpgt": self._safe_float(row.get("wpgt")),  # Wind peak gust
                            "pres": self._safe_float(row.get("pres")),  # Pressure
                            "source": "meteostat",
                        }
                    )

                return results

            return self._call_with_timeout(meteostat_breaker.call, _fetch_daily)

        except CircuitOpenError as e:
            logger.warning(f"Meteostat circuit breaker open: {e}")
            return []
        except (TimeoutError, Exception) as e:
            logger.error(f"Error fetching daily data: {e}")
            return []

    def get_latest_observation(
        self, lat: Optional[float] = None, lon: Optional[float] = None
    ) -> Optional[WeatherObservation]:
        """
        Get the most recent weather observation for a location.

        Useful as a fallback when real-time API calls fail.
        Note: Meteostat data may be delayed by a few hours.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            WeatherObservation or None if no data available
        """
        if not self.enabled:
            return None

        # Get the last 24 hours of hourly data
        end = datetime.now()
        start = end - timedelta(hours=24)

        observations = self.get_hourly_data(lat, lon, start, end)

        if observations:
            # Return the most recent observation
            return observations[-1]

        return None

    def get_historical_for_training(
        self, lat: Optional[float] = None, lon: Optional[float] = None, days: int = 365
    ) -> pd.DataFrame:
        """
        Get historical weather data formatted for ML training.

        Returns a DataFrame with columns matching the flood prediction model's
        expected input format. Uses Hourly data to get actual humidity values
        (Daily API doesn't include humidity).

        Args:
            lat: Latitude
            lon: Longitude
            days: Number of days of historical data to fetch

        Returns:
            DataFrame with temperature, humidity, precipitation columns
        """
        if not self.enabled:
            return pd.DataFrame()

        lat = lat or self.default_lat
        lon = lon or self.default_lon
        end = datetime.now()
        start = end - timedelta(days=days)

        try:
            location = Point(lat, lon)

            # First try to get hourly data which includes humidity (rhum)
            hourly_data = Hourly(location, start, end)
            hourly_df = hourly_data.fetch()

            if not hourly_df.empty and "rhum" in hourly_df.columns:
                # Aggregate hourly data to daily with actual humidity
                hourly_df = hourly_df.reset_index()
                hourly_df["date"] = hourly_df["time"].dt.date

                daily_agg = (
                    hourly_df.groupby("date")
                    .agg(
                        {
                            "temp": "mean",  # Average temperature
                            "rhum": "mean",  # Average humidity from actual data
                            "prcp": "sum",  # Total precipitation
                        }
                    )
                    .reset_index()
                )

                result = pd.DataFrame()
                result["temperature"] = daily_agg["temp"].apply(
                    lambda x: x + 273.15 if pd.notna(x) else None
                )  # Convert to Kelvin
                result["humidity"] = daily_agg["rhum"]
                result["precipitation"] = daily_agg["prcp"].fillna(0)
                result["date"] = pd.to_datetime(daily_agg["date"])

                # Only fill missing humidity with seasonal estimates if needed
                result["humidity"] = result.apply(
                    lambda row: (
                        row["humidity"] if pd.notna(row["humidity"]) else self._estimate_humidity_for_date(row["date"])
                    ),
                    axis=1,
                )

                result = result.dropna(subset=["temperature"])
                logger.info(f"Fetched {len(result)} days of historical data with actual humidity")
                return result

            # Fallback to Daily data if Hourly is not available
            data = Daily(location, start, end)
            df = data.fetch()

            if df.empty:
                return pd.DataFrame()

            # Reset index to avoid alignment issues
            df = df.reset_index()

            # Rename columns to match model expectations
            result = pd.DataFrame()
            result["temperature"] = df["tavg"].apply(lambda x: x + 273.15 if pd.notna(x) else None)  # Convert to Kelvin
            result["precipitation"] = df["prcp"].fillna(0)
            result["date"] = df["time"] if "time" in df.columns else df.index

            # Estimate humidity based on date/season since Daily API doesn't provide it
            result["humidity"] = result["date"].apply(self._estimate_humidity_for_date)

            result = result.dropna(subset=["temperature"])

            logger.info(f"Fetched {len(result)} days of historical data (estimated humidity)")
            return result

        except Exception as e:
            logger.error(f"Error fetching training data: {e}")
            return pd.DataFrame()

    def _estimate_humidity_for_date(self, date: datetime) -> float:
        """
        Estimate humidity for a given date based on Philippine seasonal patterns.

        Philippine climate has two main seasons:
        - Wet season (June-November): Higher humidity, typically 80-90%
        - Dry season (December-May): Lower humidity, typically 70-80%

        Args:
            date: The date to estimate humidity for

        Returns:
            Estimated humidity percentage
        """
        if hasattr(date, "month"):
            month = date.month
        else:
            # Handle date objects
            month = pd.to_datetime(date).month

        # Wet season: June (6) to November (11)
        if 6 <= month <= 11:
            # Peak monsoon months (July-September) have highest humidity
            if 7 <= month <= 9:
                return 85.0
            return 82.0
        # Dry season: December to May
        else:
            # Hottest months (March-May) have moderate humidity
            if 3 <= month <= 5:
                return 72.0
            return 75.0

    def get_weather_for_prediction(
        self, lat: Optional[float] = None, lon: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get weather data formatted for flood prediction.

        Returns data in the format expected by the prediction service.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Dict with temperature (Kelvin), humidity, precipitation, or None
        """
        observation = self.get_latest_observation(lat, lon)

        if observation is None:
            return None

        # Convert temperature to Kelvin if it's in Celsius
        temp_kelvin = observation.temperature + 273.15 if observation.temperature else None

        return {
            "temperature": temp_kelvin,
            "humidity": observation.humidity,
            "precipitation": observation.precipitation,
            "wind_speed": observation.wind_speed,
            "pressure": observation.pressure,
            "source": "meteostat",
            "station_id": observation.station_id,
            "timestamp": observation.timestamp.isoformat() if observation.timestamp else None,
        }

    @staticmethod
    def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
        """Safely convert a value to float."""
        if pd.isna(value) or value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default


# Module-level convenience functions
def get_meteostat_service() -> MeteostatService:
    """Get the MeteostatService singleton instance."""
    return MeteostatService.get_instance()


def get_historical_weather(
    lat: Optional[float] = None, lon: Optional[float] = None, days: int = 7
) -> List[Dict[str, Any]]:
    """
    Convenience function to get historical daily weather data.

    Args:
        lat: Latitude
        lon: Longitude
        days: Number of days of data to retrieve

    Returns:
        List of daily weather data dictionaries
    """
    service = get_meteostat_service()
    end = datetime.now()
    start = end - timedelta(days=days)
    return service.get_daily_data(lat, lon, start, end)


def get_meteostat_weather_for_ingest(
    lat: Optional[float] = None, lon: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """
    Get weather data from Meteostat for the ingest service.

    Used as a fallback when API calls fail.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Dict with weather data or None
    """
    service = get_meteostat_service()
    if not service.as_fallback:
        return None
    return service.get_weather_for_prediction(lat, lon)


def save_meteostat_data_to_db(lat: Optional[float] = None, lon: Optional[float] = None, hours: int = 24) -> int:
    """
    Fetch and save Meteostat hourly data to the database.

    This is useful for populating historical data or as a scheduled task.

    Args:
        lat: Latitude
        lon: Longitude
        hours: Number of hours of data to fetch and save

    Returns:
        Number of records saved
    """
    from app.models.db import WeatherData, get_db_session

    service = get_meteostat_service()
    if not service.enabled:
        logger.warning("Meteostat is disabled, cannot save data")
        return 0

    end = datetime.now()
    start = end - timedelta(hours=hours)

    observations = service.get_hourly_data(lat, lon, start, end)

    if not observations:
        logger.warning("No Meteostat observations to save")
        return 0

    saved_count = 0
    try:
        with get_db_session() as session:
            for obs in observations:
                # Convert temperature to Kelvin
                temp_kelvin = obs.temperature + 273.15 if obs.temperature else None

                if temp_kelvin is None:
                    continue

                weather_data = WeatherData(
                    temperature=temp_kelvin,
                    humidity=obs.humidity or 70.0,  # Default for tropical
                    precipitation=obs.precipitation or 0.0,
                    wind_speed=obs.wind_speed,
                    pressure=obs.pressure,
                    location_lat=lat or service.default_lat,
                    location_lon=lon or service.default_lon,
                    source="meteostat",
                    station_id=obs.station_id,
                    timestamp=obs.timestamp,
                )
                session.add(weather_data)
                saved_count += 1

        logger.info(f"Saved {saved_count} Meteostat observations to database")
    except Exception as e:
        logger.error(f"Error saving Meteostat data to database: {e}")

    return saved_count
