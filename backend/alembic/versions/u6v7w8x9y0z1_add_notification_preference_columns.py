"""add notification preference columns to users

Revision ID: u6v7w8x9y0z1
Revises: t5u6v7w8x9y0
Create Date: 2025-01-01 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "u6v7w8x9y0z1"
down_revision = "t5u6v7w8x9y0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("sms_alerts_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.add_column("users", sa.Column("email_alerts_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")))


def downgrade() -> None:
    op.drop_column("users", "email_alerts_enabled")
    op.drop_column("users", "sms_alerts_enabled")
