"""Add ab_tests table for A/B test persistence

Revision ID: j5k6l7m8n9o0
Revises: i4j5k6l7m8n9
Create Date: 2026-03-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'j5k6l7m8n9o0'
down_revision = 'i4j5k6l7m8n9'
branch_labels = None
depends_on = None


def upgrade():
    """Create ab_tests table for persisting A/B test state across restarts."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    json_type = sa.JSON()
    if dialect == "postgresql":
        json_type = postgresql.JSON()

    op.create_table(
        'ab_tests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('test_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('variants_json', json_type, nullable=False),
        sa.Column('strategy', sa.String(length=50), nullable=False, server_default='random'),
        sa.Column('target_sample_size', sa.Integer(), nullable=False, server_default='1000'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='created'),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metrics_json', json_type, nullable=True),
        sa.Column('user_assignments_json', json_type, nullable=True),
        sa.Column('round_robin_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('canary_percentage', sa.Float(), nullable=False, server_default='0'),
        sa.Column('canary_increment', sa.Float(), nullable=False, server_default='10'),
        sa.Column('winner', sa.String(length=100), nullable=True),
        sa.Column('statistical_significance', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ab_tests_test_id', 'ab_tests', ['test_id'], unique=True)
    op.create_index('ix_ab_tests_status', 'ab_tests', ['status'])


def downgrade():
    """Drop ab_tests table."""
    op.drop_index('ix_ab_tests_status', table_name='ab_tests')
    op.drop_index('ix_ab_tests_test_id', table_name='ab_tests')
    op.drop_table('ab_tests')
