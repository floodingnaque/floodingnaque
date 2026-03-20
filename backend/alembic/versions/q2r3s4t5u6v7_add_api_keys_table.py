"""Add api_keys table for per-user key management

Revision ID: q2r3s4t5u6v7
Revises: p1q2r3s4t5u6
Create Date: 2026-01-25 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "q2r3s4t5u6v7"
down_revision = "p1q2r3s4t5u6"
branch_labels = None
depends_on = None


def upgrade():
    """Create api_keys table with indexes."""
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("key_prefix", sa.String(length=8), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("scopes", sa.Text(), nullable=False, server_default="predict"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_ip", sa.String(length=45), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("key_hash"),
        comment="Per-user API keys with rotation and scoping support",
    )

    op.create_index("idx_api_key_hash", "api_keys", ["key_hash"])
    op.create_index("idx_api_key_user_id", "api_keys", ["user_id"])
    op.create_index("idx_api_key_is_revoked", "api_keys", ["is_revoked"])
    op.create_index("idx_api_key_is_deleted", "api_keys", ["is_deleted"])
    op.create_index(
        "idx_api_key_user_active", "api_keys", ["user_id", "is_revoked", "is_deleted"]
    )


def downgrade():
    """Drop api_keys table and indexes."""
    op.drop_index("idx_api_key_user_active", table_name="api_keys")
    op.drop_index("idx_api_key_is_deleted", table_name="api_keys")
    op.drop_index("idx_api_key_is_revoked", table_name="api_keys")
    op.drop_index("idx_api_key_user_id", table_name="api_keys")
    op.drop_index("idx_api_key_hash", table_name="api_keys")
    op.drop_table("api_keys")
