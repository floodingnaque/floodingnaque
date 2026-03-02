"""
Async Google Earth Engine Weather Service for Satellite Precipitation Data.

Provides asynchronous access to satellite-based precipitation data from Google Earth Engine,
including GPM IMERG (half-hourly) and CHIRPS (daily) datasets.

Since Earth Engine Python API is synchronous, we use asyncio.run_in_executor to run
blocking operations in a thread pool without blocking the event loop.

Features:
- Async fetch satellite precipitation estimates for any location
- Async get accumulated rainfall over custom time periods
- Async access historical climate data via BigQuery
- Automatic service account authentication
- Connection pooling via executor management
- Retry logic with exponential backoff
- Circuit breaker protection for reliability

Prerequisites:
- Google Cloud project with Earth Engine API enabled
- Service account registered with Earth Engine
- GOOGLE_APPLICATION_CREDENTIALS environment variable set
"""

import asyncio
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.constants import DEFAULT_LATITUDE, DEFAULT_LONGITUDE
from app.services.google_weather_types import SatellitePrecipitation, WeatherReanalysis
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

# Lazy imports to avoid startup errors if packages not installed
ee = None
bigquery = None


# Database imports for logging
DB_LOGGING_ENABLED = False
EarthEngineRequest = None  # type: ignore
get_db_session = None  # type: ignore
try:
    from app.models.db import EarthEngineRequest as _EarthEngineRequest
    from app.models.db import get_db_session as _get_db_session

    EarthEngineRequest = _EarthEngineRequest
    get_db_session = _get_db_session
    DB_LOGGING_ENABLED = True
except ImportError:
    pass

logger = logging.getLogger(__name__)


def _lazy_import_ee():
    """Lazy import Earth Engine to avoid startup errors."""
    global ee
    if ee is None:
        try:
            import ee as earth_engine  # type: ignore[import-untyped]

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


