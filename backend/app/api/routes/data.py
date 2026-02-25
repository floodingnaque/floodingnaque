"""
Weather Data Routes.

Provides endpoints for retrieving historical weather data with
query optimization and caching.
"""

import logging
import os
from datetime import datetime, timedelta, timezone

from app.api.middleware.auth import require_api_key
from app.api.middleware.rate_limit import get_endpoint_limit, limiter
from app.models.db import WeatherData, get_db_session
from app.utils.api_constants import (
    HTTP_BAD_REQUEST,
    HTTP_CREATED,
    HTTP_INTERNAL_ERROR,
    HTTP_NOT_FOUND,
    HTTP_OK,
    HTTP_SERVICE_UNAVAILABLE,
)
from app.utils.api_responses import api_error
from app.utils.cache import cached
from app.utils.query_optimizer import (
    _make_query_cache_key,
    query_cache_get,
    query_cache_set,
)
from flask import Blueprint, g, jsonify, request
from sqlalchemy import asc, desc

logger = logging.getLogger(__name__)

data_bp = Blueprint("data", __name__)

# Cache TTL for data queries
DATA_CACHE_TTL = int(os.getenv("DATA_CACHE_TTL", "60"))  # 1 minute default


@data_bp.route("/data", methods=["GET"])
@limiter.limit(get_endpoint_limit("data"))
def get_weather_data():
    """
    Retrieve historical weather data with query caching.

    Query Parameters:
        limit (int): Maximum number of records (default: 100, max: 1000)
        offset (int): Number of records to skip (default: 0)
        start_date (str): Filter after this date (ISO format)
        end_date (str): Filter before this date (ISO format)
        sort_by (str): Field to sort by - timestamp, temperature, humidity, precipitation (default: timestamp)
        order (str): Sort order - asc, desc (default: desc)
        source (str): Filter by data source - OWM, Manual, Meteostat

    Returns:
        200: List of weather data with pagination info
    ---
    tags:
      - Data
    parameters:
      - in: query
        name: limit
        type: integer
        default: 100
      - in: query
        name: offset
        type: integer
        default: 0
      - in: query
        name: sort_by
        type: string
        enum: [timestamp, temperature, humidity, precipitation, created_at]
        default: timestamp
      - in: query
        name: order
        type: string
        enum: [asc, desc]
        default: desc
    responses:
      200:
        description: Weather data list
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        # Get query parameters
        limit = request.args.get("limit", default=100, type=int)
        offset = request.args.get("offset", default=0, type=int)
        start_date = request.args.get("start_date", type=str)
        end_date = request.args.get("end_date", type=str)
        sort_by = request.args.get("sort_by", default="timestamp", type=str)
        order = request.args.get("order", default="desc", type=str)
        source_filter = request.args.get("source", type=str)

        # Validate limit
        if limit < 1 or limit > 1000:
            return api_error("ValidationError", "Limit must be between 1 and 1000", HTTP_BAD_REQUEST, request_id)

        # Validate sort parameters
        valid_sort_fields = ["timestamp", "temperature", "humidity", "precipitation", "created_at"]
        if sort_by not in valid_sort_fields:
            return api_error(
                "ValidationError", f"sort_by must be one of: {valid_sort_fields}", HTTP_BAD_REQUEST, request_id
            )

        if order not in ["asc", "desc"]:
            return api_error("ValidationError", "order must be asc or desc", HTTP_BAD_REQUEST, request_id)

        # Build cache key (include sort params)
        cache_key = _make_query_cache_key(
            f"weather_data:{limit}:{offset}:{start_date or ''}:{end_date or ''}:{sort_by}:{order}:{source_filter or ''}"
        )

        # Check cache first
        cached_result = query_cache_get(cache_key)
        if cached_result:
            cached_result["request_id"] = request_id
            cached_result["cache_hit"] = True
            return jsonify(cached_result), HTTP_OK

        with get_db_session() as session:
            query = session.query(WeatherData).filter(WeatherData.is_deleted.is_(False))

            # Filter by source if provided
            if source_filter:
                query = query.filter(WeatherData.source == source_filter)

            # Filter by date range if provided
            if start_date:
                try:
                    start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                    query = query.filter(WeatherData.timestamp >= start_dt)
                except ValueError:
                    return api_error(
                        "ValidationError",
                        "Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)",
                        HTTP_BAD_REQUEST,
                        request_id,
                    )

            if end_date:
                try:
                    end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                    query = query.filter(WeatherData.timestamp <= end_dt)
                except ValueError:
                    return api_error(
                        "ValidationError",
                        "Invalid end_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)",
                        HTTP_BAD_REQUEST,
                        request_id,
                    )

            # Get total count
            total = query.count()

            # Apply sorting
            sort_column = getattr(WeatherData, sort_by)
            if order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))

            # Apply pagination
            query = query.offset(offset).limit(limit)

            # Fetch results
            results = query.all()

            # Convert to dict with all relevant fields
            data = [
                {
                    "id": r.id,
                    "temperature": r.temperature,
                    "humidity": r.humidity,
                    "precipitation": r.precipitation,
                    "wind_speed": r.wind_speed,
                    "pressure": r.pressure,
                    "source": r.source,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in results
            ]

        response_data = {
            "success": True,
            "data": data,
            "total": total,
            "limit": limit,
            "offset": offset,
            "count": len(data),
            "sort_by": sort_by,
            "order": order,
            "cache_hit": False,
        }

        # Cache the result
        query_cache_set(cache_key, response_data, DATA_CACHE_TTL)

        response_data["request_id"] = request_id
        return jsonify(response_data), HTTP_OK
    except Exception as e:
        logger.error(f"Error retrieving weather data [{request_id}]: {str(e)}")
        return api_error(
            "DataRetrievalFailed", "An error occurred while retrieving weather data", HTTP_INTERNAL_ERROR, request_id
        )


# ============================================================================
# Meteostat Historical Data Endpoints
# ============================================================================


def _get_meteostat_service():
    """Lazy load meteostat service."""
    try:
        from app.services.meteostat_service import get_meteostat_service

        return get_meteostat_service()
    except ImportError:
        logger.warning("Meteostat is not installed")
        return None


@data_bp.route("/meteostat/stations", methods=["GET"])
@limiter.limit(get_endpoint_limit("data"))
def get_nearby_stations():
    """
    Get nearby weather stations from Meteostat.

    Query Parameters:
        lat (float): Latitude (default: configured default)
        lon (float): Longitude (default: configured default)
        limit (int): Maximum number of stations (default: 5)

    Returns:
        List of nearby weather stations
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        service = _get_meteostat_service()
        if not service:
            return api_error(
                "ServiceUnavailable", "Meteostat service is not available", HTTP_SERVICE_UNAVAILABLE, request_id
            )

        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        limit = request.args.get("limit", default=5, type=int)

        if limit < 1 or limit > 20:
            return api_error("ValidationError", "Limit must be between 1 and 20", HTTP_BAD_REQUEST, request_id)

        stations = service.find_nearby_stations(lat, lon, limit=limit)

        return jsonify({"stations": stations, "count": len(stations), "request_id": request_id}), HTTP_OK

    except Exception as e:
        logger.error(f"Error fetching stations [{request_id}]: {str(e)}")
        return api_error("StationFetchFailed", "Failed to fetch nearby stations", HTTP_INTERNAL_ERROR, request_id)


