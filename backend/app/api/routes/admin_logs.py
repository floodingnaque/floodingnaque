"""
Admin System Logs Routes.

Provides admin-only endpoints for viewing system activity logs,
including API requests, predictions, and error events.
"""

import logging
from datetime import datetime, timezone
from functools import wraps

from app.api.middleware.auth import require_auth
from app.models.api_request import APIRequest
from app.models.db import get_db_session
from app.utils.api_constants import HTTP_OK
from app.utils.api_responses import api_error
from flask import Blueprint, g, jsonify, request
from sqlalchemy import func

logger = logging.getLogger(__name__)

admin_logs_bp = Blueprint("admin_logs", __name__)


def require_admin(f):
    """Decorator that requires admin role after authentication."""

    @wraps(f)
    @require_auth
    def decorated(*args, **kwargs):
        if getattr(g, "current_user_role", None) != "admin":
            return api_error("Admin access required", 403, code="ADMIN_REQUIRED")
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
    session = get_db_session()
    try:
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
                (APIRequest.endpoint.ilike(search_pattern))
                | (APIRequest.error_message.ilike(search_pattern))
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
            data.append({
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
            })

        return jsonify({
            "success": True,
            "data": data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": (total + per_page - 1) // per_page,
            },
        }), HTTP_OK
    except Exception as e:
        logger.error(f"Error listing logs: {e}")
        return api_error(f"Failed to list logs: {str(e)}", 500)
    finally:
        session.close()


@admin_logs_bp.route("/stats", methods=["GET"])
@require_admin
def log_stats():
    """
    Get aggregate log statistics for the admin dashboard.

    Returns counts by category for the current day plus overall totals.
    """
    session = get_db_session()
    try:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        # Total today
        total_today = (
            session.query(func.count(APIRequest.id))
            .filter(APIRequest.is_deleted == False, APIRequest.created_at >= today_start)  # noqa: E712
            .scalar()
            or 0
        )

        # Predictions today
        predictions_today = (
            session.query(func.count(APIRequest.id))
            .filter(
                APIRequest.is_deleted == False,  # noqa: E712
                APIRequest.created_at >= today_start,
                APIRequest.endpoint.ilike("%predict%"),
            )
            .scalar()
            or 0
        )

        # Login attempts today
        login_attempts = (
            session.query(func.count(APIRequest.id))
            .filter(
                APIRequest.is_deleted == False,  # noqa: E712
                APIRequest.created_at >= today_start,
                APIRequest.endpoint.ilike("%auth/login%"),
            )
            .scalar()
            or 0
        )

        # Data uploads today
        uploads_today = (
            session.query(func.count(APIRequest.id))
            .filter(
                APIRequest.is_deleted == False,  # noqa: E712
                APIRequest.created_at >= today_start,
                APIRequest.endpoint.ilike("%upload%"),
            )
            .scalar()
            or 0
        )

        # Errors today (status >= 400)
        errors_today = (
            session.query(func.count(APIRequest.id))
            .filter(
                APIRequest.is_deleted == False,  # noqa: E712
                APIRequest.created_at >= today_start,
                APIRequest.status_code >= 400,
            )
            .scalar()
            or 0
        )

        # Total all time
        total_all = (
            session.query(func.count(APIRequest.id)).filter(APIRequest.is_deleted == False).scalar() or 0  # noqa: E712
        )

        return jsonify({
            "success": True,
            "data": {
                "total_today": total_today,
                "predictions_today": predictions_today,
                "login_attempts": login_attempts,
                "uploads_today": uploads_today,
                "errors_today": errors_today,
                "total_all_time": total_all,
            },
        }), HTTP_OK
    except Exception as e:
        logger.error(f"Error fetching log stats: {e}")
        return api_error(f"Failed to fetch stats: {str(e)}", 500)
    finally:
        session.close()