class AsyncGoogleWeatherService:
    """
    Async service for fetching weather data from Google Earth Engine and BigQuery.

    Since Earth Engine API is synchronous, uses asyncio.run_in_executor to run
    blocking operations without blocking the event loop.

    Provides satellite precipitation data (GPM, CHIRPS) and historical
    weather reanalysis (ERA5) for flood prediction.
    """

    _instance: Optional["AsyncGoogleWeatherService"] = None
    _instance_lock: threading.Lock = threading.Lock()
    _initialized: bool = False
    _executor: Optional[ThreadPoolExecutor] = None

    # Parañaque City, Philippines default coordinates
    DEFAULT_LAT = DEFAULT_LATITUDE
    DEFAULT_LON = DEFAULT_LONGITUDE

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

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_MIN_WAIT = 1  # seconds
    RETRY_MAX_WAIT = 10  # seconds

    def __init__(self):
        """Initialize the AsyncGoogleWeather Service."""
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

        # Default location (Parañaque City - from central config)
        self.default_lat = float(os.getenv("DEFAULT_LATITUDE", str(DEFAULT_LATITUDE)))
        self.default_lon = float(os.getenv("DEFAULT_LONGITUDE", str(DEFAULT_LONGITUDE)))

        # Thread pool for blocking operations
        max_workers = int(os.getenv("EARTHENGINE_EXECUTOR_WORKERS", "4"))
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="earthengine")

        logger.info(f"AsyncGoogleWeatherService initialized (enabled={self.enabled}, project={self.project_id})")

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

            if get_db_session is None or EarthEngineRequest is None:
                return None

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
    def get_instance(cls) -> "AsyncGoogleWeatherService":
        """Get the singleton instance of AsyncGoogleWeatherService (thread-safe)."""
        if cls._instance is None:
            with cls._instance_lock:
                # Double-checked locking
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        with cls._instance_lock:
            if cls._instance and cls._instance._executor:
                cls._instance._executor.shutdown(wait=False)
            cls._instance = None
            cls._initialized = False

    async def close(self):
        """Shutdown the executor and cleanup resources."""
        if self._executor:
            self._executor.shutdown(wait=True)

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
                credentials = ee_module.ServiceAccountCredentials(  # type: ignore[attr-defined]
                    self.service_account_email, self.credentials_path
                )
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

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def get_gpm_precipitation(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Optional[SatellitePrecipitation]:
        """
        Get GPM IMERG precipitation data for a location asynchronously.

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

        def _fetch_gpm():
            """Blocking function to fetch GPM data."""
            try:
                # Create point geometry
                point = ee.Geometry.Point([lon, lat])  # type: ignore[union-attr]

                # Load GPM collection
                collection = (
                    ee.ImageCollection(self.DATASETS["GPM"]["collection"])  # type: ignore[union-attr]
                    .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
                    .filterBounds(point)
                    .select(self.DATASETS["GPM"]["band"])
                )

                # Get the latest image
                latest = collection.sort("system:time_start", False).first()

                if latest is None:
                    logger.warning(f"No GPM data available for {lat}, {lon}")
                    return None

                # Sample at point
                result = latest.reduceRegion(
                    reducer=ee.Reducer.mean(),  # type: ignore[union-attr]
                    geometry=point,
                    scale=self.DATASETS["GPM"]["scale"],
                ).getInfo()

                precip_rate = result.get(self.DATASETS["GPM"]["band"], 0) or 0

                # Get accumulation over different time periods (simplified)
                # In production, you'd fetch multiple time windows
                accum_1h = precip_rate * 1  # Approximate
                accum_3h = precip_rate * 3  # Approximate
                accum_24h = precip_rate * 24  # Approximate

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
                raise

        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(self._executor, _fetch_gpm)

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

            return result

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            self._log_ee_request(
                request_type="gpm",
                dataset=self.DATASETS["GPM"]["collection"],
                lat=lat,
                lon=lon,
                start_date=start_date,
                end_date=end_date,
                status="error",
                response_time_ms=response_time_ms,
                error_message=str(e),
            )
            raise

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def get_chirps_precipitation(
        self, lat: Optional[float] = None, lon: Optional[float] = None, days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get CHIRPS daily precipitation data for a location asynchronously.

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

        def _fetch_chirps():
            """Blocking function to fetch CHIRPS data."""
            try:
                point = ee.Geometry.Point([lon, lat])  # type: ignore[union-attr]

                collection = (
                    ee.ImageCollection(self.DATASETS["CHIRPS"]["collection"])  # type: ignore[union-attr]
                    .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
                    .filterBounds(point)
                )

                # Get time series
                def extract_value(image):
                    value = image.reduceRegion(
                        reducer=ee.Reducer.mean(),  # type: ignore[union-attr]
                        geometry=point,
                        scale=self.DATASETS["CHIRPS"]["scale"],
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
                raise

        # Run in executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, _fetch_chirps)

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    async def get_era5_weather(
        self, lat: Optional[float] = None, lon: Optional[float] = None, hours: int = 24
    ) -> List[WeatherReanalysis]:
        """
        Get ERA5 reanalysis weather data asynchronously.

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

        def _fetch_era5():
            """Blocking function to fetch ERA5 data."""
            try:
                point = ee.Geometry.Point([lon, lat])  # type: ignore[union-attr]

                collection = (
                    ee.ImageCollection(self.DATASETS["ERA5"]["collection"])  # type: ignore[union-attr]
                    .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
                    .filterBounds(point)
                )

                # Sample values at point
                def extract_values(image):
                    values = image.reduceRegion(
                        reducer=ee.Reducer.mean(),  # type: ignore[union-attr]
                        geometry=point,
                        scale=self.DATASETS["ERA5"]["scale"],
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
                raise

        # Run in executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, _fetch_era5)

    async def get_weather_for_prediction(
        self, lat: Optional[float] = None, lon: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get weather data formatted for flood prediction asynchronously.

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

        # Fetch GPM and ERA5 data concurrently
        gpm_task = self.get_gpm_precipitation(lat, lon)
        era5_task = self.get_era5_weather(lat, lon, hours=3)

        gpm_data, era5_data = await asyncio.gather(gpm_task, era5_task, return_exceptions=True)

        # Handle GPM data
        if not isinstance(gpm_data, BaseException) and gpm_data is not None:
            result["precipitation"] = gpm_data.precipitation_rate
            result["precipitation_1h"] = gpm_data.accumulation_1h
            result["precipitation_3h"] = gpm_data.accumulation_3h
            result["precipitation_24h"] = gpm_data.accumulation_24h

        # Handle ERA5 data
        if not isinstance(era5_data, BaseException) and era5_data is not None and len(era5_data) > 0:
            latest = era5_data[-1]  # Most recent
            result["temperature"] = latest.temperature + 273.15  # Convert to Kelvin
            result["humidity"] = latest.humidity

        # If we have at least precipitation data, return
        if "precipitation" in result:
            return result

        return None

    async def get_historical_for_training(
        self, lat: Optional[float] = None, lon: Optional[float] = None, days: int = 365
    ) -> List[Dict[str, Any]]:
        """
        Get historical weather data formatted for ML training asynchronously.

        Fetches CHIRPS daily precipitation and ERA5 hourly reanalysis in
        parallel, then joins them by date so every training record has
        real temperature, humidity, and precipitation values.

        Args:
            lat: Latitude
            lon: Longitude
            days: Number of days of historical data

        Returns:
            List of daily weather records suitable for training
        """
        import asyncio

        lat = lat or self.default_lat
        lon = lon or self.default_lon

        # Fetch CHIRPS and ERA5 concurrently
        chirps_data, era5_data = await asyncio.gather(
            self.get_chirps_precipitation(lat, lon, days=days),
            self.get_era5_weather(lat, lon, hours=days * 24),
        )

        # Build a date -> (temp, humidity) lookup from ERA5 daily aggregates
        era5_daily: Dict[str, Dict[str, list]] = {}
        for record in era5_data:
            date_key = record.timestamp.strftime("%Y-%m-%d")
            if date_key not in era5_daily:
                era5_daily[date_key] = {"temps": [], "humidities": []}
            era5_daily[date_key]["temps"].append(record.temperature)
            era5_daily[date_key]["humidities"].append(record.humidity)

        era5_averages: Dict[str, Dict[str, float]] = {}
        for date_key, values in era5_daily.items():
            era5_averages[date_key] = {
                "temperature": sum(values["temps"]) / len(values["temps"]),
                "humidity": sum(values["humidities"]) / len(values["humidities"]),
            }

        # Join CHIRPS precipitation with ERA5 temperature/humidity by date
        results = []
        skipped = 0
        for record in chirps_data:
            date_str = record["date"]
            date_key = date_str[:10] if len(date_str) >= 10 else date_str
            era5_match = era5_averages.get(date_key)

            if era5_match is None:
                skipped += 1
                continue

            results.append(
                {
                    "date": date_str,
                    "temperature": round(era5_match["temperature"], 2),
                    "humidity": round(era5_match["humidity"], 2),
                    "precipitation": record["precipitation"],
                    "source": "chirps+era5",
                }
            )

        if skipped:
            logger.warning(
                f"Skipped {skipped}/{len(chirps_data)} CHIRPS days with no ERA5 match"
            )
        logger.info(f"Prepared {len(results)} training records with real ERA5 features")
        return results

    def check_health(self) -> Dict[str, Any]:
        """
        Check the health status of the Google Weather Service.

        Returns:
            Dict with health status information
        """
        status = {
            "service": "AsyncGoogleWeatherService",
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
            "executor_active": self._executor is not None,
        }

        # Test EE initialization
        if self.enabled and not self._initialized:
            try:
                status["ee_initialized"] = self._initialize_ee()
            except Exception as e:
                status["ee_error"] = str(e)

        return status


# Module-level convenience functions
def get_async_google_weather_service() -> AsyncGoogleWeatherService:
    """Get the AsyncGoogleWeatherService singleton instance."""
    return AsyncGoogleWeatherService.get_instance()


async def get_satellite_precipitation_async(
    lat: Optional[float] = None, lon: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """
    Convenience async function to get satellite precipitation data.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Dict with precipitation data or None
    """
    service = get_async_google_weather_service()
    data = await service.get_gpm_precipitation(lat, lon)

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


async def get_google_weather_for_ingest_async(
    lat: Optional[float] = None, lon: Optional[float] = None
) -> Optional[Dict[str, Any]]:
    """
    Get weather data from Google Earth Engine for the ingest service asynchronously.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Dict with weather data or None
    """
    service = get_async_google_weather_service()
    return await service.get_weather_for_prediction(lat, lon)
