"""
Flood Prediction Routes.

Provides endpoints for flood risk prediction using ML models.
Includes input validation, security measures, and response caching.
"""

import logging
import os
import time as _time
from datetime import datetime, timezone

from app.api.middleware.auth import require_auth_or_api_key, require_scope
from app.api.middleware.rate_limit import rate_limit_with_burst
from app.api.schemas.weather import parse_json_safely
from app.core.constants import HTTP_BAD_REQUEST, HTTP_INTERNAL_ERROR, HTTP_NOT_FOUND, HTTP_OK
from app.core.exceptions import ValidationError, api_error
from app.services.predict import predict_flood
from app.models import AlertHistory, Prediction, get_db_session
from app.utils.resilience.cache import (
    cache_prediction_result,
    get_cached_prediction,
    is_cache_enabled,
    make_weather_hash,
)
from app.utils.validation import InputValidator, validate_request_size
from app.utils.weather_fetch import WeatherFetchError, fetch_weather_by_coordinates
from flask import Blueprint, g, jsonify, request
from werkzeug.exceptions import BadRequest

logger = logging.getLogger(__name__)

predict_bp = Blueprint("predict", __name__)

# Prediction cache TTL (seconds)
PREDICTION_CACHE_TTL = int(os.getenv("PREDICTION_CACHE_TTL", "300"))  # 5 minutes default
PREDICTION_CACHE_ENABLED = os.getenv("PREDICTION_CACHE_ENABLED", "True").lower() == "true"


