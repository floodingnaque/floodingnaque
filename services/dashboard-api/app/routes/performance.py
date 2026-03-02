"""
Dashboard API - Performance Metrics Routes

Endpoints for system-wide performance monitoring, model metrics,
and service health aggregation.
"""

import logging
from flask import Blueprint, current_app, jsonify, request

performance_bp = Blueprint("performance", __name__)
logger = logging.getLogger(__name__)


@performance_bp.route("/services", methods=["GET"])
def service_health_overview():
    """
    GET /api/v1/dashboard/performance/services

    Aggregate health status from all microservices.
    Returns uptime, response latency, and error rates.
    """
    from app.services.dashboard_service import DashboardService

    try:
        service = DashboardService(current_app)
        health = service.get_service_health()
        return jsonify({"status": "success", "data": health}), 200
    except Exception as e:
        logger.error("Service health aggregation failed: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502


@performance_bp.route("/models", methods=["GET"])
def model_performance():
    """
    GET /api/v1/dashboard/performance/models

    ML model performance metrics: accuracy, precision, recall, F1,
    inference latency, prediction count.
    """
    from app.services.dashboard_service import DashboardService

    try:
        service = DashboardService(current_app)
        metrics = service.get_model_performance()
        return jsonify({"status": "success", "data": metrics}), 200
    except Exception as e:
        logger.error("Model performance error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502


@performance_bp.route("/latency", methods=["GET"])
def latency_metrics():
    """
    GET /api/v1/dashboard/performance/latency?period=1d

    Request latency percentiles (p50, p90, p99) per service.
    """
    from app.services.dashboard_service import DashboardService

    period = request.args.get("period", "1d")

    try:
        service = DashboardService(current_app)
        latency = service.get_latency_metrics(period=period)
        return jsonify({"status": "success", "data": latency}), 200
    except Exception as e:
        logger.error("Latency metrics error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502


@performance_bp.route("/throughput", methods=["GET"])
def throughput_metrics():
    """
    GET /api/v1/dashboard/performance/throughput?period=1d

    Request throughput (requests/sec) per service.
    """
    from app.services.dashboard_service import DashboardService

    period = request.args.get("period", "1d")

    try:
        service = DashboardService(current_app)
        throughput = service.get_throughput_metrics(period=period)
        return jsonify({"status": "success", "data": throughput}), 200
    except Exception as e:
        logger.error("Throughput metrics error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502


@performance_bp.route("/errors", methods=["GET"])
def error_metrics():
    """
    GET /api/v1/dashboard/performance/errors?period=7d

    Error rates and most common error types across services.
    """
    from app.services.dashboard_service import DashboardService

    period = request.args.get("period", "7d")

    try:
        service = DashboardService(current_app)
        errors = service.get_error_metrics(period=period)
        return jsonify({"status": "success", "data": errors}), 200
    except Exception as e:
        logger.error("Error metrics aggregation failed: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 502
