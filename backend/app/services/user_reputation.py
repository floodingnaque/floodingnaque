"""User Reputation Service.

Computes per-user trust scores based on their community report track record.
Integrates with the credibility_service to provide a user-level signal.

Score formula (all weights sum to 1.0):
    - Report accuracy ratio    (40 %): accepted / total reports
    - Account age factor       (20 %): min(days_since_signup / 180, 1.0)
    - Credibility trend        (25 %): avg credibility of last 20 reports
    - Consistency bonus        (15 %): 1 - std_dev of last 20 cred scores (reward steady quality)
"""

import logging
import math
from datetime import datetime, timezone

from app.models.community_report import CommunityReport
from app.models.db import User, get_db_session
from sqlalchemy import desc

logger = logging.getLogger(__name__)

# Weights (must sum to 1.0)
_W_ACCURACY = 0.40
_W_ACCOUNT_AGE = 0.20
_W_CRED_TREND = 0.25
_W_CONSISTENCY = 0.15

ACCOUNT_AGE_CAP_DAYS = 180
MIN_REPORTS_FOR_SCORE = 1


def recalculate_reputation(user_id: int) -> float | None:
    """Recompute and persist the reputation score for *user_id*.

    Returns the new score or ``None`` if the user is not found.
    """
    with get_db_session() as session:
        user = session.query(User).filter(User.id == user_id, User.is_deleted.is_(False)).first()
        if not user:
            return None

        # Pull the user's reports (most recent first)
        reports = (
            session.query(CommunityReport)
            .filter(CommunityReport.user_id == user_id, CommunityReport.is_deleted.is_(False))
            .order_by(desc(CommunityReport.created_at))
            .all()
        )

        total = len(reports)
        accepted = sum(1 for r in reports if r.status == "accepted")
        rejected = sum(1 for r in reports if r.status == "rejected")

        # 1. Accuracy ratio
        accuracy = accepted / total if total > 0 else 0.5  # neutral if no reports

        # 2. Account age factor
        if user.created_at:
            created = user.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - created).days
        else:
            age_days = 0
        age_factor = min(age_days / ACCOUNT_AGE_CAP_DAYS, 1.0)

        # 3. Credibility trend (avg of last 20 reports)
        recent = reports[:20]
        cred_scores = [r.credibility_score for r in recent if r.credibility_score is not None]
        cred_trend = sum(cred_scores) / len(cred_scores) if cred_scores else 0.5

        # 4. Consistency bonus (low std dev = high consistency → score near 1)
        if len(cred_scores) >= 2:
            mean = cred_trend
            variance = sum((s - mean) ** 2 for s in cred_scores) / len(cred_scores)
            std_dev = math.sqrt(variance)
            consistency = max(1.0 - std_dev, 0.0)
        else:
            consistency = 0.5

        score = round(
            _W_ACCURACY * accuracy
            + _W_ACCOUNT_AGE * age_factor
            + _W_CRED_TREND * cred_trend
            + _W_CONSISTENCY * consistency,
            4,
        )
        score = max(0.0, min(score, 1.0))

        # Persist
        user.reputation_score = score
        user.total_reports = total
        user.accepted_reports = accepted
        user.rejected_reports = rejected
        user.reputation_updated_at = datetime.now(timezone.utc)

        logger.info(
            "User %d reputation updated: %.4f (accuracy=%.2f age=%.2f trend=%.2f consist=%.2f, reports=%d)",
            user_id,
            score,
            accuracy,
            age_factor,
            cred_trend,
            consistency,
            total,
        )
        return score


def get_reputation(user_id: int) -> dict | None:
    """Return the current reputation snapshot for *user_id*."""
    with get_db_session() as session:
        user = session.query(User).filter(User.id == user_id, User.is_deleted.is_(False)).first()
        if not user:
            return None

        return {
            "user_id": user.id,
            "reputation_score": user.reputation_score,
            "total_reports": user.total_reports,
            "accepted_reports": user.accepted_reports,
            "rejected_reports": user.rejected_reports,
            "reputation_updated_at": (
                user.reputation_updated_at.isoformat() if user.reputation_updated_at else None
            ),
            "account_age_days": (
                (datetime.now(timezone.utc) - user.created_at.replace(tzinfo=timezone.utc)).days
                if user.created_at
                else 0
            ),
        }


def get_leaderboard(limit: int = 20) -> list[dict]:
    """Return top *limit* users by reputation score."""
    with get_db_session() as session:
        users = (
            session.query(User)
            .filter(User.is_deleted.is_(False), User.is_active.is_(True), User.total_reports >= MIN_REPORTS_FOR_SCORE)
            .order_by(desc(User.reputation_score))
            .limit(min(limit, 100))
            .all()
        )

        return [
            {
                "user_id": u.id,
                "full_name": u.full_name or "Anonymous",
                "reputation_score": u.reputation_score,
                "total_reports": u.total_reports,
                "accepted_reports": u.accepted_reports,
            }
            for u in users
        ]
