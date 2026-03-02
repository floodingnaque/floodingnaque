"""
Data Ingestion Routes.

Provides endpoints for ingesting weather data from external APIs.
Includes input validation and security measures.
"""

import logging
import os

from app.api.middleware.auth import require_api_key
from app.api.middleware.rate_limit import get_endpoint_limit, limiter
from app.api.schemas.weather import parse_json_safely
from app.core.constants import HTTP_BAD_REQUEST, HTTP_INTERNAL_ERROR, HTTP_OK
from app.core.exceptions import ValidationError, api_error
from app.services.ingest import ingest_data
from app.utils.validation import InputValidator, validate_request_size
from flask import Blueprint, g, jsonify, request
from werkzeug.exceptions import BadRequest

logger = logging.getLogger(__name__)

ingest_bp = Blueprint("ingest", __name__)


@ingest_bp.route("/ingest", methods=["GET", "POST"])
@limiter.limit(get_endpoint_limit("ingest"))
@validate_request_size(endpoint_name="ingest")  # 10KB limit for ingest payloads
@require_api_key
def ingest():
    """
    Ingest weather data from external APIs.

    Fetches current weather data from OpenWeatherMap and Weatherstack APIs
    for the specified location and stores it in the database.

    GET: Returns usage information and examples
    POST: Ingests weather data for the specified coordinates

    Request Body (POST):
        lat (float): Latitude (-90 to 90), defaults to Parañaque (14.4793)
        lon (float): Longitude (-180 to 180), defaults to Parañaque (121.0198)

    Returns:
        200: Weather data ingested successfully
        400: Validation error (invalid coordinates)
        500: Ingestion failed
    ---
    tags:
      - Data Ingestion
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: false
        schema:
          type: object
          properties:
            lat:
              type: number
              description: Latitude (-90 to 90)
              example: 14.4793
            lon:
              type: number
              description: Longitude (-180 to 180)
              example: 121.0198
    responses:
      200:
        description: Data ingested successfully
        schema:
          type: object
          properties:
            message:
              type: string
            data:
              type: object
              properties:
                temperature:
                  type: number
                  description: Temperature in Kelvin
                humidity:
                  type: number
                  description: Relative humidity (%)
                precipitation:
                  type: number
                  description: Precipitation in mm
                timestamp:
                  type: string
                  format: date-time
            request_id:
              type: string
      400:
        description: Validation error
      500:
        description: Ingestion failed
    security:
      - api_key: []
    """
    # Handle GET requests - show usage information
    if request.method == "GET":
        return (
            jsonify(
                {
                    "endpoint": "/ingest",
                    "method": "POST",
                    "description": "Ingest weather data from external APIs (OpenWeatherMap and Weatherstack)",
                    "usage": {
                        "curl_example": 'curl -X POST http://127.0.0.1:5000/ingest -H "Content-Type: application/json" -d \'{"lat": 14.6, "lon": 120.98}\'',
                        "powershell_example": '$body = @{lat=14.6; lon=120.98} | ConvertTo-Json; Invoke-RestMethod -Uri http://127.0.0.1:5000/ingest -Method POST -ContentType "application/json" -Body $body',
                        "request_body": {
                            "lat": "float (optional, -90 to 90) - Latitude",
                            "lon": "float (optional, -180 to 180) - Longitude",
                        },
                        "note": "If lat/lon are not provided, defaults to Parañaque City (14.4793, 121.0198)",
                    },
                    "response_example": {
                        "message": "Data ingested successfully",
                        "data": {
                            "temperature": 298.15,
                            "humidity": 65.0,
                            "precipitation": 0.0,
                            "timestamp": "2025-12-11T03:00:00",
                        },
                        "request_id": "uuid-string",
                    },
                    "alternative_endpoints": {
                        "api_docs": "/api/docs - Full API documentation",
                        "status": "/status - Health check",
                        "health": "/health - Detailed health check",
                    },
                }
            ),
            HTTP_OK,
        )

    # Handle POST requests - actual ingestion
    request_id = getattr(g, "request_id", "unknown")

    try:
        # Handle JSON parsing with better error handling
        try:
            request_data = request.get_json(force=True, silent=True)
        except BadRequest as e:
            logger.error(f"BadRequest parsing JSON [{request_id}]: {str(e)}")
            return api_error("InvalidJSON", "Please check your request body.", HTTP_BAD_REQUEST, request_id)

        if request_data is None:
            # Try to parse manually if get_json failed
            if request.data:
                request_data = parse_json_safely(request.data)
                if request_data is None:
                    logger.error(f"All JSON parsing attempts failed [{request_id}]")
                    return api_error(
                        "InvalidJSON", "Please ensure your JSON is properly formatted.", HTTP_BAD_REQUEST, request_id
                    )
            else:
                request_data = {}

        lat = request_data.get("lat")
        lon = request_data.get("lon")

        # Validate coordinates if provided using InputValidator
        if lat is not None or lon is not None:
            try:
                lat, lon = InputValidator.validate_coordinates(lat, lon)
            except ValidationError as e:
                logger.warning(f"Coordinate validation failed [{request_id}]: {str(e)}")
                return api_error("ValidationError", "Invalid coordinates", HTTP_BAD_REQUEST, request_id)

        data = ingest_data(lat=lat, lon=lon)

        return (
            jsonify(
                {
                    "message": "Data ingested successfully",
                    "data": {
                        "temperature": data.get("temperature"),
                        "humidity": data.get("humidity"),
                        "precipitation": data.get("precipitation"),
                        "timestamp": data.get("timestamp").isoformat() if data.get("timestamp") else None,
                    },
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except ValidationError as e:
        logger.error(f"Validation error in ingest [{request_id}]: {str(e)}")
        return api_error("ValidationError", "Invalid request data", HTTP_BAD_REQUEST, request_id)
    except ValueError as e:
        logger.error(f"Validation error in ingest [{request_id}]: {str(e)}")
        return api_error("ValidationError", "Invalid request data", HTTP_BAD_REQUEST, request_id)
    except BadRequest as e:
        logger.error(f"BadRequest error in ingest [{request_id}]: {str(e)}")
        return api_error("InvalidRequest", "The request could not be processed", HTTP_BAD_REQUEST, request_id)
    except Exception as e:
        logger.error(f"Error in ingest endpoint [{request_id}]: {str(e)}", exc_info=True)
        return api_error("IngestionFailed", "An error occurred during data ingestion", HTTP_INTERNAL_ERROR, request_id)


@ingest_bp.route("/trigger", methods=["POST"])
@limiter.limit("4 per minute")
@require_api_key
def trigger_ingest():
    """
    Manually trigger an immediate weather data ingestion.

    Use this during rapidly changing conditions (e.g. approaching typhoon)
    instead of waiting for the next scheduled run.

    Request Body (optional):
        lat (float): Latitude (-90 to 90)
        lon (float): Longitude (-180 to 180)

    Returns:
        200: Ingestion triggered and completed
        429: Rate limited
        500: Ingestion failed
    ---
    tags:
      - Data Ingestion
    responses:
      200:
        description: Manual ingestion completed
    security:
      - api_key: []
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        body = request.get_json(force=True, silent=True) or {}

        lat = body.get("lat")
        lon = body.get("lon")

        if lat is not None or lon is not None:
            try:
                lat, lon = InputValidator.validate_coordinates(lat, lon)
            except ValidationError as e:
                return api_error("ValidationError", str(e), HTTP_BAD_REQUEST, request_id)
        else:
            lat = float(os.getenv("DEFAULT_LATITUDE", "14.4793"))
            lon = float(os.getenv("DEFAULT_LONGITUDE", "121.0198"))

        data = ingest_data(lat=lat, lon=lon)

        # Also invalidate weather cache so predictions use fresh data
        invalidated = 0
        try:
            from app.utils.resilience.cache import invalidate_weather_cache

            invalidated = invalidate_weather_cache()
        except Exception:
            logger.warning("Cache invalidation failed after manual ingest", exc_info=True)

        return (
            jsonify(
                {
                    "message": "Manual ingestion completed",
                    "data": {
                        "temperature": data.get("temperature"),
                        "humidity": data.get("humidity"),
                        "precipitation": data.get("precipitation"),
                        "timestamp": data.get("timestamp").isoformat() if data.get("timestamp") else None,
                    },
                    "cache_keys_invalidated": invalidated,
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )
    except Exception as e:
        logger.error(f"Manual ingest trigger failed [{request_id}]: {str(e)}", exc_info=True)
        return api_error("IngestionFailed", "Manual ingestion failed", HTTP_INTERNAL_ERROR, request_id)
