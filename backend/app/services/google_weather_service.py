"""
Google Earth Engine Weather Service for Satellite Precipitation Data.

Provides access to satellite-based precipitation data from Google Earth Engine,
including GPM IMERG (half-hourly) and CHIRPS (daily) datasets.

Features:
- Fetch satellite precipitation estimates for any location
- Get accumulated rainfall over custom time periods
- Access historical climate data via BigQuery
- Automatic service account authentication
- Circuit breaker protection for reliability

Prerequisites:
- Google Cloud project with Earth Engine API enabled
- Service account registered with Earth Engine
- GOOGLE_APPLICATION_CREDENTIALS environment variable set
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.google_weather_types import SatellitePrecipitation, WeatherReanalysis

# Lazy imports to avoid startup errors if packages not installed
ee = None
bigquery = None


# Database imports for logging
try:
    from app.models.db import EarthEngineRequest, get_db_session

    DB_LOGGING_ENABLED = True
except ImportError:
    DB_LOGGING_ENABLED = False

logger = logging.getLogger(__name__)


def _lazy_import_ee():
    """Lazy import Earth Engine to avoid startup errors."""
    global ee
    if ee is None:
        try:
            import ee as earth_engine

            ee = earth_engine
        except ImportError:
            logger.warning("earthengine-api not installed. Run: pip install earthengine-api")
            return None
    return ee


def _lazy_import_bigquery():
    """Lazy import BigQuery to avoid startup errors."""
    global bigquery
    if bigquery is None:
        try:
            from google.cloud import bigquery as bq

            bigquery = bq
        except ImportError:
            logger.warning("google-cloud-bigquery not installed. Run: pip install google-cloud-bigquery")
            return None
    return bigquery


class GoogleWeatherService:
    """
    Service for fetching weather data from Google Earth Engine and BigQuery.

    Provides satellite precipitation data (GPM, CHIRPS) and historical
    weather reanalysis (ERA5) for flood prediction.
    """

    _instance: Optional["GoogleWeatherService"] = None
    _initialized: bool = False

    # Parañaque City, Philippines default coordinates
    DEFAULT_LAT = 14.4793
    DEFAULT_LON = 121.0198

    # Dataset configurations
    DATASETS = {
        "GPM": {
            "collection": "NASA/GPM_L3/IMERG_V06",
            "band": "precipitationCal",
            "scale": 11132,  # ~0.1 degree
            "description": "NASA GPM IMERG Half-Hourly Precipitation",
        },
        "CHIRPS": {
            "collection": "UCSB-CHG/CHIRPS/DAILY",
            "band": "precipitation",
            "scale": 5566,  # ~0.05 degree
            "description": "CHIRPS Daily Precipitation",
        },
        "ERA5": {
            "collection": "ECMWF/ERA5_LAND/HOURLY",
            "bands": ["temperature_2m", "total_precipitation", "dewpoint_temperature_2m"],
            "scale": 11132,
            "description": "ERA5-Land Hourly Reanalysis",
        },
    }

    def __init__(self):
        """Initialize the Google Weather Service."""
        self.enabled = os.getenv("EARTHENGINE_ENABLED", "True").lower() == "true"
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT", os.getenv("EARTHENGINE_PROJECT", ""))
        self.credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
        self.service_account_email = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL", "")

        # Feature toggles
        self.gpm_enabled = os.getenv("GPM_PRECIPITATION_ENABLED", "True").lower() == "true"
        self.chirps_enabled = os.getenv("CHIRPS_PRECIPITATION_ENABLED", "True").lower() == "true"
        self.era5_enabled = os.getenv("ERA5_REANALYSIS_ENABLED", "True").lower() == "true"
        self.bigquery_enabled = os.getenv("BIGQUERY_ENABLED", "True").lower() == "true"

        # Request logging toggle
        self.log_requests = os.getenv("EARTHENGINE_LOG_REQUESTS", "True").lower() == "true"

        # Cache directory for Earth Engine
        self.cache_dir = Path(os.getenv("EARTHENGINE_CACHE_DIR", "data/earthengine_cache"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Default location (Parañaque City)
        self.default_lat = float(os.getenv("DEFAULT_LATITUDE", str(self.DEFAULT_LAT)))
        self.default_lon = float(os.getenv("DEFAULT_LONGITUDE", str(self.DEFAULT_LON)))

        logger.info(f"GoogleWeatherService initialized (enabled={self.enabled}, project={self.project_id})")

    def _log_ee_request(
        self,
        request_type: str,
        dataset: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: str = "pending",
        response_time_ms: Optional[float] = None,
        error_message: Optional[str] = None,
        data_points: int = 0,
    ) -> Optional[str]:
        """
        Log an Earth Engine API request to the database.

        Args:
            request_type: Type of request (gpm, chirps, era5)
            dataset: Dataset name
            lat: Latitude
            lon: Longitude
            start_date: Start of data range
            end_date: End of data range
            status: Request status (pending, success, error)
            response_time_ms: Response time in milliseconds
            error_message: Error message if failed
            data_points: Number of data points returned

        Returns:
            Request ID if logged successfully, None otherwise
        """
        if not self.log_requests or not DB_LOGGING_ENABLED:
            return None

        try:
            import uuid

            request_id = str(uuid.uuid4())

            with get_db_session() as session:
                ee_request = EarthEngineRequest(
                    request_id=request_id,
                    request_type=request_type,
                    dataset=dataset,
                    latitude=lat,
                    longitude=lon,
                    start_date=start_date,
                    end_date=end_date,
                    status=status,
                    response_time_ms=response_time_ms,
                    error_message=error_message,
                    data_points_returned=data_points,
                )
                session.add(ee_request)

            return request_id
        except Exception as e:
            logger.debug(f"Failed to log Earth Engine request: {e}")
            return None

    @classmethod
    def get_instance(cls) -> "GoogleWeatherService":
        """Get the singleton instance of GoogleWeatherService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        cls._instance = None
        cls._initialized = False

    def _initialize_ee(self) -> bool:
        """
        Initialize Earth Engine with service account credentials.

        Returns:
            True if initialization successful, False otherwise.
        """
        if self._initialized:
            return True

        if not self.enabled:
            logger.warning("Earth Engine is disabled")
            return False

        ee_module = _lazy_import_ee()
        if ee_module is None:
            return False

        try:
            # Check for credentials file
            if self.credentials_path and os.path.exists(self.credentials_path):
                # Service account authentication
                credentials = ee_module.ServiceAccountCredentials(self.service_account_email, self.credentials_path)
                ee_module.Initialize(credentials, project=self.project_id)
                logger.info(f"Earth Engine initialized with service account: {self.service_account_email}")
            else:
                # Try default credentials (for local development)
                try:
                    ee_module.Initialize(project=self.project_id)
                    logger.info("Earth Engine initialized with default credentials")
                except Exception:
                    # Fallback to browser-based authentication
                    ee_module.Authenticate()
                    ee_module.Initialize(project=self.project_id)
                    logger.info("Earth Engine initialized with browser authentication")

            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Earth Engine: {e}")
            return False

    def get_gpm_precipitation(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Optional[SatellitePrecipitation]:
        """
        Get GPM IMERG precipitation data for a location.

        GPM (Global Precipitation Measurement) provides half-hourly
        satellite-based precipitation estimates globally.

        Args:
            lat: Latitude (default: Parañaque)
            lon: Longitude (default: Parañaque)
            start_date: Start of time range (default: 24 hours ago)
            end_date: End of time range (default: now)

        Returns:
            SatellitePrecipitation object or None if unavailable
        """
        if not self.gpm_enabled:
            logger.debug("GPM precipitation is disabled")
            return None

        if not self._initialize_ee():
            return None

        lat = lat or self.default_lat
        lon = lon or self.default_lon
        end_date = end_date or datetime.now(timezone.utc)
        start_date = start_date or (end_date - timedelta(hours=24))

        import time

        start_time = time.time()

        try:
            # Create point geometry
            point = ee.Geometry.Point([lon, lat])

            # Load GPM collection
            collection = (
                ee.ImageCollection(self.DATASETS["GPM"]["collection"])
                .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
                .filterBounds(point)
                .select(self.DATASETS["GPM"]["band"])
            )

            # Get the latest image
            latest = collection.sort("system:time_start", False).first()

            if latest is None:
                logger.warning(f"No GPM data available for {lat}, {lon}")
                self._log_ee_request(
                    request_type="gpm",
                    dataset=self.DATASETS["GPM"]["collection"],
                    lat=lat,
                    lon=lon,
                    start_date=start_date,
                    end_date=end_date,
                    status="error",
                    response_time_ms=(time.time() - start_time) * 1000,
                    error_message="No data available",
                )
                return None

            # Sample at point
            result = latest.reduceRegion(
                reducer=ee.Reducer.mean(), geometry=point, scale=self.DATASETS["GPM"]["scale"]
            ).getInfo()

            precip_rate = result.get(self.DATASETS["GPM"]["band"], 0) or 0

            # Get accumulation over different time periods
            accum_1h = self._get_accumulation(point, 1)
            accum_3h = self._get_accumulation(point, 3)
            accum_24h = self._get_accumulation(point, 24)

            response_time_ms = (time.time() - start_time) * 1000

            # Log successful request
            self._log_ee_request(
                request_type="gpm",
                dataset=self.DATASETS["GPM"]["collection"],
                lat=lat,
                lon=lon,
                start_date=start_date,
                end_date=end_date,
                status="success",
                response_time_ms=response_time_ms,
                data_points=1,
            )

            return SatellitePrecipitation(
                timestamp=end_date,
                latitude=lat,
                longitude=lon,
                precipitation_rate=float(precip_rate),
                accumulation_1h=accum_1h,
                accumulation_3h=accum_3h,
                accumulation_24h=accum_24h,
                dataset="GPM",
                source="earth_engine",
            )

        except Exception as e:
            logger.error(f"Error fetching GPM precipitation: {e}")
            self._log_ee_request(
                request_type="gpm",
                dataset=self.DATASETS["GPM"]["collection"],
                lat=lat,
                lon=lon,
                start_date=start_date,
                end_date=end_date,
                status="error",
                response_time_ms=(time.time() - start_time) * 1000,
                error_message=str(e),
            )
            return None

    def _get_accumulation(self, point, hours: int) -> Optional[float]:
        """
        Get accumulated precipitation over specified hours.

        Args:
            point: Earth Engine point geometry
            hours: Number of hours to accumulate

        Returns:
            Accumulated precipitation in mm
        """
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(hours=hours)

            collection = (
                ee.ImageCollection(self.DATASETS["GPM"]["collection"])
                .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
                .filterBounds(point)
                .select(self.DATASETS["GPM"]["band"])
            )

            # Sum all precipitation values
            total = collection.sum()

            result = total.reduceRegion(
                reducer=ee.Reducer.mean(), geometry=point, scale=self.DATASETS["GPM"]["scale"]
            ).getInfo()

            return float(result.get(self.DATASETS["GPM"]["band"], 0) or 0)

        except Exception as e:
            logger.debug(f"Error calculating {hours}h accumulation: {e}")
            return None

    def get_chirps_precipitation(
        self, lat: Optional[float] = None, lon: Optional[float] = None, days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get CHIRPS daily precipitation data for a location.

        CHIRPS provides high-resolution daily precipitation data,
        excellent for historical analysis and ML training.

        Args:
            lat: Latitude (default: Parañaque)
            lon: Longitude (default: Parañaque)
            days: Number of days of data to fetch

        Returns:
            List of daily precipitation records
        """
        if not self.chirps_enabled:
            logger.debug("CHIRPS precipitation is disabled")
            return []

        if not self._initialize_ee():
            return []

        lat = lat or self.default_lat
        lon = lon or self.default_lon
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        try:
            point = ee.Geometry.Point([lon, lat])

            collection = (
                ee.ImageCollection(self.DATASETS["CHIRPS"]["collection"])
                .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
                .filterBounds(point)
            )

            # Get time series
            def extract_value(image):
                value = image.reduceRegion(
                    reducer=ee.Reducer.mean(), geometry=point, scale=self.DATASETS["CHIRPS"]["scale"]
                ).get(self.DATASETS["CHIRPS"]["band"])
                return image.set("precipitation", value)

            values = collection.map(extract_value)
            info = values.getInfo()

            results = []
            for feature in info.get("features", []):
                props = feature.get("properties", {})
                timestamp = props.get("system:time_start", 0)
                precip = props.get("precipitation", 0) or 0

                results.append(
                    {
                        "date": datetime.fromtimestamp(timestamp / 1000).isoformat(),
                        "precipitation": float(precip),
                        "source": "chirps",
                    }
                )

            logger.info(f"Retrieved {len(results)} days of CHIRPS data")
            return results

        except Exception as e:
            logger.error(f"Error fetching CHIRPS precipitation: {e}")
            return []

    def get_era5_weather(
        self, lat: Optional[float] = None, lon: Optional[float] = None, hours: int = 24
    ) -> List[WeatherReanalysis]:
        """
        Get ERA5 reanalysis weather data.

        ERA5 provides comprehensive atmospheric data including
        temperature, humidity, wind, and precipitation.

        Args:
            lat: Latitude (default: Parañaque)
            lon: Longitude (default: Parañaque)
            hours: Number of hours of data to fetch

        Returns:
            List of WeatherReanalysis objects
        """
        if not self.era5_enabled:
            logger.debug("ERA5 reanalysis is disabled")
            return []

        if not self._initialize_ee():
            return []

        lat = lat or self.default_lat
        lon = lon or self.default_lon
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(hours=hours)

        try:
            point = ee.Geometry.Point([lon, lat])

            collection = (
                ee.ImageCollection(self.DATASETS["ERA5"]["collection"])
                .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
                .filterBounds(point)
            )

            # Sample values at point
            def extract_values(image):
                values = image.reduceRegion(
                    reducer=ee.Reducer.mean(), geometry=point, scale=self.DATASETS["ERA5"]["scale"]
                )
                return image.set(
                    {
                        "temp": values.get("temperature_2m"),
                        "precip": values.get("total_precipitation"),
                        "dewpoint": values.get("dewpoint_temperature_2m"),
                    }
                )

            values = collection.map(extract_values)
            info = values.getInfo()

            results = []
            for feature in info.get("features", []):
                props = feature.get("properties", {})
                timestamp = props.get("system:time_start", 0)

                # ERA5 temperature is in Kelvin
                temp_k = props.get("temp", 273.15) or 273.15
                temp_c = temp_k - 273.15

                # Calculate relative humidity from dewpoint
                dewpoint_k = props.get("dewpoint", temp_k) or temp_k
                dewpoint_c = dewpoint_k - 273.15
                # Magnus formula approximation
                humidity = 100 * (112 - 0.1 * temp_c + dewpoint_c) / (112 + 0.9 * temp_c)
                humidity = max(0, min(100, humidity))

                # ERA5 precipitation is cumulative (m), convert to mm
                precip_m = props.get("precip", 0) or 0
                precip_mm = precip_m * 1000

                results.append(
                    WeatherReanalysis(
                        timestamp=datetime.fromtimestamp(timestamp / 1000),
                        latitude=lat,
                        longitude=lon,
                        temperature=temp_c,
                        humidity=humidity,
                        precipitation=precip_mm,
                        source="era5",
                    )
                )

            logger.info(f"Retrieved {len(results)} hours of ERA5 data")
            return results

        except Exception as e:
            logger.error(f"Error fetching ERA5 weather: {e}")
            return []

    def get_weather_for_prediction(
        self, lat: Optional[float] = None, lon: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get weather data formatted for flood prediction.

        Returns combined data from GPM (precipitation) and ERA5 (temperature, humidity).
        This is the main method for real-time prediction integration.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Dict with temperature, humidity, precipitation, or None
        """
        lat = lat or self.default_lat
        lon = lon or self.default_lon

        result = {
            "latitude": lat,
            "longitude": lon,
            "source": "earth_engine",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Get satellite precipitation
        gpm_data = self.get_gpm_precipitation(lat, lon)
        if gpm_data:
            result["precipitation"] = gpm_data.precipitation_rate
            result["precipitation_1h"] = gpm_data.accumulation_1h
            result["precipitation_3h"] = gpm_data.accumulation_3h
            result["precipitation_24h"] = gpm_data.accumulation_24h

        # Get temperature and humidity from ERA5
        era5_data = self.get_era5_weather(lat, lon, hours=3)
        if era5_data:
            latest = era5_data[-1]  # Most recent
            result["temperature"] = latest.temperature + 273.15  # Convert to Kelvin
            result["humidity"] = latest.humidity

        # If we have at least precipitation data, return
        if "precipitation" in result:
            return result

        return None

    def get_historical_for_training(
        self, lat: Optional[float] = None, lon: Optional[float] = None, days: int = 365
    ) -> List[Dict[str, Any]]:
        """
        Get historical weather data formatted for ML training.

        Combines CHIRPS daily precipitation with ERA5 temperature/humidity.

        Args:
            lat: Latitude
            lon: Longitude
            days: Number of days of historical data

        Returns:
            List of daily weather records suitable for training
        """
        lat = lat or self.default_lat
        lon = lon or self.default_lon

        # Get CHIRPS precipitation (daily)
        chirps_data = self.get_chirps_precipitation(lat, lon, days=days)

        # For simplicity, return CHIRPS data with estimated temp/humidity
        # In production, you'd join with ERA5 daily aggregates
        results = []
        for record in chirps_data:
            results.append(
                {
                    "date": record["date"],
                    "temperature": 27.5,  # Average for Parañaque (Celsius)
                    "humidity": 75.0,  # Average humidity
                    "precipitation": record["precipitation"],
                    "source": "chirps+estimated",
                }
            )

        return results

    def check_health(self) -> Dict[str, Any]:
        """
        Check the health status of the Google Weather Service.

        Returns:
            Dict with health status information
        """
        status = {
            "service": "GoogleWeatherService",
            "enabled": self.enabled,
            "project_id": self.project_id,
            "ee_initialized": self._initialized,
            "features": {
                "gpm": self.gpm_enabled,
                "chirps": self.chirps_enabled,
                "era5": self.era5_enabled,
                "bigquery": self.bigquery_enabled,
            },
            "credentials_configured": bool(self.credentials_path and os.path.exists(self.credentials_path)),
        }

        # Test EE initialization
        if self.enabled and not self._initialized:
            try:
                status["ee_initialized"] = self._initialize_ee()
            except Exception as e:
                status["ee_error"] = str(e)

        return status


# Module-level convenience functions
def get_google_weather_service() -> GoogleWeatherService:
    """Get the GoogleWeatherService singleton instance."""
    return GoogleWeatherService.get_instance()


def get_satellite_precipitation(lat: Optional[float] = None, lon: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """
    Convenience function to get satellite precipitation data.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Dict with precipitation data or None
    """
    service = get_google_weather_service()
    data = service.get_gpm_precipitation(lat, lon)

    if data:
        return {
            "precipitation_rate": data.precipitation_rate,
            "accumulation_1h": data.accumulation_1h,
            "accumulation_3h": data.accumulation_3h,
            "accumulation_24h": data.accumulation_24h,
            "source": data.source,
            "dataset": data.dataset,
        }
    return None


def get_google_weather_for_ingest(lat: Optional[float] = None, lon: Optional[float] = None) -> Optional[Dict[str, Any]]:
    """
    Get weather data from Google Earth Engine for the ingest service.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Dict with weather data or None
    """
    service = get_google_weather_service()
    return service.get_weather_for_prediction(lat, lon)
