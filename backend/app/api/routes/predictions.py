"""
Prediction History Routes.

Provides CRUD endpoints for accessing and managing flood prediction history.
"""

import logging
from datetime import datetime, timedelta, timezone

from app.api.middleware.auth import require_api_key
from app.api.middleware.rate_limit import limiter
from app.models.db import Prediction, WeatherData, get_db_session
from app.utils.api_constants import (
    HTTP_BAD_REQUEST,
    HTTP_INTERNAL_ERROR,
    HTTP_NOT_FOUND,
    HTTP_OK,
)
from app.utils.api_responses import api_error
from flask import Blueprint, g, jsonify, request
from sqlalchemy import asc, desc

logger = logging.getLogger(__name__)

predictions_bp = Blueprint("predictions", __name__)


@predictions_bp.route("", methods=["GET"])
@limiter.limit("60 per minute")
def get_predictions():
    """
    Get list of predictions with pagination, filtering, and sorting.

    Query Parameters:
        limit (int): Maximum number of predictions (default: 50, max: 500)
        offset (int): Number of records to skip (default: 0)
        risk_level (int): Filter by risk level (0, 1, 2)
        prediction (int): Filter by prediction result (0=no flood, 1=flood)
        start_date (str): Filter predictions after this date (ISO format)
        end_date (str): Filter predictions before this date (ISO format)
        sort_by (str): Field to sort by (created_at, risk_level, confidence, model_version)
        order (str): Sort order (asc, desc) - default: desc
        min_confidence (float): Filter by minimum confidence (0-1)
        max_confidence (float): Filter by maximum confidence (0-1)
        model_version (int): Filter by specific model version
        model_name (str): Filter by model name

    Returns:
        200: List of predictions with pagination info
    ---
    tags:
      - Predictions
    parameters:
      - in: query
        name: limit
        type: integer
        default: 50
      - in: query
        name: offset
        type: integer
        default: 0
      - in: query
        name: risk_level
        type: integer
        enum: [0, 1, 2]
      - in: query
        name: prediction
        type: integer
        enum: [0, 1]
      - in: query
        name: sort_by
        type: string
        enum: [created_at, risk_level, confidence, model_version]
      - in: query
        name: order
        type: string
        enum: [asc, desc]
      - in: query
        name: min_confidence
        type: number
      - in: query
        name: max_confidence
        type: number
      - in: query
        name: model_version
        type: integer
      - in: query
        name: model_name
        type: string
    responses:
      200:
        description: List of predictions
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        # Parse query parameters
        limit = min(request.args.get("limit", 50, type=int), 500)
        offset = request.args.get("offset", 0, type=int)
        risk_level = request.args.get("risk_level", type=int)
        prediction_filter = request.args.get("prediction", type=int)
        start_date = request.args.get("start_date", type=str)
        end_date = request.args.get("end_date", type=str)
        sort_by = request.args.get("sort_by", "created_at")
        order = request.args.get("order", "desc")

        # Advanced filtering parameters
        min_confidence = request.args.get("min_confidence", type=float)
        max_confidence = request.args.get("max_confidence", type=float)
        model_version_filter = request.args.get("model_version", type=int)
        model_name_filter = request.args.get("model_name", type=str)

        if limit < 1:
            return api_error("ValidationError", "Limit must be at least 1", HTTP_BAD_REQUEST, request_id)

        # Validate sort parameters
        valid_sort_fields = ["created_at", "risk_level", "confidence", "model_version"]
        if sort_by not in valid_sort_fields:
            return api_error(
                "ValidationError", f"sort_by must be one of: {valid_sort_fields}", HTTP_BAD_REQUEST, request_id
            )

        if order not in ["asc", "desc"]:
            return api_error("ValidationError", "order must be asc or desc", HTTP_BAD_REQUEST, request_id)

        with get_db_session() as session:
            query = session.query(Prediction).filter(Prediction.is_deleted.is_(False))

            # Apply filters
            if risk_level is not None:
                if risk_level not in [0, 1, 2]:
                    return api_error("ValidationError", "Risk level must be 0, 1, or 2", HTTP_BAD_REQUEST, request_id)
                query = query.filter(Prediction.risk_level == risk_level)

            if prediction_filter is not None:
                if prediction_filter not in [0, 1]:
                    return api_error("ValidationError", "Prediction must be 0 or 1", HTTP_BAD_REQUEST, request_id)
                query = query.filter(Prediction.prediction == prediction_filter)

            if start_date:
                try:
                    start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                    query = query.filter(Prediction.created_at >= start_dt)
                except ValueError:
                    return api_error("ValidationError", "Invalid start_date format", HTTP_BAD_REQUEST, request_id)

            if end_date:
                try:
                    end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                    query = query.filter(Prediction.created_at <= end_dt)
                except ValueError:
                    return api_error("ValidationError", "Invalid end_date format", HTTP_BAD_REQUEST, request_id)

            # Advanced filtering
            if min_confidence is not None:
                if min_confidence < 0 or min_confidence > 1:
                    return api_error(
                        "ValidationError", "min_confidence must be between 0 and 1", HTTP_BAD_REQUEST, request_id
                    )
                query = query.filter(Prediction.confidence >= min_confidence)

            if max_confidence is not None:
                if max_confidence < 0 or max_confidence > 1:
                    return api_error(
                        "ValidationError", "max_confidence must be between 0 and 1", HTTP_BAD_REQUEST, request_id
                    )
                query = query.filter(Prediction.confidence <= max_confidence)

            if model_version_filter is not None:
                query = query.filter(Prediction.model_version == model_version_filter)

            if model_name_filter:
                query = query.filter(Prediction.model_name == model_name_filter)

            # Get total count
            total = query.count()

            # Apply sorting
            sort_column = getattr(Prediction, sort_by)
            if order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))

            # Apply pagination
            query = query.offset(offset).limit(limit)
            predictions = query.all()

            # Format response
            predictions_data = []
            for pred in predictions:
                predictions_data.append(
                    {
                        "id": pred.id,
                        "weather_data_id": pred.weather_data_id,
                        "prediction": pred.prediction,
                        "risk_level": pred.risk_level,
                        "risk_label": pred.risk_label,
                        "confidence": pred.confidence,
                        "model_version": pred.model_version,
                        "model_name": pred.model_name,
                        "created_at": pred.created_at.isoformat() if pred.created_at else None,
                    }
                )

        return (
            jsonify(
                {
                    "success": True,
                    "data": predictions_data,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "count": len(predictions_data),
                    "sort_by": sort_by,
                    "order": order,
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Error fetching predictions [{request_id}]: {str(e)}", exc_info=True)
        return api_error("FetchFailed", "Failed to fetch predictions", HTTP_INTERNAL_ERROR, request_id)


@predictions_bp.route("/<int:prediction_id>", methods=["GET"])
@limiter.limit("60 per minute")
def get_prediction_by_id(prediction_id):
    """
    Get a specific prediction by ID with associated weather data.

    Returns:
        200: Prediction details with weather data
        404: Prediction not found
    ---
    tags:
      - Predictions
    parameters:
      - in: path
        name: prediction_id
        type: integer
        required: true
    responses:
      200:
        description: Prediction details
      404:
        description: Not found
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        with get_db_session() as session:
            prediction = (
                session.query(Prediction)
                .filter(Prediction.id == prediction_id, Prediction.is_deleted.is_(False))
                .first()
            )

            if not prediction:
                return api_error(
                    "NotFound", f"Prediction with id {prediction_id} not found", HTTP_NOT_FOUND, request_id
                )

            prediction_data = {
                "id": prediction.id,
                "weather_data_id": prediction.weather_data_id,
                "prediction": prediction.prediction,
                "risk_level": prediction.risk_level,
                "risk_label": prediction.risk_label,
                "confidence": prediction.confidence,
                "model_version": prediction.model_version,
                "model_name": prediction.model_name,
                "created_at": prediction.created_at.isoformat() if prediction.created_at else None,
            }

            # Include associated weather data if available
            if prediction.weather_data_id:
                weather = session.query(WeatherData).filter(WeatherData.id == prediction.weather_data_id).first()

                if weather:
                    prediction_data["weather_data"] = {
                        "id": weather.id,
                        "temperature": weather.temperature,
                        "humidity": weather.humidity,
                        "precipitation": weather.precipitation,
                        "wind_speed": weather.wind_speed,
                        "pressure": weather.pressure,
                        "timestamp": weather.timestamp.isoformat() if weather.timestamp else None,
                    }

        return jsonify({"success": True, "data": prediction_data, "request_id": request_id}), HTTP_OK

    except Exception as e:
        logger.error(f"Error fetching prediction {prediction_id} [{request_id}]: {str(e)}", exc_info=True)
        return api_error("FetchFailed", "Failed to fetch prediction", HTTP_INTERNAL_ERROR, request_id)