@data_bp.route("/weather/hourly", methods=["GET"])
@data_bp.route("/hourly", methods=["GET"])  # Alias for frontend compatibility
@limiter.limit(get_endpoint_limit("data"))
@cached("weather_hourly", ttl=300)  # Cache for 5 minutes
def get_hourly_weather():
    """
    Get hourly weather observations from Meteostat.

    Query Parameters:
        lat (float): Latitude (default: configured default)
        lon (float): Longitude (default: configured default)
        start_date (str): Start date in ISO format (default: 7 days ago)
        end_date (str): End date in ISO format (default: now)

    Returns:
        Hourly weather observations
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        service = _get_meteostat_service()
        if not service:
            return api_error(
                "ServiceUnavailable", "Meteostat service is not available", HTTP_SERVICE_UNAVAILABLE, request_id
            )

        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        start_date = request.args.get("start_date", type=str)
        end_date = request.args.get("end_date", type=str)

        # Parse dates
        end = datetime.now()
        start = end - timedelta(days=7)

        if start_date:
            try:
                start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except ValueError:
                return api_error(
                    "ValidationError", "Invalid start_date format. Use ISO format", HTTP_BAD_REQUEST, request_id
                )

        if end_date:
            try:
                end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            except ValueError:
                return api_error(
                    "ValidationError", "Invalid end_date format. Use ISO format", HTTP_BAD_REQUEST, request_id
                )

        # Limit date range to 30 days for performance
        if (end - start).days > 30:
            return api_error(
                "ValidationError", "Date range cannot exceed 30 days for hourly data", HTTP_BAD_REQUEST, request_id
            )

        observations = service.get_hourly_data(lat, lon, start, end)

        # Convert to JSON-serializable format
        data = []
        for obs in observations:
            data.append(
                {
                    "timestamp": obs.timestamp.isoformat() if obs.timestamp else None,
                    "temperature": obs.temperature,
                    "humidity": obs.humidity,
                    "precipitation": obs.precipitation,
                    "wind_speed": obs.wind_speed,
                    "pressure": obs.pressure,
                    "source": obs.source,
                }
            )

        return (
            jsonify(
                {
                    "data": data,
                    "count": len(data),
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Error fetching hourly data [{request_id}]: {str(e)}")
        return api_error(
            "HourlyDataFetchFailed", "Failed to fetch hourly weather data", HTTP_INTERNAL_ERROR, request_id
        )


@data_bp.route("/meteostat/daily", methods=["GET"])
@limiter.limit(get_endpoint_limit("data"))
def get_meteostat_daily():
    """
    Get daily weather data from Meteostat.

    Query Parameters:
        lat (float): Latitude (default: configured default)
        lon (float): Longitude (default: configured default)
        start_date (str): Start date in ISO format (default: 30 days ago)
        end_date (str): End date in ISO format (default: now)

    Returns:
        Daily weather data including min/max temperatures, precipitation
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        service = _get_meteostat_service()
        if not service:
            return api_error(
                "ServiceUnavailable", "Meteostat service is not available", HTTP_SERVICE_UNAVAILABLE, request_id
            )

        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        start_date = request.args.get("start_date", type=str)
        end_date = request.args.get("end_date", type=str)

        # Parse dates
        end = datetime.now()
        start = end - timedelta(days=30)

        if start_date:
            try:
                start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except ValueError:
                return api_error(
                    "ValidationError", "Invalid start_date format. Use ISO format", HTTP_BAD_REQUEST, request_id
                )

        if end_date:
            try:
                end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            except ValueError:
                return api_error(
                    "ValidationError", "Invalid end_date format. Use ISO format", HTTP_BAD_REQUEST, request_id
                )

        # Limit date range to 365 days for daily data
        if (end - start).days > 365:
            return api_error(
                "ValidationError", "Date range cannot exceed 365 days for daily data", HTTP_BAD_REQUEST, request_id
            )

        data = service.get_daily_data(lat, lon, start, end)

        return (
            jsonify(
                {
                    "data": data,
                    "count": len(data),
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Error fetching daily data [{request_id}]: {str(e)}")
        return api_error("DailyDataFetchFailed", "Failed to fetch daily weather data", HTTP_INTERNAL_ERROR, request_id)


@data_bp.route("/meteostat/current", methods=["GET"])
@limiter.limit(get_endpoint_limit("data"))
def get_meteostat_current():
    """
    Get the latest weather observation from Meteostat.

    Note: Meteostat data may be delayed by a few hours compared to real-time APIs.
    This is useful as a fallback when real-time APIs are unavailable.

    Query Parameters:
        lat (float): Latitude (default: configured default)
        lon (float): Longitude (default: configured default)

    Returns:
        Latest weather observation from the nearest station
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        service = _get_meteostat_service()
        if not service:
            return api_error(
                "ServiceUnavailable", "Meteostat service is not available", HTTP_SERVICE_UNAVAILABLE, request_id
            )

        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)

        data = service.get_weather_for_prediction(lat, lon)

        if not data:
            return api_error(
                "NoDataAvailable", "No recent weather data available from Meteostat", HTTP_BAD_REQUEST, request_id
            )

        return (
            jsonify({"data": data, "note": "Meteostat data may be delayed by a few hours", "request_id": request_id}),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Error fetching current data [{request_id}]: {str(e)}")
        return api_error(
            "CurrentDataFetchFailed", "Failed to fetch current weather data", HTTP_INTERNAL_ERROR, request_id
        )


@data_bp.route("/meteostat/status", methods=["GET"])
@limiter.limit(get_endpoint_limit("data"))
def get_meteostat_status():
    """
    Get Meteostat service status and configuration.

    Returns:
        Service status, enabled state, and configuration
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        service = _get_meteostat_service()

        status = {
            "available": service is not None,
            "enabled": os.getenv("METEOSTAT_ENABLED", "True").lower() == "true",
            "as_fallback": os.getenv("METEOSTAT_AS_FALLBACK", "True").lower() == "true",
            "default_location": {
                "latitude": float(os.getenv("DEFAULT_LATITUDE", "14.4793")),
                "longitude": float(os.getenv("DEFAULT_LONGITUDE", "121.0198")),
            },
            "request_id": request_id,
        }

        if service:
            # Check if we can connect by fetching a station
            try:
                stations = service.find_nearby_stations(limit=1)
                status["connection_status"] = "connected" if stations else "no_stations_found"
            except Exception:
                status["connection_status"] = "error"
        else:
            status["connection_status"] = "service_unavailable"

        return jsonify(status), HTTP_OK

    except Exception as e:
        logger.error(f"Error fetching meteostat status [{request_id}]: {str(e)}")
        return api_error("StatusCheckFailed", "Failed to check Meteostat status", HTTP_INTERNAL_ERROR, request_id)


# =============================================================================
# Weather Data CRUD Endpoints
# =============================================================================


@data_bp.route("/data", methods=["POST"])
@limiter.limit(get_endpoint_limit("data"))
@require_api_key
def create_weather_data():
    """
    Create a new weather data entry (manual data entry).

    Request Body:
    {
        "temperature": 300.15,  # Kelvin (required)
        "humidity": 75.0,       # Percentage (required)
        "precipitation": 10.5,  # mm (required)
        "wind_speed": 5.0,      # m/s (optional)
        "pressure": 1013.25,    # hPa (optional)
        "source": "Manual",     # Data source (optional)
        "timestamp": "2025-01-10T10:00:00Z"  # ISO format (optional, defaults to now)
    }

    Returns:
        201: Weather data created successfully
        400: Invalid request data
    ---
    tags:
      - Data
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - temperature
            - humidity
            - precipitation
    responses:
      201:
        description: Weather data created
      400:
        description: Validation error
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        data = request.get_json()
        if not data:
            return api_error("InvalidRequest", "No data provided", HTTP_BAD_REQUEST, request_id)

        # Validate required fields
        required_fields = ["temperature", "humidity", "precipitation"]
        for field in required_fields:
            if field not in data:
                return api_error("ValidationError", f"{field} is required", HTTP_BAD_REQUEST, request_id)

        # Validate temperature (Kelvin: 173.15K to 333.15K = -100C to 60C)
        temperature = float(data["temperature"])
        if temperature < 173.15 or temperature > 333.15:
            return api_error(
                "ValidationError", "Temperature must be between 173.15K and 333.15K", HTTP_BAD_REQUEST, request_id
            )

        # Validate humidity (0-100%)
        humidity = float(data["humidity"])
        if humidity < 0 or humidity > 100:
            return api_error("ValidationError", "Humidity must be between 0 and 100", HTTP_BAD_REQUEST, request_id)

        # Validate precipitation (>= 0)
        precipitation = float(data["precipitation"])
        if precipitation < 0:
            return api_error("ValidationError", "Precipitation cannot be negative", HTTP_BAD_REQUEST, request_id)

        # Parse timestamp or use current time
        timestamp_str = data.get("timestamp")
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError:
                return api_error(
                    "ValidationError", "Invalid timestamp format. Use ISO format.", HTTP_BAD_REQUEST, request_id
                )
        else:
            timestamp = datetime.now(timezone.utc)

        with get_db_session() as session:
            weather_data = WeatherData(
                temperature=temperature,
                humidity=humidity,
                precipitation=precipitation,
                wind_speed=float(data.get("wind_speed")) if data.get("wind_speed") is not None else None,
                pressure=float(data.get("pressure")) if data.get("pressure") is not None else None,
                source=data.get("source", "Manual"),
                location_lat=float(data.get("location_lat")) if data.get("location_lat") is not None else None,
                location_lon=float(data.get("location_lon")) if data.get("location_lon") is not None else None,
                timestamp=timestamp,
            )

            session.add(weather_data)
            session.flush()

            result = weather_data.to_dict()

        logger.info(f"Weather data created: id={result['id']} [{request_id}]")

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Weather data created successfully",
                    "data": result,
                    "request_id": request_id,
                }
            ),
            HTTP_CREATED,
        )

    except ValueError as e:
        logger.warning(f"Validation error creating weather data [{request_id}]: {str(e)}")
        return api_error("ValidationError", "Invalid weather data values", HTTP_BAD_REQUEST, request_id)
    except Exception as e:
        logger.error(f"Error creating weather data [{request_id}]: {str(e)}")
        return api_error("CreateFailed", "Failed to create weather data", HTTP_INTERNAL_ERROR, request_id)


@data_bp.route("/data/<int:data_id>", methods=["GET"])
@limiter.limit(get_endpoint_limit("data"))
def get_weather_data_by_id(data_id):
    """
    Get a specific weather data entry by ID.

    Returns:
        200: Weather data found
        404: Weather data not found
    ---
    tags:
      - Data
    parameters:
      - in: path
        name: data_id
        type: integer
        required: true
    responses:
      200:
        description: Weather data found
      404:
        description: Not found
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        with get_db_session() as session:
            weather_data = (
                session.query(WeatherData).filter(WeatherData.id == data_id, WeatherData.is_deleted.is_(False)).first()
            )

            if not weather_data:
                return api_error("NotFound", f"Weather data with id {data_id} not found", HTTP_NOT_FOUND, request_id)

            result = weather_data.to_dict()

        return jsonify({"success": True, "data": result, "request_id": request_id}), HTTP_OK

    except Exception as e:
        logger.error(f"Error fetching weather data {data_id} [{request_id}]: {str(e)}")
        return api_error("FetchFailed", "Failed to fetch weather data", HTTP_INTERNAL_ERROR, request_id)


@data_bp.route("/data/<int:data_id>", methods=["PUT"])
@limiter.limit(get_endpoint_limit("data"))
@require_api_key
def update_weather_data(data_id):
    """
    Update an existing weather data entry.

    Request Body (all fields optional):
    {
        "temperature": 301.15,
        "humidity": 80.0,
        "precipitation": 15.0,
        "wind_speed": 6.0,
        "pressure": 1012.0
    }

    Returns:
        200: Weather data updated successfully
        404: Weather data not found
    ---
    tags:
      - Data
    parameters:
      - in: path
        name: data_id
        type: integer
        required: true
    responses:
      200:
        description: Weather data updated
      404:
        description: Not found
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        data = request.get_json()
        if not data:
            return api_error("InvalidRequest", "No data provided", HTTP_BAD_REQUEST, request_id)

        with get_db_session() as session:
            weather_data = (
                session.query(WeatherData).filter(WeatherData.id == data_id, WeatherData.is_deleted.is_(False)).first()
            )

            if not weather_data:
                return api_error("NotFound", f"Weather data with id {data_id} not found", HTTP_NOT_FOUND, request_id)

            # Update fields if provided
            if "temperature" in data:
                temp = float(data["temperature"])
                if temp < 173.15 or temp > 333.15:
                    return api_error(
                        "ValidationError",
                        "Temperature must be between 173.15K and 333.15K",
                        HTTP_BAD_REQUEST,
                        request_id,
                    )
                weather_data.temperature = temp

            if "humidity" in data:
                humidity = float(data["humidity"])
                if humidity < 0 or humidity > 100:
                    return api_error(
                        "ValidationError", "Humidity must be between 0 and 100", HTTP_BAD_REQUEST, request_id
                    )
                weather_data.humidity = humidity

            if "precipitation" in data:
                precip = float(data["precipitation"])
                if precip < 0:
                    return api_error(
                        "ValidationError", "Precipitation cannot be negative", HTTP_BAD_REQUEST, request_id
                    )
                weather_data.precipitation = precip

            if "wind_speed" in data:
                weather_data.wind_speed = float(data["wind_speed"]) if data["wind_speed"] is not None else None

            if "pressure" in data:
                weather_data.pressure = float(data["pressure"]) if data["pressure"] is not None else None

            if "source" in data:
                weather_data.source = data["source"]

            weather_data.updated_at = datetime.now(timezone.utc)

            result = weather_data.to_dict()

        logger.info(f"Weather data updated: id={data_id} [{request_id}]")

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Weather data updated successfully",
                    "data": result,
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except ValueError as e:
        logger.warning(f"Validation error updating weather data {data_id} [{request_id}]: {str(e)}")
        return api_error("ValidationError", "Invalid weather data values", HTTP_BAD_REQUEST, request_id)
    except Exception as e:
        logger.error(f"Error updating weather data {data_id} [{request_id}]: {str(e)}")
        return api_error("UpdateFailed", "Failed to update weather data", HTTP_INTERNAL_ERROR, request_id)


@data_bp.route("/data/<int:data_id>", methods=["DELETE"])
@limiter.limit(get_endpoint_limit("data"))
@require_api_key
def delete_weather_data(data_id):
    """
    Delete a weather data entry (soft delete).

    Returns:
        200: Weather data deleted successfully
        404: Weather data not found
    ---
    tags:
      - Data
    parameters:
      - in: path
        name: data_id
        type: integer
        required: true
    responses:
      200:
        description: Weather data deleted
      404:
        description: Not found
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        with get_db_session() as session:
            weather_data = (
                session.query(WeatherData).filter(WeatherData.id == data_id, WeatherData.is_deleted.is_(False)).first()
            )

            if not weather_data:
                return api_error("NotFound", f"Weather data with id {data_id} not found", HTTP_NOT_FOUND, request_id)

            # Soft delete
            weather_data.soft_delete()

        logger.info(f"Weather data deleted: id={data_id} [{request_id}]")

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Weather data deleted successfully",
                    "data_id": data_id,
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Error deleting weather data {data_id} [{request_id}]: {str(e)}")
        return api_error("DeleteFailed", "Failed to delete weather data", HTTP_INTERNAL_ERROR, request_id)


@data_bp.route("/data/bulk-delete", methods=["POST"])
@limiter.limit(get_endpoint_limit("data"))
@require_api_key
def bulk_delete_weather_data():
    """
    Bulk delete weather data entries (soft delete).

    Supports deletion by:
    - List of IDs
    - Date range filter
    - Source filter

    Request Body:
    {
        "ids": [1, 2, 3],  // Optional: specific IDs to delete
        "start_date": "2024-01-01T00:00:00",  // Optional: delete records after this date
        "end_date": "2024-01-31T23:59:59",    // Optional: delete records before this date
        "source": "Manual",  // Optional: delete records from specific source
        "confirm": true  // Required: must be true to execute deletion
    }

    Note: At least one filter (ids, date range, or source) must be provided.
    Maximum 1000 records can be deleted in a single request.

    Returns:
        200: Records deleted successfully
        400: Invalid request
    ---
    tags:
      - Data
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - confirm
          properties:
            ids:
              type: array
              items:
                type: integer
            start_date:
              type: string
            end_date:
              type: string
            source:
              type: string
            confirm:
              type: boolean
    responses:
      200:
        description: Bulk delete completed
      400:
        description: Validation error
    """
    request_id = getattr(g, "request_id", "unknown")
    MAX_BULK_DELETE = 1000

    try:
        data = request.get_json()
        if not data:
            return api_error("InvalidRequest", "No data provided", HTTP_BAD_REQUEST, request_id)

        # Require confirmation
        if not data.get("confirm", False):
            return api_error("ValidationError", "Bulk delete requires confirm=true", HTTP_BAD_REQUEST, request_id)

        ids = data.get("ids", [])
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        source_filter = data.get("source")

        # Require at least one filter
        if not ids and not start_date and not end_date and not source_filter:
            return api_error(
                "ValidationError",
                "At least one filter (ids, date range, or source) must be provided",
                HTTP_BAD_REQUEST,
                request_id,
            )

        # Validate IDs
        if ids:
            if not isinstance(ids, list):
                return api_error("ValidationError", "ids must be an array", HTTP_BAD_REQUEST, request_id)
            if len(ids) > MAX_BULK_DELETE:
                return api_error(
                    "ValidationError", f"Maximum {MAX_BULK_DELETE} IDs per request", HTTP_BAD_REQUEST, request_id
                )

        with get_db_session() as session:
            query = session.query(WeatherData).filter(WeatherData.is_deleted.is_(False))

            # Apply filters
            if ids:
                query = query.filter(WeatherData.id.in_(ids))

            if start_date:
                try:
                    start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                    query = query.filter(WeatherData.timestamp >= start_dt)
                except ValueError:
                    return api_error("ValidationError", "Invalid start_date format", HTTP_BAD_REQUEST, request_id)

            if end_date:
                try:
                    end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                    query = query.filter(WeatherData.timestamp <= end_dt)
                except ValueError:
                    return api_error("ValidationError", "Invalid end_date format", HTTP_BAD_REQUEST, request_id)

            if source_filter:
                query = query.filter(WeatherData.source == source_filter)

            # Count matching records
            total_count = query.count()

            if total_count == 0:
                return api_error("NotFound", "No matching records found", HTTP_NOT_FOUND, request_id)

            if total_count > MAX_BULK_DELETE:
                return api_error(
                    "ValidationError",
                    f"Query matches {total_count} records, exceeds maximum of {MAX_BULK_DELETE}. Add more filters.",
                    HTTP_BAD_REQUEST,
                    request_id,
                )

            # Perform soft delete on all matching records
            deleted_ids = []
            for record in query.all():
                record.soft_delete()
                deleted_ids.append(record.id)

        logger.info(f"Bulk delete completed: {len(deleted_ids)} records [{request_id}]")

        return (
            jsonify(
                {
                    "success": True,
                    "message": f"Successfully deleted {len(deleted_ids)} weather data records",
                    "deleted_count": len(deleted_ids),
                    "deleted_ids": deleted_ids,
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Bulk delete failed [{request_id}]: {str(e)}")
        return api_error("DeleteFailed", "Failed to perform bulk delete", HTTP_INTERNAL_ERROR, request_id)
