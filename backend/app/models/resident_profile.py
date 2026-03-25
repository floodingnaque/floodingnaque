"""Resident profile ORM model.

Stores extended registration data collected during LGU resident onboarding
(personal, household, address, notification preferences, consent).  Each
profile has a 1:1 relationship with a ``User`` row.
"""

from datetime import datetime, timezone

from app.models.db import Base
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import relationship


class ResidentProfile(Base):
    """Extended profile for residents registered via the onboarding wizard."""

    __tablename__ = "resident_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # ── Personal information ──────────────────────────────────────────
    date_of_birth = Column(Date, nullable=True)
    sex = Column(String(30), nullable=True)
    civil_status = Column(String(30), nullable=True)
    contact_number = Column(String(50), nullable=True)
    alt_contact_number = Column(String(50), nullable=True)
    alt_contact_name = Column(String(255), nullable=True)
    alt_contact_relationship = Column(String(100), nullable=True)
    is_pwd = Column(Boolean, default=False)
    is_senior_citizen = Column(Boolean, default=False)

    # ── Household information ─────────────────────────────────────────
    household_members = Column(Integer, nullable=True)
    children_count = Column(Integer, default=0)
    senior_count = Column(Integer, default=0)
    pwd_count = Column(Integer, default=0)

    # ── Address & location ────────────────────────────────────────────
    barangay = Column(String(100), nullable=True, index=True)
    purok = Column(String(100), nullable=True)
    street_address = Column(String(500), nullable=True)
    nearest_landmark = Column(String(255), nullable=True)
    home_type = Column(String(50), nullable=True)
    floor_level = Column(String(50), nullable=True)

    # ── Flood history ─────────────────────────────────────────────────
    has_flood_experience = Column(Boolean, default=False)
    most_recent_flood_year = Column(Integer, nullable=True)

    # ── Notification preferences ──────────────────────────────────────
    sms_alerts = Column(Boolean, default=True)
    email_alerts = Column(Boolean, default=True)
    push_notifications = Column(Boolean, default=False)
    preferred_language = Column(String(30), default="Filipino")

    # ── Consent ───────────────────────────────────────────────────────
    data_privacy_consent = Column(Boolean, default=False, nullable=False)

    # ── Timestamps ────────────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationship ──────────────────────────────────────────────────
    user = relationship("User", backref="resident_profile", uselist=False, lazy="joined")

    __table_args__ = (
        CheckConstraint(
            "sex IN ('Male', 'Female', 'Prefer not to say')",
            name="valid_sex",
        ),
        CheckConstraint(
            "civil_status IN ('Single', 'Married', 'Widowed', 'Separated')",
            name="valid_civil_status",
        ),
        CheckConstraint(
            "home_type IN ('Concrete', 'Semi-Concrete', 'Wood', 'Makeshift')",
            name="valid_home_type",
        ),
        CheckConstraint(
            "floor_level IN ('Ground Floor', '2nd Floor', '3rd Floor or higher')",
            name="valid_floor_level",
        ),
        CheckConstraint(
            "preferred_language IN ('Filipino', 'English')",
            name="valid_language",
        ),
        Index("idx_resident_barangay", "barangay"),
        {"comment": "Extended profile data for registered residents"},
    )

    def __repr__(self):
        return f"<ResidentProfile(id={self.id}, user_id={self.user_id}, barangay={self.barangay})>"

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth is not None else None,
            "sex": self.sex,
            "civil_status": self.civil_status,
            "contact_number": self.contact_number,
            "alt_contact_number": self.alt_contact_number,
            "alt_contact_name": self.alt_contact_name,
            "alt_contact_relationship": self.alt_contact_relationship,
            "is_pwd": self.is_pwd,
            "is_senior_citizen": self.is_senior_citizen,
            "household_members": self.household_members,
            "children_count": self.children_count,
            "senior_count": self.senior_count,
            "pwd_count": self.pwd_count,
            "barangay": self.barangay,
            "purok": self.purok,
            "street_address": self.street_address,
            "nearest_landmark": self.nearest_landmark,
            "home_type": self.home_type,
            "floor_level": self.floor_level,
            "has_flood_experience": self.has_flood_experience,
            "most_recent_flood_year": self.most_recent_flood_year,
            "sms_alerts": self.sms_alerts,
            "email_alerts": self.email_alerts,
            "push_notifications": self.push_notifications,
            "preferred_language": self.preferred_language,
            "data_privacy_consent": self.data_privacy_consent,
            "created_at": self.created_at.isoformat() if self.created_at is not None else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at is not None else None,
        }
