"""CommunityReport ORM model — crowdsourced flood reporting.

Allows residents to submit geolocated flood observations with optional
photo evidence.  Reports accumulate community votes (confirm/dispute)
and are scored by the credibility service for automatic verification.
"""

from datetime import datetime, timezone
from typing import cast

from app.models.db import Base
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship


class CommunityReport(Base):
    """A user-submitted flood observation with credibility scoring."""

    __tablename__ = "community_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── Reporter ─────────────────────────────────────────────────────────
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        info={"description": "FK to users.id — NULL for anonymous reports"},
    )
    user = relationship("User", foreign_keys=[user_id], lazy="select")

    # ── Location ─────────────────────────────────────────────────────────
    latitude = Column(Float, nullable=False, info={"description": "WGS-84 latitude"})
    longitude = Column(Float, nullable=False, info={"description": "WGS-84 longitude"})
    barangay = Column(
        String(100),
        nullable=True,
        info={"description": "Reverse-geocoded barangay name"},
    )

    # ── Observation ──────────────────────────────────────────────────────
    flood_height_cm = Column(Integer, nullable=True, info={"description": "Estimated flood height in cm"})
    description = Column(Text, nullable=True, info={"description": "Max 280 characters"})
    specific_location = Column(String(200), nullable=True, info={"description": "Landmark or street name"})
    contact_number = Column(String(20), nullable=True, info={"description": "Optional contact number"})
    photo_url = Column(Text, nullable=True, info={"description": "Supabase Storage path or local URL"})
    risk_label = Column(
        String(10),
        nullable=False,
        default="Alert",
        info={"description": "Safe / Alert / Critical"},
    )

    # ── Credibility ──────────────────────────────────────────────────────
    credibility_score = Column(Float, default=0.5, nullable=False, info={"description": "0.0–1.0 weighted score"})
    verified = Column(Boolean, default=False, nullable=False, info={"description": "Auto- or admin-verified"})
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        info={"description": "pending / accepted / rejected"},
    )
    confirmation_count = Column(Integer, default=0, nullable=False)
    dispute_count = Column(Integer, default=0, nullable=False)
    abuse_flag_count = Column(Integer, default=0, nullable=False)

    # ── Verification audit trail ─────────────────────────────────────────
    verified_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        info={"description": "User ID of admin who verified/rejected"},
    )
    verified_at = Column(DateTime(timezone=True), nullable=True, info={"description": "Timestamp of verification"})
    verifier = relationship("User", foreign_keys="CommunityReport.verified_by", lazy="select")

    # ── Timestamps ───────────────────────────────────────────────────────
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Soft delete ──────────────────────────────────────────────────────
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_report_created_desc", created_at.desc()),
        Index("idx_report_barangay", "barangay"),
        Index("idx_report_status", "status"),
        Index("idx_report_coords", "latitude", "longitude"),
        {"comment": "Crowdsourced flood reports from community members"},
    )

    def __repr__(self) -> str:
        return (
            f"<CommunityReport(id={self.id}, barangay='{self.barangay}', "
            f"risk={self.risk_label}, score={self.credibility_score:.2f})>"
        )

    def soft_delete(self) -> None:
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        self.is_deleted = False
        self.deleted_at = None

    def to_dict(self) -> dict:
        """Serialize for JSON responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "barangay": self.barangay,
            "flood_height_cm": self.flood_height_cm,
            "description": self.description,
            "specific_location": self.specific_location,
            "contact_number": self.contact_number,
            "photo_url": self.photo_url,
            "risk_label": self.risk_label,
            "credibility_score": round(cast(float, self.credibility_score), 3) if self.credibility_score is not None else None,
            "verified": self.verified,
            "status": self.status,
            "confirmation_count": self.confirmation_count,
            "dispute_count": self.dispute_count,
            "abuse_flag_count": self.abuse_flag_count,
            "verified_by": self.verified_by,
            "verified_at": cast(datetime, self.verified_at).isoformat() if self.verified_at is not None else None,
            "created_at": cast(datetime, self.created_at).isoformat() if self.created_at is not None else None,
            "updated_at": cast(datetime, self.updated_at).isoformat() if self.updated_at is not None else None,
        }
