"""
Data Export API.

Endpoints for exporting historical weather and prediction data.
"""

import csv
import logging
from datetime import datetime
from io import StringIO

from app.api.middleware.auth import require_api_key
from app.api.middleware.rate_limit import limiter
from app.models.db import Prediction, WeatherData, get_db_session
from flask import Blueprint, Response, jsonify, request

logger = logging.getLogger(__name__)

export_bp = Blueprint("export", __name__)


@export_bp.route("/weather", methods=["GET"])
@require_api_key
@limiter.limit("5 per minute")
def export_weather():
    """
    Export historical weather data.

    Query Parameters:
        format: csv or json (default: json)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        limit: Maximum records (default: 1000, max: 10000)

    Returns:
        200: Exported data
        400: Invalid parameters
    """
    try:
        # Get parameters
        export_format = request.args.get("format", "json").lower()
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        limit = int(request.args.get("limit", 1000))

        # Validate format
        if export_format not in ["csv", "json"]:
            return jsonify({"error": "Invalid format. Must be csv or json"}), 400

        # Validate limit
        max_limit = 10000
        if limit > max_limit:
            return jsonify({"error": f"Limit exceeds maximum of {max_limit}"}), 400

        # Build query
        with get_db_session() as session:
            query = session.query(WeatherData).filter_by(is_deleted=False)

            # Apply date filters
            if start_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    query = query.filter(WeatherData.timestamp >= start_dt)
                except ValueError:
                    return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD"}), 400

            if end_date:
                try:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                    query = query.filter(WeatherData.timestamp <= end_dt)
                except ValueError:
                    return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD"}), 400

            # Order and limit
            query = query.order_by(WeatherData.timestamp.desc()).limit(limit)

            # Execute query
            weather_data = query.all()

        if not weather_data:
            return jsonify({"message": "No data found", "count": 0}), 200

        # Export as CSV
        if export_format == "csv":
            output = StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow(
                [
                    "id",
                    "timestamp",
                    "temperature",
                    "humidity",
                    "precipitation",
                    "wind_speed",
                    "pressure",
                    "latitude",
                    "longitude",
                    "location",
                ]
            )

            # Write data
            for record in weather_data:
                writer.writerow(
                    [
                        record.id,
                        record.timestamp.isoformat() if record.timestamp else "",
                        record.temperature,
                        record.humidity,
                        record.precipitation,
                        record.wind_speed,
                        record.pressure,
                        record.latitude,
                        record.longitude,
                        record.location,
                    ]
                )

            csv_data = output.getvalue()
            output.close()

            return Response(
                csv_data,
                mimetype="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename=weather_data_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
                },
            )

        # Export as JSON
        else:
            data_list = []
            for record in weather_data:
                data_list.append(
                    {
                        "id": record.id,
                        "timestamp": record.timestamp.isoformat() if record.timestamp else None,
                        "temperature": record.temperature,
                        "humidity": record.humidity,
                        "precipitation": record.precipitation,
                        "wind_speed": record.wind_speed,
                        "pressure": record.pressure,
                        "latitude": record.latitude,
                        "longitude": record.longitude,
                        "location": record.location,
                    }
                )

            return jsonify({"data": data_list, "count": len(data_list), "format": "json"}), 200

    except Exception as e:
        logger.error(f"Error exporting weather data: {e}")
        return jsonify({"error": "Internal server error"}), 500


@export_bp.route("/predictions", methods=["GET"])
@require_api_key
@limiter.limit("5 per minute")
def export_predictions():
    """
    Export historical prediction data.

    Query Parameters:
        format: csv or json (default: json)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        risk_level: Filter by risk level
        limit: Maximum records (default: 1000, max: 10000)

    Returns:
        200: Exported data
        400: Invalid parameters
    """
    try:
        # Get parameters
        export_format = request.args.get("format", "json").lower()
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        risk_level = request.args.get("risk_level")
        limit = int(request.args.get("limit", 1000))

        # Validate format
        if export_format not in ["csv", "json"]:
            return jsonify({"error": "Invalid format. Must be csv or json"}), 400

        # Validate limit
        max_limit = 10000
        if limit > max_limit:
            return jsonify({"error": f"Limit exceeds maximum of {max_limit}"}), 400

        # Build query
        with get_db_session() as session:
            query = session.query(Prediction).filter_by(is_deleted=False)

            # Apply filters
            if start_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    query = query.filter(Prediction.created_at >= start_dt)
                except ValueError:
                    return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD"}), 400

            if end_date:
                try:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                    query = query.filter(Prediction.created_at <= end_dt)
                except ValueError:
                    return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD"}), 400

            if risk_level:
                query = query.filter(Prediction.risk_level == risk_level)

            # Order and limit
            query = query.order_by(Prediction.created_at.desc()).limit(limit)

            # Execute query
            predictions = query.all()

        if not predictions:
            return jsonify({"message": "No data found", "count": 0}), 200

        # Export as CSV
        if export_format == "csv":
            output = StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow(
                [
                    "id",
                    "timestamp",
                    "prediction",
                    "risk_level",
                    "confidence",
                    "temperature",
                    "humidity",
                    "precipitation",
                    "model_version",
                ]
            )

            # Write data
            for record in predictions:
                writer.writerow(
                    [
                        record.id,
                        record.created_at.isoformat() if record.created_at else "",
                        record.prediction,
                        record.risk_level,
                        record.confidence,
                        getattr(record, "temperature", None),
                        getattr(record, "humidity", None),
                        getattr(record, "precipitation", None),
                        record.model_version,
                    ]
                )

            csv_data = output.getvalue()
            output.close()

            return Response(
                csv_data,
                mimetype="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename=predictions_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
                },
            )

        # Export as JSON
        else:
            data_list = []
            for record in predictions:
                data_list.append(
                    {
                        "id": record.id,
                        "timestamp": record.created_at.isoformat() if record.created_at else None,
                        "prediction": record.prediction,
                        "risk_level": record.risk_level,
                        "confidence": record.confidence,
                        "temperature": getattr(record, "temperature", None),
                        "humidity": getattr(record, "humidity", None),
                        "precipitation": getattr(record, "precipitation", None),
                        "model_version": record.model_version,
                    }
                )

            return jsonify({"data": data_list, "count": len(data_list), "format": "json"}), 200

    except Exception as e:
        logger.error(f"Error exporting predictions: {e}")
        return jsonify({"error": "Internal server error"}), 500
