"""Add index on model_registry.created_at

Revision ID: l7m8n9o0p1q2
Revises: k6l7m8n9o0p1
Create Date: 2026-01-10 12:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "l7m8n9o0p1q2"
down_revision = "k6l7m8n9o0p1"
branch_labels = None
depends_on = None


def upgrade():
    """Add index on model_registry.created_at for faster time-based queries."""
    op.create_index("ix_model_registry_created_at", "model_registry", ["created_at"])


def downgrade():
    """Remove the created_at index."""
    op.drop_index("ix_model_registry_created_at", table_name="model_registry")
