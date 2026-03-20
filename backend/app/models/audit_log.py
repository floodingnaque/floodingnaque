"""AuditLog ORM model.

Stores security-relevant audit trail events.
"""

from datetime import datetime, timezone

from app.models.db import Base
from sqlalchemy import Column, DateTime, Index, Integer, String, Text


class AuditLog(Base):
    """Security audit log entry."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(80), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default="info", index=True)

    # Actor
    user_id = Column(Integer, nullable=True, index=True)
    user_email = Column(String(255), nullable=True)

    # Target (e.g. a different user whose role was changed)
    target_user_id = Column(Integer, nullable=True)

    # Request context
    ip_address = Column(String(45), nullable=True, index=True)
    user_agent = Column(String(500), nullable=True)
    request_id = Column(String(36), nullable=True)

    # Freeform JSON details
    details = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index("idx_audit_action_created", "action", "created_at"),
        Index("idx_audit_severity_created", "severity", "created_at"),
        Index("idx_audit_user_created", "user_id", "created_at"),
        {"comment": "Security audit trail"},
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, user={self.user_email})>"

    def to_dict(self) -> dict:
        import json

        return {
            "id": self.id,
            "action": self.action,
            "severity": self.severity,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "target_user_id": self.target_user_id,
            "ip_address": self.ip_address,
            "request_id": self.request_id,
            "details": json.loads(str(self.details)) if self.details is not None else None,
            "created_at": self.created_at.isoformat() if self.created_at is not None else None,
        }
