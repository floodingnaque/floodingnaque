"""
Admin Model Management Routes.

Provides admin-only endpoints for ML model management: listing versions,
triggering retraining, checking training status, and model rollback.
"""

import logging
from functools import wraps

from app.api.middleware.auth import require_auth
from app.services.tasks import get_task_status, trigger_model_retraining
from app.utils.api_constants import HTTP_BAD_REQUEST, HTTP_OK
from app.utils.api_responses import api_error
from flask import Blueprint, g, jsonify, request

logger = logging.getLogger(__name__)

admin_models_bp = Blueprint("admin_models", __name__)


def require_admin(f):
    """Decorator that requires admin role after authentication."""

    @wraps(f)
    @require_auth
    def decorated(*args, **kwargs):
        if getattr(g, "current_user_role", None) != "admin":
            return api_error("Admin access required", 403, code="ADMIN_REQUIRED")
        return f(*args, **kwargs)

    return decorated


@admin_models_bp.route("/", methods=["GET"])
@require_admin
def list_models():
    """
    List all available model versions with metrics.

    Returns metadata and performance metrics for every model version
    registered in the system.
    """
    try:
        from app.services.predict import get_model_metadata

        metadata = get_model_metadata()

        return jsonify({
            "success": True,
            "data": {
                "current_model": metadata,
            },
        }), HTTP_OK
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return api_error(f"Failed to list models: {str(e)}", 500)


@admin_models_bp.route("/retrain", methods=["POST"])
@require_admin
def retrain_model():
    """
    Trigger model retraining via Celery task queue.

    The retraining runs asynchronously using the UnifiedTrainer pipeline.
    Returns a task ID for status tracking.

    Request Body (optional):
        { "model_id": "v7" }
    """
    try:
        data = request.get_json(silent=True) or {}
        model_id = data.get("model_id")

        result = trigger_model_retraining(model_id)
        logger.info(f"Admin {g.current_user_email} triggered model retraining: {result}")

        return jsonify({
            "success": True,
            "data": result,
        }), HTTP_OK
    except Exception as e:
        logger.error(f"Error triggering retraining: {e}")
        return api_error(f"Failed to trigger retraining: {str(e)}", 500)


@admin_models_bp.route("/retrain/status", methods=["GET"])
@require_admin
def retrain_status():
    """
    Check the status of a retraining task.

    Query Parameters:
        task_id (str): Celery task ID returned from POST /retrain
    """
    task_id = request.args.get("task_id")
    if not task_id:
        return api_error("task_id parameter required", HTTP_BAD_REQUEST)

    try:
        status = get_task_status(task_id)
        return jsonify({
            "success": True,
            "data": status,
        }), HTTP_OK
    except Exception as e:
        logger.error(f"Error checking retraining status: {e}")
        return api_error(f"Failed to check status: {str(e)}", 500)


@admin_models_bp.route("/rollback", methods=["POST"])
@require_admin
def rollback_model():
    """
    Rollback to a previous model version.

    Request Body:
        { "version": "v5" }

    This reloads the specified model version file into the inference cache.
    """
    try:
        data = request.get_json(silent=True) or {}
        version = data.get("version")
        if not version:
            return api_error("version field is required", HTTP_BAD_REQUEST)

        from app.services.predict import ModelLoader

        loader = ModelLoader()
        # Attempt to load the specified version
        model_path = f"models/flood_model_{version}.joblib"
        try:
            import os

            if not os.path.exists(model_path):
                return api_error(f"Model file not found: {model_path}", 404)
            loader.load_model(model_path)
            logger.info(f"Admin {g.current_user_email} rolled back model to {version}")
        except Exception as load_err:
            return api_error(f"Failed to load model {version}: {str(load_err)}", 500)

        return jsonify({
            "success": True,
            "message": f"Model rolled back to {version}",
            "data": {"version": version},
        }), HTTP_OK
    except Exception as e:
        logger.error(f"Error rolling back model: {e}")
        return api_error(f"Failed to rollback: {str(e)}", 500)


@admin_models_bp.route("/comparison", methods=["GET"])
@require_admin
def compare_models():
    """
    Compare metrics between current and previous model versions.

    Returns side-by-side metrics from the MODEL_VERSIONS configuration.
    """
    try:
        from config.paranaque_config import MODEL_VERSIONS
    except ImportError:
        # Fallback: read from the frontend config or return not-available
        try:
            from app.services.predict import get_model_metadata

            current = get_model_metadata()
            return jsonify({
                "success": True,
                "data": {"current": current, "previous": None},
            }), HTTP_OK
        except Exception:
            return api_error("Model comparison not available", 500)

    return jsonify({
        "success": True,
        "data": {
            "versions": MODEL_VERSIONS,
        },
    }), HTTP_OK
