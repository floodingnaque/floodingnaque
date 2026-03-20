"""API Key ORM model for per-user key management."""

import hashlib
import os
import secrets
from datetime import datetime, timezone
from typing import cast

from app.models.db import Base
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text


class APIKey(Base):
    """
    API Key model for per-user key management.

    Supports key rotation, expiration, revocation, and scoped access.
    The raw key is shown once at creation; only a SHA-256 hash is stored.
    """

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Key identification
    name = Column(String(255), nullable=False, info={"description": "Human-readable label"})
    key_prefix = Column(String(8), nullable=False, info={"description": "First 8 chars for identification"})
    key_hash = Column(String(64), nullable=False, unique=True, info={"description": "SHA-256 of the full key"})

    # Scopes (comma-separated, e.g. "predict,dashboard,alerts")
    scopes = Column(Text, default="predict", nullable=False)

    # Usage tracking
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    last_used_ip = Column(String(45), nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)

    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Revocation
    is_revoked = Column(Boolean, default=False, nullable=False, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_api_key_hash", "key_hash"),
        Index("idx_api_key_user_active", "user_id", "is_revoked", "is_deleted"),
        {"comment": "Per-user API keys with rotation and scoping support"},
    )

    def __repr__(self):
        return f"<APIKey(id={self.id}, name={self.name}, prefix={self.key_prefix}...)>"

    @staticmethod
    def generate_key() -> tuple[str, str, str]:
        """Generate a new API key.

        Returns:
            (raw_key, key_prefix, key_hash)
        """
        raw_key = f"fnq_{secrets.token_urlsafe(40)}"
        key_prefix = raw_key[:8]
        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        return raw_key, key_prefix, key_hash

    @staticmethod
    def hash_key(raw_key: str) -> str:
        """Hash a raw API key for lookup."""
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @property
    def is_expired(self) -> bool:
        expires_at = cast(datetime | None, self.expires_at)
        if expires_at is None:
            return False
        return datetime.now(timezone.utc) > expires_at

    @property
    def is_active(self) -> bool:
        is_revoked = cast(bool, self.is_revoked)
        is_deleted = cast(bool, self.is_deleted)
        return not is_revoked and not is_deleted and not self.is_expired

    def revoke(self):
        self.is_revoked = True
        self.revoked_at = datetime.now(timezone.utc)

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def record_usage(self, ip: str | None = None):
        self.last_used_at = datetime.now(timezone.utc)
        self.last_used_ip = ip
        usage_count = cast(int, self.usage_count)
        self.usage_count = usage_count + 1

    def to_dict(self) -> dict:
        """Serialize for API response (never includes the raw key)."""
        scopes = cast(str, self.scopes)
        created_at = cast(datetime | None, self.created_at)
        expires_at = cast(datetime | None, self.expires_at)
        last_used_at = cast(datetime | None, self.last_used_at)
        is_revoked = cast(bool, self.is_revoked)
        usage_count = cast(int, self.usage_count)

        return {
            "id": self.id,
            "name": self.name,
            "prefix": self.key_prefix,
            "scopes": scopes.split(",") if scopes else [],
            "created_at": created_at.isoformat() if created_at else None,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "last_used_at": last_used_at.isoformat() if last_used_at else None,
            "is_revoked": is_revoked,
            "is_expired": self.is_expired,
            "is_active": self.is_active,
            "usage_count": usage_count,
        }
