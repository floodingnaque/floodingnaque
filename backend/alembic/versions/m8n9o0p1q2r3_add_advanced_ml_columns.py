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
from sqlalchemy import inspect as sa_inspect
import sqlalchemy as sa


# revision identifiers
revision = "m8n9o0p1q2r3"
down_revision = "l7m8n9o0p1q2"
branch_labels = None
depends_on = None

_COLUMNS = [
    ("semantic_version", sa.String(50)),
    ("f2_score", sa.Float()),
    ("cv_mean", sa.Float()),
    ("cv_std", sa.Float()),
    ("training_duration_seconds", sa.Float()),
    ("training_mode", sa.String(50)),
    ("feature_names", sa.Text()),
    ("ensemble_members", sa.Text()),
    ("comparison_report", sa.Text()),
    ("promoted_at", sa.DateTime(timezone=True)),
    ("retired_at", sa.DateTime(timezone=True)),
    ("model_checksum", sa.String(64)),
    ("retrain_trigger", sa.String(100)),
    ("parent_version", sa.Integer()),
]


def upgrade() -> None:
    bind = op.get_bind()
    existing = [c["name"] for c in sa_inspect(bind).get_columns("model_registry")]
    for col_name, col_type in _COLUMNS:
        if col_name not in existing:
            op.add_column("model_registry", sa.Column(col_name, col_type, nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    existing = [c["name"] for c in sa_inspect(bind).get_columns("model_registry")]
    for col_name, _ in reversed(_COLUMNS):
        if col_name in existing:
            op.drop_column("model_registry", col_name)
