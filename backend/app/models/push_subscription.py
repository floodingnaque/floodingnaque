"""PushSubscription ORM model — Web Push notification subscriptions."""

from datetime import datetime, timezone

from app.models.db import Base
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint


class PushSubscription(Base):
    """A browser push subscription for a user, scoped to a barangay."""

    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    barangay_id = Column(String(50), nullable=True, index=True)
    endpoint = Column(Text, nullable=False)
    subscription_json = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "endpoint", name="uq_user_endpoint"),
        {"comment": "Web Push subscriptions for flood alert notifications"},
    )

    def soft_delete(self):
        """Mark subscription as deleted without removing from DB."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self):
        """Restore a soft-deleted subscription."""
        self.is_deleted = False
        self.deleted_at = None

    def __repr__(self):
        return f"<PushSubscription(id={self.id}, user_id={self.user_id}, barangay_id={self.barangay_id})>"
