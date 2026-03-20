import logging
import os
import re
import threading
import time as _time
from datetime import datetime

import requests
from app.core.constants import DEFAULT_LATITUDE, DEFAULT_LONGITUDE
from app.models.db import WeatherData, get_db_session
from app.utils.observability.correlation import inject_correlation_headers
from app.utils.observability.metrics import record_circuit_breaker_state, record_external_api_call
from app.utils.resilience.cache import cache_get, cache_set
from app.utils.resilience.circuit_breaker import (
    CircuitOpenError,
    openweathermap_breaker,
    retry_with_backoff,
    weatherstack_breaker,
)
from app.utils.secrets import get_secret

logger = logging.getLogger(__name__)

# Lazy import for meteostat to avoid import errors if not installed
_meteostat_service = None
_worldtides_service = None
_service_init_lock = threading.Lock()


def _get_meteostat_service():
    """Lazy load meteostat service (thread-safe)."""
    global _meteostat_service
    if _meteostat_service is None:
        with _service_init_lock:
            # Double-checked locking
            if _meteostat_service is None:
                try:
                    from app.services.meteostat_service import get_meteostat_service

                    _meteostat_service = get_meteostat_service()
                except ImportError:
                    logger.warning("Meteostat is not installed. Install with: pip install meteostat")
                    _meteostat_service = False  # Mark as unavailable
    return _meteostat_service if _meteostat_service else None


def _get_worldtides_service():
    """Lazy load WorldTides service (thread-safe)."""
    global _worldtides_service
    if _worldtides_service is None:
        with _service_init_lock:
            # Double-checked locking
            if _worldtides_service is None:
                try:
                    from app.services.worldtides_service import get_worldtides_service

                    _worldtides_service = get_worldtides_service()
                except ImportError:
                    logger.warning("WorldTides service not available")
                    _worldtides_service = False  # Mark as unavailable
    return _worldtides_service if _worldtides_service else None


# Regex pattern for redacting API keys in URLs/logs
_API_KEY_PATTERNS = [
    (re.compile(r"(appid=)[^&]+"), r"\1[REDACTED]"),
    (re.compile(r"(access_key=)[^&]+"), r"\1[REDACTED]"),
    (re.compile(r"(api_key=)[^&]+"), r"\1[REDACTED]"),
    (re.compile(r"(key=)[^&]+"), r"\1[REDACTED]"),
]


def _redact_api_keys(text: str) -> str:
    """Redact API keys from URLs and log messages."""
    result = text
    for pattern, replacement in _API_KEY_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def _safe_log_url(url: str) -> str:
    """Return a URL safe for logging (with API keys redacted)."""
    return _redact_api_keys(url)


