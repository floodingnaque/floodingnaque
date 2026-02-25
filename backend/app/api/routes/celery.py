"""
Celery Task Management Routes.

Provides endpoints for managing and monitoring background tasks.
"""

import html

from app.api.middleware.rate_limit import get_endpoint_limit, limiter
from app.services.celery_app import celery_app
from app.services.tasks import get_task_status, trigger_data_processing, trigger_model_retraining
from app.utils.api_constants import HTTP_BAD_REQUEST, HTTP_NOT_FOUND, HTTP_OK
from app.utils.api_responses import api_error, api_success
from app.utils.logging import get_logger
from flask import Blueprint, g, request

logger = get_logger(__name__)

celery_bp = Blueprint("celery", __name__)


@celery_bp.route("/tasks/retrain", methods=["POST"])
@limiter.limit(get_endpoint_limit("tasks"))
def retrain_model():
    """
    Trigger model retraining task.

    Request Body:
        model_id (str, optional): Specific model ID to retrain

    Returns:
        Task information
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        data = request.get_json() or {}
        raw_model_id = data.get("model_id")
        # Validate and sanitize model_id to prevent XSS
        # Only allow alphanumeric characters, dashes, and underscores
        sanitized_model_id = None
        if raw_model_id is not None:
            model_id_str = str(raw_model_id)[:100]
            if all(c.isalnum() or c in "_-" for c in model_id_str):
                sanitized_model_id = model_id_str
            else:
                return api_error("ValidationError", "Invalid model_id format", HTTP_BAD_REQUEST, request_id)

        # Trigger retraining task
        result = trigger_model_retraining(sanitized_model_id)

        # Sanitize result data that could come from external sources
        # Double-escape model_id to ensure XSS prevention even after validation
        safe_model_id = html.escape(sanitized_model_id) if sanitized_model_id else None
        return (
            api_success(
                "ModelRetrainingTriggered",
                "Model retraining task queued successfully",
                {
                    "task_id": html.escape(str(result.get("task_id", "")))[:100],
                    "status": html.escape(str(result.get("status", "")))[:50],
                    "message": html.escape(str(result.get("message", "")))[:200],
                    "model_id": safe_model_id,
                },
                request_id,
            ),
            HTTP_OK,
        )

    except Exception:
        logger.error(f"Failed to trigger model retraining [{request_id}]")
        return api_error("TaskTriggerFailed", "Failed to trigger model retraining", HTTP_BAD_REQUEST, request_id)


@celery_bp.route("/tasks/process-data", methods=["POST"])
@limiter.limit(get_endpoint_limit("tasks"))
def process_data():
    """
    Trigger data processing task.

    Request Body:
        data_batch (list): Batch of weather data records to process

    Returns:
        Task information
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        data = request.get_json()
        if not data or "data_batch" not in data:
            return api_error("ValidationError", "data_batch is required", HTTP_BAD_REQUEST, request_id)

        data_batch = data["data_batch"]

        if not isinstance(data_batch, list):
            return api_error("ValidationError", "data_batch must be an array", HTTP_BAD_REQUEST, request_id)

        if len(data_batch) == 0:
            return api_error("ValidationError", "data_batch cannot be empty", HTTP_BAD_REQUEST, request_id)

        if len(data_batch) > 1000:
            return api_error("ValidationError", "data_batch cannot exceed 1000 records", HTTP_BAD_REQUEST, request_id)

        # Trigger data processing task
        result = trigger_data_processing(data_batch)

        return (
            api_success(
                "DataProcessingTriggered",
                "Data processing task queued successfully",
                {
                    "task_id": result["task_id"],
                    "status": result["status"],
                    "message": result["message"],
                    "batch_size": len(data_batch),
                },
                request_id,
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Failed to trigger data processing [{request_id}]: {str(e)}")
        return api_error("TaskTriggerFailed", "Failed to trigger data processing", HTTP_BAD_REQUEST, request_id)


@celery_bp.route("/tasks/<task_id>", methods=["GET"])
@limiter.limit(get_endpoint_limit("status"))
def get_task_info(task_id):
    """
    Get status and result of a specific task.

    Path Parameters:
        task_id (str): Celery task ID

    Returns:
        Task status and result
    """
    request_id = getattr(g, "request_id", "unknown")
    # Sanitize task_id to prevent XSS
    task_id = html.escape(str(task_id)[:100])

    try:
        # Get task status
        result = get_task_status(task_id)

        if result["status"] == "PENDING" and not result.get("result"):
            # Check if task exists in Celery
            from celery.result import AsyncResult

            task_result = AsyncResult(task_id, app=celery_app)
            if not task_result.exists():
                return api_error("TaskNotFound", "Task not found", HTTP_NOT_FOUND, request_id)

        return api_success("TaskStatus", "Task status retrieved successfully", result, request_id), HTTP_OK

    except Exception as e:
        logger.error(f"Failed to get task status [{request_id}]: {str(e)}")
        return api_error("TaskStatusFailed", "Failed to get task status", HTTP_BAD_REQUEST, request_id)


@celery_bp.route("/tasks", methods=["GET"])
@limiter.limit(get_endpoint_limit("status"))
def list_active_tasks():
    """
    List currently active tasks.

    Query Parameters:
        limit (int, optional): Maximum number of tasks to return (default: 50)

    Returns:
        List of active tasks
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        limit = request.args.get("limit", 50, type=int)
        limit = min(max(limit, 1), 100)  # Between 1 and 100

        # Get active tasks from Celery
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()

        tasks = []
        if active_tasks:
            for worker, task_list in active_tasks.items():
                for task in task_list[:limit]:
                    tasks.append(
                        {
                            "task_id": task["id"],
                            "name": task["name"],
                            "worker": worker,
                            "args": task.get("args", []),
                            "kwargs": task.get("kwargs", {}),
                            "time_start": task.get("time_start"),
                        }
                    )

        return (
            api_success(
                "ActiveTasksList",
                "Active tasks retrieved successfully",
                {"tasks": tasks, "count": len(tasks), "limit": limit},
                request_id,
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Failed to list active tasks [{request_id}]: {str(e)}")
        return api_error("TaskListFailed", "Failed to list active tasks", HTTP_BAD_REQUEST, request_id)


@celery_bp.route("/tasks/stats", methods=["GET"])
@limiter.limit(get_endpoint_limit("status"))
def get_celery_stats():
    """
    Get Celery worker and task statistics.

    Returns:
        Celery statistics
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        # Get Celery statistics
        inspect = celery_app.control.inspect()
        stats = inspect.stats()

        if not stats:
            return api_error("NoWorkers", "No active Celery workers found", HTTP_NOT_FOUND, request_id)

        # Process stats
        worker_stats = []
        total_tasks = 0

        for worker, worker_data in stats.items():
            worker_stats.append(
                {
                    "worker": worker,
                    "total_tasks": worker_data.get("total", 0),
                    "pool": {
                        "max_concurrency": worker_data.get("pool", {}).get("max-concurrency", 0),
                        "processes": worker_data.get("pool", {}).get("processes", []),
                        "max_tasks_per_child": worker_data.get("pool", {}).get("max-tasks-per-child", 0),
                        "timeouts": worker_data.get("pool", {}).get("timeouts", {}),
                    },
                }
            )
            total_tasks += worker_data.get("total", 0)

        return (
            api_success(
                "CeleryStats",
                "Celery statistics retrieved successfully",
                {
                    "workers": worker_stats,
                    "worker_count": len(worker_stats),
                    "total_tasks_processed": total_tasks,
                    "broker_url": celery_app.conf.broker_url,
                    "result_backend": celery_app.conf.result_backend,
                },
                request_id,
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Failed to get Celery stats [{request_id}]: {str(e)}")
        return api_error("StatsFailed", "Failed to get Celery statistics", HTTP_BAD_REQUEST, request_id)


@celery_bp.route("/tasks/cancel/<task_id>", methods=["POST"])
@limiter.limit(get_endpoint_limit("tasks"))
def cancel_task(task_id):
    """
    Cancel a running task.

    Path Parameters:
        task_id (str): Celery task ID to cancel

    Returns:
        Cancellation result
    """
    request_id = getattr(g, "request_id", "unknown")
    # Sanitize task_id to prevent XSS
    task_id = html.escape(str(task_id)[:100])

    try:
        # Revoke the task
        celery_app.control.revoke(task_id, terminate=True)

        return (
            api_success(
                "TaskCancelled",
                "Task cancellation requested",
                {"task_id": task_id, "status": "cancelled", "message": "Task cancellation requested successfully"},
                request_id,
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Failed to cancel task [{request_id}]: {str(e)}")
        return api_error("TaskCancelFailed", "Failed to cancel task", HTTP_BAD_REQUEST, request_id)
