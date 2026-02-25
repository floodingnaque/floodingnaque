"""Prediction ORM model."""

from datetime import datetime, timezone

from app.models.db import Base
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship


class Prediction(Base):
    """Flood prediction records with audit trail."""

    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    weather_data_id = Column(Integer, ForeignKey("weather_data.id", ondelete="SET NULL"), index=True)

    # Prediction results
    prediction = Column(Integer, nullable=False, info={"description": "0=no flood, 1=flood"})
    risk_level = Column(Integer, info={"description": "0=Safe, 1=Alert, 2=Critical"})
    risk_label = Column(String(50), info={"description": "Safe/Alert/Critical"})
    confidence = Column(Float, info={"description": "Prediction confidence (0-1)"})

    # Model information
    model_version = Column(Integer, info={"description": "Model version used"})
    model_name = Column(String(100), default="flood_rf_model")

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    weather_data = relationship("WeatherData", back_populates="predictions")
    alerts = relationship("AlertHistory", back_populates="prediction", cascade="all, delete-orphan")

    # Soft delete support
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("prediction IN (0, 1)", name="valid_prediction"),
        CheckConstraint("risk_level IS NULL OR risk_level IN (0, 1, 2)", name="valid_risk_level"),
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="valid_confidence"),
        Index("idx_prediction_risk", "risk_level"),
        Index("idx_prediction_model", "model_version"),
        Index("idx_prediction_active", "is_deleted"),
        Index("idx_prediction_active_created", "is_deleted", "created_at"),
        Index("idx_prediction_risk_created", "risk_level", "created_at"),
        Index("idx_prediction_active_risk", "is_deleted", "risk_level", "created_at"),
        {"comment": "Flood prediction history for analytics and audit"},
    )

    def __repr__(self):
        return f"<Prediction(id={self.id}, prediction={self.prediction}, risk={self.risk_label})>"

    def soft_delete(self):
        """Mark record as deleted without removing from database."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self):
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None
