"""add_reputation_scoring_columns_to_users

Revision ID: 4ff809e72cd8
Revises: u6v7w8x9y0z1
Create Date: 2026-03-28 03:11:43.027463

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4ff809e72cd8'
down_revision: Union[str, Sequence[str], None] = 'u6v7w8x9y0z1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("reputation_score", sa.Float(), nullable=False, server_default=sa.text("0.5")))
    op.add_column("users", sa.Column("total_reports", sa.Integer(), nullable=False, server_default=sa.text("0")))
    op.add_column("users", sa.Column("accepted_reports", sa.Integer(), nullable=False, server_default=sa.text("0")))
    op.add_column("users", sa.Column("rejected_reports", sa.Integer(), nullable=False, server_default=sa.text("0")))
    op.add_column("users", sa.Column("reputation_updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "reputation_updated_at")
    op.drop_column("users", "rejected_reports")
    op.drop_column("users", "accepted_reports")
    op.drop_column("users", "total_reports")
    op.drop_column("users", "reputation_score")