@predictions_bp.route("/<int:prediction_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
@require_api_key
def delete_prediction(prediction_id):
    """
    Delete a prediction (soft delete).

    Returns:
        200: Prediction deleted successfully
        404: Prediction not found
    ---
    tags:
      - Predictions
    parameters:
      - in: path
        name: prediction_id
        type: integer
        required: true
    responses:
      200:
        description: Prediction deleted
      404:
        description: Not found
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        with get_db_session() as session:
            prediction = (
                session.query(Prediction)
                .filter(Prediction.id == prediction_id, Prediction.is_deleted.is_(False))
                .first()
            )

            if not prediction:
                return api_error(
                    "NotFound", f"Prediction with id {prediction_id} not found", HTTP_NOT_FOUND, request_id
                )

            # Soft delete
            prediction.soft_delete()

        logger.info(f"Prediction deleted: id={prediction_id} [{request_id}]")

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Prediction deleted successfully",
                    "prediction_id": prediction_id,
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Error deleting prediction {prediction_id} [{request_id}]: {str(e)}", exc_info=True)
        return api_error("DeleteFailed", "Failed to delete prediction", HTTP_INTERNAL_ERROR, request_id)


@predictions_bp.route("/stats", methods=["GET"])
@limiter.limit("30 per minute")
def get_prediction_stats():
    """
    Get prediction statistics.

    Query Parameters:
        days (int): Number of days of history (default: 30, max: 365)

    Returns:
        200: Prediction statistics
    ---
    tags:
      - Predictions
    parameters:
      - in: query
        name: days
        type: integer
        default: 30
    responses:
      200:
        description: Prediction statistics
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        days = min(request.args.get("days", 30, type=int), 365)

        if days < 1:
            return api_error("ValidationError", "Days must be at least 1", HTTP_BAD_REQUEST, request_id)

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        with get_db_session() as session:
            # Total predictions in period
            total = (
                session.query(Prediction)
                .filter(Prediction.is_deleted.is_(False), Prediction.created_at >= cutoff_date)
                .count()
            )

            # Flood predictions
            flood_count = (
                session.query(Prediction)
                .filter(
                    Prediction.is_deleted.is_(False), Prediction.created_at >= cutoff_date, Prediction.prediction == 1
                )
                .count()
            )

            # Risk level distribution
            safe_count = (
                session.query(Prediction)
                .filter(
                    Prediction.is_deleted.is_(False), Prediction.created_at >= cutoff_date, Prediction.risk_level == 0
                )
                .count()
            )

            alert_count = (
                session.query(Prediction)
                .filter(
                    Prediction.is_deleted.is_(False), Prediction.created_at >= cutoff_date, Prediction.risk_level == 1
                )
                .count()
            )

            critical_count = (
                session.query(Prediction)
                .filter(
                    Prediction.is_deleted.is_(False), Prediction.created_at >= cutoff_date, Prediction.risk_level == 2
                )
                .count()
            )

            # Average confidence
            from sqlalchemy import func

            avg_confidence = (
                session.query(func.avg(Prediction.confidence))
                .filter(
                    Prediction.is_deleted.is_(False),
                    Prediction.created_at >= cutoff_date,
                    Prediction.confidence.isnot(None),
                )
                .scalar()
            )

        return (
            jsonify(
                {
                    "success": True,
                    "stats": {
                        "period_days": days,
                        "total_predictions": total,
                        "flood_predictions": flood_count,
                        "no_flood_predictions": total - flood_count,
                        "flood_percentage": round((flood_count / total * 100), 2) if total > 0 else 0,
                        "risk_distribution": {
                            "safe": safe_count,
                            "alert": alert_count,
                            "critical": critical_count,
                        },
                        "average_confidence": round(avg_confidence, 4) if avg_confidence else None,
                    },
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Error fetching prediction stats [{request_id}]: {str(e)}", exc_info=True)
        return api_error("FetchFailed", "Failed to fetch prediction statistics", HTTP_INTERNAL_ERROR, request_id)


@predictions_bp.route("/recent", methods=["GET"])
@limiter.limit("60 per minute")
def get_recent_predictions():
    """
    Get most recent predictions.

    Query Parameters:
        limit (int): Maximum predictions to return (default: 10, max: 50)

    Returns:
        200: List of recent predictions
    ---
    tags:
      - Predictions
    parameters:
      - in: query
        name: limit
        type: integer
        default: 10
    responses:
      200:
        description: Recent predictions
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        limit = min(request.args.get("limit", 10, type=int), 50)

        with get_db_session() as session:
            predictions = (
                session.query(Prediction)
                .filter(Prediction.is_deleted.is_(False))
                .order_by(desc(Prediction.created_at))
                .limit(limit)
                .all()
            )

            predictions_data = []
            for pred in predictions:
                predictions_data.append(
                    {
                        "id": pred.id,
                        "prediction": pred.prediction,
                        "risk_level": pred.risk_level,
                        "risk_label": pred.risk_label,
                        "confidence": pred.confidence,
                        "created_at": pred.created_at.isoformat() if pred.created_at else None,
                    }
                )

        return (
            jsonify(
                {"success": True, "data": predictions_data, "count": len(predictions_data), "request_id": request_id}
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Error fetching recent predictions [{request_id}]: {str(e)}", exc_info=True)
        return api_error("FetchFailed", "Failed to fetch recent predictions", HTTP_INTERNAL_ERROR, request_id)


@predictions_bp.route("/bulk-delete", methods=["POST"])
@limiter.limit("10 per minute")
@require_api_key
def bulk_delete_predictions():
    """
    Bulk delete prediction records (soft delete).

    Request Body:
    {
        "ids": [1, 2, 3],  // Optional: specific IDs to delete
        "start_date": "2024-01-01T00:00:00",  // Optional: delete records after this date
        "end_date": "2024-01-31T23:59:59",    // Optional: delete records before this date
        "risk_level": 0,  // Optional: delete records with specific risk level
        "confirm": true  // Required: must be true to execute deletion
    }

    Maximum 500 records can be deleted in a single request.

    Returns:
        200: Records deleted successfully
        400: Invalid request
    ---
    tags:
      - Predictions
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
            risk_level:
              type: integer
            confirm:
              type: boolean
    responses:
      200:
        description: Bulk delete completed
      400:
        description: Validation error
    """
    request_id = getattr(g, "request_id", "unknown")
    MAX_BULK_DELETE = 500

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
        risk_level = data.get("risk_level")

        # Require at least one filter
        if not ids and not start_date and not end_date and risk_level is None:
            return api_error(
                "ValidationError",
                "At least one filter (ids, date range, or risk_level) must be provided",
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
            query = session.query(Prediction).filter(Prediction.is_deleted.is_(False))

            # Apply filters
            if ids:
                query = query.filter(Prediction.id.in_(ids))

            if start_date:
                try:
                    start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                    query = query.filter(Prediction.created_at >= start_dt)
                except ValueError:
                    return api_error("ValidationError", "Invalid start_date format", HTTP_BAD_REQUEST, request_id)

            if end_date:
                try:
                    end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                    query = query.filter(Prediction.created_at <= end_dt)
                except ValueError:
                    return api_error("ValidationError", "Invalid end_date format", HTTP_BAD_REQUEST, request_id)

            if risk_level is not None:
                if risk_level not in [0, 1, 2]:
                    return api_error("ValidationError", "risk_level must be 0, 1, or 2", HTTP_BAD_REQUEST, request_id)
                query = query.filter(Prediction.risk_level == risk_level)

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

        logger.info(f"Bulk delete predictions completed: {len(deleted_ids)} records [{request_id}]")

        return (
            jsonify(
                {
                    "success": True,
                    "message": f"Successfully deleted {len(deleted_ids)} prediction records",
                    "deleted_count": len(deleted_ids),
                    "deleted_ids": deleted_ids,
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Bulk delete predictions failed [{request_id}]: {str(e)}", exc_info=True)
        return api_error("DeleteFailed", "Failed to perform bulk delete", HTTP_INTERNAL_ERROR, request_id)
