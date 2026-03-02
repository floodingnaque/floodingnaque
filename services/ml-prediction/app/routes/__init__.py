"""Routes package for ML Prediction Service."""

from app.routes.batch import batch_bp
from app.routes.models import models_bp
from app.routes.predict import predict_bp

__all__ = ["predict_bp", "models_bp", "batch_bp"]
