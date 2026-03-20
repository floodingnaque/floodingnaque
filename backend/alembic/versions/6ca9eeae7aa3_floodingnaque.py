"""Floodingnaque — initial migration.

Creates the 4 pre-Alembic tables (weather_data, predictions,
alert_history, model_registry) if they don't already exist, then
adds soft-delete columns and indexes.

Revision ID: 6ca9eeae7aa3
Revises:
Create Date: 2025-12-18 17:07:41.595347

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect as sa_inspect
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6ca9eeae7aa3'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector, table: str, column: str) -> bool:
    """Return True if *column* already exists in *table*."""
    return column in [c["name"] for c in inspector.get_columns(table)]


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    insp = sa_inspect(bind)

    # ------------------------------------------------------------------
    # 1. Conditionally create pre-Alembic tables (fresh-DB support)
    # ------------------------------------------------------------------

    # --- weather_data (13 base columns) ---
    if not insp.has_table("weather_data"):
        op.create_table(
            "weather_data",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("temperature", sa.Float(), nullable=False),
            sa.Column("humidity", sa.Float(), nullable=False),
            sa.Column("precipitation", sa.Float(), nullable=False),
            sa.Column("wind_speed", sa.Float(), nullable=True),
            sa.Column("pressure", sa.Float(), nullable=True),
            sa.Column("location_lat", sa.Float(), nullable=True),
            sa.Column("location_lon", sa.Float(), nullable=True),
            sa.Column("source", sa.String(50), nullable=True, server_default="OWM"),
            sa.Column("station_id", sa.String(50), nullable=True),
            sa.Column("timestamp", sa.DateTime(), nullable=False, index=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            comment="Weather observations for flood prediction",
        )

    # --- predictions (9 base columns, FK → weather_data) ---
    if not insp.has_table("predictions"):
        op.create_table(
            "predictions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("weather_data_id", sa.Integer(), sa.ForeignKey("weather_data.id", ondelete="SET NULL"), nullable=True, index=True),
            sa.Column("prediction", sa.Integer(), nullable=False),
            sa.Column("risk_level", sa.Integer(), nullable=True),
            sa.Column("risk_label", sa.String(50), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("model_version", sa.Integer(), nullable=True),
            sa.Column("model_name", sa.String(100), nullable=True, server_default="flood_rf_model"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
            comment="Flood predictions from ML models",
        )

    # --- alert_history (12 base columns, FK → predictions) ---
    if not insp.has_table("alert_history"):
        op.create_table(
            "alert_history",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("prediction_id", sa.Integer(), sa.ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("risk_level", sa.Integer(), nullable=False),
            sa.Column("risk_label", sa.String(50), nullable=False),
            sa.Column("location", sa.String(255), nullable=True),
            sa.Column("recipients", sa.Text(), nullable=True),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("delivery_status", sa.String(50), nullable=True),
            sa.Column("delivery_channel", sa.String(255), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
            sa.Column("delivered_at", sa.DateTime(), nullable=True),
            comment="Alert delivery history for flood warnings",
        )

    # --- model_registry (18 base columns, independent) ---
    if not insp.has_table("model_registry"):
        op.create_table(
            "model_registry",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("version", sa.Integer(), nullable=False, unique=True, index=True),
            sa.Column("file_path", sa.String(500), nullable=False),
            sa.Column("algorithm", sa.String(100), nullable=True, server_default="RandomForest"),
            sa.Column("accuracy", sa.Float(), nullable=True),
            sa.Column("precision_score", sa.Float(), nullable=True),
            sa.Column("recall_score", sa.Float(), nullable=True),
            sa.Column("f1_score", sa.Float(), nullable=True),
            sa.Column("roc_auc", sa.Float(), nullable=True),
            sa.Column("training_date", sa.DateTime(), nullable=True),
            sa.Column("dataset_size", sa.Integer(), nullable=True),
            sa.Column("dataset_path", sa.String(500), nullable=True),
            sa.Column("parameters", sa.Text(), nullable=True),
            sa.Column("feature_importance", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=True, server_default="false", index=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
            sa.Column("created_by", sa.String(100), nullable=True),
            comment="Model version tracking and performance registry",
        )

    # Refresh inspector after potential table creation
    insp = sa_inspect(bind)

    # ------------------------------------------------------------------
    # 2. Add soft-delete columns (conditional — already present on fresh DB)
    # ------------------------------------------------------------------

    # alert_history
    if not _has_column(insp, "alert_history", "is_deleted"):
        op.add_column('alert_history', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text("false")))
    if not _has_column(insp, "alert_history", "deleted_at"):
        op.add_column('alert_history', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('idx_alert_active', 'alert_history', ['is_deleted'], unique=False, if_not_exists=True)
    op.create_index(op.f('ix_alert_history_is_deleted'), 'alert_history', ['is_deleted'], unique=False, if_not_exists=True)

    # predictions
    if not _has_column(insp, "predictions", "is_deleted"):
        op.add_column('predictions', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text("false")))
    if not _has_column(insp, "predictions", "deleted_at"):
        op.add_column('predictions', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('idx_prediction_active', 'predictions', ['is_deleted'], unique=False, if_not_exists=True)
    op.create_index(op.f('ix_predictions_is_deleted'), 'predictions', ['is_deleted'], unique=False, if_not_exists=True)

    # weather_data
    if not _has_column(insp, "weather_data", "is_deleted"):
        op.add_column('weather_data', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.text("false")))
    if not _has_column(insp, "weather_data", "deleted_at"):
        op.add_column('weather_data', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('idx_weather_active', 'weather_data', ['is_deleted'], unique=False, if_not_exists=True)
    op.create_index('idx_weather_location_time', 'weather_data', ['location_lat', 'location_lon', 'timestamp'], unique=False, if_not_exists=True)
    op.create_index(op.f('ix_weather_data_is_deleted'), 'weather_data', ['is_deleted'], unique=False, if_not_exists=True)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    insp = sa_inspect(bind)

    # Drop soft-delete indexes and columns
    op.drop_index(op.f('ix_weather_data_is_deleted'), table_name='weather_data')
    op.drop_index('idx_weather_location_time', table_name='weather_data')
    op.drop_index('idx_weather_active', table_name='weather_data')
    if _has_column(insp, "weather_data", "deleted_at"):
        op.drop_column('weather_data', 'deleted_at')
    if _has_column(insp, "weather_data", "is_deleted"):
        op.drop_column('weather_data', 'is_deleted')

    op.drop_index(op.f('ix_predictions_is_deleted'), table_name='predictions')
    op.drop_index('idx_prediction_active', table_name='predictions')
    if _has_column(insp, "predictions", "deleted_at"):
        op.drop_column('predictions', 'deleted_at')
    if _has_column(insp, "predictions", "is_deleted"):
        op.drop_column('predictions', 'is_deleted')

    op.drop_index(op.f('ix_alert_history_is_deleted'), table_name='alert_history')
    op.drop_index('idx_alert_active', table_name='alert_history')
    if _has_column(insp, "alert_history", "deleted_at"):
        op.drop_column('alert_history', 'deleted_at')
    if _has_column(insp, "alert_history", "is_deleted"):
        op.drop_column('alert_history', 'is_deleted')

    # Drop tables created by this migration (reverse FK order)
    if insp.has_table("model_registry"):
        op.drop_table("model_registry")
    if insp.has_table("alert_history"):
        op.drop_table("alert_history")
    if insp.has_table("predictions"):
        op.drop_table("predictions")
    if insp.has_table("weather_data"):
        op.drop_table("weather_data")
