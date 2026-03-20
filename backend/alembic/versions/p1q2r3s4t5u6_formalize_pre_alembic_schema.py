"""Formalize pre-Alembic schema gaps.

Adds missing column, indexes, CHECK constraints, and server default
for the 4 pre-Alembic tables (weather_data, predictions, alert_history,
model_registry) whose original creation pre-dated Alembic adoption.

- model_registry.created_by  (Gap 2)
- 10 base indexes             (Gap 3)
- 15 CHECK constraints         (Gap 4, PostgreSQL only, NOT VALID then VALIDATE)
- api_requests.api_version server_default  (Gap 5)

Revision ID: p1q2r3s4t5u6
Revises: 7ea25273d2b4
Create Date: 2026-03-10 00:00:00.000000
"""

from alembic import op
from sqlalchemy import inspect as sa_inspect
import sqlalchemy as sa


# revision identifiers
revision = "p1q2r3s4t5u6"
down_revision = "7ea25273d2b4"
branch_labels = None
depends_on = None


# ── helpers ──────────────────────────────────────────────────────────
def _has_column(inspector, table: str, column: str) -> bool:
    return column in [c["name"] for c in inspector.get_columns(table)]


def _existing_index_names(inspector, table: str) -> set:
    return {idx["name"] for idx in inspector.get_indexes(table)}


def _existing_constraint_names(bind, table: str) -> set:
    """Return CHECK constraint names for *table* (PostgreSQL only)."""
    if bind.dialect.name != "postgresql":
        return set()
    result = bind.execute(sa.text(
        "SELECT conname FROM pg_constraint "
        "WHERE conrelid = (SELECT oid FROM pg_class WHERE relname = :tbl) "
        "AND contype = 'c'"
    ), {"tbl": table})
    return {row[0] for row in result}


def _add_check(bind, table: str, name: str, expr: str, existing: set) -> None:
    """Add a CHECK constraint using NOT VALID + VALIDATE (PostgreSQL)."""
    if name in existing:
        return
    op.execute(
        f'ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expr}) NOT VALID'
    )
    op.execute(f'ALTER TABLE {table} VALIDATE CONSTRAINT {name}')


# ── upgrade ──────────────────────────────────────────────────────────
def upgrade() -> None:
    bind = op.get_bind()
    insp = sa_inspect(bind)
    is_pg = bind.dialect.name == "postgresql"

    # ------------------------------------------------------------------
    # Gap 2 — model_registry.created_by
    # ------------------------------------------------------------------
    if not _has_column(insp, "model_registry", "created_by"):
        op.add_column(
            "model_registry",
            sa.Column("created_by", sa.String(100), nullable=True),
        )

    # ------------------------------------------------------------------
    # Gap 3 — 10 base indexes missing from pre-Alembic tables
    # ------------------------------------------------------------------
    # Use raw DDL with IF NOT EXISTS for PostgreSQL to be truly idempotent,
    # since the inspector may not see indexes created outside Alembic.
    if is_pg:
        _indexes = [
            ("idx_prediction_risk", "predictions", "risk_level"),
            ("idx_prediction_model", "predictions", "model_version"),
            ("idx_alert_risk", "alert_history", "risk_level"),
            ("idx_alert_status", "alert_history", "delivery_status"),
            ("idx_weather_timestamp", "weather_data", "timestamp"),
            ("idx_weather_location", "weather_data", "location_lat, location_lon"),
            ("idx_weather_created", "weather_data", "created_at"),
            ("idx_weather_source", "weather_data", "source"),
        ]
        for idx_name, table, cols in _indexes:
            op.execute(sa.text(
                f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({cols})"
            ))
        op.execute(sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_model_registry_version "
            "ON model_registry (version)"
        ))
        op.execute(sa.text(
            "CREATE INDEX IF NOT EXISTS ix_model_registry_is_active "
            "ON model_registry (is_active)"
        ))
    else:
        # SQLite / other dialects: use inspector-based guards
        _idx = {
            "predictions": _existing_index_names(insp, "predictions"),
            "alert_history": _existing_index_names(insp, "alert_history"),
            "weather_data": _existing_index_names(insp, "weather_data"),
            "model_registry": _existing_index_names(insp, "model_registry"),
        }
        if "idx_prediction_risk" not in _idx["predictions"]:
            op.create_index("idx_prediction_risk", "predictions", ["risk_level"])
        if "idx_prediction_model" not in _idx["predictions"]:
            op.create_index("idx_prediction_model", "predictions", ["model_version"])
        if "idx_alert_risk" not in _idx["alert_history"]:
            op.create_index("idx_alert_risk", "alert_history", ["risk_level"])
        if "idx_alert_status" not in _idx["alert_history"]:
            op.create_index("idx_alert_status", "alert_history", ["delivery_status"])
        if "idx_weather_timestamp" not in _idx["weather_data"]:
            op.create_index("idx_weather_timestamp", "weather_data", ["timestamp"])
        if "idx_weather_location" not in _idx["weather_data"]:
            op.create_index("idx_weather_location", "weather_data", ["location_lat", "location_lon"])
        if "idx_weather_created" not in _idx["weather_data"]:
            op.create_index("idx_weather_created", "weather_data", ["created_at"])
        if "idx_weather_source" not in _idx["weather_data"]:
            op.create_index("idx_weather_source", "weather_data", ["source"])
        if "ix_model_registry_version" not in _idx["model_registry"]:
            op.create_index("ix_model_registry_version", "model_registry", ["version"], unique=True)
        if "ix_model_registry_is_active" not in _idx["model_registry"]:
            op.create_index("ix_model_registry_is_active", "model_registry", ["is_active"])

    # ------------------------------------------------------------------
    # Gap 4 — 15 CHECK constraints (PostgreSQL only, NOT VALID pattern)
    # ------------------------------------------------------------------
    if is_pg:
        pred_ck = _existing_constraint_names(bind, "predictions")
        _add_check(bind, "predictions", "valid_prediction",
                   "prediction IN (0, 1)", pred_ck)
        _add_check(bind, "predictions", "valid_risk_level",
                   "risk_level IS NULL OR risk_level IN (0, 1, 2)", pred_ck)
        _add_check(bind, "predictions", "valid_confidence",
                   "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", pred_ck)

        wd_ck = _existing_constraint_names(bind, "weather_data")
        _add_check(bind, "weather_data", "valid_temperature",
                   "temperature >= 173.15 AND temperature <= 333.15", wd_ck)
        _add_check(bind, "weather_data", "valid_humidity",
                   "humidity >= 0 AND humidity <= 100", wd_ck)
        _add_check(bind, "weather_data", "valid_precipitation",
                   "precipitation >= 0", wd_ck)
        _add_check(bind, "weather_data", "valid_wind_speed",
                   "wind_speed IS NULL OR wind_speed >= 0", wd_ck)
        _add_check(bind, "weather_data", "valid_pressure",
                   "pressure IS NULL OR (pressure >= 870 AND pressure <= 1085)", wd_ck)
        _add_check(bind, "weather_data", "valid_latitude",
                   "location_lat IS NULL OR (location_lat >= -90 AND location_lat <= 90)", wd_ck)
        _add_check(bind, "weather_data", "valid_longitude",
                   "location_lon IS NULL OR (location_lon >= -180 AND location_lon <= 180)", wd_ck)
        _add_check(bind, "weather_data", "valid_data_quality",
                   "data_quality IS NULL OR (data_quality >= 0 AND data_quality <= 1)", wd_ck)

        mr_ck = _existing_constraint_names(bind, "model_registry")
        _add_check(bind, "model_registry", "valid_accuracy",
                   "accuracy IS NULL OR (accuracy >= 0 AND accuracy <= 1)", mr_ck)
        _add_check(bind, "model_registry", "valid_precision",
                   "precision_score IS NULL OR (precision_score >= 0 AND precision_score <= 1)", mr_ck)
        _add_check(bind, "model_registry", "valid_recall",
                   "recall_score IS NULL OR (recall_score >= 0 AND recall_score <= 1)", mr_ck)
        _add_check(bind, "model_registry", "valid_f1",
                   "f1_score IS NULL OR (f1_score >= 0 AND f1_score <= 1)", mr_ck)

    # ------------------------------------------------------------------
    # Gap 5 — api_requests.api_version server_default
    # ------------------------------------------------------------------
    op.alter_column(
        "api_requests", "api_version",
        server_default="v1",
        existing_type=sa.String(10),
        existing_nullable=True,
    )


