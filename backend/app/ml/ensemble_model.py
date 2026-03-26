"""
Ensemble Model Framework for Floodingnaque.

Provides:
- ``EnsembleTrainer``: trains RF + XGBoost + LightGBM with soft-voting,
  cross-validation, and HMAC-signed artifact storage.
- ``EnsemblePredictor``: loads the latest ensemble via ``ModelLoader``
  and returns predictions with confidence scores.
- ``ModelRegistry``: manages versioned model artifacts on disk.

Integration Notes
-----------------
- Model artifacts are stored in ``Config.MODEL_DIR`` (default ``models/``).
- HMAC signing reuses the same ``MODEL_SIGNING_KEY`` as ``predict.py``.
- Feature names align with ``DataBundle.feature_names()`` / v6 training pipeline.
- Ensemble support is gated behind the ``FLOODINGNAQUE_FLAG_ENSEMBLE_MODEL``
  feature flag.
"""

import hashlib
import json
import logging
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import pandas as pd
from app.services.data_aggregation_service import DataBundle
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_DEFAULT_MODELS_DIR = _BACKEND_DIR / "models"

# V6 feature names - single source of truth via DataBundle
FEATURE_NAMES: List[str] = DataBundle.feature_names()

RANDOM_STATE = 42


# ---------------------------------------------------------------------------
# Model Registry
# ---------------------------------------------------------------------------


@dataclass
class ModelArtifact:
    """Metadata for a stored model artifact."""

    version: str
    model_type: str  # "ensemble" or "single"
    path: str
    metadata_path: str
    created_at: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    checksum: Optional[str] = None
    hmac_signature: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ModelRegistry:
    """
    Manages versioned model artifacts on disk.

    Directory structure::

        models/
          ensemble_v1_20250101_120000.joblib
          ensemble_v1_20250101_120000.json
          ensemble_v2_20250115_090000.joblib
          ...
    """

    def __init__(self, models_dir: Optional[str] = None):
        self.models_dir = Path(models_dir) if models_dir else _DEFAULT_MODELS_DIR
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def save_artifact(
        self,
        model: Any,
        version: str,
        metrics: Dict[str, Any],
        model_type: str = "ensemble",
    ) -> ModelArtifact:
        """
        Save a model artifact with metadata and optional HMAC signing.

        Args:
            model: Trained sklearn model/pipeline.
            version: Version label (e.g. "v1").
            metrics: Training/evaluation metrics dict.
            model_type: "ensemble" or "single".

        Returns:
            ModelArtifact with file paths and metadata.
        """
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        base_name = f"{model_type}_{version}_{ts}"
        model_path = self.models_dir / f"{base_name}.joblib"
        meta_path = self.models_dir / f"{base_name}.json"

        # Save model
        joblib.dump(model, model_path)
        logger.info("Model saved to %s", model_path)

        # Compute checksum
        checksum = self._compute_checksum(str(model_path))

        # HMAC signing (reuse predict.py pattern)
        hmac_sig = None
        try:
            from app.services.predict import _get_model_signing_key, compute_model_hmac_signature

            key = _get_model_signing_key()
            if key:
                hmac_sig = compute_model_hmac_signature(str(model_path), key)
        except Exception as exc:
            logger.warning("HMAC signing skipped: %s", exc)

        # Save metadata
        metadata = {
            "version": version,
            "model_type": model_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "features": FEATURE_NAMES,
            "metrics": metrics,
            "checksum": checksum,
            "hmac_signature": hmac_sig,
            "random_state": RANDOM_STATE,
        }
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return ModelArtifact(
            version=version,
            model_type=model_type,
            path=str(model_path),
            metadata_path=str(meta_path),
            created_at=metadata["created_at"],
            metrics=metrics,
            checksum=checksum,
            hmac_signature=hmac_sig,
        )

    def list_artifacts(self, model_type: str = "ensemble") -> List[ModelArtifact]:
        """List all saved artifacts of a given type, sorted newest-first."""
        artifacts: List[ModelArtifact] = []
        for meta_file in sorted(self.models_dir.glob(f"{model_type}_*.json"), reverse=True):
            try:
                with open(meta_file) as f:
                    meta = json.load(f)
                model_file = meta_file.with_suffix(".joblib")
                if model_file.exists():
                    artifacts.append(
                        ModelArtifact(
                            version=meta.get("version", "unknown"),
                            model_type=meta.get("model_type", model_type),
                            path=str(model_file),
                            metadata_path=str(meta_file),
                            created_at=meta.get("created_at", ""),
                            metrics=meta.get("metrics", {}),
                            checksum=meta.get("checksum"),
                            hmac_signature=meta.get("hmac_signature"),
                        )
                    )
            except (json.JSONDecodeError, IOError) as exc:
                logger.warning("Skipping invalid metadata %s: %s", meta_file, exc)
        return artifacts

    def get_latest(self, model_type: str = "ensemble") -> Optional[ModelArtifact]:
        """Return the newest artifact or None."""
        artifacts = self.list_artifacts(model_type)
        return artifacts[0] if artifacts else None

    @staticmethod
    def _compute_checksum(path: str) -> str:
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()


