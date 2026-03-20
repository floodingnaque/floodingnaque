"""Evacuation Routes — evacuation center management and safe routing.

Blueprint: /api/v1/evacuation

Provides center listing with capacity tracking, nearest-center finder,
safe route generation (OSRM + simulation), SMS alert dispatch, and
real-time capacity SSE streaming.
"""

import logging
import queue
import secrets
import time
import uuid
from datetime import datetime, timezone

from app.api.middleware.auth import require_auth_or_api_key, require_scope
from app.api.middleware.rate_limit import rate_limit_with_burst
from app.models.db import get_db_session
from app.models.evacuation_center import EvacuationCenter
from app.services.evacuation_service import get_nearest_centers, get_safe_route
from app.services.sms_service import dispatch_evacuation_sms
from flask import Blueprint, Response, g, jsonify, request, stream_with_context

logger = logging.getLogger(__name__)

evacuation_bp = Blueprint("evacuation", __name__)


# ── GET /centers — List all centers ─────────────────────────────────────


@evacuation_bp.route("/centers", methods=["GET"])
@rate_limit_with_burst("60 per minute")
def list_centers():
    """List all evacuation centers with capacity info, sorted by barangay."""
    try:
        with get_db_session() as session:
            centers = (
                session.query(EvacuationCenter)
                .filter(EvacuationCenter.is_deleted.is_(False))
                .order_by(EvacuationCenter.barangay)
                .all()
            )

            return (
                jsonify(
                    {
                        "success": True,
                        "centers": [c.to_dict() for c in centers],
                    }
                ),
                200,
            )

    except Exception as exc:
        logger.error("Failed to list evacuation centers: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


# ── GET /centers/<id> — Single center detail ────────────────────────────


@evacuation_bp.route("/centers/<int:center_id>", methods=["GET"])
@rate_limit_with_burst("60 per minute")
def get_center(center_id: int):
    """Get a single evacuation center by ID."""
    try:
        with get_db_session() as session:
            center = (
                session.query(EvacuationCenter)
                .filter(EvacuationCenter.id == center_id, EvacuationCenter.is_deleted.is_(False))
                .first()
            )
            if not center:
                return jsonify({"success": False, "error": "Evacuation center not found"}), 404

            return jsonify({"success": True, "center": center.to_dict()}), 200

    except Exception as exc:
        logger.error("Failed to get center %d: %s", center_id, exc, exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


# ── PATCH /centers/<id>/capacity — Update capacity ──────────────────────


@evacuation_bp.route("/centers/<int:center_id>/capacity", methods=["PATCH"])
@rate_limit_with_burst("30 per hour")
@require_auth_or_api_key
@require_scope("alerts")
def update_capacity(center_id: int):
    """Update current occupancy for an evacuation center (admin/operator)."""
    try:
        role = getattr(g, "current_user_role", "user")
        if role not in ("admin", "operator"):
            return jsonify({"success": False, "error": "Admin or operator access required"}), 403

        data = request.get_json(silent=True) or {}
        new_capacity = data.get("capacity_current")

        if new_capacity is None or not isinstance(new_capacity, int) or new_capacity < 0:
            return jsonify({"success": False, "error": "capacity_current must be a non-negative integer"}), 400

        with get_db_session() as session:
            center = (
                session.query(EvacuationCenter)
                .filter(EvacuationCenter.id == center_id, EvacuationCenter.is_deleted.is_(False))
                .first()
            )
            if not center:
                return jsonify({"success": False, "error": "Evacuation center not found"}), 404

            center.capacity_current = new_capacity
            session.add(center)

            center_data = center.to_dict()
            near_full = center.occupancy_pct >= 90.0

        # ── SSE broadcast ───────────────────────────────────────────────
        try:
            from app.api.routes.sse import get_sse_manager

            sse = get_sse_manager()
            event_data = {
                "type": "capacity_update",
                "data": {
                    "center_id": center_id,
                    "capacity_current": new_capacity,
                    "capacity_total": center_data["capacity_total"],
                    "occupancy_pct": center_data["occupancy_pct"],
                    "near_full": near_full,
                },
            }
            sse.broadcast("capacity_update", event_data)
        except Exception as exc:
            logger.debug("SSE capacity broadcast skipped: %s", exc)

        result = {"success": True, "center": center_data}
        if near_full:
            result["warning"] = "Center is at 90%+ capacity"
        return jsonify(result), 200

    except Exception as exc:
        logger.error("Failed to update capacity for center %d: %s", center_id, exc, exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


# ── GET /nearest — Find nearest centers ─────────────────────────────────


@evacuation_bp.route("/nearest", methods=["GET"])
@rate_limit_with_burst("60 per minute")
def nearest_centers():
    """Find the nearest evacuation centers from a given location."""
    try:
        lat = request.args.get("latitude", type=float) or request.args.get("lat", type=float)
        lon = request.args.get("longitude", type=float) or request.args.get("lon", type=float)
        limit = min(int(request.args.get("limit", 3)), 10)

        if lat is None or lon is None:
            return jsonify({"success": False, "error": "latitude/lat and longitude/lon query params are required"}), 400

        centers = get_nearest_centers(lat, lon, limit=limit)

        return jsonify({"success": True, "results": centers}), 200

    except Exception as exc:
        logger.error("Failed to find nearest centers: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


# ── GET /route — Get safe route ─────────────────────────────────────────


@evacuation_bp.route("/route", methods=["GET"])
@rate_limit_with_burst("30 per minute")
def safe_route():
    """Get a walking route between two points, avoiding flooded areas."""
    try:
        origin_lat = request.args.get("origin_lat", type=float) or request.args.get("lat", type=float)
        origin_lon = request.args.get("origin_lon", type=float) or request.args.get("lon", type=float)
        dest_lat = request.args.get("dest_lat", type=float)
        dest_lon = request.args.get("dest_lon", type=float)
        center_id = request.args.get("center_id", type=int)
        avoid_flooded = request.args.get("avoid_flooded", "true").lower() in ("true", "1", "yes")

        # Resolve destination from center_id if dest coords not provided
        if dest_lat is None or dest_lon is None:
            if center_id is not None:
                with get_db_session() as session:
                    center = (
                        session.query(EvacuationCenter)
                        .filter(EvacuationCenter.id == center_id, EvacuationCenter.is_deleted.is_(False))
                        .first()
                    )
                    if not center:
                        return jsonify({"success": False, "error": "Evacuation center not found"}), 404
                    dest_lat = center.latitude
                    dest_lon = center.longitude

        if any(v is None for v in (origin_lat, origin_lon, dest_lat, dest_lon)):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "origin coordinates and destination (dest_lat/dest_lon or center_id) are required",
                    }
                ),
                400,
            )

        # Type narrowing after None check (all are guaranteed float at this point)
        route = get_safe_route(
            float(origin_lat),  # type: ignore[arg-type]
            float(origin_lon),  # type: ignore[arg-type]
            float(dest_lat),  # type: ignore[arg-type]
            float(dest_lon),  # type: ignore[arg-type]
            avoid_flooded=avoid_flooded,
        )

        google_maps_url = (
            f"https://www.google.com/maps/dir/?api=1"
            f"&origin={origin_lat},{origin_lon}"
            f"&destination={dest_lat},{dest_lon}"
            f"&travelmode=walking"
        )

        return (
            jsonify(
                {
                    "success": True,
                    "route": route,
                    "google_maps_url": google_maps_url,
                }
            ),
            200,
        )

    except Exception as exc:
        logger.error("Failed to get safe route: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


# ── POST /alert — Trigger SMS dispatch ──────────────────────────────────


@evacuation_bp.route("/alert", methods=["POST"])
@rate_limit_with_burst("10 per hour")
@require_auth_or_api_key
@require_scope("admin")
def trigger_alert():
    """Trigger evacuation SMS alert dispatch for a barangay (admin only)."""
    try:
        role = getattr(g, "current_user_role", "user")
        if role != "admin":
            return jsonify({"success": False, "error": "Admin access required"}), 403

        data = request.get_json(silent=True) or {}
        barangay = data.get("barangay")
        risk_label = data.get("risk_label")

        if not barangay or not risk_label:
            return jsonify({"success": False, "error": "barangay and risk_label are required"}), 400

        if risk_label not in ("Safe", "Alert", "Critical"):
            return jsonify({"success": False, "error": "risk_label must be Safe, Alert, or Critical"}), 400

        # Dispatch (sync or async via Celery)
        try:
            from app.services.celery_app import celery_app

            task = celery_app.send_task(
                "app.services.tasks.dispatch_sms_alert",
                args=[barangay, risk_label],
                queue="notification_tasks",
            )
            return (
                jsonify(
                    {
                        "success": True,
                        "status": "queued",
                        "task_id": task.id,
                    }
                ),
                200,
            )
        except Exception:
            # Sync fallback
            dispatched = dispatch_evacuation_sms(barangay, risk_label)
            return (
                jsonify(
                    {
                        "success": True,
                        "status": "completed",
                        "dispatched_count": dispatched,
                    }
                ),
                200,
            )

    except Exception as exc:
        logger.error("Failed to trigger alert: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


# ── POST /capacity-stream/ticket — SSE ticket for capacity stream ───────

_capacity_tickets: dict = {}
_CAPACITY_TICKET_TTL = 30  # seconds


def _cleanup_capacity_tickets() -> None:
    now = time.time()
    expired = [k for k, v in _capacity_tickets.items() if now - v["created"] > _CAPACITY_TICKET_TTL]
    for k in expired:
        _capacity_tickets.pop(k, None)


@evacuation_bp.route("/capacity-stream/ticket", methods=["POST"])
@rate_limit_with_burst("30 per minute")
def get_capacity_stream_ticket():
    """Issue a short-lived ticket for the capacity SSE stream."""
    request_id = getattr(g, "request_id", "unknown")
    ticket = secrets.token_urlsafe(32)
    _capacity_tickets[ticket] = {"created": time.time(), "request_id": request_id}
    _cleanup_capacity_tickets()
    return jsonify({"ticket": ticket, "expires_in": _CAPACITY_TICKET_TTL}), 200


# ── GET /capacity-stream — SSE for capacity updates ─────────────────────


@evacuation_bp.route("/capacity-stream", methods=["GET"])
def capacity_stream():
    """Server-Sent Events stream for real-time capacity updates."""
    client_id = str(uuid.uuid4())
    client_queue: queue.Queue = queue.Queue(maxsize=50)

    # Register with main SSE manager for capacity_update events
    try:
        from app.api.routes.sse import get_sse_manager

        sse = get_sse_manager()
        client_queue = sse.add_client(client_id)
    except Exception:  # nosec B110 — SSE client registration fallback
        pass

    def generate():
        try:
            # Send initial connection event
            yield f'event: connected\ndata: {{"client_id": "{client_id}"}}\n\n'

            while True:
                try:
                    message = client_queue.get(timeout=30)
                    # Only forward capacity_update events
                    if "capacity_update" in message:
                        yield message
                except queue.Empty:
                    # Send heartbeat to keep connection alive
                    yield f'event: heartbeat\ndata: {{"time": "{datetime.now(timezone.utc).isoformat()}"}}\n\n'
        except GeneratorExit:
            pass
        finally:
            try:
                from app.api.routes.sse import get_sse_manager

                get_sse_manager().remove_client(client_id)
            except Exception:  # nosec B110 — SSE cleanup best-effort
                pass

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