# ── downgrade ────────────────────────────────────────────────────────
def downgrade() -> None:
    bind = op.get_bind()
    insp = sa_inspect(bind)
    is_pg = bind.dialect.name == "postgresql"

    # Gap 5 — remove server_default
    op.alter_column(
        "api_requests", "api_version",
        server_default=None,
        existing_type=sa.String(10),
        existing_nullable=True,
    )

    # Gap 4 — drop CHECK constraints (PostgreSQL only)
    if is_pg:
        for name, table in [
            ("valid_f1", "model_registry"),
            ("valid_recall", "model_registry"),
            ("valid_precision", "model_registry"),
            ("valid_accuracy", "model_registry"),
            ("valid_data_quality", "weather_data"),
            ("valid_longitude", "weather_data"),
            ("valid_latitude", "weather_data"),
            ("valid_pressure", "weather_data"),
            ("valid_wind_speed", "weather_data"),
            ("valid_precipitation", "weather_data"),
            ("valid_humidity", "weather_data"),
            ("valid_temperature", "weather_data"),
            ("valid_confidence", "predictions"),
            ("valid_risk_level", "predictions"),
            ("valid_prediction", "predictions"),
        ]:
            existing = _existing_constraint_names(bind, table)
            if name in existing:
                op.drop_constraint(name, table, type_="check")

    # Gap 3 — drop indexes
    _idx = {
        "predictions": _existing_index_names(insp, "predictions"),
        "alert_history": _existing_index_names(insp, "alert_history"),
        "weather_data": _existing_index_names(insp, "weather_data"),
        "model_registry": _existing_index_names(insp, "model_registry"),
    }
    for idx_name, table in [
        ("ix_model_registry_is_active", "model_registry"),
        ("ix_model_registry_version", "model_registry"),
        ("idx_weather_source", "weather_data"),
        ("idx_weather_created", "weather_data"),
        ("idx_weather_location", "weather_data"),
        ("idx_weather_timestamp", "weather_data"),
        ("idx_alert_status", "alert_history"),
        ("idx_alert_risk", "alert_history"),
        ("idx_prediction_model", "predictions"),
        ("idx_prediction_risk", "predictions"),
    ]:
        if idx_name in _idx[table]:
            op.drop_index(idx_name, table_name=table)

    # Gap 2 — drop created_by
    if _has_column(insp, "model_registry", "created_by"):
        op.drop_column("model_registry", "created_by")