@predict_bp.route("/", methods=["POST"])
@rate_limit_with_burst("60 per hour")
@validate_request_size(endpoint_name="predict")  # 10KB limit for prediction payloads
@require_auth_or_api_key
@require_scope("predict")
def predict():
    """
    Predict flood risk based on weather data.

    Uses machine learning model to predict flood risk from weather parameters.
    Results are cached for 5 minutes to improve performance.

    Request Body:
        temperature (float): Temperature in Kelvin (required, 173.15-333.15)
        humidity (float): Relative humidity percentage (required, 0-100)
        precipitation (float): Precipitation in mm/hour (required, >= 0)
        wind_speed (float): Wind speed in m/s (optional)
        pressure (float): Atmospheric pressure in hPa (optional)
        model_version (str): Specific model version to use (optional)

    Query Parameters:
        risk_level (bool): Include 3-level risk classification (default: true)
        return_proba (bool): Include probability values (default: false)

    Returns:
        200: Prediction result with risk level and confidence
        400: Validation error (invalid input data)
        404: Model not found
        500: Prediction failed
    ---
    tags:
      - Predictions
    consumes:
      - application/json
    produces:
      - application/json
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
          properties:
            temperature:
              type: number
              description: Temperature in Kelvin
              example: 303.15
            humidity:
              type: number
              description: Relative humidity (0-100%)
              example: 85
            precipitation:
              type: number
              description: Precipitation in mm/hour
              example: 50
            wind_speed:
              type: number
              description: Wind speed in m/s
              example: 15
            pressure:
              type: number
              description: Atmospheric pressure in hPa
              example: 1005
      - in: query
        name: risk_level
        type: boolean
        default: true
        description: Include 3-level risk classification
      - in: query
        name: return_proba
        type: boolean
        default: false
        description: Include probability values
    responses:
      200:
        description: Successful prediction
        schema:
          type: object
          properties:
            prediction:
              type: integer
              description: Binary prediction (0=no flood, 1=flood)
            flood_risk:
              type: string
              enum: [low, high]
            risk_level:
              type: integer
              description: Risk level (0=Safe, 1=Alert, 2=Critical)
            risk_label:
              type: string
              enum: [Safe, Alert, Critical]
            probability:
              type: number
              description: Flood probability (0-1)
            confidence:
              type: number
              description: Model confidence score
            cache_hit:
              type: boolean
      400:
        description: Validation error
      404:
        description: Model not found
      500:
        description: Prediction failed
    security:
      - api_key: []
      - bearer_auth: []
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        # Handle JSON parsing with better error handling
        try:
            input_data = request.get_json(force=True, silent=True)
        except BadRequest as e:
            logger.error(f"BadRequest parsing JSON in predict [{request_id}]: {str(e)}")
            return api_error("InvalidJSON", "Please check your request body.", HTTP_BAD_REQUEST, request_id)

        if input_data is None:
            # Try to parse manually if get_json failed
            if request.data:
                input_data = parse_json_safely(request.data)
                if input_data is None:
                    logger.error(f"All JSON parsing attempts failed in predict [{request_id}]")
                    return api_error(
                        "InvalidJSON", "Please ensure your JSON is properly formatted.", HTTP_BAD_REQUEST, request_id
                    )
            else:
                return api_error("NoInput", "No input data provided", HTTP_BAD_REQUEST, request_id)

        if not input_data:
            return api_error("NoInput", "No input data provided", HTTP_BAD_REQUEST, request_id)

        # Reject non-dict JSON bodies (arrays, strings, integers)
        if not isinstance(input_data, dict):
            return api_error(
                "InvalidInput",
                "Request body must be a JSON object",
                HTTP_BAD_REQUEST,
                request_id,
            )

        # Validate and sanitize input using InputValidator
        try:
            validated_data = InputValidator.validate_prediction_input(input_data)
        except ValidationError as e:
            logger.warning(f"Input validation failed [{request_id}]: {e}")
            return api_error(
                "ValidationError",
                "Input validation failed",
                HTTP_BAD_REQUEST,
                request_id,
                errors=getattr(e, "errors", None),
            )

        # Check prediction cache (if enabled)
        cache_hit = False
        weather_hash = None
        if PREDICTION_CACHE_ENABLED and is_cache_enabled():
            weather_hash = make_weather_hash(validated_data)
            cached_result = get_cached_prediction(weather_hash)
            if cached_result:
                logger.debug(f"Prediction cache HIT [{request_id}]: {weather_hash}")
                cached_result["request_id"] = request_id
                cached_result["cache_hit"] = True
                # Staleness metadata so the frontend knows how old the data is
                cached_at = cached_result.get("cached_at")
                if cached_at:
                    cached_result["data_age_seconds"] = round(_time.time() - cached_at, 1)
                return jsonify(cached_result), HTTP_OK

        # Extract model version (validated separately)
        model_version = validated_data.pop("model_version", None)
        return_proba = request.args.get("return_proba", "false").lower() == "true"
        return_risk_level = request.args.get("risk_level", "true").lower() == "true"

        prediction = predict_flood(
            validated_data,  # Use validated data
            model_version=model_version,
            return_proba=return_proba or return_risk_level,
            return_risk_level=return_risk_level,
        )

        # Handle dict response (with probabilities and risk level) or int response
        if isinstance(prediction, dict):
            response = {
                "success": True,
                "prediction": prediction["prediction"],
                "flood_risk": "high" if prediction["prediction"] == 1 else "low",
                "model_version": prediction.get("model_version"),
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            # Add probability if available
            if "probability" in prediction:
                response["probability"] = prediction["probability"]
            # Add risk level classification (3-level: Safe/Alert/Critical)
            if "risk_label" in prediction:
                response["risk_level"] = prediction.get("risk_level")
                response["risk_label"] = prediction.get("risk_label")
                response["risk_color"] = prediction.get("risk_color")
                response["risk_description"] = prediction.get("risk_description")
                response["confidence"] = prediction.get("confidence")
            # Smart alert metadata
            if "smart_alert" in prediction:
                response["smart_alert"] = prediction["smart_alert"]
            # XAI explanation payload
            if "explanation" in prediction:
                response["explanation"] = prediction["explanation"]
            # Features used by the model
            if "features_used" in prediction:
                response["features_used"] = prediction["features_used"]
        else:
            # Simple int response - convert to dict with basic info
            response = {
                "success": True,
                "prediction": prediction,
                "flood_risk": "high" if prediction == 1 else "low",
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # Cache the prediction result (stamp with timestamp for staleness tracking)
        if PREDICTION_CACHE_ENABLED and weather_hash and is_cache_enabled():
            response["cached_at"] = _time.time()
            cache_prediction_result(weather_hash, response, PREDICTION_CACHE_TTL)
            logger.debug(f"Prediction cached [{request_id}]: {weather_hash}")

        # Feed monitoring service for drift detection
        try:
            from app.services.monitoring import record_prediction_result

            _risk_label = response.get("risk_label") or response.get("flood_risk", "unknown")
            _confidence = response.get("confidence") or 0.0
            record_prediction_result(risk_label=str(_risk_label), confidence=float(_confidence))
        except Exception:  # nosec B110
            pass  # Non-critical - never break a prediction request

        # Persist prediction to DB and create alert if risk >= 1
        try:
            with get_db_session() as session:
                pred_record = Prediction(
                    prediction=int(response.get("prediction", 0)),
                    risk_level=response.get("risk_level", 0),
                    risk_label=response.get("risk_label", "Safe"),
                    confidence=float(response.get("confidence") or response.get("probability") or 0),
                    model_version=response.get("model_version"),
                )
                session.add(pred_record)
                session.flush()

                # Log alert when risk is Alert (1) or Critical (2)
                risk_lvl = response.get("risk_level", 0) or 0
                if risk_lvl >= 1:
                    alert = AlertHistory(
                        prediction_id=pred_record.id,
                        risk_level=risk_lvl,
                        risk_label=response.get("risk_label", "Alert"),
                        location="Parañaque City",
                        message=response.get("risk_description", ""),
                        delivery_status="pending",
                        delivery_channel="web",
                    )
                    session.add(alert)
        except Exception:  # nosec B110
            logger.debug(f"Non-critical: failed to persist prediction [{request_id}]")

        response["cache_hit"] = False
        response.pop("cached_at", None)  # Don't expose raw timestamp on fresh responses
        return jsonify(response), HTTP_OK

    except ValidationError as e:
        logger.error(f"Validation error in predict [{request_id}]: {e}")
        return api_error(
            "ValidationError",
            "Input validation failed",
            HTTP_BAD_REQUEST,
            request_id,
            errors=getattr(e, "errors", None),
        )
    except ValueError as e:
        logger.error(f"Value error in predict [{request_id}]: {e}")
        return api_error("ValidationError", "Invalid input data provided", HTTP_BAD_REQUEST, request_id)
    except FileNotFoundError as e:
        logger.error(f"Model not found [{request_id}]: {e}")
        return api_error("ModelNotFound", "Requested model not found", HTTP_NOT_FOUND, request_id)
    except (EOFError, ModuleNotFoundError) as e:
        logger.error(f"Corrupt model artifact [{request_id}]: {e}", exc_info=True)
        return api_error("ModelError", "Model artifact is corrupt or incompatible", HTTP_INTERNAL_ERROR, request_id)
    except Exception as e:
        logger.error(f"Error in predict endpoint [{request_id}]: {e}", exc_info=True)
        return api_error("PredictionFailed", "An error occurred during prediction", HTTP_INTERNAL_ERROR, request_id)


@predict_bp.route("/location", methods=["POST"])
@rate_limit_with_burst("60 per hour")
@validate_request_size(endpoint_name="predict")
@require_auth_or_api_key
@require_scope("predict")
def predict_by_location():
    """
    Predict flood risk based on GPS coordinates.

    Accepts latitude/longitude, fetches current weather from OpenWeatherMap,
    then runs the flood prediction model on the retrieved data.

    Request Body:
        latitude (float): Latitude in decimal degrees (required, -90 to 90)
        longitude (float): Longitude in decimal degrees (required, -180 to 180)

    Returns:
        200: Prediction result with risk level, confidence, and weather data
        400: Validation error (invalid coordinates)
        404: Model not found
        500: Prediction or weather fetch failed
    ---
    tags:
      - Predictions
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - latitude
            - longitude
          properties:
            latitude:
              type: number
              description: Latitude in decimal degrees
              example: 14.4793
            longitude:
              type: number
              description: Longitude in decimal degrees
              example: 121.0198
    responses:
      200:
        description: Successful location-based prediction
        schema:
          type: object
          properties:
            prediction:
              type: integer
              description: Binary prediction (0=no flood, 1=flood)
            flood_risk:
              type: string
              enum: [low, high]
            risk_level:
              type: integer
              description: Risk level (0=Safe, 1=Alert, 2=Critical)
            risk_label:
              type: string
              enum: [Safe, Alert, Critical]
            probability:
              type: number
              description: Flood probability (0-1)
            confidence:
              type: number
              description: Model confidence score
            weather_data:
              type: object
              description: Weather data fetched for the location
      400:
        description: Validation error
      404:
        description: Model not found
      500:
        description: Prediction or weather fetch failed
    security:
      - api_key: []
      - bearer_auth: []
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        # Parse JSON body
        try:
            input_data = request.get_json(force=True, silent=True)
        except BadRequest as e:
            logger.error(f"BadRequest parsing JSON in predict/location [{request_id}]: {str(e)}")
            return api_error("InvalidJSON", "Please check your request body.", HTTP_BAD_REQUEST, request_id)

        if not input_data:
            return api_error("NoInput", "No input data provided", HTTP_BAD_REQUEST, request_id)

        # Validate coordinates
        latitude = input_data.get("latitude")
        longitude = input_data.get("longitude")

        if latitude is None or longitude is None:
            return api_error(
                "ValidationError",
                "Both 'latitude' and 'longitude' are required.",
                HTTP_BAD_REQUEST,
                request_id,
            )

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (ValueError, TypeError):
            return api_error(
                "ValidationError",
                "Latitude and longitude must be valid numbers.",
                HTTP_BAD_REQUEST,
                request_id,
            )

        if not (-90 <= latitude <= 90):
            return api_error(
                "ValidationError",
                "Latitude must be between -90 and 90 degrees.",
                HTTP_BAD_REQUEST,
                request_id,
            )
        if not (-180 <= longitude <= 180):
            return api_error(
                "ValidationError",
                "Longitude must be between -180 and 180 degrees.",
                HTTP_BAD_REQUEST,
                request_id,
            )

        # Fetch weather data from OpenWeatherMap
        weather_data = fetch_weather_by_coordinates(latitude, longitude)

        # Build prediction input (same format as manual predict endpoint)
        prediction_input = {
            "temperature": weather_data["temperature"],
            "humidity": weather_data["humidity"],
            "precipitation": weather_data["precipitation"],
            "wind_speed": weather_data.get("wind_speed", 0),
            "pressure": weather_data.get("pressure"),
        }

        # Check prediction cache
        cache_hit = False
        weather_hash = None
        if PREDICTION_CACHE_ENABLED and is_cache_enabled():
            weather_hash = make_weather_hash(prediction_input)
            cached_result = get_cached_prediction(weather_hash)
            if cached_result:
                logger.debug(f"Location prediction cache HIT [{request_id}]: {weather_hash}")
                cached_result["request_id"] = request_id
                cached_result["cache_hit"] = True
                cached_result["weather_data"] = weather_data
                return jsonify(cached_result), HTTP_OK

        # Run prediction
        prediction = predict_flood(
            prediction_input,
            return_proba=True,
            return_risk_level=True,
        )

        # Build response
        if isinstance(prediction, dict):
            response = {
                "success": True,
                "prediction": prediction["prediction"],
                "flood_risk": "high" if prediction["prediction"] == 1 else "low",
                "model_version": prediction.get("model_version"),
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "weather_data": weather_data,
            }
            if "probability" in prediction:
                response["probability"] = prediction["probability"]
            if "risk_label" in prediction:
                response["risk_level"] = prediction.get("risk_level")
                response["risk_label"] = prediction.get("risk_label")
                response["risk_color"] = prediction.get("risk_color")
                response["risk_description"] = prediction.get("risk_description")
                response["confidence"] = prediction.get("confidence")
            # Smart alert metadata
            if "smart_alert" in prediction:
                response["smart_alert"] = prediction["smart_alert"]
            # XAI explanation payload
            if "explanation" in prediction:
                response["explanation"] = prediction["explanation"]
            # Features used by the model
            if "features_used" in prediction:
                response["features_used"] = prediction["features_used"]
        else:
            response = {
                "success": True,
                "prediction": prediction,
                "flood_risk": "high" if prediction == 1 else "low",
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "weather_data": weather_data,
            }

        # Cache result
        if PREDICTION_CACHE_ENABLED and weather_hash and is_cache_enabled():
            cache_prediction_result(weather_hash, response, PREDICTION_CACHE_TTL)

        response["cache_hit"] = False
        return jsonify(response), HTTP_OK

    except WeatherFetchError as e:
        logger.error(f"Weather fetch failed [{request_id}]: {e}")
        return api_error(
            "WeatherFetchFailed",
            str(e),
            HTTP_INTERNAL_ERROR,
            request_id,
        )
    except ValidationError as e:
        logger.error(f"Validation error in predict/location [{request_id}]: {e}")
        return api_error(
            "ValidationError",
            "Input validation failed",
            HTTP_BAD_REQUEST,
            request_id,
            errors=getattr(e, "errors", None),
        )
    except FileNotFoundError as e:
        logger.error(f"Model not found [{request_id}]: {e}")
        return api_error("ModelNotFound", "Requested model not found", HTTP_NOT_FOUND, request_id)
    except (EOFError, ModuleNotFoundError) as e:
        logger.error(f"Corrupt model artifact [{request_id}]: {e}", exc_info=True)
        return api_error("ModelError", "Model artifact is corrupt or incompatible", HTTP_INTERNAL_ERROR, request_id)
    except Exception as e:
        logger.error(f"Error in predict/location endpoint [{request_id}]: {e}", exc_info=True)
        return api_error("PredictionFailed", "An error occurred during prediction", HTTP_INTERNAL_ERROR, request_id)


