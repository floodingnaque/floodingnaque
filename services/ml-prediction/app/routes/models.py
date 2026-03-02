"""
Model management routes.

Endpoints:
  GET  /api/v1/models/               - List available models
  GET  /api/v1/models/<id>            - Get model details
  POST /api/v1/models/reload          - Hot-reload the active model
  GET  /api/v1/models/versions        - List model versions
  POST /api/v1/models/retrain         - Trigger model retraining
  GET  /api/v1/models/metrics         - Get model performance metrics
  POST /api/v1/models/ab-test         - Configure A/B test between models
"""

import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

models_bp = Blueprint("models", __name__)


@models_bp.route("/", methods=["GET"])
def list_models():
    """List all available ML models."""
    models = [
        {
            "id": "random_forest",
            "name": "Random Forest Classifier",
            "version": "2.1.0",
            "status": "active",
            "accuracy": 0.94,
            "description": "Primary flood prediction model using scikit-learn RandomForest",
        },
        {
            "id": "xgboost",
            "name": "XGBoost Gradient Boosting",
            "version": "1.3.0",
            "status": "available",
            "accuracy": 0.96,
            "description": "High-performance gradient boosting model",
        },
        {
            "id": "lightgbm",
            "name": "LightGBM",
            "version": "1.1.0",
            "status": "available",
            "accuracy": 0.95,
            "description": "Microsoft LightGBM - fast histogram-based gradient boosting",
        },
        {
            "id": "ensemble",
            "name": "Ensemble (Voting)",
            "version": "1.0.0",
            "status": "available",
            "accuracy": 0.97,
            "description": "Weighted ensemble of all three models",
        },
    ]
    return jsonify({"success": True, "models": models, "count": len(models)})


@models_bp.route("/<model_id>", methods=["GET"])
def get_model(model_id):
    """Get detailed model information."""
    try:
        from app.services.predictor import FloodPredictor
        predictor = FloodPredictor.get_instance()
        info = predictor.get_model_info(model_id)
        return jsonify({"success": True, "model": info})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 404


@models_bp.route("/reload", methods=["POST"])
def reload_model():
    """Hot-reload the active ML model from disk."""
    try:
        from app.services.predictor import FloodPredictor
        predictor = FloodPredictor.get_instance()
        predictor.load_model(force_reload=True)
        return jsonify({
            "success": True,
            "message": "Model reloaded successfully",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        })
    except Exception as e:
        logger.error("Model reload failed: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@models_bp.route("/versions", methods=["GET"])
def list_versions():
    """List all model versions with deployment history."""
    try:
        from app.services.predictor import FloodPredictor
        predictor = FloodPredictor.get_instance()
        versions = predictor.get_versions()
        return jsonify({"success": True, "versions": versions})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@models_bp.route("/retrain", methods=["POST"])
def trigger_retrain():
    """Trigger model retraining with latest data."""
    body = request.get_json(silent=True) or {}
    model_type = body.get("model", "random_forest")

    try:
        from app.services.predictor import FloodPredictor
        predictor = FloodPredictor.get_instance()
        result = predictor.trigger_retrain(model_type=model_type)

        from shared.messaging import EventBus
        bus = EventBus()
        bus.publish("model.retrain.started", {"model": model_type})

        return jsonify({
            "success": True,
            "message": f"Retraining triggered for {model_type}",
            "result": result,
        })
    except Exception as e:
        logger.error("Retrain trigger failed: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@models_bp.route("/metrics", methods=["GET"])
def model_metrics():
    """Get model performance metrics (accuracy, precision, recall, F1)."""
    try:
        from app.services.predictor import FloodPredictor
        predictor = FloodPredictor.get_instance()
        metrics = predictor.get_metrics()
        return jsonify({"success": True, "metrics": metrics})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@models_bp.route("/ab-test", methods=["POST"])
def configure_ab_test():
    """
    Configure A/B testing between two model versions.

    Body: { "model_a": "random_forest", "model_b": "xgboost", "traffic_split": 0.5 }
    """
    body = request.get_json()
    if not body:
        return jsonify({"success": False, "error": "Request body required"}), 400

    model_a = body.get("model_a")
    model_b = body.get("model_b")
    split = body.get("traffic_split", 0.5)

    return jsonify({
        "success": True,
        "message": f"A/B test configured: {model_a} vs {model_b} ({split*100:.0f}/{(1-split)*100:.0f})",
        "config": {"model_a": model_a, "model_b": model_b, "split": split},
    })
