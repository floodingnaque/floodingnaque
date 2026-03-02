"""ModelRegistry ORM model."""

from datetime import datetime, timezone

from app.models.db import Base
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Float, Integer, String, Text


class ModelRegistry(Base):
    """Model version registry and metadata."""

    __tablename__ = "model_registry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(Integer, unique=True, nullable=False, index=True)

    # Semantic version string (e.g. "2.1.0")
    semantic_version = Column(String(50), info={"description": "Semantic version string (MAJOR.MINOR.PATCH)"})

    # Model file information
    file_path = Column(String(500), nullable=False)
    algorithm = Column(String(100), default="RandomForest")

    # Performance metrics
    accuracy = Column(Float)
    precision_score = Column(Float)
    recall_score = Column(Float)
    f1_score = Column(Float)
    f2_score = Column(Float)
    roc_auc = Column(Float)
    cv_mean = Column(Float, info={"description": "Cross-validation mean F1"})
    cv_std = Column(Float, info={"description": "Cross-validation std deviation"})

    # Training information
    training_date = Column(DateTime)
    training_duration_seconds = Column(Float, info={"description": "How long training took"})
    dataset_size = Column(Integer)
    dataset_path = Column(String(500))
    training_mode = Column(
        String(50),
        info={"description": "Training mode used (basic, production, xgboost, lightgbm, ensemble, comparison)"},
    )

    # Model parameters (JSON stored as text)
    parameters = Column(Text, info={"description": "JSON serialized model parameters"})
    feature_importance = Column(Text, info={"description": "JSON serialized feature importance"})
    feature_names = Column(Text, info={"description": "JSON list of feature column names used"})

    # Ensemble / comparison metadata
    ensemble_members = Column(
        Text,
        info={"description": "JSON list of sub-model names if ensemble (e.g. ['rf','xgb','lgbm'])"},
    )
    comparison_report = Column(
        Text,
        info={"description": "JSON comparison report when trained via comparison mode"},
    )

    # Status
    is_active = Column(Boolean, default=False, index=True)
    promoted_at = Column(DateTime(timezone=True), info={"description": "When this version was promoted to active"})
    retired_at = Column(DateTime(timezone=True), info={"description": "When this version was retired"})
    notes = Column(Text, info={"description": "Additional notes about this version"})

    # Data provenance
    training_data_hash = Column(
        String(64),
        info={"description": "SHA-256 hash of the training dataset for reproducibility"},
    )
    model_checksum = Column(
        String(64),
        info={"description": "SHA-256 checksum of the serialised model file"},
    )

    # Retraining metadata
    retrain_trigger = Column(
        String(100),
        info={"description": "What triggered this training (manual, scheduled, drift, new_data)"},
    )
    parent_version = Column(
        Integer,
        info={"description": "Version this model was retrained from (lineage tracking)"},
    )

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    created_by = Column(String(100), info={"description": "User or system that created this"})

    __table_args__ = (
        CheckConstraint("accuracy IS NULL OR (accuracy >= 0 AND accuracy <= 1)", name="valid_accuracy"),
        CheckConstraint(
            "precision_score IS NULL OR (precision_score >= 0 AND precision_score <= 1)", name="valid_precision"
        ),
        CheckConstraint("recall_score IS NULL OR (recall_score >= 0 AND recall_score <= 1)", name="valid_recall"),
        CheckConstraint("f1_score IS NULL OR (f1_score >= 0 AND f1_score <= 1)", name="valid_f1"),
        {"comment": "Model version tracking and performance registry"},
    )

    def __repr__(self):
        return (
            f"<ModelRegistry(version={self.version}, algorithm={self.algorithm}, "
            f"f1={self.f1_score}, active={self.is_active})>"
        )

    def to_dict(self):
        """Serialise to dictionary for API responses."""
        import json as _json

        def _safe_json(val):
            if val is None:
                return None
            try:
                return _json.loads(val)
            except (TypeError, _json.JSONDecodeError):
                return val

        return {
            "id": self.id,
            "version": self.version,
            "semantic_version": self.semantic_version,
            "file_path": self.file_path,
            "algorithm": self.algorithm,
            "metrics": {
                "accuracy": self.accuracy,
                "precision": self.precision_score,
                "recall": self.recall_score,
                "f1_score": self.f1_score,
                "f2_score": self.f2_score,
                "roc_auc": self.roc_auc,
                "cv_mean": self.cv_mean,
                "cv_std": self.cv_std,
            },
            "training_date": self.training_date.isoformat() if self.training_date else None,
            "training_duration_seconds": self.training_duration_seconds,
            "training_mode": self.training_mode,
            "dataset_size": self.dataset_size,
            "is_active": self.is_active,
            "promoted_at": self.promoted_at.isoformat() if self.promoted_at else None,
            "retired_at": self.retired_at.isoformat() if self.retired_at else None,
            "parameters": _safe_json(self.parameters),
            "feature_names": _safe_json(self.feature_names),
            "feature_importance": _safe_json(self.feature_importance),
            "ensemble_members": _safe_json(self.ensemble_members),
            "retrain_trigger": self.retrain_trigger,
            "parent_version": self.parent_version,
            "model_checksum": self.model_checksum,
            "training_data_hash": self.training_data_hash,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
        }
