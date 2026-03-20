#!/usr/bin/env python
"""
Unified Training Module for Floodingnaque
==========================================

Consolidates all training scripts into a single, configurable module.
Uses a strategy pattern to support different training modes.

Training Modes:
    - basic: Simple Random Forest training (train.py)
    - pagasa: PAGASA-enhanced with multi-station support (train_pagasa.py)
    - production: Production-ready with calibration (train_production.py)
    - progressive: 8-phase progressive training (train_progressive.py)
    - enhanced: Multi-level classification (train_enhanced.py)
    - enterprise: MLflow + registry integration (train_enterprise.py)
    - ultimate: Full combined pipeline (train_ultimate.py)

Usage:
    from scripts.train_unified import UnifiedTrainer, TrainingMode

    # Basic training
    trainer = UnifiedTrainer(mode=TrainingMode.BASIC)
    trainer.train()

    # Production training with grid search
    trainer = UnifiedTrainer(mode=TrainingMode.PRODUCTION)
    trainer.train(grid_search=True, shap=True)

    # Progressive training specific phase
    trainer = UnifiedTrainer(mode=TrainingMode.PROGRESSIVE)
    trainer.train(phase=5, quick=True)

CLI Usage:
    python -m scripts train                          # Basic
    python -m scripts train --mode production        # Production
    python -m scripts train --mode progressive       # All phases

Author: Floodingnaque Team
Date: 2026-01-23
"""

