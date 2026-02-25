"""AlertHistory ORM model."""

from datetime import datetime, timezone

from app.models.db import Base
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
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
    delivery_status = Column(String(50), info={"description": "delivered/failed/pending"})
    delivery_channel = Column(String(50), info={"description": "web/sms/email"})
    error_message = Column(Text, info={"description": "Error details if delivery failed"})

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
