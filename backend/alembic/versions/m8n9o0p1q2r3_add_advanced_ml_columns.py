"""Add advanced ML columns to model_registry.

Adds columns for:
- XGBoost / LightGBM / Ensemble metadata
- Enhanced metrics (F2, CV mean/std)
- Training mode, duration, model checksum
- Retraining lineage (parent_version, retrain_trigger)
- Promotion / retirement timestamps
- Feature names, ensemble members, comparison report

Revision ID: m8n9o0p1q2r3
Revises: l7m8n9o0p1q2
Create Date: 2026-03-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "m8n9o0p1q2r3"
down_revision = "l7m8n9o0p1q2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # New metric columns
    op.add_column("model_registry", sa.Column("semantic_version", sa.String(50), nullable=True))
    op.add_column("model_registry", sa.Column("f2_score", sa.Float(), nullable=True))
    op.add_column("model_registry", sa.Column("cv_mean", sa.Float(), nullable=True))
    op.add_column("model_registry", sa.Column("cv_std", sa.Float(), nullable=True))

    # Training metadata
    op.add_column("model_registry", sa.Column("training_duration_seconds", sa.Float(), nullable=True))
    op.add_column("model_registry", sa.Column("training_mode", sa.String(50), nullable=True))

    # Features
    op.add_column("model_registry", sa.Column("feature_names", sa.Text(), nullable=True))

    # Ensemble / comparison
    op.add_column("model_registry", sa.Column("ensemble_members", sa.Text(), nullable=True))
    op.add_column("model_registry", sa.Column("comparison_report", sa.Text(), nullable=True))

    # Lifecycle
    op.add_column("model_registry", sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("model_registry", sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True))

    # Security / provenance
    op.add_column("model_registry", sa.Column("model_checksum", sa.String(64), nullable=True))

    # Retraining lineage
    op.add_column("model_registry", sa.Column("retrain_trigger", sa.String(100), nullable=True))
    op.add_column("model_registry", sa.Column("parent_version", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("model_registry", "parent_version")
    op.drop_column("model_registry", "retrain_trigger")
    op.drop_column("model_registry", "model_checksum")
    op.drop_column("model_registry", "retired_at")
    op.drop_column("model_registry", "promoted_at")
    op.drop_column("model_registry", "comparison_report")
    op.drop_column("model_registry", "ensemble_members")
    op.drop_column("model_registry", "feature_names")
    op.drop_column("model_registry", "training_mode")
    op.drop_column("model_registry", "training_duration_seconds")
    op.drop_column("model_registry", "cv_std")
    op.drop_column("model_registry", "cv_mean")
    op.drop_column("model_registry", "f2_score")
    op.drop_column("model_registry", "semantic_version")
