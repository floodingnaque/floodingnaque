"""fixup create audit_logs table if missing

The original migration o0p1q2r3s4t5 was skipped when the database was
stamped to head.  This migration re-creates the table idempotently.

Revision ID: 2f36c366c2dc
Revises: c951d278d799
Create Date: 2026-03-21 16:33:24.205614

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2f36c366c2dc'
down_revision = 'c951d278d799'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'audit_logs' in inspector.get_table_names():
        return

    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('action', sa.String(length=80), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='info'),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('user_email', sa.String(length=255), nullable=True),
        sa.Column('target_user_id', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('request_id', sa.String(length=36), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        comment='Security audit trail',
    )
    # Single-column indexes
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_severity', 'audit_logs', ['severity'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_ip_address', 'audit_logs', ['ip_address'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    # Composite indexes from original migration
    op.create_index('idx_audit_action_created', 'audit_logs', ['action', 'created_at'])
    op.create_index('idx_audit_severity_created', 'audit_logs', ['severity', 'created_at'])
    op.create_index('idx_audit_user_created', 'audit_logs', ['user_id', 'created_at'])
    # Analytics indexes from r3s4t5u6v7w8
    op.create_index('idx_audit_created_desc', 'audit_logs', ['created_at'])
    op.create_index('idx_audit_action_severity', 'audit_logs', ['action', 'severity'])
    op.create_index('idx_audit_user_action', 'audit_logs', ['user_id', 'action'])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'audit_logs' not in inspector.get_table_names():
        return

    for idx in [
        'idx_audit_user_action', 'idx_audit_action_severity', 'idx_audit_created_desc',
        'idx_audit_user_created', 'idx_audit_severity_created', 'idx_audit_action_created',
        'ix_audit_logs_created_at', 'ix_audit_logs_ip_address',
        'ix_audit_logs_user_id', 'ix_audit_logs_severity', 'ix_audit_logs_action',
    ]:
        op.drop_index(idx, table_name='audit_logs')
    op.drop_table('audit_logs')
