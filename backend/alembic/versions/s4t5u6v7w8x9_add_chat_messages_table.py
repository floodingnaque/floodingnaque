"""add chat_messages table

Revision ID: s4t5u6v7w8x9
Revises: r3s4t5u6v7w8
Create Date: 2026-03-22 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "s4t5u6v7w8x9"
down_revision: Union[str, None] = "r3s4t5u6v7w8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(length=36), nullable=False, server_default=sa.text("gen_random_uuid()::text")),
        sa.Column("barangay_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("user_name", sa.String(length=100), nullable=False),
        sa.Column("user_role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("message_type", sa.String(length=30), nullable=False, server_default="text"),
        sa.Column("report_id", sa.Integer(), nullable=True),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_chat_user"),
        sa.ForeignKeyConstraint(["report_id"], ["community_reports.id"], name="fk_chat_report"),
        sa.CheckConstraint(
            "user_role IN ('user', 'operator', 'admin')",
            name="valid_chat_user_role",
        ),
        sa.CheckConstraint(
            "message_type IN ('text', 'alert', 'status_update', 'flood_report')",
            name="valid_chat_message_type",
        ),
        sa.CheckConstraint(
            "char_length(content) BETWEEN 1 AND 1000",
            name="chat_content_length",
        ),
    )

    # Primary query index: fetch messages for a channel, newest-first, excluding deleted
    op.create_index(
        "idx_chat_barangay_created",
        "chat_messages",
        ["barangay_id", sa.text("created_at DESC")],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # User's own messages
    op.create_index("idx_chat_user", "chat_messages", ["user_id"])

    # Report-linked messages (sparse)
    op.create_index(
        "idx_chat_report",
        "chat_messages",
        ["report_id"],
        postgresql_where=sa.text("report_id IS NOT NULL"),
    )

    # Message type filter (sparse, non-text messages only)
    op.create_index(
        "idx_chat_message_type",
        "chat_messages",
        ["message_type"],
        postgresql_where=sa.text("message_type != 'text'"),
    )


def downgrade() -> None:
    op.drop_index("idx_chat_message_type", table_name="chat_messages")
    op.drop_index("idx_chat_report", table_name="chat_messages")
    op.drop_index("idx_chat_user", table_name="chat_messages")
    op.drop_index("idx_chat_barangay_created", table_name="chat_messages")
    op.drop_table("chat_messages")
