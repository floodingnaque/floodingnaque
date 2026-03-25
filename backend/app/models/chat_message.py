"""ChatMessage ORM model — barangay-scoped community chat.

Messages are written via Flask and broadcast in real-time by
Supabase Realtime (postgres_changes).  No WebSocket code in Flask.
"""

from datetime import datetime, timezone

from app.models.db import Base
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text


class ChatMessage(Base):
    """A single chat message scoped to a barangay channel."""

    __tablename__ = "chat_messages"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    barangay_id = Column(String(50), nullable=False)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_name = Column(String(100), nullable=False)
    user_role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String(20), nullable=False, server_default="text")
    report_id = Column(
        Integer,
        ForeignKey("community_reports.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_pinned = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    author = relationship("User", foreign_keys=[user_id], backref="chat_messages")

    __table_args__ = (
        CheckConstraint(
            "user_role IN ('user', 'operator', 'admin')",
            name="valid_chat_user_role",
        ),
        CheckConstraint(
            "message_type IN ('text', 'alert', 'status_update', 'flood_report')",
            name="valid_chat_message_type",
        ),
        CheckConstraint(
            "char_length(content) BETWEEN 1 AND 1000",
            name="chat_content_length",
        ),
        Index(
            "idx_chat_barangay_created",
            "barangay_id",
            "created_at",
            postgresql_where=text("is_deleted = FALSE"),
        ),
        Index("idx_chat_user", "user_id", "created_at"),
        Index(
            "idx_chat_report",
            "report_id",
            postgresql_where=text("report_id IS NOT NULL"),
        ),
        Index(
            "idx_chat_message_type",
            "barangay_id",
            "message_type",
            postgresql_where=text("is_deleted = FALSE"),
        ),
        {"comment": "Barangay-scoped community chat messages"},
    )

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, barangay={self.barangay_id}, user={self.user_name})>"

    def to_dict(self) -> dict:
        """Serialize for JSON responses."""
        return {
            "id": str(self.id),
            "barangay_id": self.barangay_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "user_role": self.user_role,
            "content": self.content,
            "message_type": self.message_type,
            "report_id": self.report_id,
            "is_pinned": self.is_pinned,
            "created_at": self.created_at.isoformat() if self.created_at is not None else None,
        }
