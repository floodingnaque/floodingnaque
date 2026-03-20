#!/usr/bin/env python
"""
Model Performance Graph Generator
=================================

Generates and stores PNG visualizations of model performance metrics
in the reports/ directory.

Usage:
    python scripts/generate_performance_graphs.py
    python scripts/generate_performance_graphs.py --model models/flood_rf_model.joblib
    python scripts/generate_performance_graphs.py --output-dir reports/v7

Generated Plots:
    - confusion_matrix.png: Confusion matrix heatmap
    - feature_importance.png: Feature importance bar chart
    - roc_curve.png: ROC curve with AUC
    - precision_recall_curve.png: Precision-recall curve
    - learning_curves.png: Training/validation learning curves
    - metrics_comparison.png: Multi-model metrics comparison
    - calibration_curve.png: Probability calibration curve
    - model_progression_chart.png: Model version progression

Author: Floodingnaque Team
Date: 2026-01-24
"""

import argparse
import json
import logging
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    auc,
    confusion_matrix,
    precision_recall_curve,
    roc_curve,
)
from sklearn.model_selection import learning_curve

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

# Plot style settings
plt.style.use("seaborn-v0_8-whitegrid")
FIGURE_DPI = 150
FIGURE_SIZE = (10, 8)
COLOR_PALETTE = sns.color_palette("viridis", 10)


