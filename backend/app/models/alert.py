"""AlertHistory ORM model."""

from datetime import datetime, timezone

from app.models.db import Base
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship


class AlertHistory(Base):
    """Alert delivery history and tracking."""

    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id", ondelete="CASCADE"), index=True)

    # Alert details
    risk_level = Column(Integer, nullable=False)
    risk_label = Column(String(50), nullable=False)
    location = Column(String(255), info={"description": "Location name"})
    recipients = Column(Text, info={"description": "JSON array of recipients"})
    message = Column(Text, info={"description": "Alert message content"})

    # Delivery tracking
    delivery_status = Column(String(50), info={"description": "delivered/failed/pending/partial/sandbox"})
    delivery_channel = Column(
        String(255),
        info={"description": "web/sms/email/slack/firebase_push/messenger/telegram/siren (comma-separated)"},
    )
    error_message = Column(Text, info={"description": "Error details if delivery failed"})

    # Smart Alert fields
    confidence_score = Column(Float, info={"description": "Composite confidence score 0-1 (model + data quality)"})
    rainfall_3h = Column(Float, info={"description": "Rolling 3-hour rainfall accumulation in mm"})
    escalation_state = Column(
        String(50),
        default="initial",
        info={"description": "Alert lifecycle: initial / escalated / auto_escalated / suppressed"},
    )
    escalation_reason = Column(
        String(255), nullable=True, info={"description": "Reason for escalation (e.g. persisted_30min)"}
    )
    suppressed = Column(
        Boolean,
        default=False,
        nullable=False,
        info={"description": "True if alert was suppressed by false-alarm reduction"},
    )
    contributing_factors = Column(
        Text, nullable=True, info={"description": "JSON array of contributing factor strings"}
    )

    # Acknowledgement tracking
    acknowledged = Column(
        Boolean,
        default=False,
        nullable=False,
        info={"description": "Whether the alert has been acknowledged by an operator"},
    )
    acknowledged_at = Column(
        DateTime(timezone=True), nullable=True, info={"description": "When the alert was acknowledged"}
    )

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    delivered_at = Column(DateTime, info={"description": "Actual delivery timestamp"})

    # Relationships
    prediction = relationship("Prediction", back_populates="alerts")

    # Soft delete support
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_alert_risk", "risk_level"),
        Index("idx_alert_status", "delivery_status"),
        Index("idx_alert_active", "is_deleted"),
        Index("idx_alert_active_created", "is_deleted", "created_at"),
        Index("idx_alert_status_created", "delivery_status", "created_at"),
        Index("idx_alert_risk_status", "risk_level", "delivery_status"),
        Index("idx_alert_acknowledged", "acknowledged"),
        {"comment": "Alert delivery tracking and history"},
    )

    def __repr__(self):
        return f"<AlertHistory(id={self.id}, risk={self.risk_label}, status={self.delivery_status})>"

    def soft_delete(self):
        """Mark record as deleted without removing from database."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self):
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None
