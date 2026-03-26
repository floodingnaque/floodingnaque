"""EvacuationAlertLog ORM model - immutable audit trail for SMS/push alerts.

Each row records a single alert dispatch attempt.  Rows are never
soft-deleted - this table is an append-only audit log.
"""

from datetime import datetime, timezone
from typing import cast

from app.models.db import Base
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text


class EvacuationAlertLog(Base):
    """Immutable log entry for evacuation alert dispatches."""

    __tablename__ = "evacuation_alert_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── References ───────────────────────────────────────────────────────
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        info={"description": "Recipient user (NULL if number-only)"},
    )
    center_id = Column(
        Integer,
        ForeignKey("evacuation_centers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        info={"description": "Recommended evacuation center"},
    )

    # ── Dispatch details ─────────────────────────────────────────────────
    sms_status = Column(
        String(20),
        nullable=False,
        default="pending",
        info={"description": "sent / failed / pending / simulated"},
    )
    channel = Column(
        String(20),
        nullable=False,
        default="sms",
        info={"description": "sms / push / in-app"},
    )

    # ── Context ──────────────────────────────────────────────────────────
    barangay = Column(String(100), nullable=True, info={"description": "Target barangay"})
    risk_label = Column(String(10), nullable=True, info={"description": "Safe / Alert / Critical"})
    message_text = Column(Text, nullable=True, info={"description": "Full message body"})

    # ── Timestamp (audit logs are immutable - created_at only) ───────────
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index("idx_alert_log_barangay", "barangay"),
        Index("idx_alert_log_status", "sms_status"),
        Index("idx_alert_log_created", "created_at"),
        {"comment": "Immutable audit trail for evacuation alert dispatches"},
    )

    def __repr__(self) -> str:
        return (
            f"<EvacuationAlertLog(id={self.id}, channel='{self.channel}', "
            f"status='{self.sms_status}', barangay='{self.barangay}')>"
        )

    def to_dict(self) -> dict:
        """Serialize for JSON responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "center_id": self.center_id,
            "sms_status": self.sms_status,
            "channel": self.channel,
            "barangay": self.barangay,
            "risk_label": self.risk_label,
            "message_text": self.message_text,
            "created_at": cast(datetime, self.created_at).isoformat() if self.created_at is not None else None,
        }
