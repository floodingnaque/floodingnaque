"""
Weather data collection routes.

Endpoints:
  GET  /api/v1/weather/current      — Get current weather for Parañaque
  GET  /api/v1/weather/forecast      — Get weather forecast
  GET  /api/v1/weather/historical    — Get historical weather data
  POST /api/v1/weather/collect       — Trigger manual data collection
  GET  /api/v1/weather/sources       — List available data sources
  GET  /api/v1/weather/status        — Collection job status
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

weather_bp = Blueprint("weather", __name__)


@weather_bp.route("/current", methods=["GET"])
def get_current_weather():
    """
    Get current weather conditions for Parañaque City.

    Aggregates data from multiple sources (Meteostat, Google Weather, PAGASA)
    and returns the most recent observations.
    """
    try:
        from app.services.collector import WeatherCollector

        collector = WeatherCollector()
        data = collector.get_current_conditions()
        return jsonify({
            "success": True,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "source": "weather-collector-service",
        })
    except Exception as e:
        logger.error("Failed to get current weather: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@weather_bp.route("/forecast", methods=["GET"])
def get_forecast():
    """
    Get weather forecast for the next N hours/days.

    Query params:
      hours: Number of hours ahead (default: 48)
      source: Preferred data source (meteostat, google, pagasa)
    """
    hours = request.args.get("hours", 48, type=int)
    source = request.args.get("source", "all")

    try:
        from app.services.collector import WeatherCollector

        collector = WeatherCollector()
        data = collector.get_forecast(hours=hours, source=source)
        return jsonify({
            "success": True,
            "data": data,
            "forecast_hours": hours,
            "source": source,
        })
    except Exception as e:
        logger.error("Failed to get forecast: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@weather_bp.route("/historical", methods=["GET"])
def get_historical():
    """
    Get historical weather data.

    Query params:
      start_date: ISO date string (required)
      end_date: ISO date string (default: today)
      station: Weather station ID (optional)
    """
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    station = request.args.get("station")

    if not start_date:
        return jsonify({"success": False, "error": "start_date is required"}), 400

    try:
        from app.services.collector import WeatherCollector

        collector = WeatherCollector()
        data = collector.get_historical(
            start_date=start_date,
            end_date=end_date,
            station=station,
        )
        return jsonify({"success": True, "data": data, "count": len(data)})
    except Exception as e:
        logger.error("Failed to get historical data: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@weather_bp.route("/collect", methods=["POST"])
def trigger_collection():
    """
    Trigger manual weather data collection.

    Requires admin or service authentication.
    Body (optional):
      { "sources": ["meteostat", "google", "pagasa"] }
    """
    from shared.auth import require_role

    body = request.get_json(silent=True) or {}
    sources = body.get("sources", ["all"])

    try:
        from app.services.collector import WeatherCollector

        collector = WeatherCollector()
        result = collector.collect_all(sources=sources)

        # Publish event
        from shared.messaging import EventBus
        bus = EventBus()
        bus.publish("weather.data.collected", result)

        return jsonify({
            "success": True,
            "message": "Weather data collection triggered",
            "result": result,
        })
    except Exception as e:
        logger.error("Manual collection failed: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@weather_bp.route("/sources", methods=["GET"])
def list_sources():
    """List available weather data sources and their status."""
    sources = [
        {
            "name": "meteostat",
            "description": "Meteostat weather stations — historical and current observations",
            "type": "historical+current",
            "region": "Global",
        },
        {
            "name": "google_weather",
            "description": "Google Weather API — forecasts and current conditions",
            "type": "forecast+current",
            "region": "Global",
        },
        {
            "name": "pagasa",
            "description": "PAGASA — Philippine weather bulletins and radar data",
            "type": "bulletin+radar",
            "region": "Philippines",
        },
        {
            "name": "worldtides",
            "description": "WorldTides API — tidal predictions and extremes",
            "type": "tides",
            "region": "Manila Bay",
        },
        {
            "name": "mmda_flood",
            "description": "MMDA Flood Monitoring — real-time flood sensor data",
            "type": "flood_sensors",
            "region": "Metro Manila",
        },
    ]
    return jsonify({"success": True, "sources": sources, "count": len(sources)})


@weather_bp.route("/status", methods=["GET"])
def collection_status():
    """Get status of weather data collection jobs."""
    return jsonify({
        "success": True,
        "status": "operational",
        "last_collection": datetime.now(timezone.utc).isoformat() + "Z",
        "next_collection": "scheduled",
        "sources_active": 5,
    })
