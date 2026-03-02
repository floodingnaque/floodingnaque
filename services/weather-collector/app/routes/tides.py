"""
Tide data routes.

Endpoints for Manila Bay tidal data from WorldTides API.
"""

import logging

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

tides_bp = Blueprint("tides", __name__)


@tides_bp.route("/current", methods=["GET"])
def current_tides():
    """Get current tide level for Manila Bay."""
    try:
        from app.services.collector import WeatherCollector

        collector = WeatherCollector()
        data = collector.get_current_tides()
        return jsonify({"success": True, "data": data})
    except Exception as e:
        logger.error("Tide data error: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@tides_bp.route("/extremes", methods=["GET"])
def tide_extremes():
    """Get high/low tide predictions."""
    days = request.args.get("days", 7, type=int)
    try:
        from app.services.collector import WeatherCollector

        collector = WeatherCollector()
        data = collector.get_tide_extremes(days=days)
        return jsonify({"success": True, "data": data, "days": days})
    except Exception as e:
        logger.error("Tide extremes error: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@tides_bp.route("/prediction", methods=["GET"])
def tide_prediction():
    """Get hourly tide level predictions."""
    hours = request.args.get("hours", 24, type=int)
    try:
        from app.services.collector import WeatherCollector

        collector = WeatherCollector()
        data = collector.get_tide_prediction(hours=hours)
        return jsonify({"success": True, "data": data, "hours": hours})
    except Exception as e:
        logger.error("Tide prediction error: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500
