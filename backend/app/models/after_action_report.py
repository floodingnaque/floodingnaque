"""AfterActionReport ORM model - Post-incident review documentation.

Part of the RA 10121–compliant LGU workflow. Each closed incident
can have one or more after-action reports that document timeline,
response effectiveness, lessons learned, and recommendations.
"""

from datetime import datetime, timezone

from app.models.db import Base
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship


class AfterActionReport(Base):
    """Post-incident after-action report filed by LGU/MDRRMO."""

    __tablename__ = "after_action_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)

    # ── Report content ───────────────────────────────────────────────────
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False, info={"description": "Executive summary of incident response"})

    # Timeline breakdown (stored as text blocks)
    timeline = Column(Text, nullable=True, info={"description": "Chronological event timeline (markdown / plain text)"})
    response_actions = Column(Text, nullable=True, info={"description": "Actions taken during the incident"})
    resources_deployed = Column(Text, nullable=True, info={"description": "Personnel, equipment, and supplies used"})

    # ── Effectiveness metrics ────────────────────────────────────────────
    response_time_minutes = Column(Integer, nullable=True, info={"description": "Minutes from alert to first response"})
    evacuation_time_minutes = Column(Integer, nullable=True, info={"description": "Minutes to complete evacuation"})
    warning_lead_time_minutes = Column(
        Integer, nullable=True, info={"description": "Minutes between warning and event onset"}
    )
    prediction_accuracy = Column(
        Float, nullable=True, info={"description": "0-1 score of model prediction accuracy for this event"}
    )

    # ── Lessons & recommendations ────────────────────────────────────────
    lessons_learned = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)
    follow_up_actions = Column(Text, nullable=True, info={"description": "Action items for future preparedness"})

    # ── Compliance ───────────────────────────────────────────────────────
    ra10121_compliant = Column(
        Boolean, default=True, nullable=False, info={"description": "Follows RA 10121 reporting requirements"}
    )
    submitted_to_ndrrmc = Column(
        Boolean, default=False, nullable=False, info={"description": "Report forwarded to NDRRMC"}
    )
    submitted_to_dilg = Column(Boolean, default=False, nullable=False, info={"description": "Report forwarded to DILG"})

    # ── Metadata ─────────────────────────────────────────────────────────
    prepared_by = Column(String(100), nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    approved_by = Column(String(100), nullable=True)
    status = Column(
        String(30),
        nullable=False,
        default="draft",
        info={"description": "draft / submitted / reviewed / approved"},
    )

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Soft delete ──────────────────────────────────────────────────────
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # ── Relationships ────────────────────────────────────────────────────
    incident = relationship("Incident", back_populates="after_action_reports")

    __table_args__ = (
        Index("idx_aar_incident", "incident_id"),
        Index("idx_aar_status", "status"),
        Index("idx_aar_active", "is_deleted", "created_at"),
        {"comment": "After-action reports per RA 10121 compliance"},
    )

    def __repr__(self) -> str:
        return f"<AfterActionReport(id={self.id}, incident={self.incident_id}, status={self.status})>"

    def soft_delete(self) -> None:
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        self.is_deleted = False
        self.deleted_at = None
