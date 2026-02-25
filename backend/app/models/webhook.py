"""Webhook ORM model."""

from datetime import datetime, timezone

from app.models.db import Base
from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text


class Webhook(Base):
    """Webhook registrations for external system notifications."""

    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(500), nullable=False)
    events = Column(Text, nullable=False)
    secret = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_triggered_at = Column(DateTime(timezone=True))
    failure_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_webhook_active", "is_active", "is_deleted"),
        {"comment": "Webhook configurations for external notifications"},
    )

    def __repr__(self):
        return f"<Webhook(id={self.id}, url={self.url}, active={self.is_active})>"
