"""add broadcasts table

Revision ID: b1c2d3e4f5g6
Revises: a8b9c0d1e2f3
Create Date: 2026-03-21 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b1c2d3e4f5g6"
down_revision: Union[str, None] = "a8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "broadcasts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="normal"),
        sa.Column("target_barangays", sa.Text(), nullable=False),
        sa.Column("channels", sa.Text(), nullable=False),
        sa.Column("recipients", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("sent_by", sa.String(length=100), nullable=True),
        sa.Column("incident_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_broadcast_created", "broadcasts", ["created_at"])
    op.create_index("idx_broadcast_incident", "broadcasts", ["incident_id"])
    op.create_index("idx_broadcast_deleted", "broadcasts", ["is_deleted"])


def downgrade() -> None:
    op.drop_index("idx_broadcast_deleted", table_name="broadcasts")
    op.drop_index("idx_broadcast_incident", table_name="broadcasts")
    op.drop_index("idx_broadcast_created", table_name="broadcasts")
    op.drop_table("broadcasts")
