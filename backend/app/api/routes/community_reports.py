"""Community Reports Routes - crowdsourced flood reporting endpoints.

Blueprint: /api/v1/reports

Provides CRUD for community-submitted flood observations with photo
upload, community voting (confirm/dispute), abuse flagging, and
admin verification.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import cast

from app.api.middleware.auth import require_auth_or_api_key, require_scope
from app.api.middleware.rate_limit import rate_limit_with_burst
from app.core.constants import is_within_study_area
from app.core.security import decode_token
from app.models.community_report import CommunityReport
from app.models.db import get_db_session
from app.services.credibility_service import check_auto_verify, score_report
from app.services.photo_service import compress_image, upload_photo, validate_image
from app.services.reverse_geocoder import reverse_geocode_barangay
from flask import Blueprint, g, jsonify, request

logger = logging.getLogger(__name__)

community_reports_bp = Blueprint("community_reports", __name__)


# ── Helpers ──────────────────────────────────────────────────────────────


def _serialize_report(report: CommunityReport) -> dict:
    """Serialize a report with computed ``time_ago`` string."""
    data = report.to_dict()
    created_at = cast(datetime, report.created_at)
    if created_at is not None:
        delta = datetime.now(timezone.utc) - created_at.replace(tzinfo=timezone.utc)
        seconds = int(delta.total_seconds())
        if seconds < 60:
            data["time_ago"] = f"{seconds}s ago"
        elif seconds < 3600:
            data["time_ago"] = f"{seconds // 60}m ago"
        elif seconds < 86400:
            data["time_ago"] = f"{seconds // 3600}h ago"
        else:
            data["time_ago"] = f"{seconds // 86400}d ago"
    else:
        data["time_ago"] = "unknown"
    return data


def _get_current_user_id():
    """Return the authenticated user ID or None."""
    return getattr(g, "current_user_id", None)


def _get_client_ip() -> str:
    """Best-effort client IP extraction."""
    return request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()


def _parse_report_fields():
    """Parse report fields from multipart form-data or JSON body."""
    if request.content_type and "multipart" in request.content_type:
        return {
            "lat": request.form.get("latitude", type=float),
            "lon": request.form.get("longitude", type=float),
            "flood_height_cm": request.form.get("flood_height_cm", type=int),
            "description": request.form.get("description", ""),
            "risk_label": request.form.get("risk_label", "Alert"),
            "specific_location": request.form.get("specific_location", ""),
            "contact_number": request.form.get("contact_number", ""),
            "barangay_override": request.form.get("barangay", ""),
            "photo_file": request.files.get("photo"),
        }
    data = request.get_json(silent=True) or {}
    return {
        "lat": data.get("latitude"),
        "lon": data.get("longitude"),
        "flood_height_cm": data.get("flood_height_cm"),
        "description": data.get("description", ""),
        "risk_label": data.get("risk_label", "Alert"),
        "specific_location": data.get("specific_location", ""),
        "contact_number": data.get("contact_number", ""),
        "barangay_override": data.get("barangay", ""),
        "photo_file": None,
    }


def _resolve_user_id():
    """Extract user ID from Bearer token, or None for anonymous."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    try:
        from app.core.security import decode_token

        token = auth_header.split(" ", 1)[1]
        payload, error = decode_token(token)
        if not error and payload:
            sub = payload.get("sub")
            if sub is not None:
                return int(sub)
    except Exception:  # nosec B110 - intentional fallback for JWT decode
        pass
    return None


def _post_create_tasks(report_id: int, report_data: dict, risk_label: str, cred_score: float):
    """Fire-and-forget credibility scoring and SSE broadcast after report creation."""
    try:
        from app.services.celery_app import celery_app

        celery_app.send_task(
            "app.services.tasks.score_community_report",
            args=[report_id],
            queue="data_tasks",
        )
    except Exception:
        try:
            score_report(report_id)
            check_auto_verify(report_id)
        except Exception as exc:
            logger.warning("Sync credibility scoring failed: %s", exc)

    try:
        from app.api.routes.sse import get_sse_manager

        sse = get_sse_manager()
        sse.broadcast("flood_report", report_data)
        if risk_label == "Critical" and cred_score >= 0.6:
            sse.broadcast("critical_report_admin", report_data)
    except Exception as exc:
        logger.debug("SSE broadcast skipped: %s", exc)


