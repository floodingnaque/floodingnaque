"""
LGU Workflow Routes — Incident Management & After-Action Reporting.

Endpoints for the official RA 10121–compliant LGU workflow:
  Alert → LGU Confirmation → Public Broadcast → Resolution → AAR

Provides CRUD for Incidents and After-Action Reports, plus workflow
transition endpoints, analytics, and compliance status queries.
"""

import logging
from datetime import datetime, timezone
from typing import Any, cast

from app.api.middleware.auth import require_auth_or_api_key
from app.api.middleware.rate_limit import rate_limit_with_burst
from app.core.constants import HTTP_BAD_REQUEST, HTTP_CREATED, HTTP_INTERNAL_ERROR, HTTP_NOT_FOUND, HTTP_OK
from app.core.exceptions import api_error
from app.models.after_action_report import AfterActionReport
from app.models.db import get_db_session
from app.models.incident import Incident
from app.utils.validation import validate_request_size
from flask import Blueprint, g, jsonify, request
from sqlalchemy import case, extract, func

logger = logging.getLogger(__name__)

lgu_workflow_bp = Blueprint("lgu_workflow", __name__)


# ═══════════════════════════════════════════════════════════════════════════
# Incidents CRUD
# ═══════════════════════════════════════════════════════════════════════════


@lgu_workflow_bp.route("/incidents", methods=["GET"])
@rate_limit_with_burst("120 per hour")
@require_auth_or_api_key
def list_incidents():
    """List incidents with optional filters (status, risk_level, barangay)."""
    request_id = getattr(g, "request_id", "unknown")

    try:
        limit = min(int(request.args.get("limit", 25)), 100)
        offset = int(request.args.get("offset", 0))
        status = request.args.get("status")
        risk_level = request.args.get("risk_level")
        barangay = request.args.get("barangay")

        with get_db_session() as session:
            q = session.query(Incident).filter(Incident.is_deleted.is_(False))  # type: ignore[union-attr]

            if status:
                q = q.filter(Incident.status == status)
            if risk_level is not None:
                q = q.filter(Incident.risk_level == int(risk_level))
            if barangay:
                q = q.filter(Incident.barangay == barangay)

            total = q.count()
            incidents = q.order_by(Incident.created_at.desc()).offset(offset).limit(limit).all()

            return jsonify({
                "success": True,
                "data": [_serialize_incident(i) for i in incidents],
                "pagination": {"total": total, "limit": limit, "offset": offset},
                "request_id": request_id,
            }), HTTP_OK

    except Exception as e:
        logger.error("list_incidents failed [%s]: %s", request_id, e, exc_info=True)
        return api_error("InternalError", "Failed to list incidents", HTTP_INTERNAL_ERROR, request_id)


@lgu_workflow_bp.route("/incidents", methods=["POST"])
@rate_limit_with_burst("60 per hour")
@validate_request_size(endpoint_name="lgu_workflow")
@require_auth_or_api_key
def create_incident():
    """Create a new incident (status defaults to alert_raised)."""
    request_id = getattr(g, "request_id", "unknown")

    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return api_error("NoInput", "No input data provided", HTTP_BAD_REQUEST, request_id)

        # Required fields
        title = data.get("title")
        barangay = data.get("barangay")
        if not title or not barangay:
            return api_error("ValidationError", "'title' and 'barangay' are required", HTTP_BAD_REQUEST, request_id)

        with get_db_session() as session:
            incident = Incident(
                title=title,
                description=data.get("description"),
                incident_type=data.get("incident_type", "flood"),
                risk_level=int(data.get("risk_level", 1)),
                barangay=barangay,
                location_detail=data.get("location_detail"),
                latitude=data.get("latitude"),
                longitude=data.get("longitude"),
                source=data.get("source", "manual"),
                related_alert_id=data.get("related_alert_id"),
                created_by=data.get("created_by"),
                affected_families=data.get("affected_families", 0),
                evacuated_families=data.get("evacuated_families", 0),
            )
            session.add(incident)
            session.flush()
            result = _serialize_incident(incident)
            session.commit()

        return jsonify({"success": True, "data": result, "request_id": request_id}), HTTP_CREATED

    except Exception as e:
        logger.error("create_incident failed [%s]: %s", request_id, e, exc_info=True)
        return api_error("InternalError", "Failed to create incident", HTTP_INTERNAL_ERROR, request_id)


