"""add training_data_hash to model_registry

Revision ID: k6l7m8n9o0p1
Revises: j5k6l7m8n9o0
Create Date: 2026-03-01 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "k6l7m8n9o0p1"
down_revision = "j5k6l7m8n9o0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "model_registry",
        sa.Column(
            "training_data_hash",
            sa.String(64),
            nullable=True,
            comment="SHA-256 hash of the training dataset for reproducibility",
        ),
    )


def downgrade() -> None:
    op.drop_column("model_registry", "training_data_hash")