def ingest_data(lat=None, lon=None):
    """
    Ingest weather data from external APIs.

    Args:
        lat: Latitude (default: 40.7128 - New York City)
        lon: Longitude (default: -74.0060 - New York City)

    Returns:
        dict: Weather data dictionary
    """
    # API keys from environment variables
    owm_api_key = get_secret("OWM_API_KEY")
    # Note: METEOSTAT_API_KEY can also be used for Weatherstack API
    weatherstack_api_key = get_secret("METEOSTAT_API_KEY") or get_secret("WEATHERSTACK_API_KEY")

    # Default location: Parañaque City, Philippines (from environment or central config)
    if lat is None:
        lat = float(os.getenv("DEFAULT_LATITUDE", str(DEFAULT_LATITUDE)))
    if lon is None:
        lon = float(os.getenv("DEFAULT_LONGITUDE", str(DEFAULT_LONGITUDE)))

    # Validate API keys
    if not owm_api_key:
        raise ValueError("OWM_API_KEY environment variable is not set")

    data = {}

    try:
        # Fetch from OpenWeatherMap with circuit breaker protection
        # Note: OWM requires appid in query string, but we redact in logs
        owm_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={owm_api_key}"
        logger.debug("Fetching weather data from OpenWeatherMap")

        # Check cache first (5-minute TTL to avoid hammering the API)
        owm_cache_key = f"owm:weather:{lat}:{lon}"
        cached_owm = cache_get(owm_cache_key)
        _t0 = _time.monotonic()
        if cached_owm is not None:
            logger.debug("Using cached OWM response")
            owm_data = cached_owm
        else:

            @retry_with_backoff(max_retries=2, base_delay=1.0, exceptions=(requests.exceptions.RequestException,))
            def fetch_owm():
                # Inject correlation headers for distributed tracing
                headers = inject_correlation_headers({"User-Agent": "FloodingNaque/2.0 (Flood Prediction API)"})
                response = requests.get(owm_url, timeout=10, headers=headers)
                response.raise_for_status()
                return response.json()

            _t0 = _time.monotonic()
            owm_data = openweathermap_breaker.call(fetch_owm)
            record_external_api_call("openweathermap", "success", _time.monotonic() - _t0)
            cache_set(owm_cache_key, owm_data, ttl=300)

        if "main" not in owm_data:
            raise ValueError("Invalid response from OpenWeatherMap API")

        data["temperature"] = owm_data["main"].get("temp", 0)
        data["humidity"] = owm_data["main"].get("humidity", 0)

        logger.info(f"Successfully fetched data from OpenWeatherMap for lat={lat}, lon={lon}")
    except CircuitOpenError as e:
        record_external_api_call("openweathermap", "circuit_open", 0.0)
        record_circuit_breaker_state("openweathermap", "open")
        logger.error(f"OpenWeatherMap circuit breaker is open: {str(e)}")
        raise
    except requests.exceptions.RequestException as e:
        record_external_api_call("openweathermap", "error", _time.monotonic() - _t0)
        logger.error(f"Error fetching data from OpenWeatherMap: {str(e)}")
        raise
    except (KeyError, ValueError) as e:
        record_external_api_call("openweathermap", "error", _time.monotonic() - _t0)
        logger.error(f"Error parsing OpenWeatherMap response: {str(e)}")
        raise

    # Fetch precipitation data
    # Priority: OpenWeatherMap rain > Weatherstack API (conserves 250 req/month quota)
    precipitation = 0

    # Try OpenWeatherMap rain data first (already fetched, no extra API call)
    try:
        if "rain" in owm_data and "3h" in owm_data["rain"]:
            precipitation = owm_data["rain"]["3h"] / 3.0  # Convert 3h to hourly rate
            logger.info("Retrieved precipitation data from OpenWeatherMap (3h)")
        elif "rain" in owm_data and "1h" in owm_data["rain"]:
            precipitation = owm_data["rain"]["1h"]
            logger.info("Retrieved precipitation data from OpenWeatherMap (1h)")
    except (KeyError, TypeError):
        logger.debug("No rain data in OpenWeatherMap response")

    # Fallback to Weatherstack API only when OWM has no precipitation data
    if precipitation == 0 and weatherstack_api_key:
        try:
            # Check if circuit breaker is open before attempting
            if weatherstack_breaker.is_open:
                logger.warning("Weatherstack circuit breaker is open, skipping to fallback")
            else:
                # Check Weatherstack cache first (10-min TTL — conserves 250 req/month quota)
                ws_cache_key = f"weatherstack:precip:{lat}:{lon}"
                cached_ws = cache_get(ws_cache_key)
                if cached_ws is not None:
                    if "current" in cached_ws:
                        precip_value = cached_ws["current"].get("precip", 0)
                        if precip_value is not None:
                            precipitation = float(precip_value)
                            logger.debug("Using cached Weatherstack precipitation data")
                else:
                    # Weatherstack API endpoint for current weather
                    # Note: HTTPS requires paid plan, but we use it for security
                    # Free tier users should upgrade or the request will fail gracefully
                    weatherstack_url = f"https://api.weatherstack.com/current?access_key={weatherstack_api_key}&query={lat},{lon}&units=m"
                    logger.debug("Fetching precipitation data from Weatherstack")

                    @retry_with_backoff(
                        max_retries=2, base_delay=1.0, exceptions=(requests.exceptions.RequestException,)
                    )
                    def fetch_weatherstack():
                        # Inject correlation headers for distributed tracing
                        headers = inject_correlation_headers({"User-Agent": "FloodingNaque/2.0 (Flood Prediction API)"})
                        response = requests.get(weatherstack_url, timeout=10, headers=headers)
                        response.raise_for_status()
                        return response.json()

                    _t1 = _time.monotonic()
                    weatherstack_data = weatherstack_breaker.call(fetch_weatherstack)
                    record_external_api_call("weatherstack", "success", _time.monotonic() - _t1)

                    # Cache the response (10-min TTL)
                    cache_set(ws_cache_key, weatherstack_data, ttl=600)

                    # Check for errors in Weatherstack response
                    if "error" in weatherstack_data:
                        # Don't log external API error details - may contain sensitive info
                        logger.warning("Weatherstack API returned an error response")
                    elif "current" in weatherstack_data:
                        # Weatherstack provides precipitation in 'precip' field (mm)
                        precip_value = weatherstack_data["current"].get("precip", 0)
                        if precip_value is not None:
                            precipitation = float(precip_value)
                            logger.info("Retrieved precipitation data from Weatherstack")
        except CircuitOpenError:
            record_external_api_call("weatherstack", "circuit_open", 0.0)
            record_circuit_breaker_state("weatherstack", "open")
            logger.warning("Weatherstack circuit breaker open (using fallback)")
        except requests.exceptions.RequestException:
            record_external_api_call("weatherstack", "error", _time.monotonic() - _t1)
            logger.warning("Error fetching data from Weatherstack API (continuing with OpenWeatherMap)")
        except (KeyError, ValueError, TypeError):
            record_external_api_call("weatherstack", "error", _time.monotonic() - _t1)
            logger.warning("Error parsing Weatherstack response (continuing with OpenWeatherMap)")

    data["precipitation"] = precipitation
    data["timestamp"] = datetime.now()

    # If we still have no precipitation data, try Meteostat as final fallback
    if precipitation == 0 and os.getenv("METEOSTAT_AS_FALLBACK", "True").lower() == "true":
        meteostat_svc = _get_meteostat_service()
        if meteostat_svc:
            _t2 = _time.monotonic()
            try:
                meteostat_data = meteostat_svc.get_weather_for_prediction(lat, lon)
                record_external_api_call("meteostat", "success", _time.monotonic() - _t2)
                if meteostat_data and meteostat_data.get("precipitation"):
                    precipitation = meteostat_data["precipitation"]
                    data["precipitation"] = precipitation
                    data["source"] = "OWM+Meteostat"
                    logger.info(f"Got precipitation from Meteostat fallback: {precipitation} mm")
            except Exception as e:
                record_external_api_call("meteostat", "error", _time.monotonic() - _t2)
                logger.debug(f"Meteostat fallback failed: {e}")

    # ---------------------------------------------------------------------------
    # PAGASA Radar-based precipitation - barangay-level estimates
    # ---------------------------------------------------------------------------
    # If PAGASA radar integration is enabled, fetch per-barangay precipitation
    # from Doppler radar QPE and use the nearest-barangay estimate to supplement
    # or replace the station-level precipitation value.
    if os.getenv("PAGASA_RADAR_ENABLED", "True").lower() == "true":
        try:
            from app.core.constants import get_nearest_station
            from app.services.pagasa_radar_service import get_pagasa_radar_service

            pagasa = get_pagasa_radar_service()
            if pagasa.is_enabled():
                city_precip = pagasa.get_city_precipitation()
                if city_precip.get("status") == "ok":
                    # Find nearest barangay to requested coordinates
                    best_key = None
                    best_dist = float("inf")
                    for brgy_key, brgy in city_precip.get("barangays", {}).items():
                        d = (brgy.get("lat", 0) - lat) ** 2 + (brgy.get("lon", 0) - lon) ** 2
                        if d < best_dist:
                            best_dist = d
                            best_key = brgy_key

                    if best_key:
                        radar_rain = city_precip["barangays"][best_key].get("rainfall_mm", 0)
                        if radar_rain > 0:
                            # Use the higher of radar vs station estimate (conservative)
                            if radar_rain > precipitation:
                                data["precipitation"] = radar_rain
                                data["precipitation_source"] = "pagasa_radar"
                                precipitation = radar_rain
                                logger.info(
                                    f"PAGASA radar estimate ({radar_rain:.1f} mm) > station "
                                    f"({data.get('precipitation', 0):.1f} mm) - using radar"
                                )
                            else:
                                data["precipitation_radar_mm"] = radar_rain
                                data["precipitation_source"] = "station"

                    # Attach full barangay-level data for downstream consumers
                    data["pagasa_radar"] = {
                        "summary": city_precip.get("summary"),
                        "barangay_count": len(city_precip.get("barangays", {})),
                        "source": city_precip.get("summary", {}).get("source", "pagasa_radar"),
                    }
                    logger.info("PAGASA radar precipitation integrated into ingest data")
        except ImportError:
            logger.debug("PAGASA radar service not available")
        except Exception as e:
            logger.warning(f"PAGASA radar integration failed (non-critical): {e}")

    # Fetch tide data from WorldTides API (for coastal flood prediction)
    if os.getenv("WORLDTIDES_ENABLED", "True").lower() == "true":
        worldtides_svc = _get_worldtides_service()
        if worldtides_svc and worldtides_svc.is_available():
            try:
                tide_data = worldtides_svc.get_tide_data_for_prediction(lat, lon)
                if tide_data:
                    data["tide_height"] = tide_data.get("tide_height")
                    data["tide_trend"] = tide_data.get("tide_trend")
                    data["tide_risk_factor"] = tide_data.get("tide_risk_factor")
                    data["hours_until_high_tide"] = tide_data.get("hours_until_high_tide")
                    logger.info(
                        f"Got tide data: height={tide_data.get('tide_height'):.2f}m, "
                        f"trend={tide_data.get('tide_trend')}, "
                        f"risk_factor={tide_data.get('tide_risk_factor'):.2f}"
                    )
            except Exception as e:
                logger.warning(f"Failed to fetch tide data: {e}")

    # Save to DB
    try:
        # Remove keys that are not WeatherData columns before persisting
        db_data = {k: v for k, v in data.items() if hasattr(WeatherData, k)}
        with get_db_session() as session:
            weather_data = WeatherData(**db_data)
            session.add(weather_data)
        logger.info("Successfully saved weather data to database")
    except Exception as e:
        logger.error(f"Error saving data to database: {str(e)}")
        raise

    return data
