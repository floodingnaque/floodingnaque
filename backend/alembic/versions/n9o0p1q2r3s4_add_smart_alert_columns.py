"""add smart alert columns to alert_history

Revision ID: n9o0p1q2r3s4
Revises: m8n9o0p1q2r3
Create Date: 2026-03-02 12:00:00.000000

"""
from alembic import op
from sqlalchemy import inspect as sa_inspect
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'n9o0p1q2r3s4'
down_revision = 'm8n9o0p1q2r3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = [c["name"] for c in sa_inspect(bind).get_columns("alert_history")]

    # Smart Alert Logic columns
    if "confidence_score" not in columns:
        op.add_column('alert_history', sa.Column('confidence_score', sa.Float(), nullable=True))
    if "rainfall_3h" not in columns:
        op.add_column('alert_history', sa.Column('rainfall_3h', sa.Float(), nullable=True))
    if "escalation_state" not in columns:
        op.add_column('alert_history', sa.Column(
            'escalation_state', sa.String(length=50), nullable=True, server_default='initial'
        ))
    if "escalation_reason" not in columns:
        op.add_column('alert_history', sa.Column('escalation_reason', sa.String(length=255), nullable=True))
    if "suppressed" not in columns:
        op.add_column('alert_history', sa.Column(
            'suppressed', sa.Boolean(), nullable=False, server_default=sa.text('false')
        ))
    if "contributing_factors" not in columns:
        op.add_column('alert_history', sa.Column('contributing_factors', sa.Text(), nullable=True))

    # Index for filtering suppressed/escalated alerts
    op.create_index('idx_alert_escalation', 'alert_history', ['escalation_state'], if_not_exists=True)
    op.create_index('idx_alert_suppressed', 'alert_history', ['suppressed'], if_not_exists=True)


def downgrade() -> None:
    bind = op.get_bind()
    columns = [c["name"] for c in sa_inspect(bind).get_columns("alert_history")]

    op.drop_index('idx_alert_suppressed', table_name='alert_history')
    op.drop_index('idx_alert_escalation', table_name='alert_history')
    for col in ['contributing_factors', 'suppressed', 'escalation_reason',
                'escalation_state', 'rainfall_3h', 'confidence_score']:
        if col in columns:
            op.drop_column('alert_history', col)
