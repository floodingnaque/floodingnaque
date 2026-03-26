"""
Admin System Logs Routes.

Provides admin-only endpoints for viewing system activity logs,
including API requests, predictions, and error events, as well as
bulk cleanup/purge to control database storage growth.
"""

import logging
from datetime import datetime, timedelta, timezone
from functools import wraps

from app.api.middleware.auth import require_auth
from app.models.api_request import APIRequest
from app.models.db import get_db_session
from app.utils.api_constants import HTTP_OK
from app.utils.api_responses import api_error
from flask import Blueprint, g, jsonify, request
from sqlalchemy import case, func

logger = logging.getLogger(__name__)

admin_logs_bp = Blueprint("admin_logs", __name__)


def require_admin(f):
    """Decorator that requires admin role after authentication."""

    @wraps(f)
    @require_auth
    def decorated(*args, **kwargs):
        if getattr(g, "current_user_role", None) != "admin":
            return api_error("ADMIN_REQUIRED", "Admin access required", 403)
        return f(*args, **kwargs)

    return decorated


# Category classifier based on endpoint path
def _classify_endpoint(endpoint: str) -> str:
    """Classify an API request endpoint into a human-readable category."""
    if not endpoint:
        return "other"
    ep = endpoint.lower()
    if "/predict" in ep:
        return "prediction"
    if "/auth/login" in ep or "/auth/register" in ep:
        return "login"
    if "/upload" in ep or "/ingest" in ep:
        return "upload"
    if "/export" in ep:
        return "report"
    if "/health" in ep:
        return "health"
    if "/admin" in ep:
        return "admin"
    if "/alerts" in ep or "/sse" in ep:
        return "alert"
    return "other"


@admin_logs_bp.route("/", methods=["GET"])
@require_admin
def list_logs():
    """
    List system activity logs with filtering and pagination.

    Query Parameters:
        page (int): Page number (default 1)
        per_page (int): Items per page (default 50, max 200)
        category (str): Filter by category (prediction/login/upload/report/health/admin/alert/other)
        status_min (int): Minimum status code filter (e.g. 400 for errors only)
        start_date (str): ISO date filter start
        end_date (str): ISO date filter end
        search (str): Search endpoint or error message

    Returns:
        200: Paginated log list with classified categories
    """
    try:
        with get_db_session() as session:
            page = max(1, request.args.get("page", 1, type=int))
            per_page = min(200, max(1, request.args.get("per_page", 50, type=int)))
            category = request.args.get("category")
            status_min = request.args.get("status_min", type=int)
            start_date = request.args.get("start_date")
            end_date = request.args.get("end_date")
            search = request.args.get("search", "").strip()

            query = session.query(APIRequest).filter(APIRequest.is_deleted == False)  # noqa: E712

            # Date range filter
            if start_date:
                try:
                    start_dt = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
                    query = query.filter(APIRequest.created_at >= start_dt)
                except ValueError:
                    pass
            if end_date:
                try:
                    end_dt = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
                    query = query.filter(APIRequest.created_at <= end_dt)
                except ValueError:
                    pass

            # Status code filter (e.g. errors only)
            if status_min:
                query = query.filter(APIRequest.status_code >= status_min)

            # Search
            if search:
                search_pattern = f"%{search}%"
                query = query.filter(
                    (APIRequest.endpoint.ilike(search_pattern)) | (APIRequest.error_message.ilike(search_pattern))
                )

            # Category filter (post-query since it's computed)
            # For efficiency, map category to endpoint patterns
            if category:
                category_patterns = {
                    "prediction": "%predict%",
                    "login": "%auth%",
                    "upload": "%upload%",
                    "report": "%export%",
                    "health": "%health%",
                    "admin": "%admin%",
                    "alert": "%alert%",
                }
                pattern = category_patterns.get(category)
                if pattern:
                    query = query.filter(APIRequest.endpoint.ilike(pattern))

            # Order by most recent
            query = query.order_by(APIRequest.created_at.desc())

            total = query.count()
            logs = query.offset((page - 1) * per_page).limit(per_page).all()

            data = []
            for log in logs:
                data.append(
                    {
                        "id": log.id,
                        "request_id": log.request_id,
                        "endpoint": log.endpoint,
                        "method": log.method,
                        "status_code": log.status_code,
                        "response_time_ms": round(log.response_time_ms, 1) if log.response_time_ms else None,
                        "ip_address": log.ip_address,
                        "error_message": log.error_message,
                        "category": _classify_endpoint(log.endpoint),
                        "created_at": log.created_at.isoformat() if log.created_at else None,
                    }
                )

            return (
                jsonify(
                    {
                        "success": True,
                        "data": data,
                        "pagination": {
                            "page": page,
                            "per_page": per_page,
                            "total": total,
                            "total_pages": (total + per_page - 1) // per_page,
                        },
                    }
                ),
                HTTP_OK,
            )
    except Exception as e:
        logger.error(f"Error listing logs: {e}")
        return api_error(f"Failed to list logs: {str(e)}", 500)