# ---------------------------------------------------------------------------
# Ensemble Trainer
# ---------------------------------------------------------------------------


class EnsembleTrainer:
    """
    Trains a soft-voting ensemble of RF + XGBoost + LightGBM.

    Falls back gracefully if XGBoost or LightGBM are not installed,
    using RF-only in that case.
    """

    def __init__(
        self,
        cv_folds: int = 10,
        random_state: int = RANDOM_STATE,
        models_dir: Optional[str] = None,
    ):
        self.cv_folds = cv_folds
        self.random_state = random_state
        self.registry = ModelRegistry(models_dir)

    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        version: str = "v1",
        grid_search: bool = False,
    ) -> ModelArtifact:
        """
        Train the ensemble model.

        Uses stratified 80/20 train/val split for final evaluation
        metrics, plus k-fold CV for cross-validated scores.

        Args:
            X: Feature matrix with columns matching FEATURE_NAMES.
            y: Target variable (0=Safe, 1=Alert, 2=Critical).
            version: Version label for artifact naming.
            grid_search: Whether to run hyperparameter grid search.

        Returns:
            ModelArtifact with metrics and file paths.
        """
        logger.info(
            "Training ensemble %s on %d samples, %d features, cv=%d",
            version,
            len(X),
            X.shape[1],
            self.cv_folds,
        )

        # Stratified train/val split for held-out evaluation
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, stratify=y, random_state=self.random_state
        )

        # Build estimators (graceful fallback)
        estimators = self._build_estimators(grid_search)

        if len(estimators) > 1:
            ensemble = VotingClassifier(
                estimators=estimators,
                voting="soft",
                n_jobs=-1,
            )
        else:
            # Only RF available - use it directly
            ensemble = estimators[0][1]

        # Fit on training split
        ensemble.fit(X_train, y_train)

        # Cross-validation on training split
        cv = StratifiedKFold(n_splits=self.cv_folds, shuffle=True, random_state=self.random_state)
        cv_scores = cross_val_score(ensemble, X_train, y_train, cv=cv, scoring="accuracy")

        # Held-out evaluation (trustworthy metrics)
        y_pred = ensemble.predict(X_val)
        val_accuracy = float(accuracy_score(y_val, y_pred))
        val_f1 = float(f1_score(y_val, y_pred, average="weighted"))
        val_report = classification_report(y_val, y_pred, output_dict=True)

        metrics = {
            "cv_mean": round(float(cv_scores.mean()), 4),
            "cv_std": round(float(cv_scores.std()), 4),
            "cv_folds": self.cv_folds,
            "val_accuracy": round(val_accuracy, 4),
            "val_f1_weighted": round(val_f1, 4),
            "val_report": val_report,
            "train_samples": len(X_train),
            "val_samples": len(X_val),
            "n_estimators": len(estimators),
            "estimator_names": [name for name, _ in estimators],
        }

        # Refit on full data for production artifact
        ensemble.fit(X, y)

        artifact = self.registry.save_artifact(
            model=ensemble,
            version=version,
            metrics=metrics,
            model_type="ensemble",
        )

        logger.info(
            "Ensemble %s trained: cv=%.4f±%.4f, val_acc=%.4f, val_f1=%.4f",
            version,
            metrics["cv_mean"],
            metrics["cv_std"],
            val_accuracy,
            val_f1,
        )
        return artifact

    def _build_estimators(self, grid_search: bool) -> List[Tuple[str, Any]]:
        """Build the list of estimators, falling back if libs are missing."""
        estimators: List[Tuple[str, Any]] = []

        # Random Forest (always available)
        rf = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=self.random_state,
            n_jobs=-1,
        )
        estimators.append(("rf", rf))

        # XGBoost (optional)
        try:
            from xgboost import XGBClassifier

            xgb = XGBClassifier(
                n_estimators=200,
                max_depth=8,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                use_label_encoder=False,
                eval_metric="mlogloss",
                random_state=self.random_state,
                n_jobs=-1,
            )
            estimators.append(("xgb", xgb))
        except ImportError:
            logger.info("XGBoost not installed - skipping")

        # LightGBM (optional)
        try:
            from lightgbm import LGBMClassifier

            lgbm = LGBMClassifier(
                n_estimators=200,
                max_depth=8,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                class_weight="balanced",
                random_state=self.random_state,
                n_jobs=-1,
                verbose=-1,
            )
            estimators.append(("lgbm", lgbm))
        except ImportError:
            logger.info("LightGBM not installed - skipping")

        return estimators


