"""
Application Constants.

Centralized constants for the Floodingnaque API.
"""

# API Version
API_VERSION = "2.0.0"
API_NAME = "Floodingnaque API"

# =====================================================
# Study Area Configuration — Parañaque City, Philippines
# =====================================================
# Reference stations across Parañaque's flood-prone barangays.
# The ingest service fetches weather for the primary station by default.
# Services that support multi-point queries can iterate STUDY_AREA_STATIONS.
#
# To deploy for a different city, update this section and the bounding box.
# =====================================================

# Bounding box for coordinate validation (rejects points outside Parañaque)
STUDY_AREA_BOUNDS = {
    "lat_min": 14.4280,
    "lat_max": 14.5120,
    "lon_min": 120.9750,
    "lon_max": 121.0550,
    "name": "Parañaque City, Philippines",
}

# Named weather reference stations
STUDY_AREA_STATIONS = {
    "city_center": {
        "lat": 14.4793,
        "lon": 121.0198,
        "name": "Parañaque City Hall",
        "description": "Central reference point — administrative center",
        "primary": True,
    },
    "bf_homes": {
        "lat": 14.4545,
        "lon": 121.0234,
        "name": "BF Homes",
        "description": "Residential flood-prone zone — low-lying subdivision",
    },
    "la_huerta": {
        "lat": 14.4891,
        "lon": 120.9876,
        "name": "La Huerta",
        "description": "Coastal barangay near Manila Bay — storm surge risk",
    },
    "sucat": {
        "lat": 14.4625,
        "lon": 121.0456,
        "name": "Sucat",
        "description": "Eastern Parañaque — near Parañaque River flood plain",
    },
}

# Primary station (backward-compatible defaults used by env var fallbacks)
_primary = next(s for s in STUDY_AREA_STATIONS.values() if s.get("primary"))
DEFAULT_LATITUDE = _primary["lat"]
DEFAULT_LONGITUDE = _primary["lon"]
DEFAULT_LOCATION_NAME = _primary["name"]


def get_primary_station() -> dict:
    """Return the primary study area station."""
    return _primary


def get_all_stations() -> list:
    """Return all study area stations as a list of dicts with their keys."""
    return [{"key": k, **v} for k, v in STUDY_AREA_STATIONS.items()]


def get_nearest_station(lat: float, lon: float) -> dict:
    """Return the station nearest to the given coordinates (Euclidean approximation).

    For distances within a single city (~10km), Euclidean distance on lat/lon
    is accurate enough. No need for haversine at this scale.
    """
    best = None
    best_dist = float("inf")
    for key, station in STUDY_AREA_STATIONS.items():
        dist = (station["lat"] - lat) ** 2 + (station["lon"] - lon) ** 2
        if dist < best_dist:
            best_dist = dist
            best = {"key": key, **station}
    return best


def is_within_study_area(lat: float, lon: float) -> bool:
    """Check if coordinates fall within the Parañaque bounding box."""
    return (
        STUDY_AREA_BOUNDS["lat_min"] <= lat <= STUDY_AREA_BOUNDS["lat_max"]
        and STUDY_AREA_BOUNDS["lon_min"] <= lon <= STUDY_AREA_BOUNDS["lon_max"]
    )

# Weather Data Limits
MIN_TEMPERATURE_KELVIN = 200.0  # -73°C
MAX_TEMPERATURE_KELVIN = 330.0  # 57°C
MIN_TEMPERATURE_CELSIUS = -73.0
MAX_TEMPERATURE_CELSIUS = 57.0
MIN_HUMIDITY = 0.0
MAX_HUMIDITY = 100.0
MIN_PRECIPITATION = 0.0
MAX_PRECIPITATION = 1000.0  # mm

# Coordinate Limits
MIN_LATITUDE = -90.0
MAX_LATITUDE = 90.0
MIN_LONGITUDE = -180.0
MAX_LONGITUDE = 180.0

# Pagination Defaults
DEFAULT_PAGE_SIZE = 100
MIN_PAGE_SIZE = 1
MAX_PAGE_SIZE = 1000
DEFAULT_OFFSET = 0

# Rate Limiting Defaults
DEFAULT_RATE_LIMIT = 100
DEFAULT_RATE_WINDOW_SECONDS = 3600
RATE_LIMIT_PREDICT = "60 per hour;10 per minute"
RATE_LIMIT_INGEST = "30 per hour;5 per minute"
RATE_LIMIT_DATA = "120 per hour;30 per minute"
RATE_LIMIT_STATUS = "300 per hour;60 per minute"
RATE_LIMIT_DOCS = "200 per hour;40 per minute"

# Risk Level Classifications
RISK_LEVELS = {
    0: {
        "label": "Safe",
        "color": "#28a745",
        "description": "No significant flood risk detected",
        "threshold_min": 0.0,
        "threshold_max": 0.35,
    },
    1: {
        "label": "Alert",
        "color": "#ffc107",
        "description": "Moderate flood risk - stay alert",
        "threshold_min": 0.35,
        "threshold_max": 0.65,
    },
    2: {
        "label": "Critical",
        "color": "#dc3545",
        "description": "High flood risk - take immediate precautions",
        "threshold_min": 0.65,
        "threshold_max": 1.0,
    },
}

# Model Configuration
DEFAULT_MODEL_DIR = "models"
DEFAULT_MODEL_NAME = "flood_rf_model"
MODEL_FILE_EXTENSION = ".json"

# Database Configuration
DEFAULT_DB_POOL_SIZE = 20
DEFAULT_DB_MAX_OVERFLOW = 10
DEFAULT_DB_POOL_RECYCLE = 3600  # 1 hour

# Logging Levels
LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}

# HTTP Status Codes
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_TOO_MANY_REQUESTS = 429
HTTP_INTERNAL_ERROR = 500
HTTP_BAD_GATEWAY = 502
HTTP_SERVICE_UNAVAILABLE = 503

# Date/Time Formats
ISO_DATE_FORMAT = "%Y-%m-%d"
ISO_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
ISO_DATETIME_FORMAT_TZ = "%Y-%m-%dT%H:%M:%S%z"

# External API Timeouts (seconds)
API_TIMEOUT_DEFAULT = 10
API_TIMEOUT_WEATHER = 30
API_RETRY_COUNT = 3
API_RETRY_DELAY = 1

# Security Defaults
MIN_API_KEY_LENGTH = 32
MAX_INPUT_LENGTH = 10000
SESSION_TIMEOUT_HOURS = 24
JWT_EXPIRY_HOURS = 24