@admin_logs_bp.route("/stats", methods=["GET"])
@require_admin
def log_stats():
    """
    Get aggregate log statistics for the admin dashboard.

    Returns counts by category for the current day plus overall totals.
    """
    try:
        with get_db_session() as session:
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

            # Single aggregation query for all today's stats (was 6 separate queries)
            row = (
                session.query(
                    func.count(
                        case((APIRequest.created_at >= today_start, APIRequest.id))
                    ).label("total_today"),
                    func.count(
                        case(
                            (
                                (APIRequest.created_at >= today_start)
                                & (APIRequest.endpoint.ilike("%predict%")),
                                APIRequest.id,
                            )
                        )
                    ).label("predictions_today"),
                    func.count(
                        case(
                            (
                                (APIRequest.created_at >= today_start)
                                & (APIRequest.endpoint.ilike("%auth/login%")),
                                APIRequest.id,
                            )
                        )
                    ).label("login_attempts"),
                    func.count(
                        case(
                            (
                                (APIRequest.created_at >= today_start)
                                & (APIRequest.endpoint.ilike("%upload%")),
                                APIRequest.id,
                            )
                        )
                    ).label("uploads_today"),
                    func.count(
                        case(
                            (
                                (APIRequest.created_at >= today_start)
                                & (APIRequest.status_code >= 400),
                                APIRequest.id,
                            )
                        )
                    ).label("errors_today"),
                    func.count(APIRequest.id).label("total_all"),
                )
                .filter(APIRequest.is_deleted == False)  # noqa: E712
                .one()
            )

            return (
                jsonify(
                    {
                        "success": True,
                        "data": {
                            "total_today": row.total_today,
                            "predictions_today": row.predictions_today,
                            "login_attempts": row.login_attempts,
                            "uploads_today": row.uploads_today,
                            "errors_today": row.errors_today,
                            "total_all_time": row.total_all,
                        },
                    }
                ),
                HTTP_OK,
            )
    except Exception as e:
        logger.error(f"Error fetching log stats: {e}")
        return api_error(f"Failed to fetch stats: {str(e)}", 500)


