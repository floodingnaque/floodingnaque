"""add smart alert columns to alert_history

Revision ID: n9o0p1q2r3s4
Revises: m8n9o0p1q2r3
Create Date: 2026-03-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'n9o0p1q2r3s4'
down_revision = 'm8n9o0p1q2r3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Smart Alert Logic columns
    op.add_column('alert_history', sa.Column('confidence_score', sa.Float(), nullable=True))
    op.add_column('alert_history', sa.Column('rainfall_3h', sa.Float(), nullable=True))
    op.add_column('alert_history', sa.Column(
        'escalation_state', sa.String(length=50), nullable=True, server_default='initial'
    ))
    op.add_column('alert_history', sa.Column('escalation_reason', sa.String(length=255), nullable=True))
    op.add_column('alert_history', sa.Column(
        'suppressed', sa.Boolean(), nullable=False, server_default=sa.text('false')
    ))
    op.add_column('alert_history', sa.Column('contributing_factors', sa.Text(), nullable=True))

    # Index for filtering suppressed/escalated alerts
    op.create_index('idx_alert_escalation', 'alert_history', ['escalation_state'])
    op.create_index('idx_alert_suppressed', 'alert_history', ['suppressed'])


def downgrade() -> None:
    op.drop_index('idx_alert_suppressed', table_name='alert_history')
    op.drop_index('idx_alert_escalation', table_name='alert_history')
    op.drop_column('alert_history', 'contributing_factors')
    op.drop_column('alert_history', 'suppressed')
    op.drop_column('alert_history', 'escalation_reason')
    op.drop_column('alert_history', 'escalation_state')
    op.drop_column('alert_history', 'rainfall_3h')
    op.drop_column('alert_history', 'confidence_score')
