#!/usr/bin/env python
"""
Unified Model Evaluation Module for Floodingnaque
==================================================

Consolidates evaluate_model.py and evaluate_robustness.py into a single,
comprehensive evaluation module.

Evaluation Modes:
    - basic: Simple accuracy, confusion matrix, feature importance
    - robustness: Full robustness testing (noise, temporal, calibration)
    - thesis: Complete thesis defense evaluation suite

Usage:
    from scripts.evaluate_unified import UnifiedEvaluator, EvaluationMode

    # Basic evaluation
    evaluator = UnifiedEvaluator()
    results = evaluator.evaluate(mode=EvaluationMode.BASIC)

    # Full robustness evaluation
    results = evaluator.evaluate(mode=EvaluationMode.ROBUSTNESS)

    # Thesis defense evaluation
    results = evaluator.evaluate(
        mode=EvaluationMode.THESIS,
        save_plots=True,
        output_dir="reports/"
    )

CLI Usage:
    python -m scripts evaluate                    # Basic
    python -m scripts evaluate --robustness       # Full robustness
    python -m scripts evaluate --temporal         # Temporal validation only

Author: Floodingnaque Team
Date: 2026-01-23
"""

import argparse
import json
import logging
import warnings
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score

warnings.filterwarnings("ignore")

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
MODELS_DIR = BACKEND_DIR / "models"
REPORTS_DIR = BACKEND_DIR / "reports"
DATA_DIR = BACKEND_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"


class EvaluationMode(Enum):
    """Available evaluation modes."""

    BASIC = "basic"
    ROBUSTNESS = "robustness"
    THESIS = "thesis"
    TEMPORAL = "temporal"
    CALIBRATION = "calibration"


