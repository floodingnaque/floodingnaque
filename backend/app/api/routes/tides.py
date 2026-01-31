"""
Tide data API routes.

Provides endpoints for accessing tidal data from WorldTides API
for coastal flood prediction in Parañaque City.
"""

import html
import logging
import uuid

from app.utils.api_constants import HTTP_BAD_REQUEST, HTTP_OK, HTTP_SERVICE_UNAVAILABLE
from app.utils.api_responses import api_error, api_success
from flask import Blueprint, g, request

logger = logging.getLogger(__name__)

tides_bp = Blueprint("tides", __name__)


def _get_request_id():
    """Get request ID from Flask context or generate a new one."""
    if hasattr(g, "request_id"):
        return g.request_id
    return str(uuid.uuid4())


def _sanitize_external_data(data):
    """Sanitize data from external APIs to prevent XSS."""
    if isinstance(data, dict):
        return {k: _sanitize_external_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_sanitize_external_data(item) for item in data]
    elif isinstance(data, str):
        return html.escape(data)
    return data


def _get_worldtides_service():
    """Get the WorldTides service instance."""
    try:
        from app.services.worldtides_service import get_worldtides_service

        return get_worldtides_service()
    except ImportError:
        logger.error("WorldTides service not available")
        return None


@tides_bp.route("/current", methods=["GET"])
def get_current_tide():
    """
    Get current tide height for a location.

    Query Parameters:
        lat: Latitude (default: Parañaque City)
        lon: Longitude (default: Parañaque City)

    Returns:
        Current tide height and metadata
    """
    request_id = _get_request_id()

    service = _get_worldtides_service()
    if not service or not service.is_available():
        return api_error(
            "TideServiceUnavailable",
            "WorldTides service is not configured or unavailable",
            HTTP_SERVICE_UNAVAILABLE,
            request_id,
        )

    try:
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)

        tide = service.get_current_tide(lat, lon)

        if not tide:
            return api_error(
                "TideDataNotFound",
                "No tide data available for the specified location",
                HTTP_BAD_REQUEST,
                request_id,
            )

        return api_success(
            {
                "height": tide.height,
                "datum": tide.datum,
                "timestamp": tide.timestamp.isoformat(),
                "source": tide.source,
            },
            "Current tide height retrieved successfully",
            HTTP_OK,
            request_id,
        )

    except Exception as e:
        logger.error(f"Error fetching current tide [{request_id}]: {e}")
        return api_error("TideFetchError", "Failed to fetch current tide data", HTTP_BAD_REQUEST, request_id)


@tides_bp.route("/extremes", methods=["GET"])
def get_tide_extremes():
    """
    Get upcoming high and low tides.

    Query Parameters:
        lat: Latitude (default: Parañaque City)
        lon: Longitude (default: Parañaque City)
        days: Number of days of predictions (1-7, default: 2)

    Returns:
        List of tide extremes (high/low tides)
    """
    request_id = _get_request_id()

    service = _get_worldtides_service()
    if not service or not service.is_available():
        return api_error(
            "TideServiceUnavailable",
            "WorldTides service is not configured or unavailable",
            HTTP_SERVICE_UNAVAILABLE,
            request_id,
        )

    try:
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        days = request.args.get("days", default=2, type=int)
        days = min(max(days, 1), 7)  # Clamp to 1-7

        extremes = service.get_tide_extremes(lat, lon, days)

        return api_success(
            {
                "extremes": [
                    {"type": e.type, "height": e.height, "timestamp": e.timestamp.isoformat(), "datum": e.datum}
                    for e in extremes
                ],
                "count": len(extremes),
                "days": days,
            },
            f"Retrieved {len(extremes)} tide extremes",
            HTTP_OK,
            request_id,
        )

    except Exception as e:
        logger.error(f"Error fetching tide extremes [{request_id}]: {e}")
        return api_error("TideFetchError", "Failed to fetch tide extremes data", HTTP_BAD_REQUEST, request_id)


@tides_bp.route("/prediction", methods=["GET"])
def get_tide_prediction():
    """
    Get tide data formatted for flood prediction.

    Returns tide risk factors and trends that enhance flood prediction accuracy.

    Query Parameters:
        lat: Latitude (default: Parañaque City)
        lon: Longitude (default: Parañaque City)

    Returns:
        Tide data with risk factors for flood prediction
    """
    request_id = _get_request_id()

    service = _get_worldtides_service()
    if not service or not service.is_available():
        return api_error(
            "TideServiceUnavailable",
            "WorldTides service is not configured or unavailable",
            HTTP_SERVICE_UNAVAILABLE,
            request_id,
        )

    try:
        # Validate and sanitize coordinate parameters
        try:
            lat = float(request.args.get("lat", 0))
            lon = float(request.args.get("lon", 0))
        except (ValueError, TypeError):
            return api_error(
                "ValidationError",
                "Invalid coordinate parameters. lat and lon must be valid numbers.",
                HTTP_BAD_REQUEST,
                request_id,
            )

        # Validate coordinate ranges to prevent injection via extreme values
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return api_error(
                "ValidationError",
                "Coordinates out of range. lat: -90 to 90, lon: -180 to 180.",
                HTTP_BAD_REQUEST,
                request_id,
            )

        tide_data = service.get_tide_data_for_prediction(lat, lon)

        if not tide_data:
            return api_error(
                "TideDataNotFound",
                "No tide prediction data available for the specified location",
                HTTP_BAD_REQUEST,
                request_id,
            )

        # Sanitize external API data to prevent XSS
        sanitized_data = _sanitize_external_data(tide_data)

        return api_success(sanitized_data, "Tide prediction data retrieved successfully", HTTP_OK, request_id)

    except Exception:
        logger.error(f"Error fetching tide prediction data [{request_id}]", exc_info=True)
        return api_error("TideFetchError", "Failed to fetch tide data", HTTP_BAD_REQUEST, request_id)


@tides_bp.route("/status", methods=["GET"])
def get_tide_service_status():
    """
    Get WorldTides service status.

    Returns:
        Service configuration and status
    """
    request_id = _get_request_id()

    service = _get_worldtides_service()

    if not service:
        return api_success(
            {"installed": False, "enabled": False, "message": "WorldTides service module not found"},
            "WorldTides service is not installed",
            HTTP_OK,
            request_id,
        )

    status = service.get_service_status()
    status["installed"] = True

    return api_success(status, "WorldTides service status retrieved", HTTP_OK, request_id)