# ---------------------------------------------------------------------------
# Forecast Map - per-barangay predictions at current + future time offsets
# ---------------------------------------------------------------------------

# Parañaque City center for single weather fetch
_CITY_CENTER_LAT = 14.4793
_CITY_CENTER_LON = 121.0198

# Precipitation scale factors for future projections.
# These approximate intensification / dissipation patterns from PAGASA advisories.
_RAIN_SCALE = {0: 1.0, 1: 1.15, 3: 1.35}


@predict_bp.route("/forecast-map", methods=["GET"])
@rate_limit_with_burst("30 per hour")
@require_auth_or_api_key
@require_scope("predict")
def forecast_map():
    """
    Get per-barangay flood risk predictions at current, +1 h, and +3 h.

    Fetches weather once for the city, then runs the ML model for each
    barangay applying precipitation scaling factors for future offsets.

    Query Parameters:
        hours (str): Comma-separated offsets, default "0,1,3"

    Returns:
        200: ``{ barangays: { <key>: { "0": {...}, "1": {...}, "3": {...} } } }``
    """
    from app.services.gis_service import BARANGAY_META

    request_id = getattr(g, "request_id", "unknown")

    # Parse requested hour offsets
    hours_param = request.args.get("hours", "0,1,3")
    try:
        offsets = [int(h.strip()) for h in hours_param.split(",") if h.strip().isdigit()]
    except ValueError:
        offsets = [0, 1, 3]
    if not offsets:
        offsets = [0, 1, 3]
    # Clamp to safe range
    offsets = [h for h in offsets if 0 <= h <= 6]
    if not offsets:
        offsets = [0]

    try:
        # Single weather fetch for the whole city
        weather_data = fetch_weather_by_coordinates(_CITY_CENTER_LAT, _CITY_CENTER_LON)
        base_precip = weather_data.get("precipitation", 0.0)

        result: dict = {}
        for key, meta in BARANGAY_META.items():
            barangay_forecasts: dict = {}
            for offset in offsets:
                # Scale precipitation for future offsets
                scale = _RAIN_SCALE.get(offset, 1.0 + offset * 0.1)
                forecast_input = {
                    "temperature": weather_data["temperature"],
                    "humidity": weather_data["humidity"],
                    "precipitation": round(base_precip * scale, 2),
                }

                try:
                    pred = predict_flood(forecast_input, return_proba=True, return_risk_level=True)
                    if isinstance(pred, dict):
                        # FIX: predict_flood(return_proba=True) returns probability as
                        # {"no_flood": float, "flood": float}  — NOT a plain float.
                        # Calling round() directly on the dict caused:
                        #   "type dict doesn't define __round__ method"
                        # Extract the flood probability before rounding.
                        raw_prob = pred.get("probability", 0)
                        if isinstance(raw_prob, dict):
                            # Normal path: probability dict from predict_proba()
                            prob_value = float(raw_prob.get("flood", 0))
                        elif isinstance(raw_prob, (int, float)):
                            # Legacy/single-value path
                            prob_value = float(raw_prob)
                        else:
                            # Unexpected type — log descriptively instead of crashing
                            logger.warning(
                                "Forecast %s +%dh: probability has unexpected type %s (value=%r), defaulting to 0",
                                key, offset, type(raw_prob).__name__, raw_prob,
                            )
                            prob_value = 0.0

                        # Extract confidence with same type guard
                        raw_conf = pred.get("confidence", 0)
                        conf_value = float(raw_conf) if isinstance(raw_conf, (int, float)) else 0.0

                        barangay_forecasts[str(offset)] = {
                            "risk_level": pred.get("risk_level", 0),
                            "risk_label": pred.get("risk_label", "Safe"),
                            "probability": round(prob_value, 4),
                            "confidence": round(conf_value, 3),
                        }
                    else:
                        # predict_flood returned a bare int (0 or 1) — no proba requested
                        barangay_forecasts[str(offset)] = {
                            "risk_level": 1 if pred == 1 else 0,
                            "risk_label": "Alert" if pred == 1 else "Safe",
                            "probability": 0,
                            "confidence": 0.5,
                        }
                except Exception as exc:
                    logger.warning("Forecast prediction failed for %s +%dh: %s", key, offset, exc)
                    barangay_forecasts[str(offset)] = {
                        "risk_level": 0,
                        "risk_label": "Safe",
                        "probability": 0,
                        "confidence": 0,
                    }

            result[key] = barangay_forecasts

        return jsonify({
            "success": True,
            "barangays": result,
            "offsets": offsets,
            "weather_snapshot": {
                "temperature": weather_data.get("temperature"),
                "humidity": weather_data.get("humidity"),
                "precipitation": weather_data.get("precipitation"),
                "source": weather_data.get("source"),
            },
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }), HTTP_OK

    except WeatherFetchError as e:
        logger.error("Forecast map weather fetch failed [%s]: %s", request_id, e)
        return api_error("WeatherFetchFailed", str(e), HTTP_INTERNAL_ERROR, request_id)
    except Exception as e:
        logger.error("Forecast map failed [%s]: %s", request_id, e, exc_info=True)
        return api_error("ForecastFailed", "Failed to generate forecast map", HTTP_INTERNAL_ERROR, request_id)


