"""Add indexes for slow query optimization

Addresses pervasive slow queries (500ms-1000ms+) across all major tables.
Each index targets specific query patterns observed in production logs:
- weather_data: timestamp scans, source filtering
- predictions: created_at + risk_level filtering
- community_reports: status + barangay filtering
- alert_history: triggered_at + delivery_status
- users: email + role lookup
- api_requests: created_at + status_code analytics
- audit_logs: pre-emptive indexes for analytics queries

Revision ID: r3s4t5u6v7w8
Revises: q2r3s4t5u6v7
Create Date: 2026-03-20 00:00:00.000000
"""

from alembic import op
from sqlalchemy import inspect as sa_inspect, text


# revision identifiers, used by Alembic.
revision = "r3s4t5u6v7w8"
down_revision = "q2r3s4t5u6v7"
branch_labels = None
depends_on = None


def _table_exists(bind, table_name: str) -> bool:
    """Check if a table exists."""
    inspector = sa_inspect(bind)
    return table_name in inspector.get_table_names()


def _create_index_if_not_exists(bind, index_name, table_name, columns, **kwargs):
    """Create an index only if it doesn't already exist.

    Uses PostgreSQL-native IF NOT EXISTS to avoid SQLAlchemy inspector
    caching issues (the inspector can miss pre-existing indexes when
    multiple checks run in the same transaction).
    """
    if not _table_exists(bind, table_name):
        return
    using = kwargs.get("postgresql_using", "btree")
    cols_sql = ", ".join(columns)
    bind.execute(
        text(
            f'CREATE INDEX IF NOT EXISTS "{index_name}" '
            f'ON "{table_name}" USING {using} ({cols_sql})'
        )
    )


def upgrade():
    bind = op.get_bind()

    # ── weather_data ──────────────────────────────────────────────────────
    # Full table scans (530-840ms) on timestamp queries
    _create_index_if_not_exists(
        bind, "idx_weather_timestamp_desc", "weather_data", ["timestamp"],
        postgresql_using="btree",
    )
    _create_index_if_not_exists(
        bind, "idx_weather_created_at_desc", "weather_data", ["created_at"],
    )
    _create_index_if_not_exists(
        bind, "idx_weather_source_timestamp", "weather_data", ["source", "timestamp"],
    )
    # Composite for soft-delete + timestamp (most common query pattern)
    _create_index_if_not_exists(
        bind, "idx_weather_active_recent", "weather_data",
        ["is_deleted", "timestamp"],
    )

    # ── predictions ───────────────────────────────────────────────────────
    # Full scans (537-1003ms) on created_at + risk_level
    _create_index_if_not_exists(
        bind, "idx_pred_created_desc", "predictions", ["created_at"],
    )
    _create_index_if_not_exists(
        bind, "idx_pred_risk_created", "predictions",
        ["risk_level", "created_at"],
    )
    _create_index_if_not_exists(
        bind, "idx_pred_active_created", "predictions",
        ["is_deleted", "created_at"],
    )

    # ── community_reports ─────────────────────────────────────────────────
    # Count + fetch queries (530-589ms)
    _create_index_if_not_exists(
        bind, "idx_report_created_desc", "community_reports", ["created_at"],
    )
    _create_index_if_not_exists(
        bind, "idx_report_status_created", "community_reports",
        ["status", "created_at"],
    )
    _create_index_if_not_exists(
        bind, "idx_report_barangay_status", "community_reports",
        ["barangay", "status"],
    )
    _create_index_if_not_exists(
        bind, "idx_report_active_created", "community_reports",
        ["is_deleted", "created_at"],
    )

    # ── alert_history ─────────────────────────────────────────────────────
    # Fetch queries (549-573ms)
    _create_index_if_not_exists(
        bind, "idx_alert_created_desc", "alert_history", ["created_at"],
    )
    _create_index_if_not_exists(
        bind, "idx_alert_delivery_created", "alert_history",
        ["delivery_status", "created_at"],
    )

    # ── users ─────────────────────────────────────────────────────────────
    # Lookup queries (527-672ms)
    _create_index_if_not_exists(
        bind, "idx_user_email_lower", "users", ["email"],
    )
    _create_index_if_not_exists(
        bind, "idx_user_role_active", "users", ["role", "is_deleted"],
    )

    # ── api_requests ──────────────────────────────────────────────────────
    # Count queries (×5, 283-544ms)
    _create_index_if_not_exists(
        bind, "idx_apireq_created_status", "api_requests",
        ["created_at", "status_code"],
    )
    _create_index_if_not_exists(
        bind, "idx_apireq_active_created", "api_requests",
        ["is_deleted", "created_at"],
    )

    # ── incidents ─────────────────────────────────────────────────────────
    # Status/risk count queries (530-774ms)
    _create_index_if_not_exists(
        bind, "idx_incident_status_risk", "incidents",
        ["status", "risk_level"],
    )
    _create_index_if_not_exists(
        bind, "idx_incident_barangay_status", "incidents",
        ["barangay", "status"],
    )

    # ── audit_logs (pre-emptive) ──────────────────────────────────────────
    # These should already exist from the audit_logs migration, but ensure coverage
    _create_index_if_not_exists(
        bind, "idx_audit_created_desc", "audit_logs", ["created_at"],
    )
    _create_index_if_not_exists(
        bind, "idx_audit_action_severity", "audit_logs",
        ["action", "severity"],
    )
    _create_index_if_not_exists(
        bind, "idx_audit_user_action", "audit_logs",
        ["user_id", "action"],
    )


def downgrade():
    bind = op.get_bind()

    # Drop in reverse order
    for idx, tbl in [
        ("idx_audit_user_action", "audit_logs"),
        ("idx_audit_action_severity", "audit_logs"),
        ("idx_audit_created_desc", "audit_logs"),
        ("idx_incident_barangay_status", "incidents"),
        ("idx_incident_status_risk", "incidents"),
        ("idx_apireq_active_created", "api_requests"),
        ("idx_apireq_created_status", "api_requests"),
        ("idx_user_role_active", "users"),
        ("idx_user_email_lower", "users"),
        ("idx_alert_delivery_created", "alert_history"),
        ("idx_alert_created_desc", "alert_history"),
        ("idx_report_active_created", "community_reports"),
        ("idx_report_barangay_status", "community_reports"),
        ("idx_report_status_created", "community_reports"),
        ("idx_report_created_desc", "community_reports"),
        ("idx_pred_active_created", "predictions"),
        ("idx_pred_risk_created", "predictions"),
        ("idx_pred_created_desc", "predictions"),
        ("idx_weather_active_recent", "weather_data"),
        ("idx_weather_source_timestamp", "weather_data"),
        ("idx_weather_created_at_desc", "weather_data"),
        ("idx_weather_timestamp_desc", "weather_data"),
    ]:
        if _table_exists(bind, tbl):
            bind.execute(text(f'DROP INDEX IF EXISTS "{idx}"'))
