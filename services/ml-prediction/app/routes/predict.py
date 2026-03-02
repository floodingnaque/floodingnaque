"""
Prediction routes.

Endpoints:
  POST /api/v1/predict/           — Run flood risk prediction
  POST /api/v1/predict/realtime   — Real-time prediction with latest weather
  GET  /api/v1/predict/risk-levels — Get risk level definitions
"""

import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

predict_bp = Blueprint("predict", __name__)


@predict_bp.route("/", methods=["POST"])
def predict():
    """
    Run flood risk prediction.

    Body:
      {
        "temperature": 30.5,
        "humidity": 85,
        "precipitation": 45.2,
        "wind_speed": 15.0,
        "pressure": 1008.5,
        "tide_height": 0.8,
        "soil_moisture": 0.75,
        "model": "random_forest"  // optional: random_forest, xgboost, lightgbm, ensemble
      }

    Returns:
      {
        "success": true,
        "prediction": {
          "flood_probability": 0.82,
          "risk_level": "high",
          "confidence": 0.91,
          "model_used": "random_forest",
          "model_version": "2.1.0",
          "features_used": [...],
          "contributing_factors": [...]
        }
      }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Request body required"}), 400

    required = ["temperature", "humidity", "precipitation"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"success": False, "error": f"Missing features: {missing}"}), 422

    try:
        from app.services.predictor import FloodPredictor

        predictor = FloodPredictor.get_instance()
        model_type = data.pop("model", "random_forest")
        result = predictor.predict(features=data, model_type=model_type)

        # Publish prediction event
        from shared.messaging import EventBus
        bus = EventBus()
        bus.publish("prediction.completed", {
            "prediction": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return jsonify({
            "success": True,
            "prediction": result,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        })
    except Exception as e:
        logger.error("Prediction failed: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@predict_bp.route("/realtime", methods=["POST"])
def predict_realtime():
    """
    Real-time prediction using the latest weather data.

    Fetches current conditions from the Weather Collector Service
    and runs the prediction model.
    """
    try:
        from shared.messaging import create_weather_client

        weather_client = create_weather_client()
        weather_data = weather_client.get("/api/v1/weather/current")

        if not weather_data or not weather_data.get("success"):
            return jsonify({
                "success": False,
                "error": "Could not fetch current weather data",
            }), 503

        from app.services.predictor import FloodPredictor
        predictor = FloodPredictor.get_instance()

        # Extract features from weather data
        observations = weather_data.get("data", {}).get("observations", {})
        features = predictor.extract_features(observations)
        result = predictor.predict(features=features)

        return jsonify({
            "success": True,
            "prediction": result,
            "weather_data": weather_data.get("data"),
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        })
    except Exception as e:
        logger.error("Realtime prediction failed: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@predict_bp.route("/risk-levels", methods=["GET"])
def risk_levels():
    """Get risk level definitions and thresholds."""
    levels = [
        {
            "level": "low",
            "threshold": "0.0 - 0.25",
            "color": "#22c55e",
            "description": "Normal conditions — no flooding expected",
            "action": "No action required",
        },
        {
            "level": "moderate",
            "threshold": "0.25 - 0.50",
            "color": "#f59e0b",
            "description": "Elevated risk — possible minor flooding in low-lying areas",
            "action": "Monitor conditions, prepare drainage systems",
        },
        {
            "level": "high",
            "threshold": "0.50 - 0.75",
            "color": "#ef4444",
            "description": "High risk — flooding likely in flood-prone barangays",
            "action": "Issue alerts, activate emergency response teams",
        },
        {
            "level": "critical",
            "threshold": "0.75 - 1.0",
            "color": "#991b1b",
            "description": "Severe flooding expected — immediate danger",
            "action": "Mandatory evacuation of affected areas",
        },
    ]
    return jsonify({"success": True, "risk_levels": levels})
