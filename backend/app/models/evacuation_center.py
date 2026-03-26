"""EvacuationCenter ORM model - evacuation facility tracking.

Stores designated evacuation centers in Parañaque City with real-time
capacity tracking for the evacuation assistance module.
"""

from datetime import datetime, timezone
from typing import cast

from app.models.db import Base
from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String, Text


class EvacuationCenter(Base):
    """A designated evacuation facility with capacity tracking."""

    __tablename__ = "evacuation_centers"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── Identification ───────────────────────────────────────────────────
    name = Column(String(200), nullable=False, info={"description": "Facility name"})
    barangay = Column(String(100), nullable=False, info={"description": "Barangay location"})
    address = Column(Text, nullable=False, info={"description": "Full street address"})

    # ── Location ─────────────────────────────────────────────────────────
    latitude = Column(Float, nullable=False, info={"description": "WGS-84 latitude"})
    longitude = Column(Float, nullable=False, info={"description": "WGS-84 longitude"})

    # ── Capacity ─────────────────────────────────────────────────────────
    capacity_total = Column(Integer, nullable=False, info={"description": "Maximum number of evacuees"})
    capacity_current = Column(Integer, default=0, nullable=False, info={"description": "Current occupancy"})

    # ── Contact ──────────────────────────────────────────────────────────
    contact_number = Column(String(20), nullable=True, info={"description": "Emergency contact number"})

    # ── Status ───────────────────────────────────────────────────────────
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # ── Timestamps ───────────────────────────────────────────────────────
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
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
        Index("idx_evac_barangay", "barangay"),
        Index("idx_evac_active", "is_active", "is_deleted"),
        Index("idx_evac_coords", "latitude", "longitude"),
        {"comment": "Designated evacuation centers in Parañaque City"},
    )

    def __repr__(self) -> str:
        return (
            f"<EvacuationCenter(id={self.id}, name='{self.name}', "
            f"barangay='{self.barangay}', occupancy={self.capacity_current}/{self.capacity_total})>"
        )

    def soft_delete(self) -> None:
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        self.is_deleted = False
        self.deleted_at = None

    @property
    def available_slots(self) -> int:
        """Remaining capacity."""
        total = cast(int, self.capacity_total)
        current = cast(int, self.capacity_current) or 0
        return max(0, total - current)

    @property
    def occupancy_pct(self) -> float:
        """Occupancy percentage (0.0–100.0)."""
        total = cast(int, self.capacity_total)
        if not total:
            return 0.0
        current = cast(int, self.capacity_current) or 0
        return round(current / total * 100, 1)

    def to_dict(self) -> dict:
        """Serialize for JSON responses."""
        return {
            "id": self.id,
            "name": self.name,
            "barangay": self.barangay,
            "address": self.address,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "capacity_total": self.capacity_total,
            "capacity_current": self.capacity_current,
            "available_slots": self.available_slots,
            "occupancy_pct": self.occupancy_pct,
            "contact_number": self.contact_number,
            "is_active": self.is_active,
            "created_at": cast(datetime, self.created_at).isoformat() if self.created_at is not None else None,
            "updated_at": cast(datetime, self.updated_at).isoformat() if self.updated_at is not None else None,
        }
