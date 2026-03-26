"""Broadcast ORM model - LGU public warning broadcasts.

Stores records of mass notifications sent to residents during
flood incidents. Part of the RA 10121–compliant LGU workflow
(alert_raised → lgu_confirmed → **broadcast_sent** → resolved → closed).
"""

from datetime import datetime, timezone

from app.models.db import Base
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY


class Broadcast(Base):
    """A public broadcast/notification sent during a flood incident."""

    __tablename__ = "broadcasts"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── Content ──────────────────────────────────────────────────────────
    title = Column(String(255), nullable=True, info={"description": "Broadcast title / headline"})
    message = Column(Text, nullable=False, info={"description": "The broadcast message body"})
    priority = Column(
        String(20),
        nullable=False,
        default="normal",
        info={"description": "low / normal / high / critical"},
    )

    # ── Targeting ────────────────────────────────────────────────────────
    target_barangays = Column(
        Text,
        nullable=False,
        info={"description": "Comma-separated barangay names targeted by this broadcast"},
    )
    channels = Column(
        Text,
        nullable=False,
        info={"description": "Comma-separated delivery channels: sms, siren, social_media, push, email"},
    )

    # ── Delivery ─────────────────────────────────────────────────────────
    recipients = Column(Integer, nullable=True, default=0, info={"description": "Number of recipients reached"})
    sent_by = Column(String(100), nullable=True, info={"description": "Username or ID of the sender"})

    # ── Linked incident (optional) ───────────────────────────────────────
    incident_id = Column(Integer, nullable=True, index=True, info={"description": "FK-like ref to incidents.id"})

    # ── Metadata ─────────────────────────────────────────────────────────
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    # ── Soft delete ──────────────────────────────────────────────────────
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Broadcast(id={self.id}, priority='{self.priority}', recipients={self.recipients})>"

    def soft_delete(self) -> None:
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        self.is_deleted = False
        self.deleted_at = None
