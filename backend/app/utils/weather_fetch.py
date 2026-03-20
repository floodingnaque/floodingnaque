"""
Weather Fetch Utility for Location-Based Predictions.

Fetches current weather data from OpenWeatherMap using latitude/longitude
coordinates. Extracts the features required by the flood prediction model.
"""

import logging
import os
import random

import requests
from app.utils.observability.correlation import inject_correlation_headers
from app.utils.resilience.circuit_breaker import CircuitOpenError, openweathermap_breaker, retry_with_backoff
from app.utils.secrets import get_secret

logger = logging.getLogger(__name__)

# Default timeout for OWM API calls (seconds)
OWM_TIMEOUT = int(os.getenv("OWM_TIMEOUT", "10"))


class WeatherFetchError(Exception):
    """Raised when weather data cannot be fetched for given coordinates."""

    pass


# Placeholder values that ship in .env templates — treat as "not configured"
_OWM_PLACEHOLDER_KEYS = {"", "your_openweathermap_api_key_here", "changeme", "CHANGE_ME"}


def _generate_simulated_weather(lat: float, lon: float) -> dict:
    """
    Generate realistic simulated weather data for development/testing.

    Uses a seeded random based on truncated coordinates so the same
    location always returns the same values within a session, producing
    deterministic behaviour that is useful for demos and thesis screenshots.

    Returns dict matching the shape of real OWM-sourced weather data,
    with an extra ``simulated: True`` flag so the frontend can display
    a notice.
    """
    # Seed from truncated coordinates for reproducibility per location
    seed = int(abs(lat * 1000) + abs(lon * 1000))
    rng = random.Random(seed)  # nosec B311 - not used for security, just weather simulation

    # Parañaque-typical tropical ranges
    temp_c = round(rng.uniform(25.0, 35.0), 1)
    humidity = round(rng.uniform(60.0, 95.0), 1)
    precipitation = round(rng.uniform(0.0, 50.0), 1)
    wind_speed = round(rng.uniform(1.0, 15.0), 1)
    pressure = round(rng.uniform(1000.0, 1018.0), 1)

    weather = {
        "temperature": round(temp_c + 273.15, 2),  # Kelvin
        "humidity": humidity,
        "precipitation": precipitation,
        "wind_speed": wind_speed,
        "pressure": pressure,
        "source": "simulated",
        "simulated": True,
    }

    logger.info(
        f"Generated SIMULATED weather for ({lat:.4f}, {lon:.4f}): "
        f"temp={weather['temperature']:.1f}K ({temp_c}°C), "
        f"humidity={humidity}%, precip={precipitation:.1f}mm"
    )
    return weather


def fetch_weather_by_coordinates(lat: float, lon: float) -> dict:
    """
    Fetch current weather data from OpenWeatherMap for the given coordinates.

    In test mode (``TESTING=true``) with no OWM API key configured,
    returns realistic simulated weather data so the prediction flow
    can be tested end-to-end without an external API key.

    Args:
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.

    Returns:
        dict with keys: temperature (Kelvin), humidity (%), precipitation (mm),
        wind_speed (m/s), pressure (hPa), source.  When simulated data is used
        the dict also contains ``simulated: True``.

    Raises:
        WeatherFetchError: If the API key is missing (production) or the API call fails.
    """
    owm_api_key = get_secret("OWM_API_KEY")
    if not owm_api_key or owm_api_key in _OWM_PLACEHOLDER_KEYS:
        # Only allow simulated weather in test environments (TESTING=true)
        is_testing = os.getenv("TESTING", "").lower() in ("1", "true", "yes")
        if is_testing:
            logger.warning("OWM_API_KEY not configured — returning simulated weather (test mode).")
            return _generate_simulated_weather(lat, lon)
        raise WeatherFetchError("OWM_API_KEY is not configured on the server.")

    owm_url = f"https://api.openweathermap.org/data/2.5/weather" f"?lat={lat}&lon={lon}&appid={owm_api_key}"

    try:

        @retry_with_backoff(
            max_retries=2,
            base_delay=1.0,
            exceptions=(requests.exceptions.RequestException,),
        )
        def _call_owm():
            headers = inject_correlation_headers({"User-Agent": "FloodingNaque/2.0 (Location Prediction)"})
            response = requests.get(owm_url, timeout=OWM_TIMEOUT, headers=headers)
            response.raise_for_status()
            return response.json()

        owm_data = openweathermap_breaker.call(_call_owm)

    except CircuitOpenError:
        logger.error("OpenWeatherMap circuit breaker is open - cannot fetch weather.")
        raise WeatherFetchError("Weather service is temporarily unavailable. Please try again later.")
    except requests.exceptions.RequestException as exc:
        logger.error(f"OpenWeatherMap request failed for ({lat}, {lon}): {exc}")
        raise WeatherFetchError("Failed to fetch weather data. Please check your connection and try again.")

    # Validate response structure
    if "main" not in owm_data:
        logger.error(f"Invalid OWM response for ({lat}, {lon}): missing 'main'")
        raise WeatherFetchError("Invalid response from weather service.")

    main = owm_data["main"]
    wind = owm_data.get("wind", {})
    rain = owm_data.get("rain", {})

    # Extract precipitation (mm in last 1h or 3h)
    precipitation = 0.0
    if "1h" in rain:
        precipitation = float(rain["1h"])
    elif "3h" in rain:
        precipitation = float(rain["3h"]) / 3.0  # convert 3h to hourly

    weather_data = {
        "temperature": float(main.get("temp", 0)),  # Already in Kelvin from OWM
        "humidity": float(main.get("humidity", 0)),
        "precipitation": precipitation,
        "wind_speed": float(wind.get("speed", 0)),  # m/s
        "pressure": float(main.get("pressure", 0)),  # hPa
        "source": "openweathermap",
    }

    logger.info(
        f"Fetched weather for ({lat:.4f}, {lon:.4f}): "
        f"temp={weather_data['temperature']:.1f}K, "
        f"humidity={weather_data['humidity']}%, "
        f"precip={weather_data['precipitation']:.1f}mm"
    )

    return weather_data
