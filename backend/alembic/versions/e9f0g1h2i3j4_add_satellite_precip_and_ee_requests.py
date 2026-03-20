"""Add satellite precipitation columns and earth_engine_requests table

Revision ID: e9f0g1h2i3j4
Revises: d8e9f0g1h2i3
Create Date: 2025-12-22 21:00:00.000000

"""
from alembic import op
from sqlalchemy import inspect as sa_inspect
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e9f0g1h2i3j4'
down_revision = 'd8e9f0g1h2i3'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add satellite precipitation columns to weather_data and create earth_engine_requests table.

    Changes:
    1. Add satellite precipitation columns to weather_data for GPM/CHIRPS data
    2. Create earth_engine_requests table to track Earth Engine API calls
    3. Create webhooks table for external notifications
    """
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'
    columns = [c["name"] for c in sa_inspect(bind).get_columns("weather_data")]

    # ==========================================
    # 1. Add satellite precipitation columns to weather_data
    # ==========================================

    # Add satellite_precipitation_rate column
    if "satellite_precipitation_rate" not in columns:
        op.add_column('weather_data', sa.Column(
            'satellite_precipitation_rate',
            sa.Float(),
            nullable=True,
            comment='Satellite precipitation rate in mm/hour'
        ))

    # Add precipitation_1h column
    if "precipitation_1h" not in columns:
        op.add_column('weather_data', sa.Column(
            'precipitation_1h',
            sa.Float(),
            nullable=True,
            comment='Accumulated precipitation in last 1 hour (mm)'
        ))

    # Add precipitation_3h column
    if "precipitation_3h" not in columns:
        op.add_column('weather_data', sa.Column(
            'precipitation_3h',
            sa.Float(),
            nullable=True,
            comment='Accumulated precipitation in last 3 hours (mm)'
        ))

    # Add precipitation_24h column
    if "precipitation_24h" not in columns:
        op.add_column('weather_data', sa.Column(
            'precipitation_24h',
            sa.Float(),
            nullable=True,
            comment='Accumulated precipitation in last 24 hours (mm)'
        ))

    # Add data_quality column
    if "data_quality" not in columns:
        op.add_column('weather_data', sa.Column(
            'data_quality',
            sa.Float(),
            nullable=True,
            comment='Data quality score 0-1'
        ))

    # Add dataset column
    if "dataset" not in columns:
        op.add_column('weather_data', sa.Column(
            'dataset',
            sa.String(50),
            nullable=True,
            server_default='OWM',
            comment='Dataset source: OWM, GPM, CHIRPS, ERA5'
        ))

    # Add check constraint for data_quality (PostgreSQL only)
    if not is_sqlite:
        op.create_check_constraint(
            'valid_data_quality',
            'weather_data',
            'data_quality IS NULL OR (data_quality >= 0 AND data_quality <= 1)'
        )

    # ==========================================
    # 2. Create earth_engine_requests table
    # ==========================================
    op.create_table(
        'earth_engine_requests',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('request_id', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('request_type', sa.String(50), nullable=False),
        sa.Column('dataset', sa.String(100), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('response_time_ms', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('data_points_returned', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        comment='Earth Engine API request logs for GPM, CHIRPS, ERA5 data'
    )

    # Create indexes for earth_engine_requests
    op.create_index('idx_ee_request_type', 'earth_engine_requests', ['request_type'])
    op.create_index('idx_ee_request_status', 'earth_engine_requests', ['status'])
    op.create_index('idx_ee_request_created', 'earth_engine_requests', ['created_at'])

    # ==========================================
    # 3. Create webhooks table (if not exists)
    # ==========================================
    # Note: This table may already exist from previous migration
    # Using try/except to handle gracefully
    try:
        # Check if table exists
        conn = op.get_bind()
        result = conn.execute(sa.text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = 'webhooks'"
        ))
        if result.fetchone() is None:
            op.create_table(
                'webhooks',
                sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
                sa.Column('url', sa.String(500), nullable=False),
                sa.Column('events', sa.Text(), nullable=False),
                sa.Column('secret', sa.String(255), nullable=False),
                sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', index=True),
                sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
                sa.Column('failure_count', sa.Integer(), nullable=True, server_default='0'),
                sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
                sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
                sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false', index=True),
                sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
                comment='Webhook configurations for external notifications'
            )
            op.create_index('idx_webhook_active', 'webhooks', ['is_active', 'is_deleted'])
    except Exception:
        pass  # Table already exists


def downgrade():
    """Remove satellite precipitation columns and drop earth_engine_requests table."""
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'

    # Drop webhooks table indexes and table
    try:
        op.drop_index('idx_webhook_active', table_name='webhooks')
        op.drop_table('webhooks')
    except Exception:
        pass  # Table may not exist

    # Drop earth_engine_requests indexes and table
    op.drop_index('idx_ee_request_created', table_name='earth_engine_requests')
    op.drop_index('idx_ee_request_status', table_name='earth_engine_requests')
    op.drop_index('idx_ee_request_type', table_name='earth_engine_requests')
    op.drop_table('earth_engine_requests')

    # Drop check constraint (PostgreSQL only)
    if not is_sqlite:
        op.drop_constraint('valid_data_quality', 'weather_data', type_='check')

    # Drop satellite precipitation columns from weather_data (guard for fresh-DB path)
    columns = [c["name"] for c in sa_inspect(bind).get_columns("weather_data")]
    for col in ['dataset', 'data_quality', 'precipitation_24h',
                'precipitation_3h', 'precipitation_1h', 'satellite_precipitation_rate']:
        if col in columns:
            op.drop_column('weather_data', col)
