"""
Batch prediction routes.

Enables bulk flood risk predictions for multiple locations or time steps.
"""

import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

batch_bp = Blueprint("batch", __name__)


@batch_bp.route("/predict", methods=["POST"])
def batch_predict():
    """
    Run batch flood risk predictions.

    Body:
      {
        "predictions": [
          { "temperature": 30, "humidity": 85, "precipitation": 40 },
          { "temperature": 28, "humidity": 90, "precipitation": 60 }
        ],
        "model": "random_forest"
      }
    """
    data = request.get_json()
    if not data or "predictions" not in data:
        return jsonify({"success": False, "error": "predictions array required"}), 400

    items = data["predictions"]
    model_type = data.get("model", "random_forest")

    try:
        from app.services.predictor import FloodPredictor
        predictor = FloodPredictor.get_instance()

        results = []
        for i, features in enumerate(items):
            try:
                result = predictor.predict(features=features, model_type=model_type)
                results.append({"index": i, "success": True, "prediction": result})
            except Exception as e:
                results.append({"index": i, "success": False, "error": str(e)})

        return jsonify({
            "success": True,
            "results": results,
            "total": len(items),
            "successful": sum(1 for r in results if r["success"]),
            "model": model_type,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        })
    except Exception as e:
        logger.error("Batch prediction failed: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500
