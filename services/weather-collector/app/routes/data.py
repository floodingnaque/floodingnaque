"""
Weather data query routes.

Provides access to stored weather observations with filtering,
pagination, and export capabilities.
"""

import logging

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

data_bp = Blueprint("data", __name__)


@data_bp.route("/", methods=["GET"])
def list_weather_data():
    """
    List weather observations with pagination and filtering.

    Query params:
      page: Page number (default: 1)
      per_page: Items per page (default: 50, max: 200)
      source: Filter by data source
      start_date: Filter from date (ISO format)
      end_date: Filter to date (ISO format)
      sort: Sort field (default: timestamp)
      order: Sort order (asc/desc, default: desc)
    """
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 200)
    source = request.args.get("source")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    try:
        from app.services.collector import WeatherCollector

        collector = WeatherCollector()
        result = collector.query_observations(
            page=page,
            per_page=per_page,
            source=source,
            start_date=start_date,
            end_date=end_date,
        )
        return jsonify({"success": True, **result})
    except Exception as e:
        logger.error("Data query failed: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@data_bp.route("/stats", methods=["GET"])
def data_stats():
    """Get summary statistics for weather data."""
    days = request.args.get("days", 30, type=int)
    try:
        from app.services.collector import WeatherCollector

        collector = WeatherCollector()
        stats = collector.get_data_stats(days=days)
        return jsonify({"success": True, "stats": stats, "period_days": days})
    except Exception as e:
        logger.error("Stats query failed: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@data_bp.route("/export", methods=["GET"])
def export_data():
    """
    Export weather data in CSV or JSON format.

    Query params:
      format: Export format (csv/json, default: json)
      start_date: From date
      end_date: To date
    """
    fmt = request.args.get("format", "json")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    try:
        from app.services.collector import WeatherCollector

        collector = WeatherCollector()
        data = collector.export_data(
            format=fmt,
            start_date=start_date,
            end_date=end_date,
        )

        if fmt == "csv":
            from flask import Response
            return Response(
                data,
                mimetype="text/csv",
                headers={"Content-Disposition": "attachment; filename=weather_data.csv"},
            )
        return jsonify({"success": True, "data": data})
    except Exception as e:
        logger.error("Export failed: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500