class UnifiedEvaluator:
    """
    Unified model evaluator combining basic and robustness evaluation.

    Provides:
    - Basic metrics (accuracy, precision, recall, F1, ROC-AUC)
    - Confusion matrix and feature importance
    - Temporal validation (train past, test future)
    - Noise robustness testing
    - Probability calibration analysis
    - Feature threshold analysis
    - Cross-validation analysis
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        data_path: Optional[str] = None,
        output_dir: Optional[str] = None,
    ):
        self.model_path = model_path
        self.data_path = data_path
        self.output_dir = Path(output_dir) if output_dir else REPORTS_DIR

        self.model = None
        self.data = None
        self.metadata: Dict[str, Any] = {}
        self.feature_names: List[str] = []
        self.results: Dict[str, Any] = {}

    def _find_model(self) -> Path:
        """Find the best model to evaluate."""
        if self.model_path:
            return Path(self.model_path)

        # Priority order for model selection
        candidates = [
            "flood_rf_model.joblib",
            "flood_rf_model_production.joblib",
            "flood_rf_model_v6_Ultimate_Combined.joblib",
        ]

        for candidate in candidates:
            path = MODELS_DIR / candidate
            if path.exists():
                return path

        # Find latest enhanced model
        enhanced_models = list(MODELS_DIR.glob("flood_enhanced_v*.joblib"))
        if enhanced_models:
            return max(enhanced_models, key=lambda p: p.stat().st_mtime)

        # Find any model
        all_models = list(MODELS_DIR.glob("flood_*.joblib"))
        if all_models:
            return max(all_models, key=lambda p: p.stat().st_mtime)

        raise FileNotFoundError("No model found in models directory")

    def _find_data(self) -> Path:
        """Find evaluation data."""
        if self.data_path:
            return Path(self.data_path)

        # Priority order
        candidates = [
            PROCESSED_DIR / "cumulative_up_to_2025.csv",
            PROCESSED_DIR / "pagasa_training_dataset.csv",
        ]

        for path in candidates:
            if path.exists():
                return path

        raise FileNotFoundError("No evaluation data found")

    def load(self) -> Tuple[pd.DataFrame, Any]:
        """Load model and data."""
        # Find and load model
        model_path = self._find_model()
        logger.info(f"Loading model from: {model_path}")
        self.model = joblib.load(model_path)

        # Load metadata if available
        metadata_path = model_path.with_suffix(".json")
        if metadata_path.exists():
            with open(metadata_path) as f:
                self.metadata = json.load(f)

        # Get feature names
        if hasattr(self.model, "feature_names_in_"):
            self.feature_names = list(self.model.feature_names_in_)
        elif self.metadata and "features" in self.metadata:
            self.feature_names = self.metadata["features"]
        else:
            # Fallback
            self.feature_names = ["temperature", "humidity", "precipitation", "is_monsoon_season", "month"]
            logger.warning(f"Using fallback feature names: {self.feature_names}")

        logger.info(f"Features: {self.feature_names}")

        # Find and load data
        data_path = self._find_data()
        logger.info(f"Loading data from: {data_path}")
        self.data = pd.read_csv(data_path)
        logger.info(f"Loaded {len(self.data)} records")

        return self.data, self.model

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare feature matrix matching model expectations."""
        df = df.copy()

        # Create derived features if needed
        feature_creators = {
            "temp_humidity_interaction": lambda d: d["temperature"] * d["humidity"] / 100,
            "temp_precip_interaction": lambda d: d["temperature"] * np.log1p(d["precipitation"]),
            "humidity_precip_interaction": lambda d: d["humidity"] * np.log1p(d["precipitation"]),
            "precipitation_squared": lambda d: d["precipitation"] ** 2,
            "precipitation_log": lambda d: np.log1p(d["precipitation"]),
            "monsoon_precip_interaction": lambda d: d["is_monsoon_season"] * d["precipitation"],
            "saturation_risk": lambda d: (d["humidity"] > 85).astype(int) * d["precipitation"],
        }

        for feature, creator in feature_creators.items():
            if feature in self.feature_names and feature not in df.columns:
                try:
                    df[feature] = creator(df)
                except Exception:
                    df[feature] = 0

        # Ensure all features present
        for f in self.feature_names:
            if f not in df.columns:
                logger.warning(f"Missing feature: {f}, filling with 0")
                df[f] = 0

        X = df[self.feature_names].fillna(0)
        return X

    # =========================================================================
    # Basic Evaluation Methods
    # =========================================================================

    def basic_metrics(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """Calculate basic classification metrics."""
        assert self.model is not None, "Model not loaded. Call load() first."  # nosec B101
        y_pred = self.model.predict(X)
        y_pred_proba = None
        if hasattr(self.model, "predict_proba"):
            y_pred_proba = self.model.predict_proba(X)[:, 1]

        metrics = {
            "accuracy": float(accuracy_score(y, y_pred)),
            "precision": float(precision_score(y, y_pred, average="weighted", zero_division=0)),
            "recall": float(recall_score(y, y_pred, average="weighted", zero_division=0)),
            "f1_score": float(f1_score(y, y_pred, average="weighted", zero_division=0)),
        }

        if y_pred_proba is not None:
            metrics["roc_auc"] = float(roc_auc_score(y, y_pred_proba))
            metrics["brier_score"] = float(brier_score_loss(y, y_pred_proba))

        logger.info(f"Basic Metrics: Acc={metrics['accuracy']:.4f}, F1={metrics['f1_score']:.4f}")

        return metrics

    def confusion_matrix_analysis(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """Generate confusion matrix analysis."""
        assert self.model is not None, "Model not loaded. Call load() first."  # nosec B101
        y_pred = self.model.predict(X)
        cm = confusion_matrix(y, y_pred)

        tn, fp, fn, tp = cm.ravel()

        return {
            "confusion_matrix": cm.tolist(),
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp),
            "specificity": float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0,
            "sensitivity": float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0,
        }

    def feature_importance(self) -> Dict[str, float]:
        """Get feature importance from model."""
        if self.model is None:
            logger.warning("Model not loaded")
            return {}
        if not hasattr(self.model, "feature_importances_"):
            # Try to get from calibrated model
            if hasattr(self.model, "estimator") and hasattr(self.model.estimator, "feature_importances_"):
                importances = self.model.estimator.feature_importances_
            else:
                logger.warning("Model does not support feature importance")
                return {}
        else:
            importances = self.model.feature_importances_

        importance_dict = dict(zip(self.feature_names, importances.tolist()))
        sorted_importance = dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))

        logger.info("Feature Importance (top 5):")
        for i, (feat, imp) in enumerate(sorted_importance.items()):
            if i < 5:
                logger.info(f"  {feat}: {imp:.4f}")

        return sorted_importance

    # =========================================================================
    # Robustness Evaluation Methods
    # =========================================================================

    def temporal_validation(self, test_year: int = 2025) -> Optional[Dict[str, Any]]:
        """
        Temporal validation: train on past, test on future year.
        Simulates real-world deployment.
        """
        logger.info("=" * 60)
        logger.info(f"TEMPORAL VALIDATION (Test Year: {test_year})")
        logger.info("=" * 60)

        if self.data is None:
            logger.warning("Data not loaded, skipping temporal validation")
            return None

        if "year" not in self.data.columns:
            logger.warning("No 'year' column in data, skipping temporal validation")
            return None

        test_data = self.data[self.data["year"] == test_year]
        if len(test_data) == 0:
            logger.warning(f"No data for year {test_year}")
            return None

        logger.info(f"Test samples ({test_year}): {len(test_data)}")

        X_test = self.prepare_features(test_data)
        y_test = test_data["flood"]

        assert self.model is not None, "Model not loaded. Call load() first."  # nosec B101
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)[:, 1] if hasattr(self.model, "predict_proba") else None

        metrics = {
            "test_year": test_year,
            "test_samples": len(test_data),
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision": float(precision_score(y_test, y_pred, zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, zero_division=0)),
            "f1_score": float(f1_score(y_test, y_pred, zero_division=0)),
        }

        if y_pred_proba is not None:
            metrics["roc_auc"] = float(roc_auc_score(y_test, y_pred_proba))
            metrics["brier_score"] = float(brier_score_loss(y_test, y_pred_proba))

        logger.info(f"Temporal Results: Acc={metrics['accuracy']:.4f}, F1={metrics['f1_score']:.4f}")

        return metrics

    def noise_robustness(self, noise_levels: Optional[List[float]] = None) -> List[Dict[str, float]]:
        """
        Test model robustness by adding Gaussian noise to inputs.
        Simulates sensor measurement errors.
        """
        logger.info("=" * 60)
        logger.info("NOISE ROBUSTNESS TESTING")
        logger.info("=" * 60)

        if noise_levels is None:
            noise_levels = [0.05, 0.10, 0.15, 0.20]

        assert self.data is not None, "Data not loaded. Call load() first."  # nosec B101
        assert self.model is not None, "Model not loaded. Call load() first."  # nosec B101

        X = self.prepare_features(self.data)
        y = self.data["flood"]

        # Baseline
        y_pred = self.model.predict(X)
        baseline_acc = accuracy_score(y, y_pred)
        baseline_f1 = f1_score(y, y_pred)

        results = [
            {
                "noise_level": 0.0,
                "accuracy": float(baseline_acc),
                "f1_score": float(baseline_f1),
                "accuracy_drop": 0.0,
                "f1_drop": 0.0,
            }
        ]

        logger.info(f"Baseline (no noise): Acc={baseline_acc:.4f}, F1={baseline_f1:.4f}")
        logger.info("Noise% | Accuracy | F1 Score | Acc Drop | F1 Drop")
        logger.info("-" * 55)

        for noise_level in noise_levels:
            # Add Gaussian noise
            np.random.seed(42)
            X_noisy = X.copy()
            for col in X_noisy.columns:
                std = X_noisy[col].std()
                if std > 0:
                    noise = np.random.normal(0, noise_level * std, size=len(X_noisy))
                    X_noisy[col] = X_noisy[col] + noise

            y_pred_noisy = self.model.predict(X_noisy)  # model is asserted above
            noisy_acc = accuracy_score(y, y_pred_noisy)
            noisy_f1 = f1_score(y, y_pred_noisy)

            acc_drop = baseline_acc - noisy_acc
            f1_drop = baseline_f1 - noisy_f1

            logger.info(
                f"{noise_level*100:5.1f}% | {noisy_acc:.4f}   | {noisy_f1:.4f}   | {acc_drop:+.4f}  | {f1_drop:+.4f}"
            )

            results.append(
                {
                    "noise_level": float(noise_level),
                    "accuracy": float(noisy_acc),
                    "f1_score": float(noisy_f1),
                    "accuracy_drop": float(acc_drop),
                    "f1_drop": float(f1_drop),
                }
            )

        return results

    def calibration_analysis(self) -> Optional[Dict[str, Any]]:
        """
        Analyze prediction probability distributions.
        Well-calibrated models have probabilities matching actual frequencies.
        """
        logger.info("=" * 60)
        logger.info("PROBABILITY CALIBRATION ANALYSIS")
        logger.info("=" * 60)

        if self.model is None:
            logger.warning("Model not loaded")
            return None

        if not hasattr(self.model, "predict_proba"):
            logger.warning("Model does not support probability predictions")
            return None

        if self.data is None:
            logger.warning("Data not loaded")
            return None

        X = self.prepare_features(self.data)
        y = self.data["flood"]
        y_pred_proba = self.model.predict_proba(X)[:, 1]

        # Distribution stats
        logger.info(f"Probability Distribution:")
        logger.info(f"  Min: {y_pred_proba.min():.4f}, Max: {y_pred_proba.max():.4f}")
        logger.info(f"  Mean: {y_pred_proba.mean():.4f}, Std: {y_pred_proba.std():.4f}")

        # Confidence buckets
        high_conf_flood = (y_pred_proba > 0.9).sum()
        high_conf_no_flood = (y_pred_proba < 0.1).sum()
        uncertain = ((y_pred_proba >= 0.3) & (y_pred_proba <= 0.7)).sum()

        logger.info(f"Confidence Distribution:")
        logger.info(f"  High confidence flood (>90%): {high_conf_flood}")
        logger.info(f"  High confidence no-flood (<10%): {high_conf_no_flood}")
        logger.info(f"  Uncertain (30-70%): {uncertain}")

        brier = brier_score_loss(y, y_pred_proba)
        logger.info(f"Brier Score: {brier:.6f} (0=perfect, 0.25=random)")

        # Calibration curve
        calibration_data = {}
        try:
            prob_true, prob_pred = calibration_curve(y, y_pred_proba, n_bins=10)
            calibration_data["calibration_curve"] = {
                "predicted": prob_pred.tolist(),
                "actual": prob_true.tolist(),
            }
        except Exception as e:
            logger.warning(f"Could not compute calibration curve: {e}")

        return {
            "brier_score": float(brier),
            "high_conf_flood": int(high_conf_flood),
            "high_conf_no_flood": int(high_conf_no_flood),
            "uncertain": int(uncertain),
            "prob_mean": float(y_pred_proba.mean()),
            "prob_std": float(y_pred_proba.std()),
            **calibration_data,
        }

    def threshold_analysis(self) -> Dict[str, Any]:
        """
        Analyze the precipitation threshold separating flood/no-flood.
        Explains high accuracy for well-separated classes.
        """
        logger.info("=" * 60)
        logger.info("FEATURE THRESHOLD ANALYSIS")
        logger.info("=" * 60)

        if self.data is None:
            logger.warning("Data not loaded for threshold analysis")
            return {}

        if "precipitation" not in self.data.columns:
            logger.warning("No precipitation column for threshold analysis")
            return {}

        flood_precip = self.data[self.data["flood"] == 1]["precipitation"]
        no_flood_precip = self.data[self.data["flood"] == 0]["precipitation"]

        logger.info(f"No-Flood: mean={no_flood_precip.mean():.2f}mm, max={no_flood_precip.max():.2f}mm")
        logger.info(f"Flood: mean={flood_precip.mean():.2f}mm, min={flood_precip.min():.2f}mm")

        gap = flood_precip.min() - no_flood_precip.max()
        perfectly_separable = gap > 0

        if perfectly_separable:
            logger.info(f"Classes perfectly separable by precipitation! Gap: {gap:.2f}mm")
        else:
            overlap = no_flood_precip.max() - flood_precip.min()
            logger.info(f"Classes overlap by {overlap:.2f}mm")

        return {
            "no_flood_max": float(no_flood_precip.max()),
            "no_flood_mean": float(no_flood_precip.mean()),
            "flood_min": float(flood_precip.min()),
            "flood_mean": float(flood_precip.mean()),
            "gap": float(gap) if gap > 0 else 0.0,
            "perfectly_separable": bool(perfectly_separable),
        }

    def cross_validation(self, n_folds: int = 5) -> Dict[str, float]:
        """Stratified k-fold cross-validation."""
        logger.info("=" * 60)
        logger.info(f"CROSS-VALIDATION ({n_folds}-Fold)")
        logger.info("=" * 60)

        assert self.data is not None, "Data not loaded. Call load() first."  # nosec B101
        assert self.model is not None, "Model not loaded. Call load() first."  # nosec B101

        X = self.prepare_features(self.data)
        y = self.data["flood"]

        cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)

        accuracy = cross_val_score(self.model, X, y, cv=cv, scoring="accuracy")
        f1 = cross_val_score(self.model, X, y, cv=cv, scoring="f1")
        precision = cross_val_score(self.model, X, y, cv=cv, scoring="precision")
        recall = cross_val_score(self.model, X, y, cv=cv, scoring="recall")

        logger.info(f"Accuracy:  {accuracy.mean():.4f} (+/- {accuracy.std()*2:.4f})")
        logger.info(f"F1 Score:  {f1.mean():.4f} (+/- {f1.std()*2:.4f})")
        logger.info(f"Precision: {precision.mean():.4f} (+/- {precision.std()*2:.4f})")
        logger.info(f"Recall:    {recall.mean():.4f} (+/- {recall.std()*2:.4f})")

        return {
            "accuracy_mean": float(accuracy.mean()),
            "accuracy_std": float(accuracy.std()),
            "f1_mean": float(f1.mean()),
            "f1_std": float(f1.std()),
            "precision_mean": float(precision.mean()),
            "recall_mean": float(recall.mean()),
        }

    # =========================================================================
    # Plotting Methods
    # =========================================================================

    def save_plots(self, X: pd.DataFrame, y: pd.Series) -> List[Path]:
        """Save evaluation plots."""
        saved_plots = []

        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
        except ImportError:
            logger.warning("matplotlib/seaborn not available for plotting")
            return saved_plots

        self.output_dir.mkdir(parents=True, exist_ok=True)

        if self.model is None:
            logger.warning("No model loaded for plotting")
            return saved_plots

        # Confusion Matrix
        y_pred = self.model.predict(X)
        cm = confusion_matrix(y, y_pred)

        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues")
        plt.title("Confusion Matrix")
        plt.ylabel("Actual")
        plt.xlabel("Predicted")
        cm_path = self.output_dir / "confusion_matrix.png"
        plt.savefig(cm_path, dpi=300, bbox_inches="tight")
        plt.close()
        saved_plots.append(cm_path)
        logger.info(f"Saved: {cm_path}")

        # Feature Importance
        if hasattr(self.model, "feature_importances_"):
            plt.figure(figsize=(10, 6))
            importance = pd.Series(self.model.feature_importances_, index=self.feature_names)
            importance.nlargest(10).plot(kind="barh")
            plt.title("Top 10 Feature Importances")
            plt.xlabel("Importance")
            plt.tight_layout()
            fi_path = self.output_dir / "feature_importance.png"
            plt.savefig(fi_path, dpi=300, bbox_inches="tight")
            plt.close()
            saved_plots.append(fi_path)
            logger.info(f"Saved: {fi_path}")

        return saved_plots

    # =========================================================================
    # Main Evaluation Methods
    # =========================================================================

    def evaluate(
        self,
        mode: EvaluationMode = EvaluationMode.BASIC,
        save_plots: bool = False,
        save_report: bool = True,
    ) -> Dict[str, Any]:
        """
        Run evaluation based on specified mode.

        Args:
            mode: Evaluation mode (BASIC, ROBUSTNESS, THESIS)
            save_plots: Whether to save visualization plots
            save_report: Whether to save JSON report

        Returns:
            Dictionary with evaluation results
        """
        # Load data and model
        self.load()

        assert self.data is not None, "Data not loaded"  # nosec B101
        X = self.prepare_features(self.data)
        y = self.data["flood"]

        self.results = {
            "generated_at": datetime.now().isoformat(),
            "model_path": str(self._find_model()),
            "data_records": len(self.data),
            "features": self.feature_names,
        }

        # Basic metrics (always computed)
        self.results["basic_metrics"] = self.basic_metrics(X, y)
        self.results["confusion_matrix"] = self.confusion_matrix_analysis(X, y)
        self.results["feature_importance"] = self.feature_importance()

        # Mode-specific evaluations
        if mode in [EvaluationMode.ROBUSTNESS, EvaluationMode.THESIS]:
            self.results["cross_validation"] = self.cross_validation()
            self.results["robustness"] = self.noise_robustness()
            self.results["calibration"] = self.calibration_analysis()
            self.results["threshold_analysis"] = self.threshold_analysis()

        if mode in [EvaluationMode.TEMPORAL, EvaluationMode.ROBUSTNESS, EvaluationMode.THESIS]:
            temporal = self.temporal_validation()
            if temporal:
                self.results["temporal_validation"] = temporal

        if mode == EvaluationMode.CALIBRATION:
            self.results["calibration"] = self.calibration_analysis()

        # Save plots if requested
        if save_plots:
            self.results["plots"] = [str(p) for p in self.save_plots(X, y)]

        # Save report
        if save_report:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            report_path = self.output_dir / f"evaluation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_path, "w") as f:
                json.dump(self.results, f, indent=2)
            logger.info(f"Report saved: {report_path}")
            self.results["report_path"] = str(report_path)

        return self.results

    def print_summary(self):
        """Print evaluation summary to console."""
        logger.info("\n" + "=" * 70)
        logger.info("EVALUATION SUMMARY")
        logger.info("=" * 70)

        if "basic_metrics" in self.results:
            m = self.results["basic_metrics"]
            logger.info(f"Accuracy:  {m['accuracy']:.4f}")
            logger.info(f"Precision: {m['precision']:.4f}")
            logger.info(f"Recall:    {m['recall']:.4f}")
            logger.info(f"F1 Score:  {m['f1_score']:.4f}")
            if "roc_auc" in m:
                logger.info(f"ROC-AUC:   {m['roc_auc']:.4f}")

        if "cross_validation" in self.results:
            cv = self.results["cross_validation"]
            logger.info(f"\nCross-Validation:")
            logger.info(f"  F1: {cv['f1_mean']:.4f} (+/- {cv['f1_std']*2:.4f})")

        if "threshold_analysis" in self.results:
            ta = self.results["threshold_analysis"]
            if ta.get("perfectly_separable"):
                logger.info(f"\nClasses are perfectly separable (gap: {ta['gap']:.2f}mm)")


