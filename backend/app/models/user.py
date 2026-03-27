"""User ORM model."""

import hashlib
import os
from datetime import datetime, timedelta, timezone

from app.models.db import Base
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Float, Index, Integer, String


class User(Base):
    """
    User model for authentication and authorization.

    Supports JWT-based authentication with refresh tokens.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # Profile information
    full_name = Column(String(255), info={"description": "User full name"})
    phone_number = Column(String(50), info={"description": "Phone number for SMS alerts"})

    # Role-based access control
    role = Column(String(50), default="user", nullable=False, info={"description": "user/admin/operator"})

    # Account status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_verified = Column(Boolean, default=False, nullable=False, info={"description": "Email verified"})

    # Notification preferences
    sms_alerts_enabled = Column(
        Boolean, default=True, nullable=False, info={"description": "Opt-in for SMS flood alerts"}
    )
    email_alerts_enabled = Column(
        Boolean, default=True, nullable=False, info={"description": "Opt-in for email flood alerts"}
    )

    # Password reset
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)

    # Refresh token management
    refresh_token_hash = Column(String(255), nullable=True)
    refresh_token_expires = Column(DateTime(timezone=True), nullable=True)

    # Login tracking
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    # Reputation / trust scoring
    reputation_score = Column(Float, default=0.5, nullable=False, info={"description": "Aggregate trust score 0-1"})
    total_reports = Column(Integer, default=0, nullable=False)
    accepted_reports = Column(Integer, default=0, nullable=False)
    rejected_reports = Column(Integer, default=0, nullable=False)
    reputation_updated_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin', 'operator')", name="valid_user_role"),
        Index("idx_user_email_active", "email", "is_active"),
        Index("idx_user_role", "role"),
        {"comment": "User accounts for authentication and authorization"},
    )

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            # Alias expected by the frontend
            "name": self.full_name or "",
            "role": self.role,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "sms_alerts_enabled": self.sms_alerts_enabled,
            "email_alerts_enabled": self.email_alerts_enabled,
            "reputation_score": self.reputation_score,
            "total_reports": self.total_reports,
            "accepted_reports": self.accepted_reports,
            "rejected_reports": self.rejected_reports,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_sensitive:
            result["phone_number"] = self.phone_number
            result["last_login_ip"] = self.last_login_ip
        return result

    def soft_delete(self):
        """Mark user as deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        self.is_active = False

    def is_locked(self) -> bool:
        """Check if user account is locked."""
        if self.locked_until is None:
            return False
        locked_until = self.locked_until
        # SQLite returns naive datetimes even for timezone=True columns.
        # Treat any naive datetime as UTC so the comparison is always valid.
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < locked_until

    # ------------------------------------------------------------------
    # IP retention helpers (GDPR / Data Privacy Act)
    # ------------------------------------------------------------------
    IP_RETENTION_DAYS = int(os.getenv("IP_RETENTION_DAYS", "90"))

    def purge_stale_ip(self) -> bool:
        """Clear ``last_login_ip`` if it is older than the retention window.

        Returns ``True`` if the IP was purged.
        """
        if not self.last_login_ip or not self.last_login_at:
            return False

        last_login = self.last_login_at
        if last_login.tzinfo is None:
            last_login = last_login.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) - last_login > timedelta(days=self.IP_RETENTION_DAYS):
            self.last_login_ip = None
            return True
        return False

    @classmethod
    def purge_expired_ips(cls, session) -> int:
        """Bulk-purge all login IPs that exceed the retention window.

        Suitable for being called from a scheduled task / management command.
        Returns the number of rows updated.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=cls.IP_RETENTION_DAYS)
        result = (
            session.query(cls)
            .filter(
                cls.last_login_ip.isnot(None),
                cls.last_login_at < cutoff,
            )
            .update({cls.last_login_ip: None}, synchronize_session="fetch")
        )
        return result
