"""
Advanced ML Models - XGBoost, LightGBM & Ensemble Classifiers.

Provides:
- XGBoostFloodClassifier  : XGBoost wrapper with flood-tuned defaults
- LightGBMFloodClassifier : LightGBM wrapper with flood-tuned defaults
- EnsembleFloodClassifier  : Soft-voting ensemble (RF + XGB + LGBM)
- compare_models()         : Head-to-head comparison table

Author: Floodingnaque Team
Date: 2026-03-02
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import (
    GradientBoostingClassifier,
    RandomForestClassifier,
    VotingClassifier,
)
from sklearn.metrics import (
    accuracy_score,
    classification_report,
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
    cross_val_score,
    train_test_split,
)

logger = logging.getLogger(__name__)

# ═════════════════════════════════════════════════════════════════════════════
# Optional imports - graceful fallback if XGBoost / LightGBM not installed
# ═════════════════════════════════════════════════════════════════════════════
try:
    from xgboost import XGBClassifier as _XGBClassifierBase

    _XGBOOST_AVAILABLE = True

    class XGBClassifier(_XGBClassifierBase):
        """XGBClassifier wrapper that ensures sklearn classifier compatibility.

        XGBoost 2.x dropped the ``_estimator_type`` attribute that
        sklearn's ``VotingClassifier`` checks.  This subclass re-adds it
        so ensemble estimators accept the model.
        """

        _estimator_type = "classifier"

        def __sklearn_tags__(self):  # type: ignore[override]
            tags = super().__sklearn_tags__()
            tags.estimator_type = "classifier"
            return tags

except ImportError:  # pragma: no cover
    _XGBOOST_AVAILABLE = False
    XGBClassifier = None  # type: ignore[misc,assignment]

try:
    from lightgbm import LGBMClassifier

    _LIGHTGBM_AVAILABLE = True
except ImportError:  # pragma: no cover
    _LIGHTGBM_AVAILABLE = False
    LGBMClassifier = None  # type: ignore[misc,assignment]


# ═════════════════════════════════════════════════════════════════════════════
# Configuration
# ═════════════════════════════════════════════════════════════════════════════


@dataclass
class XGBoostConfig:
    """Configuration for XGBoost classifier."""

    n_estimators: int = 300
    max_depth: int = 8
    learning_rate: float = 0.05
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    min_child_weight: int = 3
    gamma: float = 0.1
    reg_alpha: float = 0.1
    reg_lambda: float = 1.0
    scale_pos_weight: float = 1.0  # auto-calculated in factory
    random_state: int = 42
    n_jobs: int = -1
    eval_metric: str = "logloss"
    early_stopping_rounds: Optional[int] = 20
    objective: str = "binary:logistic"

    def to_xgb_params(self) -> Dict[str, Any]:
        """Convert to XGBClassifier constructor kwargs."""
        return {
            "n_estimators": self.n_estimators,
            "max_depth": self.max_depth,
            "learning_rate": self.learning_rate,
            "subsample": self.subsample,
            "colsample_bytree": self.colsample_bytree,
            "min_child_weight": self.min_child_weight,
            "gamma": self.gamma,
            "reg_alpha": self.reg_alpha,
            "reg_lambda": self.reg_lambda,
            "scale_pos_weight": self.scale_pos_weight,
            "random_state": self.random_state,
            "n_jobs": self.n_jobs,
            "eval_metric": self.eval_metric,
            "objective": self.objective,
        }


@dataclass
class LightGBMConfig:
    """Configuration for LightGBM classifier."""

    n_estimators: int = 300
    max_depth: int = -1  # no limit
    num_leaves: int = 63
    learning_rate: float = 0.05
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    min_child_samples: int = 20
    reg_alpha: float = 0.1
    reg_lambda: float = 1.0
    is_unbalance: bool = True  # auto-handles class imbalance
    random_state: int = 42
    n_jobs: int = -1
    verbose: int = -1  # suppress LightGBM output
    boosting_type: str = "gbdt"

    def to_lgbm_params(self) -> Dict[str, Any]:
        """Convert to LGBMClassifier constructor kwargs."""
        return {
            "n_estimators": self.n_estimators,
            "max_depth": self.max_depth,
            "num_leaves": self.num_leaves,
            "learning_rate": self.learning_rate,
            "subsample": self.subsample,
            "colsample_bytree": self.colsample_bytree,
            "min_child_samples": self.min_child_samples,
            "reg_alpha": self.reg_alpha,
            "reg_lambda": self.reg_lambda,
            "is_unbalance": self.is_unbalance,
            "random_state": self.random_state,
            "n_jobs": self.n_jobs,
            "verbose": self.verbose,
            "boosting_type": self.boosting_type,
        }


@dataclass
class EnsembleConfig:
    """Configuration for Ensemble (Voting) classifier."""

    voting: str = "soft"  # 'soft' for probability-weighted, 'hard' for majority vote
    weights: Optional[List[float]] = None  # e.g. [2, 1, 1] to weight RF higher
    include_rf: bool = True
    include_xgboost: bool = True
    include_lightgbm: bool = True
    include_gradient_boosting: bool = False  # optional sklearn GBM
    calibrate: bool = True  # calibrate ensemble for better probabilities
    random_state: int = 42


# ═════════════════════════════════════════════════════════════════════════════
# Hyperparameter search grids
# ═════════════════════════════════════════════════════════════════════════════

XGBOOST_PARAM_GRID = {
    "n_estimators": [200, 300, 500],
    "max_depth": [4, 6, 8, 10],
    "learning_rate": [0.01, 0.05, 0.1],
    "subsample": [0.7, 0.8, 0.9],
    "colsample_bytree": [0.7, 0.8, 0.9],
    "min_child_weight": [1, 3, 5],
    "gamma": [0, 0.1, 0.3],
}

XGBOOST_PARAM_GRID_FAST = {
    "n_estimators": [200, 300],
    "max_depth": [6, 8],
    "learning_rate": [0.05, 0.1],
    "subsample": [0.8],
    "colsample_bytree": [0.8],
}

LIGHTGBM_PARAM_GRID = {
    "n_estimators": [200, 300, 500],
    "num_leaves": [31, 63, 127],
    "max_depth": [-1, 8, 12],
    "learning_rate": [0.01, 0.05, 0.1],
    "subsample": [0.7, 0.8, 0.9],
    "colsample_bytree": [0.7, 0.8, 0.9],
    "min_child_samples": [10, 20, 30],
}

LIGHTGBM_PARAM_GRID_FAST = {
    "n_estimators": [200, 300],
    "num_leaves": [31, 63],
    "learning_rate": [0.05, 0.1],
    "subsample": [0.8],
}


# ═════════════════════════════════════════════════════════════════════════════
# Factory helpers
# ═════════════════════════════════════════════════════════════════════════════


def create_xgboost_model(
    config: Optional[XGBoostConfig] = None,
    y_train: Optional[pd.Series] = None,
) -> "XGBClassifier":
    """
    Create an XGBoost classifier with flood-tuned defaults.

    Parameters
    ----------
    config : XGBoostConfig, optional
        Custom configuration.  Falls back to sensible defaults.
    y_train : pd.Series, optional
        Training labels - used to auto-calculate ``scale_pos_weight``
        for class imbalance.

    Returns
    -------
    XGBClassifier
    """
    if not _XGBOOST_AVAILABLE:
        raise ImportError("XGBoost is not installed. Install with: pip install xgboost>=2.1")

    config = config or XGBoostConfig()

    # Auto-calculate scale_pos_weight for class imbalance
    if y_train is not None and config.scale_pos_weight == 1.0:
        neg = (y_train == 0).sum()
        pos = (y_train == 1).sum()
        if pos > 0:
            config.scale_pos_weight = float(neg / pos)
            logger.info(
                f"XGBoost scale_pos_weight auto-set to {config.scale_pos_weight:.2f} " f"(neg={neg}, pos={pos})"
            )

    return XGBClassifier(**config.to_xgb_params())


def create_lightgbm_model(
    config: Optional[LightGBMConfig] = None,
) -> "LGBMClassifier":
    """
    Create a LightGBM classifier with flood-tuned defaults.

    Parameters
    ----------
    config : LightGBMConfig, optional
        Custom configuration.  Falls back to sensible defaults.

    Returns
    -------
    LGBMClassifier
    """
    if not _LIGHTGBM_AVAILABLE:
        raise ImportError("LightGBM is not installed. Install with: pip install lightgbm>=4.5")

    config = config or LightGBMConfig()
    return LGBMClassifier(**config.to_lgbm_params())


def create_ensemble_model(
    rf_config: Optional[Dict[str, Any]] = None,
    xgb_config: Optional[XGBoostConfig] = None,
    lgbm_config: Optional[LightGBMConfig] = None,
    ensemble_config: Optional[EnsembleConfig] = None,
    y_train: Optional[pd.Series] = None,
) -> VotingClassifier:
    """
    Create a soft-voting ensemble combining RF, XGBoost, and LightGBM.

    Parameters
    ----------
    rf_config : dict, optional
        Kwargs for ``RandomForestClassifier``.
    xgb_config : XGBoostConfig, optional
        Configuration for XGBoost.
    lgbm_config : LightGBMConfig, optional
        Configuration for LightGBM.
    ensemble_config : EnsembleConfig, optional
        Ensemble-level settings.
    y_train : pd.Series, optional
        Training labels for class-imbalance handling.

    Returns
    -------
    sklearn.ensemble.VotingClassifier
    """
    ensemble_config = ensemble_config or EnsembleConfig()
    estimators: List[Tuple[str, Any]] = []

    # ── Random Forest ───────────────────────────────────────────────────────
    if ensemble_config.include_rf:
        rf_defaults = {
            "n_estimators": 200,
            "max_depth": 15,
            "min_samples_split": 5,
            "min_samples_leaf": 2,
            "max_features": "sqrt",
            "class_weight": "balanced",
            "random_state": ensemble_config.random_state,
            "n_jobs": -1,
        }
        if rf_config:
            rf_defaults.update(rf_config)
        estimators.append(("rf", RandomForestClassifier(**rf_defaults)))

    # ── XGBoost ─────────────────────────────────────────────────────────────
    if ensemble_config.include_xgboost:
        if not _XGBOOST_AVAILABLE:
            logger.warning("XGBoost requested for ensemble but not installed - skipping")
        else:
            xgb = create_xgboost_model(config=xgb_config, y_train=y_train)
            estimators.append(("xgb", xgb))

    # ── LightGBM ────────────────────────────────────────────────────────────
    if ensemble_config.include_lightgbm:
        if not _LIGHTGBM_AVAILABLE:
            logger.warning("LightGBM requested for ensemble but not installed - skipping")
        else:
            lgbm = create_lightgbm_model(config=lgbm_config)
            estimators.append(("lgbm", lgbm))

    # ── Gradient Boosting (sklearn built-in, optional) ──────────────────────
    if ensemble_config.include_gradient_boosting:
        estimators.append(
            (
                "gbm",
                GradientBoostingClassifier(
                    n_estimators=200,
                    max_depth=6,
                    learning_rate=0.05,
                    random_state=ensemble_config.random_state,
                ),
            )
        )

    if len(estimators) < 2:
        raise ValueError(
            f"Ensemble requires at least 2 estimators, got {len(estimators)}. "
            "Ensure XGBoost and/or LightGBM are installed."
        )

    # ── Weights ─────────────────────────────────────────────────────────────
    weights = ensemble_config.weights
    if weights and len(weights) != len(estimators):
        logger.warning(
            f"Weight count ({len(weights)}) != estimator count ({len(estimators)}). " "Falling back to equal weights."
        )
        weights = None

    voter = VotingClassifier(
        estimators=estimators,
        voting=ensemble_config.voting,
        weights=weights,
        n_jobs=-1,
    )

    logger.info(
        f"Ensemble created: {[name for name, _ in estimators]}, " f"voting={ensemble_config.voting}, weights={weights}"
    )

    return voter


# ═════════════════════════════════════════════════════════════════════════════
# Model Comparison
# ═════════════════════════════════════════════════════════════════════════════


@dataclass
class ModelComparisonResult:
    """Result of a single model evaluation in a comparison."""

    name: str
    algorithm: str
    metrics: Dict[str, float]
    training_time_seconds: float
    inference_time_ms: float
    model_size_bytes: int = 0
    feature_importances: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compare_models(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    feature_names: Optional[List[str]] = None,
    include_rf: bool = True,
    include_xgboost: bool = True,
    include_lightgbm: bool = True,
    include_ensemble: bool = True,
    cv_folds: int = 5,
    random_state: int = 42,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Train and compare multiple ML algorithms head-to-head.

    Trains RF, XGBoost, LightGBM, and an ensemble model on the same data,
    then produces a comparison report with metrics, training time, and
    inference latency.

    Parameters
    ----------
    X_train, y_train : Training data
    X_test, y_test   : Test data
    feature_names    : Feature column names (for importance extraction)
    include_* : bool  : Which models to include
    cv_folds  : int   : Cross-validation folds
    random_state : int
    output_dir : str, optional
        Directory to save comparison report and models.

    Returns
    -------
    dict with 'results' (list of ModelComparisonResult), 'best_model',
    'comparison_table' (DataFrame as dict), 'report_path'.
    """
    results: List[ModelComparisonResult] = []
    trained_models: Dict[str, Any] = {}
    feature_names = feature_names or list(X_train.columns)

    def _evaluate(name: str, algorithm: str, model: Any) -> ModelComparisonResult:
        """Train, evaluate, and record metrics for a model."""
        # Train
        t0 = time.time()
        model.fit(X_train, y_train)
        train_time = time.time() - t0

        # Predict
        t0 = time.time()
        y_pred = model.predict(X_test)
        inference_time = (time.time() - t0) * 1000  # ms

        y_proba = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else y_pred.astype(float)

        metrics = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision": float(precision_score(y_test, y_pred, average="weighted", zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, average="weighted", zero_division=0)),
            "f1_score": float(f1_score(y_test, y_pred, average="weighted", zero_division=0)),
            "f2_score": float(fbeta_score(y_test, y_pred, beta=2, average="weighted", zero_division=0)),
            "roc_auc": float(roc_auc_score(y_test, y_proba)),
        }

        # Cross-validation on full data
        X_full = pd.concat([X_train, X_test], ignore_index=True)
        y_full = pd.concat([y_train, y_test], ignore_index=True)
        n_folds = min(cv_folds, len(y_full) // 2)
        if n_folds >= 2:
            cv_scores = cross_val_score(
                model,
                X_full,
                y_full,
                cv=StratifiedKFold(n_folds, shuffle=True, random_state=random_state),
                scoring="f1_weighted",
                n_jobs=-1,
            )
            metrics["cv_mean"] = float(cv_scores.mean())
            metrics["cv_std"] = float(cv_scores.std())

        # Feature importances
        importances = None
        if hasattr(model, "feature_importances_"):
            importances = dict(zip(feature_names, model.feature_importances_.tolist()))
        elif hasattr(model, "estimators_") and hasattr(model, "voting"):
            # For VotingClassifier, average importances from fitted sub-estimators
            imp_list = []
            for est in model.estimators_:
                if hasattr(est, "feature_importances_"):
                    imp_list.append(est.feature_importances_)
            if imp_list:
                avg_imp = np.mean(imp_list, axis=0)
                importances = dict(zip(feature_names, avg_imp.tolist()))

        result = ModelComparisonResult(
            name=name,
            algorithm=algorithm,
            metrics=metrics,
            training_time_seconds=round(train_time, 2),
            inference_time_ms=round(inference_time, 2),
            feature_importances=importances,
        )

        trained_models[name] = model
        logger.info(
            f"[{name}] F1={metrics['f1_score']:.4f}  ROC-AUC={metrics['roc_auc']:.4f}  "
            f"Train={train_time:.1f}s  Infer={inference_time:.1f}ms"
        )

        return result

    # ── Train each model ────────────────────────────────────────────────────
    if include_rf:
        rf = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            max_features="sqrt",
            class_weight="balanced",
            random_state=random_state,
            n_jobs=-1,
        )
        results.append(_evaluate("RandomForest", "RandomForestClassifier", rf))

    if include_xgboost:
        if _XGBOOST_AVAILABLE:
            xgb = create_xgboost_model(y_train=y_train)
            results.append(_evaluate("XGBoost", "XGBClassifier", xgb))
        else:
            logger.warning("XGBoost not installed - skipping comparison")

    if include_lightgbm:
        if _LIGHTGBM_AVAILABLE:
            lgbm = create_lightgbm_model()
            results.append(_evaluate("LightGBM", "LGBMClassifier", lgbm))
        else:
            logger.warning("LightGBM not installed - skipping comparison")

    if include_ensemble and len(trained_models) >= 2:
        ensemble = create_ensemble_model(y_train=y_train)
        results.append(_evaluate("Ensemble", "VotingClassifier", ensemble))

    # ── Comparison table ────────────────────────────────────────────────────
    rows = []
    for r in results:
        row = {"model": r.name, "algorithm": r.algorithm}
        row.update(r.metrics)
        row["train_time_s"] = r.training_time_seconds
        row["inference_ms"] = r.inference_time_ms
        rows.append(row)

    comparison_df = pd.DataFrame(rows)

    # Determine best model by F1 score
    best_idx = comparison_df["f1_score"].idxmax() if len(comparison_df) > 0 else 0
    best_name = comparison_df.loc[best_idx, "model"] if len(comparison_df) > 0 else "N/A"

    logger.info(f"\n{'='*70}\nMODEL COMPARISON RESULTS\n{'='*70}")
    logger.info(f"\n{comparison_df.to_string(index=False)}")
    logger.info(f"\nBest model: {best_name}")

    # ── Save report ─────────────────────────────────────────────────────────
    report: Dict[str, Any] = {
        "results": [r.to_dict() for r in results],
        "best_model": best_name,
        "comparison_table": comparison_df.to_dict(orient="records"),
        "compared_at": datetime.now(timezone.utc).isoformat(),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "n_features": len(feature_names),
    }

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        # Save report JSON
        report_path = out / f"model_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        report["report_path"] = str(report_path)
        logger.info(f"Comparison report saved: {report_path}")

        # Save best model
        if best_name in trained_models:
            best_path = out / f"flood_best_model_{best_name.lower()}.joblib"
            joblib.dump(trained_models[best_name], best_path)
            report["best_model_path"] = str(best_path)
            logger.info(f"Best model saved: {best_path}")

    report["trained_models"] = trained_models  # in-memory reference

    return report


# ═════════════════════════════════════════════════════════════════════════════
# Availability checks
# ═════════════════════════════════════════════════════════════════════════════


def get_available_algorithms() -> Dict[str, bool]:
    """Return which advanced ML frameworks are installed."""
    return {
        "random_forest": True,  # always available via scikit-learn
        "xgboost": _XGBOOST_AVAILABLE,
        "lightgbm": _LIGHTGBM_AVAILABLE,
        "gradient_boosting": True,  # sklearn built-in
        "ensemble": _XGBOOST_AVAILABLE or _LIGHTGBM_AVAILABLE,
    }
