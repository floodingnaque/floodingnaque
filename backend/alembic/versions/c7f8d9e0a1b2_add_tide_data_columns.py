"""Add tide data columns to weather_data table

Revision ID: c7f8d9e0a1b2
Revises: 15b0123df378
Create Date: 2025-12-22 20:20:00.000000

"""
from alembic import op
from sqlalchemy import inspect as sa_inspect
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c7f8d9e0a1b2'
down_revision = '15b0123df378'  # Skipped empty migration b91cb3188c42
branch_labels = None
depends_on = None


def upgrade():
    """
    Add tide data columns to weather_data table.

    New columns:
    - tide_height: Current tide height in meters (relative to datum)
    - tide_trend: Tide direction ('rising' or 'falling')
    - tide_risk_factor: Flood risk contribution factor (0-1 scale)
    - hours_until_high_tide: Hours until next high tide

    These fields support the WorldTides API integration for
    coastal flood prediction in Parañaque City.
    """
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'
    columns = [c["name"] for c in sa_inspect(bind).get_columns("weather_data")]

    # Add tide_height column
    if "tide_height" not in columns:
        op.add_column('weather_data', sa.Column(
            'tide_height',
            sa.Float(),
            nullable=True,
            comment='Tide height in meters relative to datum (MSL)'
        ))

    # Add tide_trend column
    if "tide_trend" not in columns:
        op.add_column('weather_data', sa.Column(
            'tide_trend',
            sa.String(20),
            nullable=True,
            comment='Tide trend: rising or falling'
        ))

    # Add tide_risk_factor column
    if "tide_risk_factor" not in columns:
        op.add_column('weather_data', sa.Column(
            'tide_risk_factor',
            sa.Float(),
            nullable=True,
            comment='Tide risk factor 0-1 for flood prediction'
        ))

    # Add hours_until_high_tide column
    if "hours_until_high_tide" not in columns:
        op.add_column('weather_data', sa.Column(
            'hours_until_high_tide',
            sa.Float(),
            nullable=True,
            comment='Hours until next high tide'
        ))

    # Add check constraints for PostgreSQL only (SQLite has limited constraint support)
    if not is_sqlite:
        # Tide risk factor should be between 0 and 1
        op.create_check_constraint(
            'valid_tide_risk_factor',
            'weather_data',
            'tide_risk_factor IS NULL OR (tide_risk_factor >= 0 AND tide_risk_factor <= 1)'
        )

        # Tide trend should be 'rising' or 'falling'
        op.create_check_constraint(
            'valid_tide_trend',
            'weather_data',
            "tide_trend IS NULL OR tide_trend IN ('rising', 'falling')"
        )

        # Hours until high tide should be non-negative
        op.create_check_constraint(
            'valid_hours_until_high_tide',
            'weather_data',
            'hours_until_high_tide IS NULL OR hours_until_high_tide >= 0'
        )


def downgrade():
    """Remove tide data columns from weather_data table."""
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'
    columns = [c["name"] for c in sa_inspect(bind).get_columns("weather_data")]

    # Drop constraints first (PostgreSQL only)
    if not is_sqlite:
        op.drop_constraint('valid_hours_until_high_tide', 'weather_data', type_='check')
        op.drop_constraint('valid_tide_trend', 'weather_data', type_='check')
        op.drop_constraint('valid_tide_risk_factor', 'weather_data', type_='check')

    # Drop columns (guard for fresh-DB path)
    if "hours_until_high_tide" in columns:
        op.drop_column('weather_data', 'hours_until_high_tide')
    if "tide_risk_factor" in columns:
        op.drop_column('weather_data', 'tide_risk_factor')
    if "tide_trend" in columns:
        op.drop_column('weather_data', 'tide_trend')
    if "tide_height" in columns:
        op.drop_column('weather_data', 'tide_height')
