"""Incident ORM model — LGU flood incident tracking.

Supports the official alert → LGU confirmation → public broadcast
workflow required by RA 10121 and local DRRM protocols.
"""

from datetime import datetime, timezone
from typing import cast

from app.models.db import Base
from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import relationship


class Incident(Base):
    """A confirmed or pending flood incident logged by LGU/MDRRMO staff."""

    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── Classification ───────────────────────────────────────────────────
    title = Column(String(255), nullable=False, info={"description": "Short incident title"})
    description = Column(Text, nullable=True, info={"description": "Detailed description of the incident"})
    incident_type = Column(
        String(50),
        nullable=False,
        default="flood",
        info={"description": "flood / storm_surge / landslide / flash_flood"},
    )
    risk_level = Column(Integer, nullable=False, default=1, info={"description": "0=Safe, 1=Alert, 2=Critical"})

    # ── Location ─────────────────────────────────────────────────────────
    barangay = Column(String(100), nullable=False, info={"description": "Affected barangay"})
    location_detail = Column(String(255), nullable=True, info={"description": "Street / zone / purok detail"})
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # ── LGU Workflow Pipeline ────────────────────────────────────────────
    status = Column(
        String(30),
        nullable=False,
        default="alert_raised",
        info={"description": "alert_raised → lgu_confirmed → broadcast_sent → resolved → closed"},
    )
    confirmed_by = Column(String(100), nullable=True, info={"description": "Name or user-id of LGU officer who confirmed"})
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    broadcast_sent_at = Column(DateTime(timezone=True), nullable=True)
    broadcast_channels = Column(
        String(255),
        nullable=True,
        info={"description": "Comma-separated: sms, siren, social_media, radio, megaphone"},
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(100), nullable=True)

    # ── Impact ───────────────────────────────────────────────────────────
    affected_families = Column(Integer, nullable=True, default=0)
    evacuated_families = Column(Integer, nullable=True, default=0)
    casualties = Column(Integer, nullable=True, default=0)
    estimated_damage = Column(Float, nullable=True, info={"description": "Estimated damage in PHP"})

    # ── Source ───────────────────────────────────────────────────────────
    source = Column(
        String(50),
        nullable=False,
        default="manual",
        info={"description": "manual / system_alert / barangay_report / pagasa"},
    )
    related_alert_id = Column(Integer, nullable=True, index=True, info={"description": "FK-like ref to alert_history.id"})

    # ── Metadata ─────────────────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    created_by = Column(String(100), nullable=True)

    # ── Soft delete ──────────────────────────────────────────────────────
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    after_action_reports = relationship("AfterActionReport", back_populates="incident", lazy="select")

    __table_args__ = (
        Index("idx_incident_status", "status"),
        Index("idx_incident_risk", "risk_level"),
        Index("idx_incident_barangay", "barangay"),
        Index("idx_incident_active", "is_deleted", "created_at"),
        Index("idx_incident_status_risk", "status", "risk_level"),
        {"comment": "LGU flood incident tracking (RA 10121 compliant)"},
    )

    def __repr__(self) -> str:
        return f"<Incident(id={self.id}, title='{self.title}', status={self.status}, risk={self.risk_level})>"

    # ── Workflow transitions ─────────────────────────────────────────────
    VALID_TRANSITIONS = {
        "alert_raised": ["lgu_confirmed"],
        "lgu_confirmed": ["broadcast_sent"],
        "broadcast_sent": ["resolved"],
        "resolved": ["closed"],
    }

    def can_transition_to(self, next_status: str) -> bool:
        """Check if a status transition is valid under the LGU workflow."""
        current = cast(str, self.status)
        return next_status in self.VALID_TRANSITIONS.get(current, [])

    def transition_to(self, next_status: str, actor: str | None = None) -> None:
        """Advance the incident through the LGU workflow pipeline."""
        if not self.can_transition_to(next_status):
            current = cast(str, self.status)
            raise ValueError(
                f"Cannot transition from '{current}' to '{next_status}'. "
                f"Valid: {self.VALID_TRANSITIONS.get(current, [])}"
            )
        now = datetime.now(timezone.utc)
        self.status = next_status
        self.updated_at = now
        if next_status == "lgu_confirmed":
            self.confirmed_at = now
            self.confirmed_by = actor
        elif next_status == "broadcast_sent":
            self.broadcast_sent_at = now
        elif next_status == "resolved":
            self.resolved_at = now
            self.resolved_by = actor

    def soft_delete(self) -> None:
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        self.is_deleted = False
        self.deleted_at = None
