"""
Weather data ingestion routes.

Handles incoming weather data from external sensors,
manual uploads, and third-party integrations.
"""

import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

ingest_bp = Blueprint("ingest", __name__)


@ingest_bp.route("/", methods=["POST"])
def ingest_weather():
    """
    Ingest weather observation data.

    Body:
      {
        "station_id": "PAGASA-MNL",
        "timestamp": "2026-03-02T10:00:00Z",
        "temperature": 31.2,
        "humidity": 78,
        "precipitation": 5.4,
        "wind_speed": 12.3,
        "wind_direction": 180,
        "pressure": 1013.25,
        "source": "manual"
      }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Request body required"}), 400

    required = ["temperature", "humidity"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"success": False, "error": f"Missing fields: {missing}"}), 422

    try:
        from app.services.collector import WeatherCollector

        collector = WeatherCollector()
        record_id = collector.store_observation(data)

        # Publish event
        from shared.messaging import EventBus
        bus = EventBus()
        bus.publish("weather.data.ingested", {
            "record_id": record_id,
            "source": data.get("source", "manual"),
            "timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat()),
        })

        return jsonify({
            "success": True,
            "message": "Weather data ingested",
            "record_id": record_id,
        }), 201
    except Exception as e:
        logger.error("Ingestion failed: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@ingest_bp.route("/batch", methods=["POST"])
def ingest_batch():
    """
    Batch ingest multiple weather observations.

    Body: { "observations": [ ... ] }
    """
    data = request.get_json()
    if not data or "observations" not in data:
        return jsonify({"success": False, "error": "observations array required"}), 400

    observations = data["observations"]
    if not isinstance(observations, list):
        return jsonify({"success": False, "error": "observations must be an array"}), 422

    try:
        from app.services.collector import WeatherCollector

        collector = WeatherCollector()
        results = collector.store_batch(observations)

        return jsonify({
            "success": True,
            "message": f"Batch ingested {results['stored']} of {len(observations)} records",
            "stored": results["stored"],
            "errors": results.get("errors", []),
        }), 201
    except Exception as e:
        logger.error("Batch ingestion failed: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500