@admin_logs_bp.route("/bulk-delete", methods=["POST"])
@require_admin
def bulk_delete_logs():
    """
    Bulk soft-delete API request logs.

    Request Body:
    {
        "older_than_days": 30,         // Delete records older than N days
        "status_code_min": null,       // Optional: only delete errors (>= 400)
        "endpoint_pattern": null,      // Optional: LIKE pattern filter
        "confirm": true                // Required
    }

    Maximum 5000 records per request.
    """
    MAX_BULK = 5000

    try:
        data = request.get_json() or {}

        if not data.get("confirm"):
            return api_error("CONFIRM_REQUIRED", "Bulk delete requires confirm=true", 400)

        older_than_days = data.get("older_than_days")
        status_min = data.get("status_code_min")
        endpoint_pattern = data.get("endpoint_pattern")

        if older_than_days is None and status_min is None and endpoint_pattern is None:
            return api_error(
                "At least one filter (older_than_days, status_code_min, endpoint_pattern) is required", 400
            )

        with get_db_session() as session:
            query = session.query(APIRequest).filter(APIRequest.is_deleted.is_(False))

            if older_than_days is not None:
                cutoff = datetime.now(timezone.utc) - timedelta(days=int(older_than_days))
                query = query.filter(APIRequest.created_at < cutoff)

            if status_min is not None:
                query = query.filter(APIRequest.status_code >= int(status_min))

            if endpoint_pattern:
                query = query.filter(APIRequest.endpoint.ilike(f"%{endpoint_pattern}%"))

            total_count = query.count()

            if total_count == 0:
                return jsonify({"success": True, "deleted_count": 0, "message": "No matching records found"}), HTTP_OK

            if total_count > MAX_BULK:
                return api_error(
                    f"Query matches {total_count} records, exceeds max of {MAX_BULK}. Add stricter filters.",
                    400,
                    code="TOO_MANY_RECORDS",
                )

            now = datetime.now(timezone.utc)
            deleted = query.update({"is_deleted": True, "deleted_at": now}, synchronize_session="fetch")

        logger.info("Admin bulk-deleted %d API request logs", deleted)

        return (
            jsonify(
                {
                    "success": True,
                    "deleted_count": deleted,
                    "message": f"Successfully deleted {deleted} API request log(s)",
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Bulk delete logs failed: {e}", exc_info=True)
        return api_error(f"Failed to bulk delete: {str(e)}", 500)


@admin_logs_bp.route("/storage", methods=["GET"])
@require_admin
def storage_stats():
    """
    Get row counts, estimated sizes, and last record timestamps per table.

    Returns counts for: api_requests, predictions, weather_data,
    community_reports, alert_history, evacuation_centers.
    """
    # Rough average row size in bytes per table (estimated from schema)
    AVG_ROW_BYTES = {
        "api_requests": 512,
        "predictions": 256,
        "weather_data": 384,
        "community_reports": 640,
        "alert_history": 320,
        "evacuation_centers": 512,
    }

    try:
        from app.models.alert import AlertHistory
        from app.models.community_report import CommunityReport
        from app.models.evacuation_center import EvacuationCenter
        from app.models.prediction import Prediction
        from app.models.weather import WeatherData

        with get_db_session() as session:
            models = [
                ("api_requests", APIRequest),
                ("predictions", Prediction),
                ("weather_data", WeatherData),
                ("community_reports", CommunityReport),
                ("alert_history", AlertHistory),
                ("evacuation_centers", EvacuationCenter),
            ]

            # Each COUNT is O(index scan) with the is_deleted indexes.
            # Still 6 queries but each is a single fast aggregate -
            # down from 18 (3 per table in a loop).
            result = {}
            grand_total_rows = 0
            grand_total_bytes = 0

            for name, model in models:
                row = (
                    session.query(
                        func.count(model.id).label("total"),
                        func.count(case((model.is_deleted.is_(False), model.id))).label("active"),
                        func.max(model.created_at).label("last_record"),
                    )
                    .one()
                )

                total = row.total or 0
                active = row.active or 0
                soft_deleted = total - active
                last_record = row.last_record

                row_bytes = AVG_ROW_BYTES.get(name, 256)
                est_bytes = total * row_bytes

                result[name] = {
                    "total": total,
                    "active": active,
                    "soft_deleted": soft_deleted,
                    "last_record_at": last_record.isoformat() if last_record else None,
                    "estimated_size_bytes": est_bytes,
                }
                grand_total_rows += total
                grand_total_bytes += est_bytes

        return (
            jsonify(
                {
                    "success": True,
                    "tables": result,
                    "summary": {
                        "total_rows": grand_total_rows,
                        "total_active": grand_total_rows - sum(t["soft_deleted"] for t in result.values()),
                        "total_soft_deleted": sum(t["soft_deleted"] for t in result.values()),
                        "estimated_total_bytes": grand_total_bytes,
                    },
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Error fetching storage stats: {e}", exc_info=True)
        return api_error(f"Failed to fetch storage stats: {str(e)}", 500)


@admin_logs_bp.route("/storage/cleanup-count", methods=["GET"])
@require_admin
def cleanup_count_preview():
    """
    Preview how many rows would be affected by a cleanup operation.

    Query params:
        type: logs | reports | alerts (required)
        older_than_days: int (required)
        status: str (optional, for reports)
        delivery_status: str (optional, for alerts)
    """
    try:
        cleanup_type = request.args.get("type")
        older_than_days = request.args.get("older_than_days", type=int)

        if not cleanup_type or older_than_days is None:
            return api_error("type and older_than_days are required", 400)

        if older_than_days < 1:
            return api_error("older_than_days must be >= 1", 400)

        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)

        with get_db_session() as session:
            if cleanup_type == "logs":
                query = session.query(func.count(APIRequest.id)).filter(
                    APIRequest.is_deleted.is_(False),
                    APIRequest.created_at < cutoff,
                )
                count = query.scalar() or 0

            elif cleanup_type == "reports":
                from app.models.community_report import CommunityReport

                query = session.query(func.count(CommunityReport.id)).filter(
                    CommunityReport.is_deleted.is_(False),
                    CommunityReport.created_at < cutoff,
                )
                status = request.args.get("status")
                if status and status != "all":
                    query = query.filter(CommunityReport.status == status)
                count = query.scalar() or 0

            elif cleanup_type == "alerts":
                from app.models.alert import AlertHistory

                query = session.query(func.count(AlertHistory.id)).filter(
                    AlertHistory.is_deleted.is_(False),
                    AlertHistory.created_at < cutoff,
                )
                delivery_status = request.args.get("delivery_status")
                if delivery_status and delivery_status != "all":
                    query = query.filter(AlertHistory.delivery_status == delivery_status)
                count = query.scalar() or 0

            else:
                return api_error("type must be one of: logs, reports, alerts", 400)

        return jsonify({"success": True, "count": count}), HTTP_OK

    except Exception as e:
        logger.error(f"Cleanup count preview failed: {e}", exc_info=True)
        return api_error(f"Failed to get cleanup count: {str(e)}", 500)


@admin_logs_bp.route("/purge-deleted", methods=["POST"])
@require_admin
def purge_deleted():
    """
    Hard-delete records already soft-deleted across selected tables.

    This permanently removes rows from the database and frees storage.

    Request Body:
    {
        "tables": ["api_requests", "predictions"],  // Required
        "confirm": true                              // Required
    }
    """
    ALLOWED_TABLES = {
        "api_requests",
        "predictions",
        "weather_data",
        "community_reports",
        "alert_history",
    }

    try:
        data = request.get_json() or {}

        if not data.get("confirm"):
            return api_error("CONFIRM_REQUIRED", "Purge requires confirm=true", 400)

        table_names = data.get("tables", [])
        if not table_names or not isinstance(table_names, list):
            return api_error("tables must be a non-empty array", 400)

        invalid = set(table_names) - ALLOWED_TABLES
        if invalid:
            return api_error(f"Invalid table(s): {', '.join(invalid)}", 400)

        from app.models.alert import AlertHistory
        from app.models.community_report import CommunityReport
        from app.models.prediction import Prediction
        from app.models.weather import WeatherData

        model_map = {
            "api_requests": APIRequest,
            "predictions": Prediction,
            "weather_data": WeatherData,
            "community_reports": CommunityReport,
            "alert_history": AlertHistory,
        }

        purged = {}
        with get_db_session() as session:
            for name in table_names:
                model = model_map[name]
                count = session.query(model).filter(model.is_deleted.is_(True)).delete(synchronize_session="fetch")
                purged[name] = count

        total = sum(purged.values())
        logger.info("Admin purged %d soft-deleted records: %s", total, purged)

        return (
            jsonify(
                {
                    "success": True,
                    "purged": purged,
                    "total_purged": total,
                    "message": f"Permanently removed {total} record(s)",
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Purge failed: {e}", exc_info=True)
        return api_error(f"Failed to purge: {str(e)}", 500)