# ---------------------------------------------------------------------------
# Scenario Simulation - ephemeral what-if prediction (no DB persistence)
# ---------------------------------------------------------------------------

# Default Parañaque climate values for parameters not overridden
_SIMULATION_DEFAULTS = {
    "temperature": 303.15,  # ~30°C
    "humidity": 75.0,
    "precipitation": 5.0,
    "wind_speed": 3.0,
    "pressure": 1010.0,
}

# Preset scenario configurations (realistic Parañaque weather)
_SCENARIO_PRESETS = {
    "normal": {
        "label": "Normal Day",
        "temperature": 304.15,
        "humidity": 72.0,
        "precipitation": 2.0,
    },
    "heavy_monsoon": {
        "label": "Heavy Monsoon",
        "temperature": 300.15,
        "humidity": 95.0,
        "precipitation": 45.0,
    },
    "typhoon": {
        "label": "Typhoon Conditions",
        "temperature": 298.15,
        "humidity": 98.0,
        "precipitation": 120.0,
        "wind_speed": 45.0,
    },
    "high_tide_rain": {
        "label": "High Tide + Rain",
        "temperature": 302.15,
        "humidity": 88.0,
        "precipitation": 30.0,
    },
}


@predict_bp.route("/simulate", methods=["POST"])
@rate_limit_with_burst("30 per hour")
@validate_request_size(endpoint_name="predict")
@require_auth_or_api_key
@require_scope("predict")
def simulate():
    """
    Run a what-if flood prediction without persisting to the database.

    Accepts weather parameter overrides. Omitted parameters use safe
    defaults for Parañaque City. Returns the full prediction result
    including XAI explanation.

    Request Body:
        temperature (float): Temperature in Kelvin (optional)
        humidity (float): Relative humidity 0-100 (optional)
        precipitation (float): Precipitation in mm/hour (optional)
        wind_speed (float): Wind speed in m/s (optional)
        pressure (float): Atmospheric pressure in hPa (optional)
        preset (str): Named scenario preset (optional, overrides individual params)

    Returns:
        200: Simulation result with prediction, risk classification, and XAI
    ---
    tags:
      - Predictions
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            temperature:
              type: number
              description: Temperature in Kelvin (default 303.15)
            humidity:
              type: number
              description: Relative humidity 0-100% (default 75)
            precipitation:
              type: number
              description: Precipitation in mm/hour (default 5)
            wind_speed:
              type: number
              description: Wind speed in m/s (default 3)
            pressure:
              type: number
              description: Atmospheric pressure in hPa (default 1010)
            preset:
              type: string
              enum: [normal, heavy_monsoon, typhoon, high_tide_rain]
              description: Named preset scenario
    responses:
      200:
        description: Simulation result
      400:
        description: Validation error
    security:
      - api_key: []
      - bearer_auth: []
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        input_data = request.get_json(force=True, silent=True) or {}
        if not isinstance(input_data, dict):
            return api_error("InvalidInput", "Request body must be a JSON object", HTTP_BAD_REQUEST, request_id)

        # Apply preset if specified
        preset_name = input_data.get("preset")
        if preset_name:
            if preset_name not in _SCENARIO_PRESETS:
                return api_error(
                    "ValidationError",
                    f"Unknown preset. Valid presets: {', '.join(_SCENARIO_PRESETS)}",
                    HTTP_BAD_REQUEST,
                    request_id,
                )
            base = {**_SIMULATION_DEFAULTS, **_SCENARIO_PRESETS[preset_name]}
        else:
            base = dict(_SIMULATION_DEFAULTS)

        # Override defaults with any explicitly provided values
        for key in ("temperature", "humidity", "precipitation", "wind_speed", "pressure"):
            val = input_data.get(key)
            if val is not None:
                try:
                    base[key] = float(val)
                except (TypeError, ValueError):
                    return api_error("ValidationError", f"{key} must be a number", HTTP_BAD_REQUEST, request_id)

        # Validate ranges
        try:
            validated = InputValidator.validate_prediction_input(base)
        except ValidationError as e:
            return api_error(
                "ValidationError", "Input validation failed", HTTP_BAD_REQUEST, request_id, errors=getattr(e, "errors", None)
            )

        # Run prediction (ephemeral - not persisted)
        prediction = predict_flood(
            validated,
            return_proba=True,
            return_risk_level=True,
        )

        if isinstance(prediction, dict):
            response = {
                "success": True,
                "simulation": True,
                "prediction": prediction["prediction"],
                "flood_risk": "high" if prediction["prediction"] == 1 else "low",
                "model_version": prediction.get("model_version"),
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "input_parameters": base,
                "preset": preset_name,
                "available_presets": {k: v.get("label", k) for k, v in _SCENARIO_PRESETS.items()},
            }
            if "probability" in prediction:
                response["probability"] = prediction["probability"]
            if "risk_label" in prediction:
                response["risk_level"] = prediction.get("risk_level")
                response["risk_label"] = prediction.get("risk_label")
                response["risk_color"] = prediction.get("risk_color")
                response["risk_description"] = prediction.get("risk_description")
                response["confidence"] = prediction.get("confidence")
            if "smart_alert" in prediction:
                response["smart_alert"] = prediction["smart_alert"]
            if "explanation" in prediction:
                response["explanation"] = prediction["explanation"]
            if "features_used" in prediction:
                response["features_used"] = prediction["features_used"]
        else:
            response = {
                "success": True,
                "simulation": True,
                "prediction": prediction,
                "flood_risk": "high" if prediction == 1 else "low",
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "input_parameters": base,
                "preset": preset_name,
                "available_presets": {k: v.get("label", k) for k, v in _SCENARIO_PRESETS.items()},
            }

        return jsonify(response), HTTP_OK

    except FileNotFoundError as e:
        logger.error(f"Model not found in simulate [{request_id}]: {e}")
        return api_error("ModelNotFound", "Requested model not found", HTTP_NOT_FOUND, request_id)
    except Exception as e:
        logger.error(f"Simulation failed [{request_id}]: {e}", exc_info=True)
        return api_error("SimulationFailed", "An error occurred during simulation", HTTP_INTERNAL_ERROR, request_id)
