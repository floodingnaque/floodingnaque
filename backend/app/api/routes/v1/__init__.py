"""API Version 1 Blueprint - Backward Compatible Endpoints.

This module provides V1 API endpoints with backward-compatible response formats.
V1 endpoints support legacy clients and provide versioned API access.

STATUS: Active - Primary versioned API
REVIEWED: 2026-01 - Implemented for backward compatibility.

Endpoints:
    POST /api/v1/predict - Flood prediction with V1 response format
    GET  /api/v1/weather - Weather data retrieval
    GET  /api/v1/data    - Historical data access

See Also:
    - backend/docs/BACKEND_ARCHITECTURE.md for API design decisions
    - tests/api/test_versioning.py for V1 API contract tests
"""

import logging
from functools import wraps
from typing import Any, Dict, Optional, Tuple, Union

from flask import Blueprint, jsonify, request
from werkzeug.exceptions import BadRequest

logger = logging.getLogger(__name__)

# Create V1 blueprint
v1_bp = Blueprint("v1", __name__)


def v1_wrapper(f):
    """
    Decorator to add V1-specific response formatting.

    Adds api_version to all responses and ensures consistent formatting.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        response = f(*args, **kwargs)

        # Handle tuple responses (data, status_code)
        if isinstance(response, tuple):
            data, status = response
        else:
            data = response
            status = 200

        # Add version info to dict responses
        if isinstance(data, dict):
            data["api_version"] = "v1"

        return jsonify(data), status

    return decorated


@v1_bp.route("/predict", methods=["POST"])
@v1_wrapper
def v1_predict():
    """
    V1 Predict endpoint - backward compatible flood prediction.

    Accepts flat weather parameters and returns prediction with V1 format.

    Request Body:
        temperature (float): Temperature in Kelvin (required)
        humidity (float): Relative humidity percentage (required)
        precipitation (float): Precipitation in mm (required)
        wind_speed (float): Wind speed in m/s (optional)
        pressure (float): Atmospheric pressure in hPa (optional)

    Returns:
        200: Prediction result with V1 format
        400: Validation error
        500: Prediction failed
    """
    try:
        data = request.get_json() or {}

        # Validate required fields
        required_fields = ["temperature", "humidity", "precipitation"]
        missing_fields = [f for f in required_fields if f not in data or data.get(f) is None]

        if missing_fields:
            return {"error": f"Missing required fields: {', '.join(missing_fields)}"}, 400

        # Validate field types
        for field in required_fields:
            value = data.get(field)
            if not isinstance(value, (int, float)):
                return {"error": f"Field '{field}' must be a number"}, 400

        # Import prediction service
        from app.services.predict import predict_flood

        # Build features dict - V1 accepts flat parameters
        features = {
            "temperature": data.get("temperature"),
            "humidity": data.get("humidity"),
            "precipitation": data.get("precipitation"),
        }

        # Add optional fields if present
        if "wind_speed" in data:
            features["wind_speed"] = data.get("wind_speed")
        if "pressure" in data:
            features["pressure"] = data.get("pressure")

        # Make prediction with probabilities
        result = predict_flood(features, return_proba=True, return_risk_level=True)

        # Build V1 response format
        if isinstance(result, dict):
            response = {
                "success": True,
                "prediction": result.get("prediction", 0),
                "flood_risk": "high" if result.get("prediction", 0) == 1 else "low",
                "probability": result.get("probability", {}),
                "confidence": (
                    result.get("probability", {}).get("no_flood", 0.5)
                    if result.get("prediction", 0) == 0
                    else result.get("probability", {}).get("flood", 0.5)
                ),
                "risk_level": result.get("risk_level", 0),
                "risk_label": result.get("risk_label", "Safe"),
                "model_version": result.get("model_version", "1.0.0"),
            }
        else:
            # Simple int result
            response = {
                "success": True,
                "prediction": int(result),
                "flood_risk": "high" if result == 1 else "low",
                "probability": {"flood": 0.5, "no_flood": 0.5},
                "confidence": 0.5,
                "risk_level": 1 if result == 1 else 0,
                "risk_label": "Alert" if result == 1 else "Safe",
                "model_version": "1.0.0",
            }

        return response, 200

    except FileNotFoundError as e:
        logger.error(f"V1 predict - model not found: {e}")
        return {"error": "Prediction model not available"}, 503

    except BadRequest as e:
        logger.warning(f"V1 predict - bad request (malformed JSON): {e}")
        return {"error": "Invalid JSON in request body"}, 400

    except ValueError as e:
        logger.warning(f"V1 predict validation error: {e}")
        return {"error": str(e)}, 400

    except Exception as e:
        logger.error(f"V1 predict error: {e}")
        return {"error": "Prediction failed"}, 500


@v1_bp.route("/weather", methods=["GET"])
@v1_wrapper
def v1_weather():
    """
    V1 Weather endpoint - backward compatible weather data retrieval.

    Query Parameters:
        lat (float): Latitude (optional, uses default if not provided)
        lon (float): Longitude (optional, uses default if not provided)

    Returns:
        200: Current weather data in V1 format
        500: Weather data retrieval failed
    """
    try:
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)

        # Use MeteostatService for weather data
        from app.services.meteostat_service import MeteostatService

        service = MeteostatService.get_instance()

        # Get latest observation (uses defaults if lat/lon not provided)
        weather_data = service.get_latest_observation(lat, lon)

        if weather_data:
            # V1 response format - WeatherObservation dataclass
            return {
                "temperature": weather_data.temperature,
                "humidity": weather_data.humidity,
                "precipitation": weather_data.precipitation,
                "wind_speed": weather_data.wind_speed,
                "pressure": weather_data.pressure,
                "timestamp": str(weather_data.timestamp) if weather_data.timestamp else None,
                "source": weather_data.source,
            }, 200
        else:
            return {
                "temperature": None,
                "humidity": None,
                "precipitation": None,
                "message": "No weather data available",
            }, 200

    except Exception as e:
        logger.error(f"V1 weather error: {e}")
        return {"error": "Weather data retrieval failed"}, 500


@v1_bp.route("/data", methods=["GET"])
@v1_wrapper
def v1_data():
    """
    V1 Data endpoint - backward compatible historical data access.

    Query Parameters:
        limit (int): Maximum records to return (default: 100, max: 1000)
        offset (int): Number of records to skip (default: 0)

    Returns:
        200: Historical data records in V1 format
        500: Data retrieval failed
    """
    try:
        limit = request.args.get("limit", 100, type=int)
        offset = request.args.get("offset", 0, type=int)

        # Enforce limits
        limit = min(max(1, limit), 1000)  # Between 1 and 1000
        offset = max(0, offset)

        # Import database session and model
        from app.models.db import WeatherData, get_db_session

        with get_db_session() as session:
            query = (
                session.query(WeatherData)
                .filter(WeatherData.is_deleted == False)  # noqa: E712 - SQLAlchemy comparison
                .order_by(WeatherData.timestamp.desc())
                .limit(limit)
                .offset(offset)
            )
            records = query.all()

            # V1 response format
            return {
                "data": [r.to_dict() for r in records],
                "count": len(records),
                "limit": limit,
                "offset": offset,
            }, 200

    except Exception as e:
        logger.error(f"V1 data error: {e}")
        return {"error": "Data retrieval failed"}, 500


# Re-export all blueprints from the main routes package for backward compatibility
from app.api.routes import (
    alerts_bp,
    batch_bp,
    celery_bp,
    csp_report_bp,
    dashboard_bp,
    data_bp,
    export_bp,
    graphql_bp,
    health_bp,
    health_k8s_bp,
    ingest_bp,
    models_bp,
    performance_bp,
    predict_bp,
    predictions_bp,
    rate_limits_bp,
    security_txt_bp,
    sse_bp,
    tides_bp,
    users_bp,
    webhooks_bp,
)

__all__ = [
    # V1 Blueprint
    "v1_bp",
    # Re-exported blueprints for backward compatibility
    "health_bp",
    "health_k8s_bp",
    "ingest_bp",
    "predict_bp",
    "data_bp",
    "models_bp",
    "batch_bp",
    "export_bp",
    "webhooks_bp",
    "celery_bp",
    "rate_limits_bp",
    "tides_bp",
    "graphql_bp",
    "security_txt_bp",
    "csp_report_bp",
    "performance_bp",
    "users_bp",
    "alerts_bp",
    "dashboard_bp",
    "predictions_bp",
    "sse_bp",
]