import argparse
import json
import logging
import sys
import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Type, Union, cast

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import (
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
    StackingClassifier,
    VotingClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    fbeta_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import (
    GridSearchCV,
    RandomizedSearchCV,
    StratifiedKFold,
    TimeSeriesSplit,
    cross_val_score,
    train_test_split,
)

# Setup
warnings.filterwarnings("ignore", category=FutureWarning)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
MODELS_DIR = BACKEND_DIR / "models"
REPORTS_DIR = BACKEND_DIR / "reports"
DATA_DIR = BACKEND_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"


class TrainingMode(Enum):
    """Available training modes."""

    BASIC = "basic"
    PAGASA = "pagasa"
    PRODUCTION = "production"
    PROGRESSIVE = "progressive"
    ENHANCED = "enhanced"
    ENTERPRISE = "enterprise"
    ULTIMATE = "ultimate"
    DEEP_LEARNING = "deep_learning"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    ENSEMBLE = "ensemble"
    COMPARISON = "comparison"


@dataclass
class TrainingConfig:
    """Configuration for training."""

    # Data settings
    data_path: Optional[str] = None
    test_size: float = 0.2
    random_state: int = 42

    # Model settings
    n_estimators: int = 200
    max_depth: int = 15
    min_samples_split: int = 5
    min_samples_leaf: int = 2
    class_weight: Literal["balanced", "balanced_subsample"] = "balanced"

    # Training options
    grid_search: bool = False
    randomized_search: bool = False
    cv_folds: int = 5
    n_iter: int = 50  # For randomized search

    # Output settings
    output_dir: Optional[str] = None
    save_metadata: bool = True
    save_plots: bool = True

    # Mode-specific options
    version: Optional[int] = None
    phase: Optional[int] = None
    quick: bool = False
    with_smote: bool = False
    all_stations: bool = False
    shap: bool = False
    mlflow: bool = False
    promote: Optional[str] = None
    multi_level: bool = False

    # Feature enrichment
    include_enso: bool = False
    include_spatial: bool = False
    default_barangay: Optional[str] = None

    # Deep learning
    dl_model_type: str = "lstm"  # "lstm" or "transformer"
    dl_sequence_length: int = 14
    dl_epochs: int = 100
    dl_hidden_dim: int = 128


# =============================================================================
# Feature Configurations
# =============================================================================

FEATURE_CONFIGS = {
    "basic": [
        "temperature",
        "humidity",
        "precipitation",
        "is_monsoon_season",
        "month",
    ],
    "pagasa": [
        "temperature",
        "humidity",
        "precipitation",
        "is_monsoon_season",
        "month",
        "precip_3day_sum",
        "precip_7day_sum",
        "precip_14day_sum",
        "rain_streak",
        "temp_humidity_interaction",
        "humidity_precip_interaction",
        "monsoon_precip_interaction",
    ],
    "production": [
        "temperature",
        "humidity",
        "precipitation",
        "month",
        "is_monsoon_season",
        "temp_humidity_interaction",
        "humidity_precip_interaction",
        "temp_precip_interaction",
        "monsoon_precip_interaction",
        "saturation_risk",
    ],
    "enhanced": [
        "temperature",
        "humidity",
        "precipitation",
        "is_monsoon_season",
        "month",
        "temp_humidity_interaction",
        "humidity_precip_interaction",
        "temp_precip_interaction",
        "monsoon_precip_interaction",
        "saturation_risk",
    ],
}

# =============================================================================
# Hyperparameter Grids
# =============================================================================

PARAM_GRIDS = {
    "basic": {
        "n_estimators": [100, 200, 300],
        "max_depth": [10, 15, 20, None],
        "min_samples_split": [2, 5, 10],
        "min_samples_leaf": [1, 2, 4],
    },
    "production": {
        "n_estimators": [200, 300, 500],
        "max_depth": [10, 15, 20, 25, None],
        "min_samples_split": [2, 5, 10],
        "min_samples_leaf": [1, 2, 4],
        "max_features": ["sqrt", "log2", 0.5],
        "criterion": ["gini", "entropy"],
    },
    "randomized": {
        "n_estimators": [100, 150, 200, 250, 300],
        "max_depth": [10, 15, 20, 25, None],
        "min_samples_split": [2, 5, 10, 15],
        "min_samples_leaf": [1, 2, 4, 6],
        "max_features": ["sqrt", "log2", 0.3, 0.5],
    },
}

# =============================================================================
# Data Version Registry
# =============================================================================

VERSION_REGISTRY = {
    1: {
        "name": "Baseline_2022",
        "file": "cumulative_up_to_2022.csv",
        "description": "Official Records 2022 Only",
    },
    2: {
        "name": "Extended_2023",
        "file": "cumulative_up_to_2023.csv",
        "description": "Official Records 2022-2023",
    },
    3: {
        "name": "Extended_2024",
        "file": "cumulative_up_to_2024.csv",
        "description": "Official Records 2022-2024",
    },
    4: {
        "name": "Full_Official_2025",
        "file": "cumulative_up_to_2025.csv",
        "description": "Official Records 2022-2025 (Complete)",
    },
    5: {
        "name": "PAGASA_Merged",
        "file": "pagasa_training_dataset.csv",
        "description": "PAGASA Weather Data (2020-2025)",
    },
    6: {
        "name": "Ultimate_Combined",
        "files": ["cumulative_up_to_2025.csv", "pagasa_training_dataset.csv"],
        "description": "Combined: Official + PAGASA",
    },
}


# =============================================================================
# Training Strategy Base
# =============================================================================


class TrainingStrategy(ABC):
    """Abstract base class for training strategies."""

    def __init__(self, config: TrainingConfig):
        self.config = config
        self.models_dir = Path(config.output_dir) if config.output_dir else MODELS_DIR
        self.reports_dir = REPORTS_DIR
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        self.model = None
        self.feature_names: List[str] = []
        self.metrics: Dict[str, Any] = {}
        self.training_info: Dict[str, Any] = {}

    @abstractmethod
    def get_features(self) -> List[str]:
        """Get features for this training mode."""
        pass

    @abstractmethod
    def get_default_data_path(self) -> Path:
        """Get default data path for this mode."""
        pass

    def load_data(self, data_path: Optional[str] = None) -> pd.DataFrame:
        """Load training data."""
        if data_path:
            path = Path(data_path)
        else:
            path = self.get_default_data_path()

        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {path}")

        df = pd.read_csv(path)
        logger.info(f"Loaded {len(df)} records from {path.name}")

        self.training_info["data_source"] = str(path)
        self.training_info["total_records"] = len(df)

        return df

    def prepare_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare feature matrix and target vector."""
        features = self.get_features()

        # ── Optional ENSO feature enrichment ────────────────────────────────
        if self.config.include_enso:
            try:
                from app.services.enso_service import add_enso_features, get_enso_feature_names

                df = add_enso_features(df, include_lags=True)
                enso_feats = get_enso_feature_names(include_lags=True)
                features = features + [f for f in enso_feats if f not in features]
                logger.info(f"ENSO features added: {enso_feats}")
            except Exception as e:
                logger.warning(f"ENSO enrichment skipped: {e}")

        # ── Optional spatial feature enrichment ─────────────────────────────
        if self.config.include_spatial:
            try:
                from app.services.spatial_features import add_spatial_features, get_spatial_feature_names

                df = add_spatial_features(df, default_barangay=self.config.default_barangay)
                spatial_feats = get_spatial_feature_names()
                features = features + [f for f in spatial_feats if f not in features]
                logger.info(f"Spatial features added: {spatial_feats}")
            except Exception as e:
                logger.warning(f"Spatial enrichment skipped: {e}")

        available = [f for f in features if f in df.columns]
        missing = [f for f in features if f not in df.columns]

        if missing:
            logger.warning(f"Missing features: {missing}")

        if not available:
            raise ValueError("No features available for training")

        X = df[available].copy()
        y = df["flood"].copy()

        # Fill missing values
        X = X.fillna(X.median())

        self.feature_names = available
        logger.info(f"Features ({len(available)}): {available}")
        logger.info(f"Target distribution: {y.value_counts().to_dict()}")

        return X, y

    def create_model(self) -> RandomForestClassifier:
        """Create the base model."""
        return RandomForestClassifier(
            n_estimators=self.config.n_estimators,
            max_depth=self.config.max_depth,
            min_samples_split=self.config.min_samples_split,
            min_samples_leaf=self.config.min_samples_leaf,
            max_features="sqrt",
            class_weight=self.config.class_weight,
            random_state=self.config.random_state,
            n_jobs=-1,
        )

    def train_with_grid_search(
        self, X_train: pd.DataFrame, y_train: pd.Series, param_grid: Optional[Dict] = None
    ) -> RandomForestClassifier:
        """Train with grid search optimization."""
        if param_grid is None:
            param_grid = PARAM_GRIDS["basic"]

        logger.info("Running grid search hyperparameter optimization...")

        base_model = RandomForestClassifier(
            class_weight=self.config.class_weight,
            random_state=self.config.random_state,
            n_jobs=-1,
        )

        grid_search = GridSearchCV(
            base_model,
            param_grid,
            cv=StratifiedKFold(self.config.cv_folds, shuffle=True, random_state=self.config.random_state),
            scoring="f1_weighted",
            n_jobs=-1,
            verbose=1,
        )
        grid_search.fit(X_train, y_train)

        logger.info(f"Best params: {grid_search.best_params_}")
        logger.info(f"Best CV score: {grid_search.best_score_:.4f}")

        self.training_info["best_params"] = grid_search.best_params_
        self.training_info["best_cv_score"] = float(grid_search.best_score_)

        return cast(RandomForestClassifier, grid_search.best_estimator_)

    def train_with_randomized_search(
        self, X_train: pd.DataFrame, y_train: pd.Series, param_dist: Optional[Dict] = None
    ) -> RandomForestClassifier:
        """Train with randomized search optimization."""
        if param_dist is None:
            param_dist = PARAM_GRIDS["randomized"]

        logger.info("Running randomized search hyperparameter optimization...")

        base_model = RandomForestClassifier(
            class_weight=self.config.class_weight,
            random_state=self.config.random_state,
            n_jobs=-1,
        )

        search = RandomizedSearchCV(
            base_model,
            param_dist,
            n_iter=self.config.n_iter,
            cv=StratifiedKFold(self.config.cv_folds, shuffle=True, random_state=self.config.random_state),
            scoring="f1_weighted",
            n_jobs=-1,
            verbose=1,
            random_state=self.config.random_state,
        )
        search.fit(X_train, y_train)

        logger.info(f"Best params: {search.best_params_}")
        logger.info(f"Best CV score: {search.best_score_:.4f}")

        self.training_info["best_params"] = search.best_params_
        self.training_info["best_cv_score"] = float(search.best_score_)

        return cast(RandomForestClassifier, search.best_estimator_)

    def evaluate_model(
        self,
        model: Union[RandomForestClassifier, CalibratedClassifierCV],
        X_test: pd.DataFrame,
        y_test: pd.Series,
        X_full: Optional[pd.DataFrame] = None,
        y_full: Optional[pd.Series] = None,
    ) -> Dict[str, float]:
        """Evaluate model performance.

        Held-out metrics (accuracy, precision, recall, F1, ROC-AUC) are computed
        on the test set.  Cross-validation is run on the **full** dataset when
        provided, giving a more robust generalisation estimate.
        """
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]

        metrics = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision": float(precision_score(y_test, y_pred, average="weighted", zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, average="weighted", zero_division=0)),
            "f1_score": float(f1_score(y_test, y_pred, average="weighted", zero_division=0)),
            "roc_auc": float(roc_auc_score(y_test, y_pred_proba)),
        }

        # Cross-validation on the full dataset for robust generalisation estimate
        cv_X = X_full if X_full is not None else X_test
        cv_y = y_full if y_full is not None else y_test
        n_folds = min(self.config.cv_folds, len(cv_y) // 2)
        if n_folds >= 2:
            cv_scores = cross_val_score(
                model,
                cv_X,
                cv_y,
                cv=StratifiedKFold(n_folds, shuffle=True, random_state=self.config.random_state),
                scoring="f1_weighted",
                n_jobs=-1,
            )
            metrics["cv_mean"] = float(cv_scores.mean())
            metrics["cv_std"] = float(cv_scores.std())
        else:
            metrics["cv_mean"] = metrics["f1_score"]
            metrics["cv_std"] = 0.0

        logger.info(f"Metrics: F1={metrics['f1_score']:.4f}, ROC-AUC={metrics['roc_auc']:.4f}")
        if X_full is not None:
            logger.info(f"CV ({n_folds}-fold on full data): mean={metrics['cv_mean']:.4f} +/- {metrics['cv_std']:.4f}")

        return metrics

    def save_model(self, model, name: str, metrics: Dict[str, Any]) -> Path:
        """Save model and metadata."""
        model_path = self.models_dir / f"{name}.joblib"
        joblib.dump(model, model_path)
        logger.info(f"Model saved: {model_path}")

        # Save metadata
        if self.config.save_metadata:
            metadata = {
                "name": name,
                "created_at": datetime.now().isoformat(),
                "model_type": type(model).__name__,
                "features": self.feature_names,
                "metrics": metrics,
                "training_info": self.training_info,
                "config": {
                    "n_estimators": self.config.n_estimators,
                    "max_depth": self.config.max_depth,
                    "min_samples_split": self.config.min_samples_split,
                    "min_samples_leaf": self.config.min_samples_leaf,
                    "class_weight": self.config.class_weight,
                },
            }
            metadata_path = model_path.with_suffix(".json")
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"Metadata saved: {metadata_path}")

        return model_path

    @abstractmethod
    def train(self, **kwargs) -> Dict[str, Any]:
        """Execute training. Returns metrics and model paths."""
        pass


# =============================================================================
# Concrete Training Strategies
# =============================================================================


class BasicTrainingStrategy(TrainingStrategy):
    """Basic training with simple Random Forest."""

    def get_features(self) -> List[str]:
        return FEATURE_CONFIGS["basic"]

    def get_default_data_path(self) -> Path:
        path = PROCESSED_DIR / "cumulative_up_to_2025.csv"
        if not path.exists():
            path = DATA_DIR / "synthetic_dataset.csv"
        return path

    def train(self, **kwargs) -> Dict[str, Any]:
        """Train basic model."""
        logger.info("=" * 60)
        logger.info("BASIC TRAINING")
        logger.info("=" * 60)

        # Load and prepare data
        df = self.load_data(self.config.data_path)
        X, y = self.prepare_features(df)

        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.config.test_size, random_state=self.config.random_state, stratify=y
        )

        logger.info(f"Train: {len(X_train)}, Test: {len(X_test)}")

        # Train
        if self.config.grid_search:
            model = self.train_with_grid_search(X_train, y_train)
        elif self.config.randomized_search:
            model = self.train_with_randomized_search(X_train, y_train)
        else:
            model = self.create_model()
            model.fit(X_train, y_train)

        # Evaluate
        metrics = self.evaluate_model(model, X_test, y_test, X_full=X, y_full=y)
        self.metrics = metrics
        self.model = model

        # Save
        model_path = self.save_model(model, "flood_rf_model", metrics)

        return {
            "model_path": str(model_path),
            "metrics": metrics,
            "features": self.feature_names,
        }


class PAGASATrainingStrategy(TrainingStrategy):
    """PAGASA-enhanced training with multi-station support."""

    def get_features(self) -> List[str]:
        return FEATURE_CONFIGS["pagasa"]

    def get_default_data_path(self) -> Path:
        return PROCESSED_DIR / "pagasa_training_dataset.csv"

    def train(self, **kwargs) -> Dict[str, Any]:
        """Train PAGASA-enhanced model."""
        logger.info("=" * 60)
        logger.info("PAGASA-ENHANCED TRAINING")
        logger.info("=" * 60)

        # Load and prepare data
        df = self.load_data(self.config.data_path)
        X, y = self.prepare_features(df)

        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.config.test_size, random_state=self.config.random_state, stratify=y
        )

        # Train with optional optimization
        if self.config.grid_search:
            model = self.train_with_grid_search(X_train, y_train, PARAM_GRIDS["production"])
        else:
            model = self.create_model()
            model.fit(X_train, y_train)

        # Evaluate
        metrics = self.evaluate_model(model, X_test, y_test, X_full=X, y_full=y)
        self.metrics = metrics
        self.model = model

        # Save
        model_path = self.save_model(model, "flood_rf_model_pagasa", metrics)

        return {
            "model_path": str(model_path),
            "metrics": metrics,
            "features": self.feature_names,
        }


class ProductionTrainingStrategy(TrainingStrategy):
    """Production-ready training with calibration."""

    def get_features(self) -> List[str]:
        return FEATURE_CONFIGS["production"]

    def get_default_data_path(self) -> Path:
        path = PROCESSED_DIR / "cumulative_up_to_2025.csv"
        if not path.exists():
            path = PROCESSED_DIR / "pagasa_training_dataset.csv"
        return path

    def train(self, **kwargs) -> Dict[str, Any]:
        """Train production-ready model."""
        logger.info("=" * 60)
        logger.info("PRODUCTION TRAINING")
        logger.info("=" * 60)

        # Load and prepare data
        df = self.load_data(self.config.data_path)
        X, y = self.prepare_features(df)

        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.config.test_size, random_state=self.config.random_state, stratify=y
        )

        # Train with grid search for production
        if self.config.grid_search:
            model = self.train_with_grid_search(X_train, y_train, PARAM_GRIDS["production"])
        else:
            model = self.create_model()
            model.fit(X_train, y_train)

        # Calibrate for better probability estimates
        logger.info("Calibrating model...")
        calibrated_model = CalibratedClassifierCV(model, cv=5, method="isotonic")
        calibrated_model.fit(X_train, y_train)

        # Evaluate calibrated model
        metrics = self.evaluate_model(calibrated_model, X_test, y_test, X_full=X, y_full=y)
        self.metrics = metrics
        self.model = calibrated_model

        # Save both models
        self.save_model(model, "flood_rf_model_production_uncalibrated", metrics)
        model_path = self.save_model(calibrated_model, "flood_rf_model_production", metrics)

        # Also save as default
        default_path = self.models_dir / "flood_rf_model.joblib"
        joblib.dump(calibrated_model, default_path)
        logger.info(f"Also saved as default: {default_path}")

        return {
            "model_path": str(model_path),
            "metrics": metrics,
            "features": self.feature_names,
        }


class ProgressiveTrainingStrategy(TrainingStrategy):
    """Progressive training through all data versions."""

    def get_features(self) -> List[str]:
        return FEATURE_CONFIGS["production"]

    def get_default_data_path(self) -> Path:
        return PROCESSED_DIR / "cumulative_up_to_2025.csv"

    def train(self, **kwargs) -> Dict[str, Any]:
        """Train progressively through all versions."""
        logger.info("=" * 60)
        logger.info("PROGRESSIVE TRAINING")
        logger.info("=" * 60)

        phase = self.config.phase
        results = {}

        if phase:
            # Train single phase
            phases = [phase]
        else:
            # Train all phases
            phases = list(VERSION_REGISTRY.keys())

        for p in phases:
            version_info = VERSION_REGISTRY.get(p)
            if not version_info:
                logger.warning(f"Unknown phase: {p}")
                continue

            logger.info(f"\n--- Phase {p}: {version_info['name']} ---")
            logger.info(f"Description: {version_info['description']}")

            # Handle multi-file versions
            if "files" in version_info:
                # Merge multiple files
                dfs = []
                for f in version_info["files"]:
                    path = PROCESSED_DIR / f
                    if path.exists():
                        dfs.append(pd.read_csv(path))
                if dfs:
                    df = pd.concat(dfs, ignore_index=True).drop_duplicates()
                else:
                    logger.warning(f"No data files found for phase {p}")
                    continue
            else:
                path = PROCESSED_DIR / version_info["file"]
                if not path.exists():
                    logger.warning(f"Data not found: {path}")
                    continue
                df = pd.read_csv(path)

            logger.info(f"Loaded {len(df)} records")

            # Prepare and train
            X, y = self.prepare_features(df)
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=self.config.test_size, random_state=self.config.random_state, stratify=y
            )

            model = self.create_model()
            model.fit(X_train, y_train)

            metrics = self.evaluate_model(model, X_test, y_test, X_full=X, y_full=y)

            # Save
            model_name = f"flood_rf_model_v{p}_{version_info['name']}"
            model_path = self.save_model(model, model_name, metrics)

            results[f"v{p}"] = {
                "name": version_info["name"],
                "model_path": str(model_path),
                "metrics": metrics,
                "records": len(df),
            }

        # Save progression report
        report_path = self.reports_dir / f"progression_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Progression report: {report_path}")

        return results


class EnhancedTrainingStrategy(TrainingStrategy):
    """Enhanced training with multi-level classification."""

    def get_features(self) -> List[str]:
        return FEATURE_CONFIGS["enhanced"]

    def get_default_data_path(self) -> Path:
        return PROCESSED_DIR / "cumulative_up_to_2025.csv"

    def train(self, **kwargs) -> Dict[str, Any]:
        """Train enhanced model with optional multi-level classification."""
        logger.info("=" * 60)
        logger.info("ENHANCED TRAINING")
        logger.info("=" * 60)

        # Load and prepare data
        df = self.load_data(self.config.data_path)
        X, y = self.prepare_features(df)

        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.config.test_size, random_state=self.config.random_state, stratify=y
        )

        # Train with randomized search
        if self.config.randomized_search:
            model = self.train_with_randomized_search(X_train, y_train)
        elif self.config.grid_search:
            model = self.train_with_grid_search(X_train, y_train)
        else:
            model = self.create_model()
            model.fit(X_train, y_train)

        # Evaluate
        metrics = self.evaluate_model(model, X_test, y_test, X_full=X, y_full=y)
        self.metrics = metrics
        self.model = model

        # Save
        model_path = self.save_model(model, "flood_rf_model_enhanced", metrics)

        return {
            "model_path": str(model_path),
            "metrics": metrics,
            "features": self.feature_names,
        }


class XGBoostTrainingStrategy(TrainingStrategy):
    """XGBoost training strategy."""

    def get_features(self) -> List[str]:
        return FEATURE_CONFIGS["production"]

    def get_default_data_path(self) -> Path:
        path = PROCESSED_DIR / "cumulative_up_to_2025.csv"
        if not path.exists():
            path = PROCESSED_DIR / "pagasa_training_dataset.csv"
        return path

    def train(self, **kwargs) -> Dict[str, Any]:
        """Train XGBoost model."""
        logger.info("=" * 60)
        logger.info("XGBOOST TRAINING")
        logger.info("=" * 60)

        from app.services.advanced_models import (
            XGBOOST_PARAM_GRID,
            XGBOOST_PARAM_GRID_FAST,
            XGBoostConfig,
            create_xgboost_model,
        )

        df = self.load_data(self.config.data_path)
        X, y = self.prepare_features(df)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.config.test_size, random_state=self.config.random_state, stratify=y
        )
        logger.info(f"Train: {len(X_train)}, Test: {len(X_test)}")

        if self.config.grid_search:
            from app.services.advanced_models import XGBClassifier as _XGB

            base = _XGB(
                objective="binary:logistic",
                eval_metric="logloss",
                random_state=self.config.random_state,
                n_jobs=-1,
            )
            grid = XGBOOST_PARAM_GRID_FAST if self.config.quick else XGBOOST_PARAM_GRID
            search = GridSearchCV(
                base,
                grid,
                cv=StratifiedKFold(self.config.cv_folds, shuffle=True, random_state=self.config.random_state),
                scoring="f1_weighted",
                n_jobs=-1,
                verbose=1,
            )
            search.fit(X_train, y_train)
            model = search.best_estimator_
            self.training_info["best_params"] = search.best_params_
            self.training_info["best_cv_score"] = float(search.best_score_)
            logger.info(f"Best params: {search.best_params_}")
        else:
            model = create_xgboost_model(y_train=y_train)
            model.fit(X_train, y_train)

        metrics = self.evaluate_model(model, X_test, y_test, X_full=X, y_full=y)
        self.metrics = metrics
        self.model = model
        model_path = self.save_model(model, "flood_xgb_model", metrics)

        return {
            "model_path": str(model_path),
            "metrics": metrics,
            "features": self.feature_names,
            "algorithm": "XGBClassifier",
        }


class LightGBMTrainingStrategy(TrainingStrategy):
    """LightGBM training strategy."""

    def get_features(self) -> List[str]:
        return FEATURE_CONFIGS["production"]

    def get_default_data_path(self) -> Path:
        path = PROCESSED_DIR / "cumulative_up_to_2025.csv"
        if not path.exists():
            path = PROCESSED_DIR / "pagasa_training_dataset.csv"
        return path

    def train(self, **kwargs) -> Dict[str, Any]:
        """Train LightGBM model."""
        logger.info("=" * 60)
        logger.info("LIGHTGBM TRAINING")
        logger.info("=" * 60)

        from app.services.advanced_models import (
            LIGHTGBM_PARAM_GRID,
            LIGHTGBM_PARAM_GRID_FAST,
            LightGBMConfig,
            create_lightgbm_model,
        )

        df = self.load_data(self.config.data_path)
        X, y = self.prepare_features(df)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.config.test_size, random_state=self.config.random_state, stratify=y
        )
        logger.info(f"Train: {len(X_train)}, Test: {len(X_test)}")

        if self.config.grid_search:
            from lightgbm import LGBMClassifier as _LGBM

            base = _LGBM(
                verbose=-1,
                random_state=self.config.random_state,
                n_jobs=-1,
            )
            grid = LIGHTGBM_PARAM_GRID_FAST if self.config.quick else LIGHTGBM_PARAM_GRID
            search = GridSearchCV(
                base,
                grid,
                cv=StratifiedKFold(self.config.cv_folds, shuffle=True, random_state=self.config.random_state),
                scoring="f1_weighted",
                n_jobs=-1,
                verbose=1,
            )
            search.fit(X_train, y_train)
            model = search.best_estimator_
            self.training_info["best_params"] = search.best_params_
            self.training_info["best_cv_score"] = float(search.best_score_)
            logger.info(f"Best params: {search.best_params_}")
        else:
            model = create_lightgbm_model()
            model.fit(X_train, y_train)

        metrics = self.evaluate_model(model, X_test, y_test, X_full=X, y_full=y)
        self.metrics = metrics
        self.model = model
        model_path = self.save_model(model, "flood_lgbm_model", metrics)

        return {
            "model_path": str(model_path),
            "metrics": metrics,
            "features": self.feature_names,
            "algorithm": "LGBMClassifier",
        }


class EnsembleTrainingStrategy(TrainingStrategy):
    """Ensemble Voting Classifier combining RF + XGBoost + LightGBM."""

    def get_features(self) -> List[str]:
        return FEATURE_CONFIGS["production"]

    def get_default_data_path(self) -> Path:
        path = PROCESSED_DIR / "cumulative_up_to_2025.csv"
        if not path.exists():
            path = PROCESSED_DIR / "pagasa_training_dataset.csv"
        return path

    def train(self, **kwargs) -> Dict[str, Any]:
        """Train ensemble voting classifier."""
        logger.info("=" * 60)
        logger.info("ENSEMBLE VOTING CLASSIFIER TRAINING")
        logger.info("=" * 60)

        from app.services.advanced_models import create_ensemble_model

        df = self.load_data(self.config.data_path)
        X, y = self.prepare_features(df)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.config.test_size, random_state=self.config.random_state, stratify=y
        )
        logger.info(f"Train: {len(X_train)}, Test: {len(X_test)}")

        model = create_ensemble_model(y_train=y_train)
        model.fit(X_train, y_train)

        metrics = self.evaluate_model(model, X_test, y_test, X_full=X, y_full=y)
        self.metrics = metrics
        self.model = model
        model_path = self.save_model(model, "flood_ensemble_model", metrics)

        return {
            "model_path": str(model_path),
            "metrics": metrics,
            "features": self.feature_names,
            "algorithm": "VotingClassifier(RF+XGB+LGBM)",
        }


class ComparisonTrainingStrategy(TrainingStrategy):
    """Head-to-head comparison of all models."""

    def get_features(self) -> List[str]:
        return FEATURE_CONFIGS["production"]

    def get_default_data_path(self) -> Path:
        path = PROCESSED_DIR / "cumulative_up_to_2025.csv"
        if not path.exists():
            path = PROCESSED_DIR / "pagasa_training_dataset.csv"
        return path

    def train(self, **kwargs) -> Dict[str, Any]:
        """Run model comparison and save the best one."""
        logger.info("=" * 60)
        logger.info("MODEL COMPARISON (RF vs XGBoost vs LightGBM vs Ensemble)")
        logger.info("=" * 60)

        from app.services.advanced_models import compare_models

        df = self.load_data(self.config.data_path)
        X, y = self.prepare_features(df)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.config.test_size, random_state=self.config.random_state, stratify=y
        )
        logger.info(f"Train: {len(X_train)}, Test: {len(X_test)}")

        result = compare_models(
            X_train=X_train,
            y_train=y_train,
            X_test=X_test,
            y_test=y_test,
            feature_names=self.feature_names,
            cv_folds=self.config.cv_folds,
            random_state=self.config.random_state,
            output_dir=str(self.models_dir.parent / "reports"),
        )

        # Save the best model as the default
        best_name = result.get("best_model", "")
        trained = result.get("trained_models", {})
        if best_name in trained:
            best = trained[best_name]
            best_metrics = {}
            for r in result.get("results", []):
                if r["name"] == best_name:
                    best_metrics = r["metrics"]
            model_path = self.save_model(best, f"flood_best_{best_name.lower()}", best_metrics)
            # Also copy to default path
            default_path = self.models_dir / "flood_rf_model.joblib"
            joblib.dump(best, default_path)
            result["model_path"] = str(model_path)
            result["metrics"] = best_metrics

        result["features"] = self.feature_names
        # Remove non-serialisable trained_models from return
        result.pop("trained_models", None)
        return result


class DeepLearningTrainingStrategy(TrainingStrategy):
    """Deep learning (LSTM / Transformer) training strategy."""

    def get_features(self) -> List[str]:
        return FEATURE_CONFIGS["production"]

    def get_default_data_path(self) -> Path:
        path = PROCESSED_DIR / "cumulative_up_to_2025.csv"
        if not path.exists():
            path = PROCESSED_DIR / "pagasa_training_dataset.csv"
        return path

    def train(self, **kwargs) -> Dict[str, Any]:
        """Train a deep learning model (LSTM or Transformer)."""
        logger.info("=" * 60)
        logger.info(f"DEEP LEARNING TRAINING ({self.config.dl_model_type.upper()})")
        logger.info("=" * 60)

        try:
            from app.services.deep_learning_models import train_deep_learning_model
        except ImportError as e:
            logger.error(f"Deep learning dependencies not available: {e}")
            raise ImportError(
                "PyTorch is required for deep learning training. " "Install with: pip install torch"
            ) from e

        # Load data
        df = self.load_data(self.config.data_path)

        # Get features (enrichment handled by prepare_features)
        features = self.get_features()

        # Apply ENSO/spatial enrichment to the raw DataFrame
        if self.config.include_enso:
            try:
                from app.services.enso_service import add_enso_features, get_enso_feature_names

                df = add_enso_features(df, include_lags=True)
                features = features + [f for f in get_enso_feature_names() if f not in features]
            except Exception as e:
                logger.warning(f"ENSO enrichment skipped: {e}")

        if self.config.include_spatial:
            try:
                from app.services.spatial_features import add_spatial_features, get_spatial_feature_names

                df = add_spatial_features(df, default_barangay=self.config.default_barangay)
                features = features + [f for f in get_spatial_feature_names() if f not in features]
            except Exception as e:
                logger.warning(f"Spatial enrichment skipped: {e}")

        available = [f for f in features if f in df.columns]
        self.feature_names = available

        # Train
        result = train_deep_learning_model(
            df,
            feature_cols=available,
            model_type=self.config.dl_model_type,
            sequence_length=self.config.dl_sequence_length,
            epochs=self.config.dl_epochs,
            output_dir=str(self.models_dir),
            hidden_dim=self.config.dl_hidden_dim,
        )

        self.metrics = result.get("metrics", {})
        return result


# =============================================================================
# Unified Trainer
# =============================================================================


class UnifiedTrainer:
    """
    Unified trainer that delegates to appropriate strategy based on mode.

    Usage:
        trainer = UnifiedTrainer(mode=TrainingMode.PRODUCTION)
        result = trainer.train(grid_search=True)
    """

    STRATEGY_MAP: Dict[TrainingMode, Type[TrainingStrategy]] = {
        TrainingMode.BASIC: BasicTrainingStrategy,
        TrainingMode.PAGASA: PAGASATrainingStrategy,
        TrainingMode.PRODUCTION: ProductionTrainingStrategy,
        TrainingMode.PROGRESSIVE: ProgressiveTrainingStrategy,
        TrainingMode.ENHANCED: EnhancedTrainingStrategy,
        TrainingMode.DEEP_LEARNING: DeepLearningTrainingStrategy,
        TrainingMode.XGBOOST: XGBoostTrainingStrategy,
        TrainingMode.LIGHTGBM: LightGBMTrainingStrategy,
        TrainingMode.ENSEMBLE: EnsembleTrainingStrategy,
        TrainingMode.COMPARISON: ComparisonTrainingStrategy,
        # ENTERPRISE and ULTIMATE use specialized external modules
    }

    def __init__(self, mode: TrainingMode = TrainingMode.BASIC, config: Optional[TrainingConfig] = None):
        self.mode = mode
        self.config = config or TrainingConfig()

        # Apply config updates based on mode
        if mode in self.STRATEGY_MAP:
            self.strategy = self.STRATEGY_MAP[mode](self.config)
        else:
            raise ValueError(f"Unsupported training mode: {mode}")

    def train(self, **kwargs) -> Dict[str, Any]:
        """
        Execute training with the configured strategy.

        Returns dict with model_path, metrics, and other training artifacts.
        """
        # Update config from kwargs
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

        logger.info(f"Starting training with mode: {self.mode.value}")
        return self.strategy.train(**kwargs)

    @classmethod
    def available_modes(cls) -> List[str]:
        """List available training modes."""
        return [m.value for m in TrainingMode]


# =============================================================================
# CLI Main
# =============================================================================


def main():
    """Main entry point for standalone usage."""
    parser = argparse.ArgumentParser(
        description="Unified Model Training",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--mode",
        "-m",
        choices=[m.value for m in TrainingMode],
        default="basic",
        help="Training mode",
    )

    parser.add_argument("--data", "-d", type=str, help="Path to training data")
    parser.add_argument("--grid-search", action="store_true", help="Enable grid search")
    parser.add_argument("--randomized-search", action="store_true", help="Enable randomized search")
    parser.add_argument("--cv-folds", type=int, default=5, help="CV folds")
    parser.add_argument("--phase", type=int, help="Phase for progressive training")
    parser.add_argument("--output-dir", type=str, help="Output directory")
    parser.add_argument("--include-enso", action="store_true", help="Include ENSO climate indices")
    parser.add_argument("--include-spatial", action="store_true", help="Include barangay spatial features")
    parser.add_argument("--barangay", type=str, help="Default barangay for spatial features")
    parser.add_argument(
        "--dl-model-type",
        choices=["lstm", "transformer"],
        default="lstm",
        help="Deep learning model type (for --mode deep_learning)",
    )
    parser.add_argument("--dl-epochs", type=int, default=100, help="Deep learning training epochs")
    parser.add_argument("--dl-sequence-length", type=int, default=14, help="Look-back window in days for DL models")

    args = parser.parse_args()

    config = TrainingConfig(
        data_path=args.data,
        grid_search=args.grid_search,
        randomized_search=args.randomized_search,
        cv_folds=args.cv_folds,
        phase=args.phase,
        output_dir=args.output_dir,
        include_enso=args.include_enso,
        include_spatial=args.include_spatial,
        default_barangay=args.barangay,
        dl_model_type=args.dl_model_type,
        dl_epochs=args.dl_epochs,
        dl_sequence_length=args.dl_sequence_length,
    )

    mode = TrainingMode(args.mode)
    trainer = UnifiedTrainer(mode=mode, config=config)
    result = trainer.train()

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    if isinstance(result, dict) and "metrics" in result:
        print(f"Model: {result.get('model_path', 'N/A')}")
        print(f"F1 Score: {result['metrics'].get('f1_score', 'N/A'):.4f}")
    elif isinstance(result, dict):
        for version, data in result.items():
            print(f"{version}: F1={data['metrics'].get('f1_score', 0):.4f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