@lgu_workflow_bp.route("/incidents/<int:incident_id>", methods=["GET"])
@rate_limit_with_burst("120 per hour")
@require_auth_or_api_key
def get_incident(incident_id: int):
    """Get a single incident by ID."""
    request_id = getattr(g, "request_id", "unknown")

    try:
        with get_db_session() as session:
            incident = (
                session.query(Incident)
                .filter(Incident.id == incident_id, Incident.is_deleted.is_(False))  # type: ignore[union-attr]
                .first()
            )
            if not incident:
                return api_error("NotFound", f"Incident {incident_id} not found", HTTP_NOT_FOUND, request_id)

            return jsonify({"success": True, "data": _serialize_incident(incident), "request_id": request_id}), HTTP_OK

    except Exception as e:
        logger.error("get_incident failed [%s]: %s", request_id, e, exc_info=True)
        return api_error("InternalError", "Failed to get incident", HTTP_INTERNAL_ERROR, request_id)


@lgu_workflow_bp.route("/incidents/<int:incident_id>", methods=["PATCH"])
@rate_limit_with_burst("60 per hour")
@validate_request_size(endpoint_name="lgu_workflow")
@require_auth_or_api_key
def update_incident(incident_id: int):
    """Update editable fields of an incident."""
    request_id = getattr(g, "request_id", "unknown")

    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return api_error("NoInput", "No update data provided", HTTP_BAD_REQUEST, request_id)

        editable = [
            "title", "description", "incident_type", "risk_level", "barangay",
            "location_detail", "latitude", "longitude", "affected_families",
            "evacuated_families", "casualties", "estimated_damage",
            "broadcast_channels",
        ]

        with get_db_session() as session:
            incident = (
                session.query(Incident)
                .filter(Incident.id == incident_id, Incident.is_deleted.is_(False))  # type: ignore[union-attr]
                .first()
            )
            if not incident:
                return api_error("NotFound", f"Incident {incident_id} not found", HTTP_NOT_FOUND, request_id)

            for key in editable:
                if key in data:
                    setattr(incident, key, data[key])
            incident.updated_at = datetime.now(timezone.utc)

            session.flush()
            result = _serialize_incident(incident)
            session.commit()

        return jsonify({"success": True, "data": result, "request_id": request_id}), HTTP_OK

    except Exception as e:
        logger.error("update_incident failed [%s]: %s", request_id, e, exc_info=True)
        return api_error("InternalError", "Failed to update incident", HTTP_INTERNAL_ERROR, request_id)


# ═══════════════════════════════════════════════════════════════════════════
# Workflow Transition
# ═══════════════════════════════════════════════════════════════════════════


