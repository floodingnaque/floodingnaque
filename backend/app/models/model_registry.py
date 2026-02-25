"""ModelRegistry ORM model."""

from datetime import datetime, timezone

from app.models.db import Base
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Float, Integer, String, Text


class ModelRegistry(Base):
    """Model version registry and metadata."""

    __tablename__ = "model_registry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(Integer, unique=True, nullable=False, index=True)

    # Model file information
    file_path = Column(String(500), nullable=False)
    algorithm = Column(String(100), default="RandomForest")

    # Performance metrics
    accuracy = Column(Float)
    precision_score = Column(Float)
    recall_score = Column(Float)
    f1_score = Column(Float)
    roc_auc = Column(Float)

    # Training information
    training_date = Column(DateTime)
    dataset_size = Column(Integer)
    dataset_path = Column(String(500))

    # Model parameters (JSON stored as text)
    parameters = Column(Text, info={"description": "JSON serialized model parameters"})
    feature_importance = Column(Text, info={"description": "JSON serialized feature importance"})

    # Status
    is_active = Column(Boolean, default=False, index=True)
    notes = Column(Text, info={"description": "Additional notes about this version"})

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
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
        return f"<ModelRegistry(version={self.version}, accuracy={self.accuracy}, active={self.is_active})>"