# ---------------------------------------------------------------------------
# Ensemble Predictor
# ---------------------------------------------------------------------------


class EnsemblePredictor:
    """
    Loads the latest ensemble model and provides prediction interface.

    Delegates to ``ModelLoader`` for HMAC verification and caching when
    ensemble mode is enabled via feature flag.
    """

    _instance: Optional["EnsemblePredictor"] = None
    _lock = threading.Lock()

    def __init__(self, models_dir: Optional[str] = None):
        self.registry = ModelRegistry(models_dir)
        self._model: Optional[Any] = None
        self._artifact: Optional[ModelArtifact] = None

    @classmethod
    def get_instance(cls) -> "EnsemblePredictor":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            cls._instance = None

    @staticmethod
    def is_enabled() -> bool:
        """Check if ensemble model is enabled via feature flag."""
        return os.getenv("FLOODINGNAQUE_FLAG_ENSEMBLE_MODEL", "false").lower() == "true"

    def load_latest(self) -> bool:
        """
        Load the latest ensemble model from the registry.

        Uses ``ModelLoader`` integrity verification when possible.

        Returns:
            True if a model was successfully loaded.
        """
        artifact = self.registry.get_latest("ensemble")
        if not artifact:
            logger.warning("No ensemble artifacts found")
            return False

        try:
            from app.services.predict import verify_model_integrity

            if not verify_model_integrity(artifact.path, artifact.checksum):
                logger.error("Ensemble model integrity check failed: %s", artifact.path)
                return False
        except Exception as exc:
            logger.warning("Integrity check skipped: %s", exc)

        try:
            self._model = joblib.load(artifact.path)
            self._artifact = artifact
            logger.info("Loaded ensemble model %s from %s", artifact.version, artifact.path)
            return True
        except Exception as exc:
            logger.error("Failed to load ensemble: %s", exc)
            return False

    def predict(self, features: List[float]) -> Dict[str, Any]:
        """
        Run prediction with the loaded ensemble model.

        Args:
            features: Feature vector in V6 order (from DataBundle.to_feature_vector()).

        Returns:
            Dict with prediction, confidence, model_version.
        """
        if self._model is None:
            if not self.load_latest():
                return {"error": "No ensemble model available"}

        model = self._model
        if model is None:
            return {"error": "No ensemble model available"}

        df = pd.DataFrame([features], columns=FEATURE_NAMES)

        prediction = int(model.predict(df)[0])

        confidence = 0.0
        if hasattr(model, "predict_proba"):
            probas = model.predict_proba(df)[0]
            confidence = float(max(probas))

        return {
            "prediction": prediction,
            "confidence": round(confidence, 4),
            "model_version": self._artifact.version if self._artifact else "unknown",
            "model_type": "ensemble",
        }