# ── POST / - Submit a new report ────────────────────────────────────────


@community_reports_bp.route("/", methods=["POST"])
@rate_limit_with_burst("10 per hour")
def create_report():
    """Submit a community flood report (multipart/form-data with optional photo)."""
    try:
        fields = _parse_report_fields()
        lat = fields["lat"]
        lon = fields["lon"]
        flood_height_cm = fields["flood_height_cm"]
        description = fields["description"]
        risk_label = fields["risk_label"]
        specific_location = fields["specific_location"]
        contact_number = fields["contact_number"]
        barangay_override = fields["barangay_override"]
        photo_file = fields["photo_file"]

        # ── Validation ──────────────────────────────────────────────────
        if lat is None or lon is None:
            return jsonify({"success": False, "error": "latitude and longitude are required"}), 400

        lat, lon = float(lat), float(lon)

        if not is_within_study_area(lat, lon):
            return jsonify({"success": False, "error": "Coordinates are outside the Parañaque study area"}), 400

        if risk_label not in ("Safe", "Alert", "Critical"):
            return jsonify({"success": False, "error": "risk_label must be Safe, Alert, or Critical"}), 400

        if flood_height_cm is not None:
            try:
                flood_height_cm = int(flood_height_cm)
            except (TypeError, ValueError):
                return jsonify({"success": False, "error": "flood_height_cm must be an integer"}), 400
            if flood_height_cm < 0 or flood_height_cm > 500:
                return jsonify({"success": False, "error": "flood_height_cm must be between 0 and 500"}), 400

        if description and len(description) > 280:
            return jsonify({"success": False, "error": "description must be at most 280 characters"}), 400

        # Reverse-geocode barangay (use override if provided)
        barangay = (
            barangay_override.strip()
            if barangay_override and barangay_override.strip()
            else reverse_geocode_barangay(lat, lon)
        )

        # Get authenticated user (optional)
        user_id = _resolve_user_id()

        # ── Create report ───────────────────────────────────────────────
        with get_db_session() as session:
            report = CommunityReport(
                user_id=user_id,
                latitude=lat,
                longitude=lon,
                barangay=barangay,
                flood_height_cm=flood_height_cm,
                description=description[:280] if description else None,
                specific_location=specific_location[:200] if specific_location else None,
                contact_number=contact_number[:20] if contact_number else None,
                risk_label=risk_label,
            )
            session.add(report)
            session.flush()  # get report.id

            # ── Photo handling ──────────────────────────────────────────
            photo_url = None
            if photo_file:
                valid, error_msg = validate_image(photo_file)
                if not valid:
                    return jsonify({"success": False, "error": f"Photo invalid: {error_msg}"}), 400
                raw_bytes = photo_file.read()
                clean_bytes = compress_image(raw_bytes)
                photo_url = upload_photo(clean_bytes, cast(int, report.id))
                report.photo_url = photo_url  # type: ignore[assignment]

            report_id = cast(int, report.id)
            report_data = _serialize_report(report)
            cred_score = cast(float, report.credibility_score or 0)

        _post_create_tasks(report_id, report_data, risk_label, cred_score)

        # Auto-post to barangay chat channel (non-fatal)
        try:
            from app.api.routes.chat import post_flood_report_to_chat_internal

            user_id = _resolve_user_id()
            if user_id:
                with get_db_session() as sess:
                    u = sess.query(CommunityReport).filter(CommunityReport.id == report_id).first()
                    from app.models.user import User as UserModel

                    author = sess.query(UserModel).filter(UserModel.id == user_id).first()
                    author_name = (author.full_name or author.email) if author else "Anonymous"
                    from app.models.resident_profile import ResidentProfile

                    profile = sess.query(ResidentProfile).filter(ResidentProfile.user_id == user_id).first()
                    brgy_raw = profile.barangay if profile else barangay
                    # Normalize barangay display name to slug
                    brgy_slug = None
                    if brgy_raw:
                        from app.core.chat_constants import BARANGAY_DISPLAY_NAMES

                        for bid, dname in BARANGAY_DISPLAY_NAMES.items():
                            if dname.lower() == brgy_raw.strip().lower():
                                brgy_slug = bid
                                break
                        if not brgy_slug:
                            brgy_slug = brgy_raw.strip().lower().replace(" ", "_")

                    post_flood_report_to_chat_internal(
                        user_id=user_id,
                        user_name=author_name,
                        user_role=author.role if author else "user",
                        barangay_id=brgy_slug,
                        report_id=report_id,
                        flood_depth=f"{flood_height_cm} cm" if flood_height_cm else "Unknown depth",
                        location=specific_location or barangay or "Location not specified",
                    )
        except Exception as e:
            logger.warning("Failed to post flood report to chat: %s", e)

        return jsonify({"success": True, "report": report_data}), 201

    except Exception as exc:
        logger.error("Failed to create community report: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


# ── GET /stats - Aggregate stats ────────────────────────────────────────


@community_reports_bp.route("/stats", methods=["GET"])
@rate_limit_with_burst("60 per minute")
def report_stats():
    """Return aggregate counts for community reports."""
    try:
        hours = int(request.args.get("hours", 24))
        barangay = request.args.get("barangay")
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        with get_db_session() as session:
            from sqlalchemy import case, func

            filters = [
                CommunityReport.is_deleted.is_(False),
                CommunityReport.created_at >= cutoff,
            ]
            if barangay:
                filters.append(CommunityReport.barangay == barangay)

            # Single aggregation query (was 4 separate COUNT queries)
            row = (
                session.query(
                    func.count(CommunityReport.id).label("total"),
                    func.count(
                        case((CommunityReport.verified.is_(True), CommunityReport.id))
                    ).label("verified"),
                    func.count(
                        case((CommunityReport.status == "pending", CommunityReport.id))
                    ).label("pending"),
                    func.count(
                        case((CommunityReport.risk_label == "Critical", CommunityReport.id))
                    ).label("critical"),
                )
                .filter(*filters)
                .one()
            )

            return (
                jsonify(
                    {
                        "success": True,
                        "stats": {
                            "total": row.total,
                            "verified": row.verified,
                            "pending": row.pending,
                            "critical": row.critical,
                        },
                    }
                ),
                200,
            )

    except Exception as exc:
        logger.error("Failed to get report stats: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


# ── GET / - List reports (paginated) ────────────────────────────────────


@community_reports_bp.route("/", methods=["GET"])
@rate_limit_with_burst("60 per minute")
def list_reports():
    """List community flood reports with optional filters."""
    try:
        barangay = request.args.get("barangay")
        hours = int(request.args.get("hours", 6))
        status = request.args.get("status")
        verified = request.args.get("verified")
        mine = request.args.get("mine")
        limit = min(int(request.args.get("limit", 50)), 100)
        page = max(int(request.args.get("page", 1)), 1)
        offset = (page - 1) * limit

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        with get_db_session() as session:
            query = session.query(CommunityReport).filter(
                CommunityReport.is_deleted.is_(False),
            )

            # When filtering by user's own reports, skip the time cutoff
            if mine and mine.lower() in ("true", "1", "yes"):
                user_id = _get_current_user_id()
                # If auth middleware didn't set user_id, try decoding the token directly
                if not user_id:
                    auth_header = request.headers.get("Authorization", "")
                    if auth_header.startswith("Bearer "):
                        token = auth_header.split(" ", 1)[1]
                        payload, err = decode_token(token)
                        if not err:
                            user_id = int(payload.get("sub"))
                if user_id:
                    query = query.filter(CommunityReport.user_id == user_id)
                else:
                    return jsonify({"success": False, "error": "Authentication required for mine=true"}), 401
            else:
                query = query.filter(CommunityReport.created_at >= cutoff)

            if barangay:
                query = query.filter(CommunityReport.barangay == barangay)
            if status:
                query = query.filter(CommunityReport.status == status)
            elif not mine or mine.lower() not in ("true", "1", "yes"):
                # Public listing: exclude rejected reports by default
                query = query.filter(CommunityReport.status != "rejected")
            if verified is not None:
                v = verified.lower() in ("true", "1", "yes")
                query = query.filter(CommunityReport.verified.is_(v))

            total = query.count()
            pages = max(1, (total + limit - 1) // limit)

            reports = query.order_by(CommunityReport.created_at.desc()).offset(offset).limit(limit).all()

            return (
                jsonify(
                    {
                        "success": True,
                        "reports": [_serialize_report(r) for r in reports],
                        "total": total,
                        "pages": pages,
                        "page": page,
                    }
                ),
                200,
            )

    except Exception as exc:
        logger.error("Failed to list reports: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


# ── GET /<id> - Single report detail ────────────────────────────────────


@community_reports_bp.route("/<int:report_id>", methods=["GET"])
@rate_limit_with_burst("60 per minute")
def get_report(report_id: int):
    """Get a single community report by ID."""
    try:
        with get_db_session() as session:
            report = (
                session.query(CommunityReport)
                .filter(CommunityReport.id == report_id, CommunityReport.is_deleted.is_(False))
                .first()
            )
            if not report:
                return jsonify({"success": False, "error": "Report not found"}), 404

            return jsonify({"success": True, "report": _serialize_report(report)}), 200

    except Exception as exc:
        logger.error("Failed to get report %d: %s", report_id, exc, exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


# ── PATCH /<id> - Edit own report (within 10 minutes) ──────────────────


@community_reports_bp.route("/<int:report_id>", methods=["PATCH"])
@rate_limit_with_burst("30 per hour")
@require_auth_or_api_key
@require_scope("alerts")
def edit_report(report_id: int):
    """Edit own report. Only within 10 minutes of creation."""
    try:
        user_id = _get_current_user_id()
        data = request.get_json(silent=True) or {}

        with get_db_session() as session:
            report = (
                session.query(CommunityReport)
                .filter(CommunityReport.id == report_id, CommunityReport.is_deleted.is_(False))
                .first()
            )
            if not report:
                return jsonify({"success": False, "error": "Report not found"}), 404

            if report.user_id != user_id:
                return jsonify({"success": False, "error": "You can only edit your own reports"}), 403

            created = (
                report.created_at.replace(tzinfo=timezone.utc) if report.created_at else datetime.now(timezone.utc)
            )
            if datetime.now(timezone.utc) - created > timedelta(minutes=10):
                return (
                    jsonify({"success": False, "error": "Reports can only be edited within 10 minutes of creation"}),
                    403,
                )

            # Editable fields
            if "description" in data:
                desc = data["description"]
                if desc and len(desc) > 280:
                    return jsonify({"success": False, "error": "description must be at most 280 characters"}), 400
                report.description = desc[:280] if desc else None

            if "flood_height_cm" in data:
                report.flood_height_cm = data["flood_height_cm"]

            if "risk_label" in data:
                if data["risk_label"] not in ("Safe", "Alert", "Critical"):
                    return jsonify({"success": False, "error": "risk_label must be Safe, Alert, or Critical"}), 400
                report.risk_label = data["risk_label"]

            session.add(report)
            return jsonify({"success": True, "report": _serialize_report(report)}), 200

    except Exception as exc:
        logger.error("Failed to edit report %d: %s", report_id, exc, exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


# ── DELETE /<id> - Soft-delete own report ───────────────────────────────


@community_reports_bp.route("/<int:report_id>", methods=["DELETE"])
@rate_limit_with_burst("30 per hour")
@require_auth_or_api_key
@require_scope("alerts")
def delete_report(report_id: int):
    """Soft-delete own report. Only within 10 minutes of creation."""
    try:
        user_id = _get_current_user_id()

        with get_db_session() as session:
            report = (
                session.query(CommunityReport)
                .filter(CommunityReport.id == report_id, CommunityReport.is_deleted.is_(False))
                .first()
            )
            if not report:
                return jsonify({"success": False, "error": "Report not found"}), 404

            if report.user_id != user_id:
                return jsonify({"success": False, "error": "You can only delete your own reports"}), 403

            created = (
                report.created_at.replace(tzinfo=timezone.utc) if report.created_at else datetime.now(timezone.utc)
            )
            if datetime.now(timezone.utc) - created > timedelta(minutes=10):
                return (
                    jsonify({"success": False, "error": "Reports can only be deleted within 10 minutes of creation"}),
                    403,
                )

            report.soft_delete()
            session.add(report)
            return jsonify({"success": True, "message": "Report deleted"}), 200

    except Exception as exc:
        logger.error("Failed to delete report %d: %s", report_id, exc, exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


# ── PATCH /<id>/verify - Admin verify/reject ───────────────────────────


@community_reports_bp.route("/<int:report_id>/verify", methods=["PATCH"])
@rate_limit_with_burst("30 per hour")
@require_auth_or_api_key
@require_scope("admin")
def verify_report(report_id: int):
    """Admin verify or reject a report."""
    try:
        role = getattr(g, "current_user_role", "user")
        if role != "admin":
            return jsonify({"success": False, "error": "Admin access required"}), 403

        data = request.get_json(silent=True) or {}
        new_status = data.get("status")
        if new_status not in ("accepted", "rejected"):
            return jsonify({"success": False, "error": "status must be 'accepted' or 'rejected'"}), 400

        with get_db_session() as session:
            report = (
                session.query(CommunityReport)
                .filter(CommunityReport.id == report_id, CommunityReport.is_deleted.is_(False))
                .first()
            )
            if not report:
                return jsonify({"success": False, "error": "Report not found"}), 404

            report.status = new_status
            if new_status == "accepted":
                report.verified = True
            report.verified_by = getattr(g, "current_user_id", None)
            report.verified_at = datetime.now(timezone.utc)
            session.add(report)

            serialized = _serialize_report(report)

            # Broadcast status change via SSE for real-time updates
            try:
                from app.api.routes.sse import get_sse_manager

                sse = get_sse_manager()
                sse.broadcast("report_status_changed", {"report_id": report_id, "status": new_status, "report": serialized})
            except Exception as exc:
                logger.debug("SSE broadcast skipped for verify: %s", exc)

            return jsonify({"success": True, "report": serialized}), 200

    except Exception as exc:
        logger.error("Failed to verify report %d: %s", report_id, exc, exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


# ── POST /<id>/confirm - Community vote ─────────────────────────────────


@community_reports_bp.route("/<int:report_id>/confirm", methods=["POST"])
@rate_limit_with_burst("30 per hour")
def confirm_report(report_id: int):
    """Cast a community vote (confirm or dispute) on a report."""
    try:
        data = request.get_json(silent=True) or {}
        vote = data.get("vote")
        if vote not in ("confirm", "dispute"):
            return jsonify({"success": False, "error": "vote must be 'confirm' or 'dispute'"}), 400

        with get_db_session() as session:
            # Atomic increment via SQL UPDATE (avoids SELECT + UPDATE round-trip)
            if vote == "confirm":
                updated = (
                    session.query(CommunityReport)
                    .filter(CommunityReport.id == report_id, CommunityReport.is_deleted.is_(False))
                    .update(
                        {CommunityReport.confirmation_count: (CommunityReport.confirmation_count or 0) + 1},
                        synchronize_session="fetch",
                    )
                )
            else:
                updated = (
                    session.query(CommunityReport)
                    .filter(CommunityReport.id == report_id, CommunityReport.is_deleted.is_(False))
                    .update(
                        {CommunityReport.dispute_count: (CommunityReport.dispute_count or 0) + 1},
                        synchronize_session="fetch",
                    )
                )

            if not updated:
                return jsonify({"success": False, "error": "Report not found"}), 404

            # Fetch updated counts for response
            report = session.query(CommunityReport).filter(CommunityReport.id == report_id).first()

            # Re-check auto-verify after new confirmation
            if vote == "confirm":
                try:
                    check_auto_verify(report_id)
                except Exception:  # nosec B110 - non-critical post-vote task
                    pass

            return (
                jsonify(
                    {
                        "success": True,
                        "confirmation_count": report.confirmation_count,
                        "dispute_count": report.dispute_count,
                    }
                ),
                200,
            )

    except Exception as exc:
        logger.error("Failed to vote on report %d: %s", report_id, exc, exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


# ── POST /<id>/flag - Abuse flagging ────────────────────────────────────


@community_reports_bp.route("/<int:report_id>/flag", methods=["POST"])
@rate_limit_with_burst("10 per hour")
def flag_report(report_id: int):
    """Flag a report for abuse. Auto-rejects at 3 flags."""
    try:
        with get_db_session() as session:
            report = (
                session.query(CommunityReport)
                .filter(CommunityReport.id == report_id, CommunityReport.is_deleted.is_(False))
                .first()
            )
            if not report:
                return jsonify({"success": False, "error": "Report not found"}), 404

            report.abuse_flag_count = (report.abuse_flag_count or 0) + 1

            # Auto-reject at 3 flags
            if report.abuse_flag_count >= 3:
                report.status = "rejected"
                logger.info("Report %d auto-rejected due to %d abuse flags", report_id, report.abuse_flag_count)

            session.add(report)

            response_data = {
                "success": True,
                "abuse_flag_count": report.abuse_flag_count,
                "status": report.status,
            }

            # Broadcast flag event via SSE for real-time updates
            try:
                from app.api.routes.sse import get_sse_manager

                sse = get_sse_manager()
                sse.broadcast("report_status_changed", {"report_id": report_id, "status": report.status, "flagged": True})
            except Exception as exc:
                logger.debug("SSE broadcast skipped for flag: %s", exc)

            return jsonify(response_data), 200

    except Exception as exc:
        logger.error("Failed to flag report %d: %s", report_id, exc, exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


# ── POST /admin/bulk-delete - Admin bulk soft-delete ────────────────────


@community_reports_bp.route("/admin/bulk-delete", methods=["POST"])
@require_auth_or_api_key
@require_scope("admin")
def admin_bulk_delete_reports():
    """
    Admin bulk soft-delete community reports.

    Request Body:
    {
        "older_than_days": 30,        // Delete reports older than N days
        "status": null,               // Optional: filter by status (pending/accepted/rejected)
        "barangay": null,             // Optional: filter by barangay
        "confirm": true               // Required
    }

    Maximum 5000 records per request.
    """
    MAX_BULK = 5000

    try:
        role = getattr(g, "current_user_role", "user")
        if role != "admin":
            return jsonify({"success": False, "error": "Admin access required"}), 403

        data = request.get_json(silent=True) or {}

        if not data.get("confirm"):
            return jsonify({"success": False, "error": "Bulk delete requires confirm=true"}), 400

        older_than_days = data.get("older_than_days")
        status_filter = data.get("status")
        barangay_filter = data.get("barangay")

        if older_than_days is None and status_filter is None and barangay_filter is None:
            return jsonify({"success": False, "error": "At least one filter is required"}), 400

        with get_db_session() as session:
            query = session.query(CommunityReport).filter(CommunityReport.is_deleted.is_(False))

            if older_than_days is not None:
                cutoff = datetime.now(timezone.utc) - timedelta(days=int(older_than_days))
                query = query.filter(CommunityReport.created_at < cutoff)

            if status_filter:
                query = query.filter(CommunityReport.status == status_filter)

            if barangay_filter:
                query = query.filter(CommunityReport.barangay == barangay_filter)

            total_count = query.count()

            if total_count == 0:
                return jsonify({"success": True, "deleted_count": 0, "message": "No matching records found"}), 200

            if total_count > MAX_BULK:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"Query matches {total_count} records, exceeds max of {MAX_BULK}. Add stricter filters.",
                        }
                    ),
                    400,
                )

            now = datetime.now(timezone.utc)
            deleted = query.update({"is_deleted": True, "deleted_at": now}, synchronize_session="fetch")

        logger.info("Admin bulk-deleted %d community reports", deleted)
        return (
            jsonify(
                {
                    "success": True,
                    "deleted_count": deleted,
                    "message": f"Successfully deleted {deleted} community report(s)",
                }
            ),
            200,
        )

    except Exception as exc:
        logger.error("Admin bulk delete reports failed: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# Report Density - GeoJSON heatmap data for community reports
# ---------------------------------------------------------------------------

_GRID_SIZE_DEG = 0.001  # ~100 m at equator


@community_reports_bp.route("/density", methods=["GET"])
@rate_limit_with_burst("30 per minute")
def get_report_density():
    """
    Get report density as a GeoJSON FeatureCollection for heatmap display.

    Groups reports into ~100 m grid cells and returns:
      - Per-cell report count (weight for HeatmapLayer)
      - Average credibility score
      - Dominant risk_label per cell

    Query Parameters:
        hours (int): Lookback window in hours (default: 168 = 7 days, max: 720)
        min_credibility (float): Minimum credibility score filter (0-1, default: 0)

    Returns:
        200: GeoJSON FeatureCollection with point features per grid cell
    ---
    tags:
      - Community Reports
    parameters:
      - in: query
        name: hours
        type: integer
        default: 168
      - in: query
        name: min_credibility
        type: number
        default: 0
    responses:
      200:
        description: Report density GeoJSON
    """
    import math

    request_id = getattr(g, "request_id", "unknown")

    try:
        hours = min(max(request.args.get("hours", 168, type=int), 1), 720)
        min_cred = max(request.args.get("min_credibility", 0.0, type=float), 0.0)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        with get_db_session() as session:
            query = session.query(CommunityReport).filter(
                CommunityReport.is_deleted.is_(False),
                CommunityReport.created_at >= cutoff,
                CommunityReport.latitude.isnot(None),
                CommunityReport.longitude.isnot(None),
            )

            if min_cred > 0:
                query = query.filter(CommunityReport.credibility_score >= min_cred)

            reports = query.all()

            # Aggregate into grid cells
            grid: dict = {}
            for r in reports:
                lat = r.latitude
                lon = r.longitude
                if lat is None or lon is None:
                    continue
                # Snap to grid
                cell_lat = round(math.floor(lat / _GRID_SIZE_DEG) * _GRID_SIZE_DEG, 6)
                cell_lon = round(math.floor(lon / _GRID_SIZE_DEG) * _GRID_SIZE_DEG, 6)
                key = (cell_lat, cell_lon)

                if key not in grid:
                    grid[key] = {
                        "count": 0,
                        "cred_sum": 0.0,
                        "risk_counts": {},
                        "max_height": 0.0,
                    }

                cell = grid[key]
                cell["count"] += 1
                cell["cred_sum"] += r.credibility_score or 0.0
                rl = r.risk_label or "Unknown"
                cell["risk_counts"][rl] = cell["risk_counts"].get(rl, 0) + 1
                if r.flood_height_cm:
                    cell["max_height"] = max(cell["max_height"], r.flood_height_cm)

        # Build GeoJSON
        features = []
        for (lat, lon), cell in grid.items():
            dominant_risk = max(cell["risk_counts"], key=cell["risk_counts"].get)
            avg_cred = round(cell["cred_sum"] / cell["count"], 2) if cell["count"] > 0 else 0.0
            # Center of grid cell
            center_lat = round(lat + _GRID_SIZE_DEG / 2, 6)
            center_lon = round(lon + _GRID_SIZE_DEG / 2, 6)

            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [center_lon, center_lat]},
                    "properties": {
                        "count": cell["count"],
                        "weight": cell["count"],
                        "avg_credibility": avg_cred,
                        "dominant_risk": dominant_risk,
                        "max_flood_height_cm": cell["max_height"],
                    },
                }
            )

        return (
            jsonify(
                {
                    "success": True,
                    "type": "FeatureCollection",
                    "features": features,
                    "meta": {
                        "hours": hours,
                        "min_credibility": min_cred,
                        "total_reports": sum(c["count"] for c in grid.values()),
                        "grid_cells": len(features),
                        "grid_size_degrees": _GRID_SIZE_DEG,
                    },
                    "request_id": request_id,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error("Error fetching report density [%s]: %s", request_id, e, exc_info=True)
        return jsonify({"success": False, "error": "Failed to compute report density"}), 500
