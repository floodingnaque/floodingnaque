"""
Model Management and API Documentation Routes.

Provides endpoints for listing models and API documentation.
"""

import logging

from app.api.middleware.rate_limit import get_endpoint_limit, limiter
from app.services.predict import get_current_model_info, list_available_models
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

models_bp = Blueprint("models", __name__)


@models_bp.route("/api/version", methods=["GET"])
def api_version():
    """
    Get API version information.

    Returns:
        200: API version details
    ---
    tags:
      - API Info
    produces:
      - application/json
    responses:
      200:
        description: API version information
        schema:
          type: object
          properties:
            version:
              type: string
              example: "2.0.0"
            name:
              type: string
              example: "Floodingnaque API"
            base_url:
              type: string
    """
    return jsonify({"version": "2.0.0", "name": "Floodingnaque API", "base_url": request.url_root.rstrip("/")}), 200


@models_bp.route("/api/models", methods=["GET"])
def list_models():
    """
    List all available ML model versions.

    Returns a list of all available model versions with their metadata.
    Includes accuracy metrics and indicates which model is currently active.

    Returns:
        200: List of available models
        500: Internal server error
    ---
    tags:
      - Models
    produces:
      - application/json
    responses:
      200:
        description: List of available models
        schema:
          type: object
          properties:
            models:
              type: array
              items:
                type: object
                properties:
                  version:
                    type: string
                  path:
                    type: string
                  is_current:
                    type: boolean
                  created_at:
                    type: string
                    format: date-time
                  metrics:
                    type: object
                    properties:
                      accuracy:
                        type: number
                      precision:
                        type: number
                      recall:
                        type: number
                      f1_score:
                        type: number
            current_version:
              type: string
            total_versions:
              type: integer
      500:
        description: Internal server error
    """
    try:
        models = list_available_models()
        current_info = get_current_model_info()
        current_version = None
        if current_info and current_info.get("metadata"):
            current_version = current_info["metadata"].get("version")

        # Format response
        formatted_models = []
        for model in models:
            formatted_model = {
                "version": model["version"],
                "path": model["path"],
                "is_current": model["version"] == current_version,
            }
            if model.get("metadata"):
                metadata = model["metadata"]
                formatted_model["created_at"] = metadata.get("created_at")
                formatted_model["metrics"] = {
                    "accuracy": metadata.get("metrics", {}).get("accuracy"),
                    "precision": metadata.get("metrics", {}).get("precision"),
                    "recall": metadata.get("metrics", {}).get("recall"),
                    "f1_score": metadata.get("metrics", {}).get("f1_score"),
                }
            formatted_models.append(formatted_model)

        request_id = getattr(request, "request_id", "unknown")
        return (
            jsonify(
                {
                    "models": formatted_models,
                    "current_version": current_version,
                    "total_versions": len(formatted_models),
                    "request_id": request_id,
                }
            ),
            200,
        )
    except Exception as e:
        request_id = getattr(request, "request_id", "unknown")
        logger.error(f"Error listing models [{request_id}]: {str(e)}")
        return jsonify({"error": "Failed to list models", "request_id": request_id}), 500


@models_bp.route("/api/docs", methods=["GET"])
@limiter.limit(get_endpoint_limit("docs"))
def api_docs():
    """
    Get API documentation.

    Returns comprehensive documentation of all available API endpoints,
    including request/response formats and parameters.

    Returns:
        200: API documentation
    ---
    tags:
      - API Info
    produces:
      - application/json
    responses:
      200:
        description: API documentation
        schema:
          type: object
          properties:
            endpoints:
              type: object
            version:
              type: string
            base_url:
              type: string
    """
    docs = {
        "endpoints": {
            "GET /status": {
                "description": "Basic health check endpoint",
                "response": {"status": "running", "database": "connected", "model": "loaded | not found"},
            },
            "GET /health": {
                "description": "Detailed health check endpoint",
                "response": {
                    "status": "healthy",
                    "database": "connected",
                    "model_available": "boolean",
                    "scheduler_running": "boolean",
                },
            },
            "POST /ingest": {
                "description": "Ingest weather data from external APIs",
                "request_body": {"lat": "float (optional, -90 to 90)", "lon": "float (optional, -180 to 180)"},
                "response": {
                    "message": "Data ingested successfully",
                    "data": {
                        "temperature": "float",
                        "humidity": "float",
                        "precipitation": "float",
                        "timestamp": "ISO datetime string",
                    },
                },
            },
            "GET /data": {
                "description": "Retrieve historical weather data",
                "query_parameters": {
                    "limit": "int (1-1000, default: 100)",
                    "offset": "int (default: 0)",
                    "start_date": "ISO datetime string (optional)",
                    "end_date": "ISO datetime string (optional)",
                },
                "response": {
                    "data": "array of weather records",
                    "total": "int",
                    "limit": "int",
                    "offset": "int",
                    "count": "int",
                },
            },
            "POST /predict": {
                "description": "Predict flood risk based on weather data with 3-level classification (Safe/Alert/Critical)",
                "request_body": {
                    "temperature": "float (required)",
                    "humidity": "float (required)",
                    "precipitation": "float (required)",
                    "model_version": "int (optional) - Specific model version to use",
                },
                "query_parameters": {
                    "return_proba": "boolean (default: false) - Include prediction probabilities",
                    "risk_level": "boolean (default: true) - Include 3-level risk classification",
                },
                "response": {
                    "prediction": "0 or 1 (binary)",
                    "flood_risk": "low | high (binary, backward compatible)",
                    "risk_level": "0 (Safe) | 1 (Alert) | 2 (Critical)",
                    "risk_label": "Safe | Alert | Critical",
                    "risk_color": "Hex color code",
                    "risk_description": "Human-readable description",
                    "confidence": "float (0-1)",
                    "probability": "object with no_flood and flood probabilities (if return_proba=true)",
                },
            },
        },
        "version": "2.0.0",
        "base_url": request.url_root.rstrip("/"),
    }
    return jsonify(docs), 200