class PerformanceGraphGenerator:
    """Generate and save model performance visualizations."""

    def __init__(
        self,
        model_path: Optional[Path] = None,
        data_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
    ):
        """
        Initialize the graph generator.

        Args:
            model_path: Path to the trained model file
            data_path: Path to the evaluation dataset
            output_dir: Directory to save generated plots
        """
        self.model_path = model_path or MODELS_DIR / "flood_rf_model.joblib"
        self.data_path = data_path or self._find_latest_dataset()
        self.output_dir = output_dir or REPORTS_DIR

        self.model: Any = None
        self.data: Optional[pd.DataFrame] = None
        self.X: Optional[pd.DataFrame] = None
        self.y: Optional[pd.Series] = None
        self.y_pred: Optional[np.ndarray] = None
        self.y_proba: Optional[np.ndarray] = None

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _find_latest_dataset(self) -> Path:
        """Find the latest cumulative dataset."""
        candidates = [
            PROCESSED_DIR / "cumulative_v2_up_to_2025.csv",
            PROCESSED_DIR / "cumulative_up_to_2025.csv",
        ]
        for path in candidates:
            if path.exists():
                return path
        raise FileNotFoundError("No suitable dataset found")

    def load_model_and_data(self) -> None:
        """Load the model and evaluation data."""
        logger.info(f"Loading model from {self.model_path}")
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")

        self.model = joblib.load(self.model_path)

        logger.info(f"Loading data from {self.data_path}")
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data not found: {self.data_path}")

        self.data = pd.read_csv(self.data_path)

        # Handle different column naming conventions
        target_col = None
        for col in ["flood", "Flood", "FLOOD", "flood_occurred"]:
            if col in self.data.columns:
                target_col = col
                break

        if target_col is None:
            raise ValueError("No target column found in dataset")

        self.X = self.data.drop(columns=[target_col])
        self.y = self.data[target_col]

        # Generate predictions
        self.y_pred = self.model.predict(self.X)

        # Get probability predictions if available
        if hasattr(self.model, "predict_proba"):
            self.y_proba = self.model.predict_proba(self.X)[:, 1]
        else:
            self.y_proba = np.asarray(self.y_pred, dtype=float)

        logger.info(f"Loaded {len(self.data)} samples with {len(self.X.columns)} features")

    def generate_confusion_matrix(self) -> Path:
        """Generate confusion matrix heatmap."""
        logger.info("Generating confusion matrix...")

        if self.y is None or self.y_pred is None:
            raise RuntimeError("Must call load_model_and_data first")
        cm = confusion_matrix(self.y, self.y_pred)

        fig, ax = plt.subplots(figsize=(8, 6), dpi=FIGURE_DPI)

        sns.heatmap(
            cm,
            annot=True,
            fmt="d",
            cmap="Blues",
            ax=ax,
            xticklabels=["No Flood", "Flood"],
            yticklabels=["No Flood", "Flood"],
            annot_kws={"size": 14},
        )

        ax.set_xlabel("Predicted", fontsize=12)
        ax.set_ylabel("Actual", fontsize=12)
        ax.set_title("Confusion Matrix - Flood Prediction Model", fontsize=14)

        # Add accuracy annotation
        accuracy = (cm[0, 0] + cm[1, 1]) / cm.sum()
        fig.text(
            0.5,
            0.02,
            f"Overall Accuracy: {accuracy:.2%}",
            ha="center",
            fontsize=11,
            style="italic",
        )

        plt.tight_layout()

        output_path = self.output_dir / "confusion_matrix.png"
        plt.savefig(output_path, dpi=FIGURE_DPI, bbox_inches="tight")
        plt.close()

        logger.info(f"Saved: {output_path}")
        return output_path

    def generate_feature_importance(self) -> Optional[Path]:
        """Generate feature importance bar chart."""
        logger.info("Generating feature importance chart...")

        if self.model is None or self.X is None:
            raise RuntimeError("Must call load_model_and_data first")

        if not hasattr(self.model, "feature_importances_"):
            logger.warning("Model doesn't support feature_importances_, skipping")
            return None

        importance = self.model.feature_importances_
        feature_names = self.X.columns.tolist()

        # Sort by importance
        indices = np.argsort(importance)[::-1]

        # Take top 15 features
        top_n = min(15, len(feature_names))
        top_indices = indices[:top_n]

        fig, ax = plt.subplots(figsize=(12, 8), dpi=FIGURE_DPI)

        colors = sns.color_palette("viridis", top_n)

        bars = ax.barh(
            range(top_n),
            importance[top_indices],
            color=colors,
            edgecolor="white",
            linewidth=0.7,
        )

        ax.set_yticks(range(top_n))
        ax.set_yticklabels([feature_names[i] for i in top_indices])
        ax.invert_yaxis()

        ax.set_xlabel("Feature Importance", fontsize=12)
        ax.set_title("Top Feature Importances - Flood Prediction Model", fontsize=14)

        # Add value labels
        for bar, val in zip(bars, importance[top_indices]):
            ax.text(
                val + 0.005,
                bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}",
                va="center",
                fontsize=9,
            )

        plt.tight_layout()

        output_path = self.output_dir / "feature_importance.png"
        plt.savefig(output_path, dpi=FIGURE_DPI, bbox_inches="tight")
        plt.close()

        logger.info(f"Saved: {output_path}")
        return output_path

    def generate_roc_curve(self) -> Path:
        """Generate ROC curve with AUC."""
        logger.info("Generating ROC curve...")

        if self.y is None or self.y_proba is None:
            raise RuntimeError("Must call load_model_and_data first")
        fpr, tpr, _ = roc_curve(self.y, self.y_proba)
        roc_auc = auc(fpr, tpr)

        fig, ax = plt.subplots(figsize=(8, 8), dpi=FIGURE_DPI)

        ax.plot(
            fpr,
            tpr,
            color="#2196F3",
            lw=2.5,
            label=f"ROC Curve (AUC = {roc_auc:.4f})",
        )
        ax.plot([0, 1], [0, 1], "k--", lw=1.5, label="Random Classifier")

        ax.fill_between(fpr, tpr, alpha=0.2, color="#2196F3")

        ax.set_xlim(0.0, 1.0)
        ax.set_ylim(0.0, 1.05)
        ax.set_xlabel("False Positive Rate", fontsize=12)
        ax.set_ylabel("True Positive Rate", fontsize=12)
        ax.set_title("Receiver Operating Characteristic (ROC) Curve", fontsize=14)
        ax.legend(loc="lower right", fontsize=11)
        ax.grid(True, alpha=0.3)

        # Add threshold annotation
        ax.annotate(
            f"AUC = {roc_auc:.4f}",
            xy=(0.6, 0.4),
            fontsize=16,
            fontweight="bold",
            color="#2196F3",
        )

        plt.tight_layout()

        output_path = self.output_dir / "roc_curve.png"
        plt.savefig(output_path, dpi=FIGURE_DPI, bbox_inches="tight")
        plt.close()

        logger.info(f"Saved: {output_path}")
        return output_path

    def generate_precision_recall_curve(self) -> Path:
        """Generate precision-recall curve."""
        logger.info("Generating precision-recall curve...")

        if self.y is None or self.y_proba is None:
            raise RuntimeError("Must call load_model_and_data first")
        precision, recall, _ = precision_recall_curve(self.y, self.y_proba)
        pr_auc = auc(recall, precision)

        fig, ax = plt.subplots(figsize=(8, 8), dpi=FIGURE_DPI)

        ax.plot(
            recall,
            precision,
            color="#4CAF50",
            lw=2.5,
            label=f"PR Curve (AUC = {pr_auc:.4f})",
        )

        # Baseline (random classifier)
        baseline = float(self.y.sum()) / len(self.y)
        ax.axhline(y=baseline, color="gray", linestyle="--", lw=1.5, label="Baseline")

        ax.fill_between(recall, precision, alpha=0.2, color="#4CAF50")

        ax.set_xlim(0.0, 1.0)
        ax.set_ylim(0.0, 1.05)
        ax.set_xlabel("Recall", fontsize=12)
        ax.set_ylabel("Precision", fontsize=12)
        ax.set_title("Precision-Recall Curve", fontsize=14)
        ax.legend(loc="lower left", fontsize=11)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        output_path = self.output_dir / "precision_recall_curve.png"
        plt.savefig(output_path, dpi=FIGURE_DPI, bbox_inches="tight")
        plt.close()

        logger.info(f"Saved: {output_path}")
        return output_path

    def generate_learning_curves(self) -> Path:
        """Generate learning curves showing training/validation performance."""
        logger.info("Generating learning curves...")

        if self.model is None or self.X is None or self.y is None:
            raise RuntimeError("Must call load_model_and_data first")

        train_sizes, train_scores, val_scores, *_ = learning_curve(
            self.model,
            self.X,
            self.y,
            cv=5,
            train_sizes=np.linspace(0.1, 1.0, 10),
            scoring="accuracy",
            n_jobs=-1,
        )

        train_mean = np.mean(train_scores, axis=1)
        train_std = np.std(train_scores, axis=1)
        val_mean = np.mean(val_scores, axis=1)
        val_std = np.std(val_scores, axis=1)

        fig, ax = plt.subplots(figsize=(10, 6), dpi=FIGURE_DPI)

        ax.plot(train_sizes, train_mean, "o-", color="#2196F3", lw=2, label="Training Score")
        ax.fill_between(
            train_sizes,
            train_mean - train_std,
            train_mean + train_std,
            alpha=0.2,
            color="#2196F3",
        )

        ax.plot(train_sizes, val_mean, "o-", color="#FF9800", lw=2, label="Validation Score")
        ax.fill_between(
            train_sizes,
            val_mean - val_std,
            val_mean + val_std,
            alpha=0.2,
            color="#FF9800",
        )

        ax.set_xlabel("Training Set Size", fontsize=12)
        ax.set_ylabel("Accuracy Score", fontsize=12)
        ax.set_title("Learning Curves - Model Convergence Analysis", fontsize=14)
        ax.legend(loc="lower right", fontsize=11)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0.5, 1.05)

        plt.tight_layout()

        output_path = self.output_dir / "learning_curves.png"
        plt.savefig(output_path, dpi=FIGURE_DPI, bbox_inches="tight")
        plt.close()

        logger.info(f"Saved: {output_path}")
        return output_path

    def generate_calibration_curve(self) -> Path:
        """Generate probability calibration curve."""
        logger.info("Generating calibration curve...")

        if self.y is None or self.y_proba is None:
            raise RuntimeError("Must call load_model_and_data first")
        fraction_of_positives, mean_predicted_value = calibration_curve(self.y, self.y_proba, n_bins=10)

        fig, ax = plt.subplots(figsize=(8, 8), dpi=FIGURE_DPI)

        ax.plot([0, 1], [0, 1], "k--", lw=1.5, label="Perfectly Calibrated")
        ax.plot(
            mean_predicted_value,
            fraction_of_positives,
            "s-",
            color="#9C27B0",
            lw=2,
            markersize=8,
            label="Model Calibration",
        )

        ax.set_xlabel("Mean Predicted Probability", fontsize=12)
        ax.set_ylabel("Fraction of Positives", fontsize=12)
        ax.set_title("Calibration Curve (Reliability Diagram)", fontsize=14)
        ax.legend(loc="lower right", fontsize=11)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        output_path = self.output_dir / "calibration_curve.png"
        plt.savefig(output_path, dpi=FIGURE_DPI, bbox_inches="tight")
        plt.close()

        logger.info(f"Saved: {output_path}")
        return output_path

    def generate_metrics_comparison(self) -> Path:
        """Generate multi-metric comparison bar chart."""
        logger.info("Generating metrics comparison chart...")

        from sklearn.metrics import (
            accuracy_score,
            f1_score,
            precision_score,
            recall_score,
            roc_auc_score,
        )

        if self.y is None or self.y_pred is None or self.y_proba is None:
            raise RuntimeError("Must call load_model_and_data first")

        metrics = {
            "Accuracy": accuracy_score(self.y, self.y_pred),
            "Precision": precision_score(self.y, self.y_pred, zero_division=0),
            "Recall": recall_score(self.y, self.y_pred, zero_division=0),
            "F1 Score": f1_score(self.y, self.y_pred, zero_division=0),
            "ROC-AUC": roc_auc_score(self.y, self.y_proba),
        }

        fig, ax = plt.subplots(figsize=(10, 6), dpi=FIGURE_DPI)

        colors = ["#2196F3", "#4CAF50", "#FF9800", "#9C27B0", "#F44336"]

        bars = ax.bar(
            list(metrics.keys()),
            list(metrics.values()),
            color=colors,
            edgecolor="white",
            linewidth=1.5,
        )

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                height + 0.02,
                f"{height:.3f}",
                ha="center",
                va="bottom",
                fontsize=12,
                fontweight="bold",
            )

        ax.set_ylim(0, 1.15)
        ax.set_ylabel("Score", fontsize=12)
        ax.set_title("Model Performance Metrics Comparison", fontsize=14)
        ax.axhline(y=0.5, color="gray", linestyle="--", lw=1, alpha=0.5)

        plt.tight_layout()

        output_path = self.output_dir / "metrics_comparison.png"
        plt.savefig(output_path, dpi=FIGURE_DPI, bbox_inches="tight")
        plt.close()

        logger.info(f"Saved: {output_path}")
        return output_path

    def generate_model_progression(self) -> Path:
        """Generate model version progression chart from historical reports."""
        logger.info("Generating model progression chart...")

        # Try to load historical data from reports
        progression_data = []

        # Check for progressive training report
        progressive_report = REPORTS_DIR / "progressive_training_report.json"
        if progressive_report.exists():
            with open(progressive_report) as f:
                report = json.load(f)
                if "results" in report:
                    for result in report["results"]:
                        progression_data.append(
                            {
                                "version": result.get("dataset", "Unknown"),
                                "accuracy": result.get("accuracy", 0),
                                "f1": result.get("f1_score", 0),
                            }
                        )

        # If no historical data, create from current model
        if not progression_data:
            from sklearn.metrics import accuracy_score, f1_score

            if self.y is None or self.y_pred is None:
                raise RuntimeError("Must call load_model_and_data first")
            progression_data = [
                {
                    "version": "Current",
                    "accuracy": accuracy_score(self.y, self.y_pred),
                    "f1": f1_score(self.y, self.y_pred, zero_division=0),
                }
            ]

        fig, ax = plt.subplots(figsize=(12, 6), dpi=FIGURE_DPI)

        versions = [d["version"] for d in progression_data]
        accuracies = [d["accuracy"] for d in progression_data]
        f1_scores = [d["f1"] for d in progression_data]

        x = np.arange(len(versions))
        width = 0.35

        ax.bar(x - width / 2, accuracies, width, label="Accuracy", color="#2196F3")
        ax.bar(x + width / 2, f1_scores, width, label="F1 Score", color="#4CAF50")

        ax.set_xlabel("Model Version / Dataset", fontsize=12)
        ax.set_ylabel("Score", fontsize=12)
        ax.set_title("Model Performance Progression", fontsize=14)
        ax.set_xticks(x)
        ax.set_xticklabels(versions, rotation=45, ha="right")
        ax.legend()
        ax.set_ylim(0, 1.1)
        ax.grid(True, alpha=0.3, axis="y")

        plt.tight_layout()

        output_path = self.output_dir / "model_progression_chart.png"
        plt.savefig(output_path, dpi=FIGURE_DPI, bbox_inches="tight")
        plt.close()

        logger.info(f"Saved: {output_path}")
        return output_path

    def generate_all(self) -> Dict[str, Path]:
        """Generate all performance graphs."""
        self.load_model_and_data()

        generated = {}

        try:
            generated["confusion_matrix"] = self.generate_confusion_matrix()
        except Exception as e:
            logger.error(f"Failed to generate confusion matrix: {e}")

        try:
            generated["feature_importance"] = self.generate_feature_importance()
        except Exception as e:
            logger.error(f"Failed to generate feature importance: {e}")

        try:
            generated["roc_curve"] = self.generate_roc_curve()
        except Exception as e:
            logger.error(f"Failed to generate ROC curve: {e}")

        try:
            generated["precision_recall"] = self.generate_precision_recall_curve()
        except Exception as e:
            logger.error(f"Failed to generate precision-recall curve: {e}")

        try:
            generated["learning_curves"] = self.generate_learning_curves()
        except Exception as e:
            logger.error(f"Failed to generate learning curves: {e}")

        try:
            generated["calibration"] = self.generate_calibration_curve()
        except Exception as e:
            logger.error(f"Failed to generate calibration curve: {e}")

        try:
            generated["metrics_comparison"] = self.generate_metrics_comparison()
        except Exception as e:
            logger.error(f"Failed to generate metrics comparison: {e}")

        try:
            generated["model_progression"] = self.generate_model_progression()
        except Exception as e:
            logger.error(f"Failed to generate model progression: {e}")

        # Save generation summary
        summary = {
            "generated_at": datetime.now().isoformat(),
            "model_path": str(self.model_path),
            "data_path": str(self.data_path),
            "output_dir": str(self.output_dir),
            "graphs": {k: str(v) for k, v in generated.items() if v},
        }

        summary_path = self.output_dir / "graphs_generation_summary.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Generated {len(generated)} graphs in {self.output_dir}")
        return generated


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate model performance visualization graphs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--model",
        type=Path,
        help="Path to trained model file",
    )
    parser.add_argument(
        "--data",
        type=Path,
        help="Path to evaluation dataset",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory to save generated graphs",
    )
    parser.add_argument(
        "--graph",
        choices=[
            "confusion_matrix",
            "feature_importance",
            "roc_curve",
            "precision_recall",
            "learning_curves",
            "calibration",
            "metrics_comparison",
            "model_progression",
            "all",
        ],
        default="all",
        help="Specific graph to generate (default: all)",
    )

    args = parser.parse_args()

    generator = PerformanceGraphGenerator(
        model_path=args.model,
        data_path=args.data,
        output_dir=args.output_dir,
    )

    if args.graph == "all":
        generator.generate_all()
    else:
        generator.load_model_and_data()
        method_name = f"generate_{args.graph}"
        if hasattr(generator, method_name):
            getattr(generator, method_name)()
        else:
            logger.error(f"Unknown graph type: {args.graph}")


if __name__ == "__main__":
    main()
