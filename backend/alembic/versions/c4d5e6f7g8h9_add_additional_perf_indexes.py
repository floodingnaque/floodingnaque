"""Add additional performance indexes for query optimization

Supplements existing indexes (f1g2h3i4j5k6 and r3s4t5u6v7w8) with
covering indexes for specific query patterns identified during
systematic performance audit:
- incidents: created_at for time-series, is_deleted composite
- evacuation_centers: barangay_id + is_active for directory queries
- after_action_reports: incident_id + status for AAR lookups

Revision ID: c4d5e6f7g8h9
Revises: b1c2d3e4f5g6
Create Date: 2026-03-23 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect as sa_inspect, text

revision: str = "c4d5e6f7g8h9"
down_revision: Union[str, None] = "b1c2d3e4f5g6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(bind, table_name: str) -> bool:
    inspector = sa_inspect(bind)
    return table_name in inspector.get_table_names()


def _create_index_if_not_exists(bind, index_name, table_name, columns):
    if not _table_exists(bind, table_name):
        return
    # Verify all columns exist on the table before creating the index
    inspector = sa_inspect(bind)
    existing_cols = {c["name"] for c in inspector.get_columns(table_name)}
    for col in columns:
        if col not in existing_cols:
            return
    cols_sql = ", ".join(columns)
    bind.execute(
        text(
            f'CREATE INDEX IF NOT EXISTS "{index_name}" '
            f'ON "{table_name}" USING btree ({cols_sql})'
        )
    )


def upgrade() -> None:
    bind = op.get_bind()

    # incidents: soft-delete + created_at for paginated listing
    _create_index_if_not_exists(
        bind, "idx_incident_active_created", "incidents",
        ["is_deleted", "created_at"],
    )

    # evacuation_centers: barangay directory queries
    _create_index_if_not_exists(
        bind, "idx_evac_barangay_active", "evacuation_centers",
        ["barangay_id", "is_active"],
    )

    # after_action_reports: incident lookups + status filters
    _create_index_if_not_exists(
        bind, "idx_aar_incident_status", "after_action_reports",
        ["incident_id", "is_deleted"],
    )
    _create_index_if_not_exists(
        bind, "idx_aar_status_compliant", "after_action_reports",
        ["status", "ra10121_compliant", "is_deleted"],
    )

    # api_requests: endpoint ILIKE filtering (admin logs)
    _create_index_if_not_exists(
        bind, "idx_apireq_endpoint_status", "api_requests",
        ["endpoint", "status_code", "is_deleted"],
    )

    # weather_data: is_deleted filter for COUNT queries
    _create_index_if_not_exists(
        bind, "idx_weather_deleted_id", "weather_data",
        ["is_deleted"],
    )

    # predictions: is_deleted filter for COUNT queries
    _create_index_if_not_exists(
        bind, "idx_pred_deleted_id", "predictions",
        ["is_deleted"],
    )


def downgrade() -> None:
    bind = op.get_bind()

    for idx, tbl in [
        ("idx_pred_deleted_id", "predictions"),
        ("idx_weather_deleted_id", "weather_data"),
        ("idx_apireq_endpoint_status", "api_requests"),
        ("idx_aar_status_compliant", "after_action_reports"),
        ("idx_aar_incident_status", "after_action_reports"),
        ("idx_evac_barangay_active", "evacuation_centers"),
        ("idx_incident_active_created", "incidents"),
    ]:
        if _table_exists(bind, tbl):
            bind.execute(text(f'DROP INDEX IF EXISTS "{idx}"'))
