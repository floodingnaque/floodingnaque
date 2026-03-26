"""Credibility service - 6-signal weighted scoring for community reports.

Computes a 0–1 credibility score for each :class:`CommunityReport` and
handles automatic verification when thresholds are met.
"""

import logging
import math
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.models.community_report import CommunityReport
from app.models.db import get_db_session
from app.models.user import User
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)

# ── Scoring weights ──────────────────────────────────────────────────────
WEIGHT_ACCOUNT_AGE = 0.15
WEIGHT_PAST_ACCURACY = 0.20
WEIGHT_CORROBORATION = 0.25
WEIGHT_ML_AGREEMENT = 0.25
WEIGHT_PHOTO = 0.10
WEIGHT_DUPLICATE_PENALTY = 0.05

# ── Thresholds ───────────────────────────────────────────────────────────
_VERIFY_THRESHOLD: Optional[float] = None
_VERIFY_MIN_CONFIRMATIONS = 3


def _get_verify_threshold() -> float:
    """Lazy-load the credibility verification threshold."""
    global _VERIFY_THRESHOLD
    if _VERIFY_THRESHOLD is None:
        _VERIFY_THRESHOLD = float(os.getenv("CREDIBILITY_VERIFY_THRESHOLD", "0.750"))
    return _VERIFY_THRESHOLD


# ── Haversine helper (metres) ────────────────────────────────────────────
_R_EARTH_M = 6_371_000.0


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in metres between two points."""
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return _R_EARTH_M * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── Nearby-reports query ─────────────────────────────────────────────────


def get_reports_near(
    lat: float,
    lon: float,
    radius_m: float,
    within_hours: float,
    exclude_id: Optional[int] = None,
) -> List[CommunityReport]:
    """Return community reports within *radius_m* of (lat, lon) in the last *within_hours*.

    Uses a bounding-box SQL pre-filter + Python-side Haversine check.
    """
    # Approximate degree delta for the bounding box
    degree_delta = radius_m / 111_000.0  # ~111 km per degree at equator

    cutoff = datetime.now(timezone.utc) - timedelta(hours=within_hours)

    with get_db_session() as session:
        query = session.query(CommunityReport).filter(
            CommunityReport.is_deleted.is_(False),
            CommunityReport.created_at >= cutoff,
            CommunityReport.latitude.between(lat - degree_delta, lat + degree_delta),
            CommunityReport.longitude.between(lon - degree_delta, lon + degree_delta),
        )
        if exclude_id is not None:
            query = query.filter(CommunityReport.id != exclude_id)

        candidates = query.all()

        # Exact Haversine distance filter
        return [r for r in candidates if _haversine_m(lat, lon, r.latitude, r.longitude) <= radius_m]


# ── Core scoring function ────────────────────────────────────────────────


def score_report(report_id: int) -> float:
    """Compute the credibility score for a report and persist it.

    Returns the computed score (0.0–1.0).
    """
    with get_db_session() as session:
        report = (
            session.query(CommunityReport)
            .options(joinedload(CommunityReport.user))
            .filter(CommunityReport.id == report_id, CommunityReport.is_deleted.is_(False))
            .first()
        )
        if report is None:
            logger.warning("score_report: report %d not found", report_id)
            return 0.0

        # ── Signal 1: Reporter account age (0.15) ───────────────────────
        age_score = 0.0
        if report.user_id:
            user = report.user  # eagerly loaded, no extra query
            if user and user.created_at:
                days_old = (datetime.now(timezone.utc) - user.created_at.replace(tzinfo=timezone.utc)).days
                age_score = min(days_old / 90.0, 1.0)

        # ── Signal 2: Reporter past accuracy (0.20) ─────────────────────
        accuracy_score = 0.5  # default for anonymous
        if report.user_id:
            total = (
                session.query(CommunityReport)
                .filter(
                    CommunityReport.user_id == report.user_id,
                    CommunityReport.is_deleted.is_(False),
                    CommunityReport.id != report_id,
                )
                .count()
            )
            if total > 0:
                accepted = (
                    session.query(CommunityReport)
                    .filter(
                        CommunityReport.user_id == report.user_id,
                        CommunityReport.is_deleted.is_(False),
                        CommunityReport.status == "accepted",
                        CommunityReport.id != report_id,
                    )
                    .count()
                )
                accuracy_score = accepted / total

        # ── Signal 3: Corroboration count (0.25) ────────────────────────
        nearby = get_reports_near(
            report.latitude,
            report.longitude,
            radius_m=500,
            within_hours=1,
            exclude_id=report.id,
        )
        corroboration_score = min(len(nearby) / 5.0, 1.0)

        # ── Signal 4: ML model agreement (0.25) ─────────────────────────
        ml_score = 0.0
        try:
            from app.services.predict import predict_flood

            # Build minimal feature dict for prediction
            result = predict_flood(
                {
                    "temperature": 30.0,
                    "humidity": 80.0,
                    "precipitation": 10.0,
                    "month": datetime.now(timezone.utc).month,
                },
                return_risk_level=True,
            )
            predicted_label = result.get("risk_level", "") if isinstance(result, dict) else ""
            if predicted_label and predicted_label.lower() == (report.risk_label or "").lower():
                ml_score = 1.0
        except Exception as exc:
            logger.debug("ML model agreement check skipped: %s", exc)
            ml_score = 0.5  # neutral if unavailable

        # ── Signal 5: Photo present (0.10) ──────────────────────────────
        photo_score = 1.0 if report.photo_url else 0.0

        # ── Signal 6: Duplicate proximity penalty (0.05) ────────────────
        duplicate_penalty = 0.0
        dupl_nearby = get_reports_near(
            report.latitude,
            report.longitude,
            radius_m=200,
            within_hours=0.25,
            exclude_id=report.id,
        )
        if dupl_nearby:
            duplicate_penalty = -0.05

        # ── Weighted sum ────────────────────────────────────────────────
        raw_score = (
            WEIGHT_ACCOUNT_AGE * age_score
            + WEIGHT_PAST_ACCURACY * accuracy_score
            + WEIGHT_CORROBORATION * corroboration_score
            + WEIGHT_ML_AGREEMENT * ml_score
            + WEIGHT_PHOTO * photo_score
            + duplicate_penalty
        )
        final_score = max(0.0, min(1.0, raw_score))

        report.credibility_score = final_score
        session.add(report)

        logger.info(
            "Scored report %d: %.3f (age=%.2f acc=%.2f corr=%.2f ml=%.2f photo=%.2f dup=%.2f)",
            report_id,
            final_score,
            age_score,
            accuracy_score,
            corroboration_score,
            ml_score,
            photo_score,
            duplicate_penalty,
        )
        return final_score


def check_auto_verify(report_id: int) -> bool:
    """Auto-verify a report if credibility score and confirmation count meet thresholds.

    Returns True if the report was auto-verified.
    """
    threshold = _get_verify_threshold()

    with get_db_session() as session:
        report = (
            session.query(CommunityReport)
            .filter(CommunityReport.id == report_id, CommunityReport.is_deleted.is_(False))
            .first()
        )
        if report is None:
            return False

        if (
            report.credibility_score >= threshold
            and report.confirmation_count >= _VERIFY_MIN_CONFIRMATIONS
            and not report.verified
        ):
            report.verified = True
            report.status = "accepted"
            session.add(report)
            logger.info(
                "Auto-verified report %d (score=%.3f, confirmations=%d)",
                report_id,
                report.credibility_score,
                report.confirmation_count,
            )
            return True

    return False
