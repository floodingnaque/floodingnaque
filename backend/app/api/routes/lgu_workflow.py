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
from app.models.broadcast import Broadcast
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

            return (
                jsonify(
                    {
                        "success": True,
                        "data": [_serialize_incident(i) for i in incidents],
                        "pagination": {"total": total, "limit": limit, "offset": offset},
                        "request_id": request_id,
                    }
                ),
                HTTP_OK,
            )

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
            "title",
            "description",
            "incident_type",
            "risk_level",
            "barangay",
            "location_detail",
            "latitude",
            "longitude",
            "affected_families",
            "evacuated_families",
            "casualties",
            "estimated_damage",
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
                s: func.count(case((Incident.status == s, 1))) for s in status_list  # type: ignore[arg-type]
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
                rl: func.count(case((Incident.risk_level == rl, 1))) for rl in risk_levels  # type: ignore[arg-type]
            }
            risk_row = (
                session.query(*risk_cols.values())
                .filter(Incident.is_deleted.is_(False))  # type: ignore[union-attr]
                .one()
            )
            by_risk_level = {str(rl): cnt for rl, cnt in zip(risk_levels, risk_row)}

            # total_active = everything except resolved and closed
            total_active = sum(cnt for s, cnt in by_status.items() if s not in ("resolved", "closed"))

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
            # ── Query 1: All incident aggregates in a single query ───────
            # (was 7 separate COUNT + 3 AVG queries)
            stall_threshold = datetime.now(timezone.utc).timestamp() - 86400

            incident_agg = (
                session.query(
                    func.count(Incident.id).label("total"),
                    func.count(
                        case((Incident.status.in_(["resolved", "closed"]), Incident.id))
                    ).label("resolved_count"),
                    func.count(
                        case((Incident.status == "closed", Incident.id))
                    ).label("closed_count"),
                    func.count(
                        case(
                            (
                                Incident.status.in_(["resolved", "closed"])
                                & (Incident.affected_families == 0)
                                & (Incident.casualties == 0),
                                Incident.id,
                            )
                        )
                    ).label("false_alarms"),
                    func.count(
                        case(
                            (
                                Incident.status.in_(["alert_raised", "lgu_confirmed"])
                                & (extract("epoch", Incident.created_at) < stall_threshold),
                                Incident.id,
                            )
                        )
                    ).label("stalled"),
                    func.avg(
                        case(
                            (
                                Incident.confirmed_at.isnot(None),
                                extract("epoch", Incident.confirmed_at) - extract("epoch", Incident.created_at),
                            )
                        )
                    ).label("avg_confirm"),
                    func.avg(
                        case(
                            (
                                Incident.broadcast_sent_at.isnot(None) & Incident.confirmed_at.isnot(None),
                                extract("epoch", Incident.broadcast_sent_at) - extract("epoch", Incident.confirmed_at),
                            )
                        )
                    ).label("avg_broadcast"),
                    func.avg(
                        case(
                            (
                                Incident.resolved_at.isnot(None),
                                extract("epoch", Incident.resolved_at) - extract("epoch", Incident.created_at),
                            )
                        )
                    ).label("avg_resolve"),
                )
                .filter(Incident.is_deleted.is_(False))
                .one()
            )

            total = incident_agg.total or 0
            resolved_count = incident_agg.resolved_count or 0
            closed_count = incident_agg.closed_count or 0
            false_alarms = incident_agg.false_alarms or 0
            false_alarm_rate = (false_alarms / resolved_count) if resolved_count > 0 else 0

            # ── Query 2: AAR aggregates in a single query ────────────────
            # (was 3 separate COUNT queries)
            aar_agg = (
                session.query(
                    func.count(AfterActionReport.id).label("total_aars"),
                    func.count(
                        case((AfterActionReport.status == "approved", AfterActionReport.id))
                    ).label("approved_aars"),
                    func.count(
                        case((AfterActionReport.ra10121_compliant.is_(True), AfterActionReport.id))
                    ).label("compliant_aars"),
                )
                .filter(AfterActionReport.is_deleted.is_(False))
                .one()
            )

            total_aars = aar_agg.total_aars or 0
            approved_aars = aar_agg.approved_aars or 0
            compliant_aars = aar_agg.compliant_aars or 0
            aar_completion_rate = (total_aars / closed_count) if closed_count > 0 else 0

            # ── Query 3: Monthly frequency (already efficient) ───────────
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
            monthly_frequency = [{"year": int(r.year), "month": int(r.month), "count": r.count} for r in monthly]

            analytics = {
                "avg_confirm_minutes": round(incident_agg.avg_confirm / 60, 1) if incident_agg.avg_confirm else None,
                "avg_broadcast_minutes": round(incident_agg.avg_broadcast / 60, 1) if incident_agg.avg_broadcast else None,
                "avg_resolve_minutes": round(incident_agg.avg_resolve / 60, 1) if incident_agg.avg_resolve else None,
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
                "stalled_incidents": incident_agg.stalled or 0,
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
            return (
                jsonify(
                    {
                        "success": True,
                        "data": [_serialize_aar(r) for r in reports],
                        "request_id": request_id,
                    }
                ),
                HTTP_OK,
            )
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
            "title",
            "summary",
            "timeline",
            "response_actions",
            "resources_deployed",
            "response_time_minutes",
            "evacuation_time_minutes",
            "warning_lead_time_minutes",
            "prediction_accuracy",
            "lessons_learned",
            "recommendations",
            "follow_up_actions",
            "prepared_by",
            "reviewed_by",
            "approved_by",
            "status",
            "ra10121_compliant",
            "submitted_to_ndrrmc",
            "submitted_to_dilg",
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


# ═══════════════════════════════════════════════════════════════════════════
# Advance (auto-detect next status alias for /transition)
# ═══════════════════════════════════════════════════════════════════════════


@lgu_workflow_bp.route("/incidents/<int:incident_id>/advance", methods=["POST"])
@rate_limit_with_burst("60 per hour")
@require_auth_or_api_key
def advance_incident(incident_id: int):
    """Auto-advance an incident to the next workflow stage.

    Unlike /transition, this does not require `next_status` in the body —
    it picks the single valid next state automatically.
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        data = request.get_json(force=True, silent=True) or {}

        with get_db_session() as session:
            incident = (
                session.query(Incident)
                .filter(Incident.id == incident_id, Incident.is_deleted.is_(False))  # type: ignore[union-attr]
                .first()
            )
            if not incident:
                return api_error("NotFound", f"Incident {incident_id} not found", HTTP_NOT_FOUND, request_id)

            current = cast(str, incident.status)
            valid = Incident.VALID_TRANSITIONS.get(current, [])
            if not valid:
                return api_error(
                    "InvalidTransition",
                    f"Incident is in terminal state '{current}' — cannot advance",
                    HTTP_BAD_REQUEST,
                    request_id,
                )

            next_status = valid[0]
            actor = data.get("actor")

            # Stage-specific field handling (same as transition)
            if next_status == "broadcast_sent":
                channels = data.get("broadcast_channels")
                if channels:
                    incident.broadcast_channels = channels
            if next_status == "resolved":
                for field in ("affected_families", "evacuated_families", "casualties"):
                    if field in data:
                        setattr(incident, field, int(data[field]))
                if "estimated_damage" in data and data["estimated_damage"] is not None:
                    incident.estimated_damage = float(data["estimated_damage"])

            incident.transition_to(next_status, actor=actor)
            session.flush()
            result = _serialize_incident(incident)
            session.commit()

        logger.info("Incident %d advanced to %s [%s]", incident_id, next_status, request_id)
        return jsonify({"success": True, "data": result, "request_id": request_id}), HTTP_OK

    except ValueError as e:
        return api_error("InvalidTransition", str(e), HTTP_BAD_REQUEST, request_id)
    except Exception as e:
        logger.error("advance_incident failed [%s]: %s", request_id, e, exc_info=True)
        return api_error("InternalError", "Failed to advance incident", HTTP_INTERNAL_ERROR, request_id)


# ═══════════════════════════════════════════════════════════════════════════
# Standalone After-Action Report routes (GET/POST /aar)
# ═══════════════════════════════════════════════════════════════════════════


@lgu_workflow_bp.route("/aar", methods=["GET"])
@rate_limit_with_burst("120 per hour")
@require_auth_or_api_key
def list_all_aar():
    """List all after-action reports with optional filters."""
    request_id = getattr(g, "request_id", "unknown")

    try:
        limit = min(int(request.args.get("limit", 25)), 100)
        offset = int(request.args.get("offset", 0))
        status = request.args.get("status")
        search = request.args.get("search")

        with get_db_session() as session:
            q = session.query(AfterActionReport).filter(AfterActionReport.is_deleted.is_(False))  # type: ignore[union-attr]

            if status:
                q = q.filter(AfterActionReport.status == status)
            if search:
                q = q.filter(AfterActionReport.title.ilike(f"%{search}%"))

            total = q.count()
            reports = q.order_by(AfterActionReport.created_at.desc()).offset(offset).limit(limit).all()

            return (
                jsonify(
                    {
                        "success": True,
                        "data": [_serialize_aar(r) for r in reports],
                        "pagination": {"total": total, "limit": limit, "offset": offset},
                        "request_id": request_id,
                    }
                ),
                HTTP_OK,
            )
    except Exception as e:
        logger.error("list_all_aar failed [%s]: %s", request_id, e, exc_info=True)
        return api_error("InternalError", "Failed to list reports", HTTP_INTERNAL_ERROR, request_id)


@lgu_workflow_bp.route("/aar", methods=["POST"])
@rate_limit_with_burst("30 per hour")
@validate_request_size(endpoint_name="lgu_workflow")
@require_auth_or_api_key
def create_standalone_aar():
    """Create an after-action report (incident_id in body)."""
    request_id = getattr(g, "request_id", "unknown")

    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return api_error("NoInput", "No input data provided", HTTP_BAD_REQUEST, request_id)

        title = data.get("title")
        summary = data.get("summary")
        incident_id = data.get("incident_id")
        if not title or not summary or not incident_id:
            return api_error(
                "ValidationError",
                "'title', 'summary', and 'incident_id' are required",
                HTTP_BAD_REQUEST,
                request_id,
            )

        with get_db_session() as session:
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
        logger.error("create_standalone_aar failed [%s]: %s", request_id, e, exc_info=True)
        return api_error("InternalError", "Failed to create report", HTTP_INTERNAL_ERROR, request_id)


# ═══════════════════════════════════════════════════════════════════════════
# Broadcasts CRUD
# ═══════════════════════════════════════════════════════════════════════════


@lgu_workflow_bp.route("/broadcasts", methods=["GET"])
@rate_limit_with_burst("120 per hour")
@require_auth_or_api_key
def list_broadcasts():
    """List broadcasts with optional filters."""
    request_id = getattr(g, "request_id", "unknown")

    try:
        limit = min(int(request.args.get("limit", 25)), 100)
        offset = int(request.args.get("offset", 0))
        priority = request.args.get("priority")

        with get_db_session() as session:
            q = session.query(Broadcast).filter(Broadcast.is_deleted.is_(False))  # type: ignore[union-attr]

            if priority:
                q = q.filter(Broadcast.priority == priority)

            total = q.count()
            broadcasts = q.order_by(Broadcast.created_at.desc()).offset(offset).limit(limit).all()

            return (
                jsonify(
                    {
                        "success": True,
                        "data": [_serialize_broadcast(b) for b in broadcasts],
                        "pagination": {"total": total, "limit": limit, "offset": offset},
                        "request_id": request_id,
                    }
                ),
                HTTP_OK,
            )

    except Exception as e:
        logger.error("list_broadcasts failed [%s]: %s", request_id, e, exc_info=True)
        return api_error("InternalError", "Failed to list broadcasts", HTTP_INTERNAL_ERROR, request_id)


@lgu_workflow_bp.route("/broadcasts", methods=["POST"])
@rate_limit_with_burst("30 per hour")
@validate_request_size(endpoint_name="lgu_workflow")
@require_auth_or_api_key
def create_broadcast():
    """Send a public broadcast to targeted barangays with real SMS/email dispatch."""
    request_id = getattr(g, "request_id", "unknown")

    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return api_error("NoInput", "No input data provided", HTTP_BAD_REQUEST, request_id)

        message = data.get("message")
        target_barangays = data.get("target_barangays")
        channels = data.get("channels")
        if not message or not target_barangays or not channels:
            return api_error(
                "ValidationError",
                "'message', 'target_barangays', and 'channels' are required",
                HTTP_BAD_REQUEST,
                request_id,
            )

        # Validate lists
        if isinstance(target_barangays, list):
            target_barangays_str = ",".join(target_barangays)
        else:
            target_barangays_str = str(target_barangays)

        if isinstance(channels, list):
            channels_list = channels
            channels_str = ",".join(channels)
        else:
            channels_list = [c.strip() for c in str(channels).split(",")]
            channels_str = str(channels)

        # Get sender identity from auth context
        user = getattr(g, "current_user", None)
        sent_by = getattr(user, "full_name", None) or getattr(user, "email", "system")

        # ── Dispatch to real channels ────────────────────────────────────
        from app.models.user import User

        delivery_results: dict = {}
        actual_recipients = 0

        with get_db_session() as session:
            # SMS dispatch
            if "sms" in channels_list:
                sms_users = (
                    session.query(User.phone_number)
                    .filter(
                        User.is_deleted.is_(False),
                        User.is_active.is_(True),
                        User.phone_number.isnot(None),
                        User.phone_number != "",
                    )
                    .all()
                )
                phone_numbers = [u.phone_number for u in sms_users]
                if phone_numbers:
                    from app.services.alerts import get_alert_system

                    alert_sys = get_alert_system()
                    sms_status = alert_sys._send_sms(phone_numbers, message)
                    delivery_results["sms"] = sms_status
                    if sms_status in ("delivered", "partial", "sandbox"):
                        actual_recipients += len(phone_numbers)
                    logger.info("Broadcast SMS dispatched to %d numbers: %s", len(phone_numbers), sms_status)
                else:
                    delivery_results["sms"] = "no_recipients"

            # Email dispatch
            if "email" in channels_list:
                email_users = (
                    session.query(User.email)
                    .filter(
                        User.is_deleted.is_(False),
                        User.is_active.is_(True),
                    )
                    .all()
                )
                email_addrs = [u.email for u in email_users]
                if email_addrs:
                    from app.services.alerts import get_alert_system

                    alert_sys = get_alert_system()
                    title = data.get("title", "Flood Alert Broadcast")
                    email_status = alert_sys._send_email(email_addrs, title, message)
                    delivery_results["email"] = email_status
                    if email_status in ("delivered", "partial", "sandbox"):
                        actual_recipients += len(email_addrs)
                    logger.info("Broadcast email dispatched to %d addresses: %s", len(email_addrs), email_status)
                else:
                    delivery_results["email"] = "no_recipients"

            # SSE / In-App broadcast
            if "sse" in channels_list or "web" in channels_list:
                try:
                    from app.api.routes.sse import broadcast_alert

                    sse_record = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "risk_label": data.get("priority", "normal").capitalize(),
                        "message": message,
                        "location": target_barangays_str,
                        "delivery_status": {"sse": "delivered"},
                    }
                    client_count = broadcast_alert(sse_record)
                    delivery_results["sse"] = f"delivered ({client_count} clients)"
                except Exception as sse_exc:
                    logger.warning("SSE broadcast failed: %s", sse_exc)
                    delivery_results["sse"] = "failed"

        # ── Persist broadcast record ─────────────────────────────────────
        with get_db_session() as session:
            broadcast = Broadcast(
                title=data.get("title"),
                message=message,
                priority=data.get("priority", "normal"),
                target_barangays=target_barangays_str,
                channels=channels_str,
                recipients=actual_recipients,
                sent_by=sent_by,
                incident_id=data.get("incident_id"),
            )
            session.add(broadcast)
            session.flush()
            result = _serialize_broadcast(broadcast)
            result["delivery_results"] = delivery_results
            session.commit()

        logger.info(
            "Broadcast %d sent to %s via %s — %d recipients [%s]",
            result["id"],
            target_barangays_str,
            channels_str,
            actual_recipients,
            request_id,
        )
        return (
            jsonify(
                {
                    "success": True,
                    "data": {
                        "broadcast_id": result["id"],
                        "recipients": actual_recipients,
                        "delivery_results": delivery_results,
                    },
                    "request_id": request_id,
                }
            ),
            HTTP_CREATED,
        )

    except Exception as e:
        logger.error("create_broadcast failed [%s]: %s", request_id, e, exc_info=True)
        return api_error("InternalError", "Failed to send broadcast", HTTP_INTERNAL_ERROR, request_id)


def _serialize_broadcast(b: Broadcast) -> dict:
    return {
        "id": b.id,
        "title": b.title,
        "message": b.message,
        "priority": b.priority,
        "target_barangays": b.target_barangays.split(",") if b.target_barangays else [],
        "channels": b.channels.split(",") if b.channels else [],
        "recipients": b.recipients,
        "sent_by": b.sent_by,
        "incident_id": b.incident_id,
        "sent_at": _isoformat(b.created_at),
    }