@lgu_workflow_bp.route("/incidents/<int:incident_id>/transition", methods=["POST"])
@rate_limit_with_burst("60 per hour")
@validate_request_size(endpoint_name="lgu_workflow")
@require_auth_or_api_key
def transition_incident(incident_id: int):
    """
    Advance an incident through the LGU workflow pipeline.

    Body varies by transition:
    - alert_raised → lgu_confirmed:  { next_status, actor, confirmation_notes? }
    - lgu_confirmed → broadcast_sent: { next_status, actor, broadcast_channels }
    - broadcast_sent → resolved:      { next_status, actor, affected_families?, evacuated_families?, casualties?, estimated_damage? }
    - resolved → closed:             { next_status, actor, requires_aar? }
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        data = request.get_json(force=True, silent=True) or {}
        next_status = data.get("next_status")
        actor = data.get("actor")

        if not next_status:
            return api_error("ValidationError", "'next_status' is required", HTTP_BAD_REQUEST, request_id)

        with get_db_session() as session:
            incident = (
                session.query(Incident)
                .filter(Incident.id == incident_id, Incident.is_deleted.is_(False))  # type: ignore[union-attr]
                .first()
            )
            if not incident:
                return api_error("NotFound", f"Incident {incident_id} not found", HTTP_NOT_FOUND, request_id)

            if not incident.can_transition_to(next_status):
                valid = Incident.VALID_TRANSITIONS.get(incident.status, [])
                return api_error(
                    "InvalidTransition",
                    f"Cannot move from '{incident.status}' to '{next_status}'. Valid: {valid}",
                    HTTP_BAD_REQUEST,
                    request_id,
                )

            # Stage-specific validation and field updates
            if next_status == "broadcast_sent":
                channels = data.get("broadcast_channels")
                if channels:
                    incident.broadcast_channels = channels

            if next_status == "resolved":
                # Accept impact data at resolution
                for field in ("affected_families", "evacuated_families", "casualties"):
                    if field in data:
                        setattr(incident, field, int(data[field]))
                if "estimated_damage" in data and data["estimated_damage"] is not None:
                    incident.estimated_damage = float(data["estimated_damage"])

            incident.transition_to(next_status, actor=actor)
            session.flush()
            result = _serialize_incident(incident)
            session.commit()

        logger.info("Incident %d transitioned to %s by %s [%s]", incident_id, next_status, actor, request_id)
        return jsonify({"success": True, "data": result, "request_id": request_id}), HTTP_OK

    except ValueError as e:
        return api_error("InvalidTransition", str(e), HTTP_BAD_REQUEST, request_id)
    except Exception as e:
        logger.error("transition_incident failed [%s]: %s", request_id, e, exc_info=True)
        return api_error("InternalError", "Failed to transition incident", HTTP_INTERNAL_ERROR, request_id)


# ═══════════════════════════════════════════════════════════════════════════
# Incident Stats
# ═══════════════════════════════════════════════════════════════════════════


@lgu_workflow_bp.route("/incidents/stats", methods=["GET"])
@rate_limit_with_burst("120 per hour")
@require_auth_or_api_key
def incident_stats():
    """Summary statistics for incident dashboard."""
    request_id = getattr(g, "request_id", "unknown")

    try:
        with get_db_session() as session:
            # Single query: count by status using conditional aggregation
            status_list = ["alert_raised", "lgu_confirmed", "broadcast_sent", "resolved", "closed"]
            status_cols = {
                s: func.count(case((Incident.status == s, 1)))  # type: ignore[arg-type]
                for s in status_list
            }
            status_row = (
                session.query(*status_cols.values())
                .filter(Incident.is_deleted.is_(False))  # type: ignore[union-attr]
                .one()
            )
            by_status = dict(zip(status_list, status_row))

            # Single query: count by risk_level using conditional aggregation
            risk_levels = [0, 1, 2]
            risk_cols = {
                rl: func.count(case((Incident.risk_level == rl, 1)))  # type: ignore[arg-type]
                for rl in risk_levels
            }
            risk_row = (
                session.query(*risk_cols.values())
                .filter(Incident.is_deleted.is_(False))  # type: ignore[union-attr]
                .one()
            )
            by_risk_level = {str(rl): cnt for rl, cnt in zip(risk_levels, risk_row)}

            # total_active = everything except resolved and closed
            total_active = sum(
                cnt for s, cnt in by_status.items() if s not in ("resolved", "closed")
            )

            stats = {
                "total_active": total_active,
                "by_status": by_status,
                "by_risk_level": by_risk_level,
            }

        return jsonify({"success": True, "data": stats, "request_id": request_id}), HTTP_OK
    except Exception as e:
        logger.error("incident_stats failed [%s]: %s", request_id, e, exc_info=True)
        return api_error("InternalError", "Failed to get stats", HTTP_INTERNAL_ERROR, request_id)


# ═══════════════════════════════════════════════════════════════════════════
# Workflow Analytics
# ═══════════════════════════════════════════════════════════════════════════


@lgu_workflow_bp.route("/incidents/analytics", methods=["GET"])
@rate_limit_with_burst("60 per hour")
@require_auth_or_api_key
def incident_analytics():
    """Workflow performance analytics: avg times, false-alarm rate, AAR metrics."""
    request_id = getattr(g, "request_id", "unknown")

    try:
        with get_db_session() as session:
            # Average times: confirmation, broadcast, resolution
            avg_confirm = (
                session.query(
                    func.avg(
                        extract("epoch", Incident.confirmed_at) - extract("epoch", Incident.created_at)
                    )
                )
                .filter(
                    Incident.is_deleted.is_(False),
                    Incident.confirmed_at.isnot(None),
                )
                .scalar()
            )
            avg_broadcast = (
                session.query(
                    func.avg(
                        extract("epoch", Incident.broadcast_sent_at) - extract("epoch", Incident.confirmed_at)
                    )
                )
                .filter(
                    Incident.is_deleted.is_(False),
                    Incident.broadcast_sent_at.isnot(None),
                    Incident.confirmed_at.isnot(None),
                )
                .scalar()
            )
            avg_resolve = (
                session.query(
                    func.avg(
                        extract("epoch", Incident.resolved_at) - extract("epoch", Incident.created_at)
                    )
                )
                .filter(
                    Incident.is_deleted.is_(False),
                    Incident.resolved_at.isnot(None),
                )
                .scalar()
            )

            # Counts
            total = session.query(func.count(Incident.id)).filter(Incident.is_deleted.is_(False)).scalar() or 0
            resolved_count = (
                session.query(func.count(Incident.id))
                .filter(Incident.is_deleted.is_(False), Incident.status.in_(["resolved", "closed"]))
                .scalar()
                or 0
            )
            closed_count = (
                session.query(func.count(Incident.id))
                .filter(Incident.is_deleted.is_(False), Incident.status == "closed")
                .scalar()
                or 0
            )

            # False alarm rate: resolved with 0 affected families / total resolved
            false_alarms = (
                session.query(func.count(Incident.id))
                .filter(
                    Incident.is_deleted.is_(False),
                    Incident.status.in_(["resolved", "closed"]),
                    Incident.affected_families == 0,
                    Incident.casualties == 0,
                )
                .scalar()
                or 0
            )
            false_alarm_rate = (false_alarms / resolved_count) if resolved_count > 0 else 0

            # AAR metrics
            total_aars = session.query(func.count(AfterActionReport.id)).filter(AfterActionReport.is_deleted.is_(False)).scalar() or 0
            approved_aars = (
                session.query(func.count(AfterActionReport.id))
                .filter(AfterActionReport.is_deleted.is_(False), AfterActionReport.status == "approved")
                .scalar()
                or 0
            )
            compliant_aars = (
                session.query(func.count(AfterActionReport.id))
                .filter(AfterActionReport.is_deleted.is_(False), AfterActionReport.ra10121_compliant.is_(True))
                .scalar()
                or 0
            )
            aar_completion_rate = (total_aars / closed_count) if closed_count > 0 else 0

            # Monthly incident frequency (last 12 months)
            monthly = (
                session.query(
                    extract("year", Incident.created_at).label("year"),
                    extract("month", Incident.created_at).label("month"),
                    func.count(Incident.id).label("count"),
                )
                .filter(Incident.is_deleted.is_(False))
                .group_by("year", "month")
                .order_by("year", "month")
                .limit(12)
                .all()
            )
            monthly_frequency = [
                {"year": int(r.year), "month": int(r.month), "count": r.count} for r in monthly
            ]

            # Stalled incidents: in alert_raised or lgu_confirmed for > 24h
            stall_threshold = datetime.now(timezone.utc).timestamp() - 86400  # 24h ago
            stalled = (
                session.query(func.count(Incident.id))
                .filter(
                    Incident.is_deleted.is_(False),
                    Incident.status.in_(["alert_raised", "lgu_confirmed"]),
                    extract("epoch", Incident.created_at) < stall_threshold,
                )
                .scalar()
                or 0
            )

            analytics = {
                "avg_confirm_minutes": round(avg_confirm / 60, 1) if avg_confirm else None,
                "avg_broadcast_minutes": round(avg_broadcast / 60, 1) if avg_broadcast else None,
                "avg_resolve_minutes": round(avg_resolve / 60, 1) if avg_resolve else None,
                "total_incidents": total,
                "resolved_incidents": resolved_count,
                "closed_incidents": closed_count,
                "false_alarm_rate": round(false_alarm_rate, 3),
                "false_alarm_count": false_alarms,
                "total_aars": total_aars,
                "approved_aars": approved_aars,
                "compliant_aars": compliant_aars,
                "aar_completion_rate": round(min(aar_completion_rate, 1.0), 3),
                "monthly_frequency": monthly_frequency,
                "stalled_incidents": stalled,
            }

        return jsonify({"success": True, "data": analytics, "request_id": request_id}), HTTP_OK
    except Exception as e:
        logger.error("incident_analytics failed [%s]: %s", request_id, e, exc_info=True)
        return api_error("InternalError", "Failed to compute analytics", HTTP_INTERNAL_ERROR, request_id)


# ═══════════════════════════════════════════════════════════════════════════
# After-Action Reports CRUD
# ═══════════════════════════════════════════════════════════════════════════


@lgu_workflow_bp.route("/incidents/<int:incident_id>/aar", methods=["GET"])
@rate_limit_with_burst("120 per hour")
@require_auth_or_api_key
def list_aar(incident_id: int):
    """List after-action reports for a given incident."""
    request_id = getattr(g, "request_id", "unknown")

    try:
        with get_db_session() as session:
            reports = (
                session.query(AfterActionReport)
                .filter(AfterActionReport.incident_id == incident_id, AfterActionReport.is_deleted.is_(False))  # type: ignore[union-attr]
                .order_by(AfterActionReport.created_at.desc())
                .all()
            )
            return jsonify({
                "success": True,
                "data": [_serialize_aar(r) for r in reports],
                "request_id": request_id,
            }), HTTP_OK
    except Exception as e:
        logger.error("list_aar failed [%s]: %s", request_id, e, exc_info=True)
        return api_error("InternalError", "Failed to list reports", HTTP_INTERNAL_ERROR, request_id)


@lgu_workflow_bp.route("/incidents/<int:incident_id>/aar", methods=["POST"])
@rate_limit_with_burst("30 per hour")
@validate_request_size(endpoint_name="lgu_workflow")
@require_auth_or_api_key
def create_aar(incident_id: int):
    """Create an after-action report for an incident."""
    request_id = getattr(g, "request_id", "unknown")

    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return api_error("NoInput", "No input data provided", HTTP_BAD_REQUEST, request_id)

        title = data.get("title")
        summary = data.get("summary")
        if not title or not summary:
            return api_error("ValidationError", "'title' and 'summary' are required", HTTP_BAD_REQUEST, request_id)

        with get_db_session() as session:
            # Verify incident exists
            incident = session.query(Incident).filter(Incident.id == incident_id, Incident.is_deleted.is_(False)).first()  # type: ignore[union-attr]
            if not incident:
                return api_error("NotFound", f"Incident {incident_id} not found", HTTP_NOT_FOUND, request_id)

            aar = AfterActionReport(
                incident_id=incident_id,
                title=title,
                summary=summary,
                timeline=data.get("timeline"),
                response_actions=data.get("response_actions"),
                resources_deployed=data.get("resources_deployed"),
                response_time_minutes=data.get("response_time_minutes"),
                evacuation_time_minutes=data.get("evacuation_time_minutes"),
                warning_lead_time_minutes=data.get("warning_lead_time_minutes"),
                prediction_accuracy=data.get("prediction_accuracy"),
                lessons_learned=data.get("lessons_learned"),
                recommendations=data.get("recommendations"),
                follow_up_actions=data.get("follow_up_actions"),
                prepared_by=data.get("prepared_by"),
                reviewed_by=data.get("reviewed_by"),
            )
            session.add(aar)
            session.flush()
            result = _serialize_aar(aar)
            session.commit()

        return jsonify({"success": True, "data": result, "request_id": request_id}), HTTP_CREATED

    except Exception as e:
        logger.error("create_aar failed [%s]: %s", request_id, e, exc_info=True)
        return api_error("InternalError", "Failed to create report", HTTP_INTERNAL_ERROR, request_id)


@lgu_workflow_bp.route("/aar/<int:aar_id>", methods=["PATCH"])
@rate_limit_with_burst("60 per hour")
@validate_request_size(endpoint_name="lgu_workflow")
@require_auth_or_api_key
def update_aar(aar_id: int):
    """Update an after-action report."""
    request_id = getattr(g, "request_id", "unknown")

    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return api_error("NoInput", "No update data provided", HTTP_BAD_REQUEST, request_id)

        editable = [
            "title", "summary", "timeline", "response_actions", "resources_deployed",
            "response_time_minutes", "evacuation_time_minutes", "warning_lead_time_minutes",
            "prediction_accuracy", "lessons_learned", "recommendations", "follow_up_actions",
            "prepared_by", "reviewed_by", "approved_by", "status",
            "ra10121_compliant", "submitted_to_ndrrmc", "submitted_to_dilg",
        ]

        with get_db_session() as session:
            aar = (
                session.query(AfterActionReport)
                .filter(AfterActionReport.id == aar_id, AfterActionReport.is_deleted.is_(False))  # type: ignore[union-attr]
                .first()
            )
            if not aar:
                return api_error("NotFound", f"Report {aar_id} not found", HTTP_NOT_FOUND, request_id)

            for key in editable:
                if key in data:
                    setattr(aar, key, data[key])
            aar.updated_at = datetime.now(timezone.utc)

            session.flush()
            result = _serialize_aar(aar)
            session.commit()

        return jsonify({"success": True, "data": result, "request_id": request_id}), HTTP_OK

    except Exception as e:
        logger.error("update_aar failed [%s]: %s", request_id, e, exc_info=True)
        return api_error("InternalError", "Failed to update report", HTTP_INTERNAL_ERROR, request_id)


# ═══════════════════════════════════════════════════════════════════════════
# Serialisation helpers
# ═══════════════════════════════════════════════════════════════════════════


def _isoformat(dt: Any) -> str | None:
    """Safely format a datetime (or SQLAlchemy Column wrapper) to ISO string."""
    if dt is None:
        return None
    return cast(datetime, dt).isoformat()


def _serialize_incident(i: Incident) -> dict:
    return {
        "id": i.id,
        "title": i.title,
        "description": i.description,
        "incident_type": i.incident_type,
        "risk_level": i.risk_level,
        "barangay": i.barangay,
        "location_detail": i.location_detail,
        "latitude": i.latitude,
        "longitude": i.longitude,
        "status": i.status,
        "confirmed_by": i.confirmed_by,
        "confirmed_at": _isoformat(i.confirmed_at),
        "broadcast_sent_at": _isoformat(i.broadcast_sent_at),
        "broadcast_channels": i.broadcast_channels,
        "resolved_at": _isoformat(i.resolved_at),
        "resolved_by": i.resolved_by,
        "affected_families": i.affected_families,
        "evacuated_families": i.evacuated_families,
        "casualties": i.casualties,
        "estimated_damage": i.estimated_damage,
        "source": i.source,
        "related_alert_id": i.related_alert_id,
        "created_at": _isoformat(i.created_at),
        "updated_at": _isoformat(i.updated_at),
        "created_by": i.created_by,
    }


def _serialize_aar(r: AfterActionReport) -> dict:
    return {
        "id": r.id,
        "incident_id": r.incident_id,
        "title": r.title,
        "summary": r.summary,
        "timeline": r.timeline,
        "response_actions": r.response_actions,
        "resources_deployed": r.resources_deployed,
        "response_time_minutes": r.response_time_minutes,
        "evacuation_time_minutes": r.evacuation_time_minutes,
        "warning_lead_time_minutes": r.warning_lead_time_minutes,
        "prediction_accuracy": r.prediction_accuracy,
        "lessons_learned": r.lessons_learned,
        "recommendations": r.recommendations,
        "follow_up_actions": r.follow_up_actions,
        "ra10121_compliant": r.ra10121_compliant,
        "submitted_to_ndrrmc": r.submitted_to_ndrrmc,
        "submitted_to_dilg": r.submitted_to_dilg,
        "prepared_by": r.prepared_by,
        "reviewed_by": r.reviewed_by,
        "approved_by": r.approved_by,
        "status": r.status,
        "created_at": _isoformat(r.created_at),
        "updated_at": _isoformat(r.updated_at),
    }