# =============================================================================
# CLI Main
# =============================================================================


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Unified Model Evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--model-path", "-m", type=str, help="Path to model file")
    parser.add_argument("--data-path", "-d", type=str, help="Path to evaluation data")
    parser.add_argument("--output-dir", "-o", type=str, help="Output directory for reports")

    # Mode selection
    parser.add_argument("--robustness", "-r", action="store_true", help="Full robustness evaluation")
    parser.add_argument("--thesis", action="store_true", help="Complete thesis defense evaluation")
    parser.add_argument("--temporal", action="store_true", help="Temporal validation only")
    parser.add_argument("--calibration", action="store_true", help="Calibration analysis only")

    # Options
    parser.add_argument("--save-plots", action="store_true", help="Save evaluation plots")
    parser.add_argument("--no-report", action="store_true", help="Skip saving JSON report")

    args = parser.parse_args()

    # Determine mode
    if args.thesis:
        mode = EvaluationMode.THESIS
    elif args.robustness:
        mode = EvaluationMode.ROBUSTNESS
    elif args.temporal:
        mode = EvaluationMode.TEMPORAL
    elif args.calibration:
        mode = EvaluationMode.CALIBRATION
    else:
        mode = EvaluationMode.BASIC

    # Run evaluation
    evaluator = UnifiedEvaluator(
        model_path=args.model_path,
        data_path=args.data_path,
        output_dir=args.output_dir,
    )

    results = evaluator.evaluate(
        mode=mode,
        save_plots=args.save_plots,
        save_report=not args.no_report,
    )

    evaluator.print_summary()

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
