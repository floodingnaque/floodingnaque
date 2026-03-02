"""
Dashboard API — Prediction History Routes

Endpoints to browse, filter, and analyse prediction results
fetched from the ML Prediction Service.
"""

import logging
from flask import Blueprint, current_app, jsonify, request

predictions_bp = Blueprint("predictions", __name__)
logger = logging.getLogger(__name__)


@predictions_bp.route("/", methods=["GET"])
def list_predictions():
    """
    GET /api/v1/dashboard/predictions?page=1&per_page=20&risk_level=high

    Paginated listing of recent predictions.
    Filterable by risk_level, location, date range.
    """
    from app.services.dashboard_service import DashboardService

    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 20)), 100)
    risk_level = request.args.get("risk_level")
    location = request.args.get("location")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    filters = {
        "risk_level": risk_level,
        "location": location,
        "start_date": start_date,
        "end_date": end_date,
    }
    filters = {k: v for k, v in filters.items() if v is not None}

    try:
        service = DashboardService(current_app)
        result = service.list_predictions(page=page, per_page=per_page, filters=filters)
        return jsonify({
            "status": "success",
            "data": result["items"],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": result.get("total", 0),
                "pages": result.get("pages", 0),
            },
        }), 200
    except Exception as e:
        logger.error("Failed to list predictions: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502


@predictions_bp.route("/<prediction_id>", methods=["GET"])
def get_prediction_detail(prediction_id: str):
    """
    GET /api/v1/dashboard/predictions/<id>

    Detailed view of a single prediction including input features,
    model used, confidence, and risk classification breakdown.
    """
    from app.services.dashboard_service import DashboardService

    try:
        service = DashboardService(current_app)
        prediction = service.get_prediction_detail(prediction_id)
        if prediction is None:
            return jsonify({"status": "error", "message": "Prediction not found"}), 404
        return jsonify({"status": "success", "data": prediction}), 200
    except Exception as e:
        logger.error("Prediction detail error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502


@predictions_bp.route("/analytics", methods=["GET"])
def prediction_analytics():
    """
    GET /api/v1/dashboard/predictions/analytics?period=30d

    Analytics over predictions: accuracy, risk distribution,
    average confidence, trend lines.
    """
    from app.services.dashboard_service import DashboardService

    period = request.args.get("period", "30d")

    try:
        service = DashboardService(current_app)
        analytics = service.get_prediction_analytics(period)
        return jsonify({"status": "success", "data": analytics}), 200
    except Exception as e:
        logger.error("Prediction analytics error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502


@predictions_bp.route("/comparison", methods=["GET"])
def model_comparison():
    """
    GET /api/v1/dashboard/predictions/comparison

    Compare performance metrics between different ML models
    used for flood prediction (e.g. XGBoost vs LightGBM vs RandomForest).
    """
    from app.services.dashboard_service import DashboardService

    try:
        service = DashboardService(current_app)
        comparison = service.get_model_comparison()
        return jsonify({"status": "success", "data": comparison}), 200
    except Exception as e:
        logger.error("Model comparison error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502
