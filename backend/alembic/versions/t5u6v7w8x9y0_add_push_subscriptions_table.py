"""add push_subscriptions table

Revision ID: t5u6v7w8x9y0
Revises: 235db5db1b04
Create Date: 2025-06-26 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "t5u6v7w8x9y0"
down_revision: Union[str, None] = "235db5db1b04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("barangay_id", sa.String(length=50), nullable=True),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("subscription_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_push_subscriptions_user_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "endpoint", name="uq_user_endpoint"),
        comment="Web Push subscriptions for flood alert notifications",
    )
    op.create_index("ix_push_subscriptions_user_id", "push_subscriptions", ["user_id"])
    op.create_index("ix_push_subscriptions_barangay_id", "push_subscriptions", ["barangay_id"])
    op.create_index("ix_push_subscriptions_is_deleted", "push_subscriptions", ["is_deleted"])


def downgrade() -> None:
    op.drop_index("ix_push_subscriptions_is_deleted", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_barangay_id", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_user_id", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
