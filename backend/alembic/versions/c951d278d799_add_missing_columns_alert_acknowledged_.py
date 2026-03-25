"""add missing columns alert_acknowledged and community_report_details

Revision ID: c951d278d799
Revises: r3s4t5u6v7w8
Create Date: 2026-03-21 16:27:31.257661

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c951d278d799"
down_revision: Union[str, Sequence[str], None] = "r3s4t5u6v7w8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing columns to alert_history and community_reports."""
    # alert_history: acknowledged + acknowledged_at
    op.add_column(
        "alert_history",
        sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "alert_history",
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_alert_acknowledged", "alert_history", ["acknowledged"], unique=False)

    # community_reports: specific_location, contact_number, verified_by, verified_at
    op.add_column(
        "community_reports",
        sa.Column("specific_location", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "community_reports",
        sa.Column("contact_number", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "community_reports",
        sa.Column("verified_by", sa.Integer(), nullable=True),
    )
    op.add_column(
        "community_reports",
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_community_reports_verified_by",
        "community_reports",
        "users",
        ["verified_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Remove added columns."""
    op.drop_constraint("fk_community_reports_verified_by", "community_reports", type_="foreignkey")
    op.drop_column("community_reports", "verified_at")
    op.drop_column("community_reports", "verified_by")
    op.drop_column("community_reports", "contact_number")
    op.drop_column("community_reports", "specific_location")
    op.drop_index("idx_alert_acknowledged", table_name="alert_history")
    op.drop_column("alert_history", "acknowledged_at")
    op.drop_column("alert_history", "acknowledged")
