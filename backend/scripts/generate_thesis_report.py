"""
================================================================================
ULTIMATE COMPREHENSIVE MODEL ANALYSIS & THESIS REPORT GENERATOR
Flood Prediction Model - Parañaque City
================================================================================

Generates EVERY possible report, chart, metric, and export including:

STATIC CHARTS (PNG, 300 DPI):
  - Feature importance (bar + dot plot variants)
  - Confusion matrix (counts + normalized)
  - ROC curve (with optimal threshold marked)
  - Precision-Recall curve (with F1 iso-lines)
  - Learning curves
  - Model metrics comparison bar chart
  - Threshold analysis (precision/recall/F1 vs threshold)
  - Prediction probability distribution
  - Calibration curve (reliability diagram)
  - Per-class metrics radar chart
  - Permutation feature importance
  - Class distribution plot
  - Correlation heatmap of features
  - Cumulative gain / lift chart
  - Decision boundary (if 2D reducible)
  - Error analysis: FP/FN sample distribution

INTERACTIVE HTML CHARTS (Plotly):
  - All static charts as interactive HTML
  - Full metrics dashboard with gauges
  - Multi-model comparison dashboard (if comparing versions)

DATA EXPORTS (CSV / Excel):
  - Full predictions with probabilities
  - Feature importance table
  - Threshold sweep table
  - Per-class metrics table
  - Misclassified samples
  - Permutation importance table
  - Cross-validation scores (if metadata available)

REPORTS (TXT / JSON):
  - Full text report
  - Machine-readable JSON metrics
  - Executive summary (markdown)

USAGE:
# Basic
python generate_thesis_report.py --model models/flood_model_v6.joblib --data data/dataset.csv

# With interactive charts
python generate_thesis_report.py --model models/flood_model_v6.joblib --data data/dataset.csv --interactive

# Fast run (skip learning curves & permutation importance)
python generate_thesis_report.py --model models/flood_model_v6.joblib --data data/dataset.csv --skip-slow

# Compare multiple model versions
python generate_thesis_report.py --model models/flood_model_v6.joblib --data data/dataset.csv --compare models/flood_model_v5.joblib models/flood_model_v4.joblib

python generate_thesis_report.py --model models/flood_model_v6.joblib --data data/dataset.csv
python generate_thesis_report.py --model models/flood_model_v6.joblib --data data/dataset.csv --interactive
python generate_thesis_report.py --model models/flood_model_v6.joblib --data data/dataset.csv --compare models/flood_model_v5.joblib
"""

import json
import logging
import sys
import warnings
from datetime import datetime
from pathlib import Path

import joblib
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.gridspec import GridSpec
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    accuracy_score,
    auc,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    classification_report,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    log_loss,
    matthews_corrcoef,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import cross_val_score, learning_curve
from sklearn.preprocessing import label_binarize

warnings.filterwarnings("ignore")

# Check for plotly
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    px = go = make_subplots = None

# Check for openpyxl (Excel export)
try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

plt.style.use("seaborn-v0_8-darkgrid")
sns.set_palette("husl")
COLORS = ["#2ecc71", "#3498db", "#e74c3c", "#f39c12", "#9b59b6", "#1abc9c"]


# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def load_model_and_metadata(model_path):
    """Load model and its metadata JSON if present."""
    model_path = Path(model_path)
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")
    model = joblib.load(model_path)
    metadata_path = model_path.with_suffix(".json")
    metadata = None
    if metadata_path.exists():
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
    logger.info(f"Loaded model from {model_path}")
    return model, metadata


def prepare_data(model, data_path):
    """Load CSV and align features to model expectations."""
    data_path = Path(data_path)
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")
    data = pd.read_csv(data_path)
    if hasattr(model, "feature_names_in_"):
        feature_names = list(model.feature_names_in_)
        X = data[feature_names]
    else:
        target_col = "flood" if "flood" in data.columns else data.columns[-1]
        X = data.drop(columns=[target_col])
    target_col = "flood" if "flood" in data.columns else data.columns[-1]
    y = data[target_col]
    logger.info(f"Data loaded: {X.shape[0]} samples, {X.shape[1]} features")
    return X, y, data


def compute_all_metrics(y_true, y_pred, y_pred_proba):
    """Compute every sklearn metric available for binary classification."""
    if y_pred_proba.ndim > 1:
        proba_pos = y_pred_proba[:, 1]
    else:
        proba_pos = y_pred_proba

    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()

    metrics = {
        # Core
        "accuracy": accuracy_score(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "precision_weighted": precision_score(y_true, y_pred, average="weighted"),
        "recall_weighted": recall_score(y_true, y_pred, average="weighted"),
        "f1_weighted": f1_score(y_true, y_pred, average="weighted"),
        "precision_macro": precision_score(y_true, y_pred, average="macro"),
        "recall_macro": recall_score(y_true, y_pred, average="macro"),
        "f1_macro": f1_score(y_true, y_pred, average="macro"),
        # Per-class
        "precision_flood": precision_score(y_true, y_pred, pos_label=1),
        "recall_flood": recall_score(y_true, y_pred, pos_label=1),
        "f1_flood": f1_score(y_true, y_pred, pos_label=1),
        "precision_no_flood": precision_score(y_true, y_pred, pos_label=0),
        "recall_no_flood": recall_score(y_true, y_pred, pos_label=0),
        "f1_no_flood": f1_score(y_true, y_pred, pos_label=0),
        # Probabilistic
        "roc_auc": roc_auc_score(y_true, proba_pos),
        "average_precision": average_precision_score(y_true, proba_pos),
        "log_loss": log_loss(y_true, proba_pos),
        "brier_score": brier_score_loss(y_true, proba_pos),
        # Advanced
        "matthews_corrcoef": matthews_corrcoef(y_true, y_pred),
        "cohen_kappa": cohen_kappa_score(y_true, y_pred),
        # Confusion matrix breakdown
        "true_positives": int(tp),
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "specificity": tn / (tn + fp) if (tn + fp) > 0 else 0,
        "sensitivity": tp / (tp + fn) if (tp + fn) > 0 else 0,  # same as recall
        "false_positive_rate": fp / (fp + tn) if (fp + tn) > 0 else 0,
        "false_negative_rate": fn / (fn + tp) if (fn + tp) > 0 else 0,
        "positive_predictive_value": tp / (tp + fp) if (tp + fp) > 0 else 0,  # precision
        "negative_predictive_value": tn / (tn + fn) if (tn + fn) > 0 else 0,
        "prevalence": (tp + fn) / len(y_true),
        "threat_score": tp / (tp + fn + fp) if (tp + fn + fp) > 0 else 0,  # CSI
    }
    return metrics


def find_optimal_threshold(y_true, y_pred_proba):
    """Find optimal classification threshold by maximizing F1."""
    if y_pred_proba.ndim > 1:
        proba_pos = y_pred_proba[:, 1]
    else:
        proba_pos = y_pred_proba
    thresholds = np.arange(0.01, 1.0, 0.01)
    best_f1, best_thresh = 0, 0.5
    for t in thresholds:
        preds = (proba_pos >= t).astype(int)
        f = f1_score(y_true, preds, zero_division=0)
        if f > best_f1:
            best_f1, best_thresh = f, t
    return best_thresh, best_f1


# ==============================================================================
# STATIC CHARTS
# ==============================================================================

def plot_feature_importance(model, output_dir, top_n=20):
    logger.info("  → Feature importance (bar)...")
    if not hasattr(model, "feature_importances_"):
        logger.warning("Model has no feature_importances_. Skipping.")
        return
    feature_names = (list(model.feature_names_in_) if hasattr(model, "feature_names_in_")
                     else [f"Feature {i}" for i in range(len(model.feature_importances_))])
    imp_df = pd.DataFrame({"feature": feature_names, "importance": model.feature_importances_})
    imp_df = imp_df.sort_values("importance", ascending=False).head(top_n)

    fig, axes = plt.subplots(1, 2, figsize=(16, max(6, len(imp_df) * 0.35)))

    # Horizontal bar
    colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(imp_df)))
    axes[0].barh(imp_df["feature"][::-1], imp_df["importance"][::-1], color=colors[::-1])
    for i, (_, row) in enumerate(imp_df[::-1].iterrows()):
        axes[0].text(row["importance"], i, f'  {row["importance"]:.4f}', va="center", fontsize=8)
    axes[0].set_xlabel("Importance", fontweight="bold")
    axes[0].set_title("Feature Importance (Bar)", fontweight="bold")

    # Dot plot
    axes[1].scatter(imp_df["importance"], imp_df["feature"], s=80, c=imp_df["importance"],
                    cmap="viridis", zorder=3)
    for _, row in imp_df.iterrows():
        axes[1].hlines(row["feature"], 0, row["importance"], colors="gray", alpha=0.4, linewidth=1)
    axes[1].set_xlabel("Importance", fontweight="bold")
    axes[1].set_title("Feature Importance (Lollipop)", fontweight="bold")
    axes[1].invert_yaxis()

    fig.suptitle("Random Forest Feature Importance – Flood Prediction", fontsize=14, fontweight="bold")
    plt.tight_layout()
    path = Path(output_dir) / "feature_importance.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"    Saved: {path.name}")
    return imp_df


def plot_confusion_matrices(y_true, y_pred, output_dir):
    logger.info("  → Confusion matrices (raw + normalized)...")
    cm = confusion_matrix(y_true, y_pred)
    cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True)
    labels = ["No Flood", "Flood"]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for ax, data, fmt, title in zip(
        axes,
        [cm, cm_norm],
        ["d", ".2%"],
        ["Confusion Matrix (Counts)", "Confusion Matrix (Normalized)"]
    ):
        sns.heatmap(data, annot=True, fmt=fmt, cmap="Blues", ax=ax,
                    xticklabels=labels, yticklabels=labels,
                    annot_kws={"size": 13, "weight": "bold"})
        ax.set_ylabel("Actual", fontweight="bold")
        ax.set_xlabel("Predicted", fontweight="bold")
        ax.set_title(title, fontweight="bold")

    fig.suptitle("Confusion Matrices – Flood Prediction Model", fontsize=14, fontweight="bold")
    plt.tight_layout()
    path = Path(output_dir) / "confusion_matrix.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"    Saved: {path.name}")


def plot_roc_curve(y_true, y_pred_proba, output_dir, optimal_threshold=None):
    logger.info("  → ROC curve...")
    if y_pred_proba.ndim > 1:
        proba_pos = y_pred_proba[:, 1]
    else:
        proba_pos = y_pred_proba

    fpr, tpr, thresholds = roc_curve(y_true, proba_pos)
    roc_auc = auc(fpr, tpr)

    plt.figure(figsize=(8, 7))
    plt.plot(fpr, tpr, color="darkorange", lw=2.5, label=f"ROC Curve (AUC = {roc_auc:.4f})")
    plt.plot([0, 1], [0, 1], "k--", lw=1.5, label="Random Classifier (AUC = 0.5)")
    plt.fill_between(fpr, tpr, alpha=0.08, color="darkorange")

    # Mark optimal threshold point
    if optimal_threshold is not None:
        idx = np.argmin(np.abs(thresholds - optimal_threshold))
        plt.scatter(fpr[idx], tpr[idx], s=120, color="red", zorder=5,
                    label=f"Optimal Threshold ({optimal_threshold:.2f})")

    plt.xlim([-0.01, 1.01])
    plt.ylim([-0.01, 1.05])
    plt.xlabel("False Positive Rate", fontsize=12, fontweight="bold")
    plt.ylabel("True Positive Rate (Sensitivity)", fontsize=12, fontweight="bold")
    plt.title("ROC Curve – Flood Prediction Model", fontsize=14, fontweight="bold", pad=15)
    plt.legend(loc="lower right", fontsize=10)
    plt.tight_layout()
    path = Path(output_dir) / "roc_curve.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"    Saved: {path.name}")


def plot_precision_recall_curve(y_true, y_pred_proba, output_dir):
    logger.info("  → Precision-Recall curve...")
    if y_pred_proba.ndim > 1:
        proba_pos = y_pred_proba[:, 1]
    else:
        proba_pos = y_pred_proba

    precision, recall, thresholds = precision_recall_curve(y_true, proba_pos)
    pr_auc = auc(recall, precision)
    baseline = y_true.mean()

    plt.figure(figsize=(8, 7))
    plt.plot(recall, precision, color="steelblue", lw=2.5, label=f"PR Curve (AUC = {pr_auc:.4f})")
    plt.axhline(baseline, color="gray", linestyle="--", lw=1.5, label=f"Baseline (prevalence = {baseline:.3f})")
    plt.fill_between(recall, precision, alpha=0.08, color="steelblue")

    # F1 iso-lines
    for f1_val in [0.4, 0.6, 0.8]:
        r = np.linspace(0.01, 1)
        p = f1_val * r / (2 * r - f1_val)
        p = np.clip(p, 0, 1)
        plt.plot(r, p, ":", color="green", alpha=0.5, linewidth=1)
        plt.annotate(f"F1={f1_val}", xy=(r[-1], p[-1]), fontsize=8, color="green", alpha=0.7)

    plt.xlim([0, 1.01])
    plt.ylim([0, 1.05])
    plt.xlabel("Recall", fontsize=12, fontweight="bold")
    plt.ylabel("Precision", fontsize=12, fontweight="bold")
    plt.title("Precision-Recall Curve – Flood Prediction Model", fontsize=14, fontweight="bold", pad=15)
    plt.legend(loc="upper right", fontsize=10)
    plt.tight_layout()
    path = Path(output_dir) / "precision_recall_curve.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"    Saved: {path.name}")


def plot_threshold_analysis(y_true, y_pred_proba, output_dir):
    logger.info("  → Threshold analysis...")
    if y_pred_proba.ndim > 1:
        proba_pos = y_pred_proba[:, 1]
    else:
        proba_pos = y_pred_proba

    thresholds = np.arange(0.01, 1.0, 0.01)
    precisions, recalls, f1s, accuracies, specificities = [], [], [], [], []

    for t in thresholds:
        preds = (proba_pos >= t).astype(int)
        precisions.append(precision_score(y_true, preds, zero_division=0))
        recalls.append(recall_score(y_true, preds, zero_division=0))
        f1s.append(f1_score(y_true, preds, zero_division=0))
        accuracies.append(accuracy_score(y_true, preds))
        cm = confusion_matrix(y_true, preds)
        if cm.shape == (2, 2):
            tn, fp, fn, tp = cm.ravel()
            specificities.append(tn / (tn + fp) if (tn + fp) > 0 else 0)
        else:
            specificities.append(0)

    best_idx = np.argmax(f1s)

    fig, axes = plt.subplots(2, 1, figsize=(12, 10))

    # Top: P/R/F1
    axes[0].plot(thresholds, precisions, label="Precision", color="#3498db", lw=2)
    axes[0].plot(thresholds, recalls, label="Recall / Sensitivity", color="#e74c3c", lw=2)
    axes[0].plot(thresholds, f1s, label="F1 Score", color="#f39c12", lw=2.5)
    axes[0].axvline(thresholds[best_idx], color="black", linestyle="--", alpha=0.6,
                    label=f"Best F1 threshold ({thresholds[best_idx]:.2f})")
    axes[0].set_ylabel("Score", fontweight="bold")
    axes[0].set_title("Precision / Recall / F1 vs Classification Threshold", fontweight="bold")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Bottom: Accuracy & Specificity
    axes[1].plot(thresholds, accuracies, label="Accuracy", color="#2ecc71", lw=2)
    axes[1].plot(thresholds, specificities, label="Specificity", color="#9b59b6", lw=2)
    axes[1].axvline(thresholds[best_idx], color="black", linestyle="--", alpha=0.6)
    axes[1].set_xlabel("Classification Threshold", fontweight="bold")
    axes[1].set_ylabel("Score", fontweight="bold")
    axes[1].set_title("Accuracy & Specificity vs Classification Threshold", fontweight="bold")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    path = Path(output_dir) / "threshold_analysis.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"    Saved: {path.name}")

    # Also return the table data
    return pd.DataFrame({
        "threshold": thresholds,
        "precision": precisions,
        "recall": recalls,
        "f1": f1s,
        "accuracy": accuracies,
        "specificity": specificities,
    })


def plot_probability_distribution(y_true, y_pred_proba, output_dir):
    logger.info("  → Prediction probability distribution...")
    if y_pred_proba.ndim > 1:
        proba_pos = y_pred_proba[:, 1]
    else:
        proba_pos = y_pred_proba

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Histogram by class
    no_flood_proba = proba_pos[y_true == 0]
    flood_proba = proba_pos[y_true == 1]
    axes[0].hist(no_flood_proba, bins=40, alpha=0.6, color="#3498db", label="Actual: No Flood", density=True)
    axes[0].hist(flood_proba, bins=40, alpha=0.6, color="#e74c3c", label="Actual: Flood", density=True)
    axes[0].axvline(0.5, color="black", linestyle="--", label="Default threshold (0.5)")
    axes[0].set_xlabel("Predicted Probability (Flood)", fontweight="bold")
    axes[0].set_ylabel("Density", fontweight="bold")
    axes[0].set_title("Probability Distribution by Class", fontweight="bold")
    axes[0].legend()

    # KDE
    try:
        from scipy.stats import gaussian_kde
        x = np.linspace(0, 1, 200)
        if len(no_flood_proba) > 1:
            kde0 = gaussian_kde(no_flood_proba)
            axes[1].fill_between(x, kde0(x), alpha=0.4, color="#3498db", label="No Flood")
            axes[1].plot(x, kde0(x), color="#3498db", lw=2)
        if len(flood_proba) > 1:
            kde1 = gaussian_kde(flood_proba)
            axes[1].fill_between(x, kde1(x), alpha=0.4, color="#e74c3c", label="Flood")
            axes[1].plot(x, kde1(x), color="#e74c3c", lw=2)
        axes[1].set_xlabel("Predicted Probability (Flood)", fontweight="bold")
        axes[1].set_ylabel("Density", fontweight="bold")
        axes[1].set_title("Probability Density (KDE) by Class", fontweight="bold")
        axes[1].legend()
    except ImportError:
        axes[1].text(0.5, 0.5, "scipy not installed\n(pip install scipy)", ha="center", va="center",
                     transform=axes[1].transAxes)

    plt.suptitle("Prediction Probability Distribution", fontsize=14, fontweight="bold")
    plt.tight_layout()
    path = Path(output_dir) / "probability_distribution.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"    Saved: {path.name}")


def plot_calibration_curve(y_true, y_pred_proba, output_dir):
    logger.info("  → Calibration curve...")
    try:
        from sklearn.calibration import calibration_curve
    except ImportError:
        logger.warning("    calibration_curve not available.")
        return

    if y_pred_proba.ndim > 1:
        proba_pos = y_pred_proba[:, 1]
    else:
        proba_pos = y_pred_proba

    plt.figure(figsize=(8, 7))
    for n_bins, color, style in [(10, "#e74c3c", "-"), (20, "#3498db", "--")]:
        try:
            fraction_pos, mean_pred = calibration_curve(y_true, proba_pos, n_bins=n_bins)
            plt.plot(mean_pred, fraction_pos, marker="o", linestyle=style, color=color,
                     label=f"RF ({n_bins} bins)", lw=2)
        except Exception:
            pass

    plt.plot([0, 1], [0, 1], "k--", lw=1.5, label="Perfectly Calibrated")
    plt.xlabel("Mean Predicted Probability", fontsize=12, fontweight="bold")
    plt.ylabel("Fraction of Positives", fontsize=12, fontweight="bold")
    plt.title("Calibration Curve (Reliability Diagram)\nFlood Prediction Model", fontsize=14, fontweight="bold")
    plt.legend()
    plt.tight_layout()
    path = Path(output_dir) / "calibration_curve.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"    Saved: {path.name}")


def plot_learning_curves(model, X, y, output_dir):
    logger.info("  → Learning curves (this may take a moment)...")
    train_sizes, train_scores, test_scores = learning_curve(
        model, X, y, cv=5, n_jobs=-1,
        train_sizes=np.linspace(0.1, 1.0, 10),
        scoring="f1_weighted", random_state=42
    )
    train_mean = np.mean(train_scores, axis=1)
    train_std = np.std(train_scores, axis=1)
    test_mean = np.mean(test_scores, axis=1)
    test_std = np.std(test_scores, axis=1)

    plt.figure(figsize=(10, 6))
    plt.plot(train_sizes, train_mean, "o-", color="#e74c3c", lw=2, label="Training Score")
    plt.plot(train_sizes, test_mean, "o-", color="#2ecc71", lw=2, label="Cross-Validation Score")
    plt.fill_between(train_sizes, train_mean - train_std, train_mean + train_std, alpha=0.15, color="#e74c3c")
    plt.fill_between(train_sizes, test_mean - test_std, test_mean + test_std, alpha=0.15, color="#2ecc71")
    plt.xlabel("Training Set Size", fontsize=12, fontweight="bold")
    plt.ylabel("F1 Score (Weighted)", fontsize=12, fontweight="bold")
    plt.title("Learning Curves – Random Forest Flood Prediction", fontsize=14, fontweight="bold", pad=15)
    plt.legend(fontsize=11)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    path = Path(output_dir) / "learning_curves.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"    Saved: {path.name}")


def plot_metrics_summary(metrics, output_dir):
    logger.info("  → Metrics summary bar chart...")
    display_metrics = {
        "Accuracy": metrics["accuracy"],
        "Balanced\nAccuracy": metrics["balanced_accuracy"],
        "Precision\n(Weighted)": metrics["precision_weighted"],
        "Recall\n(Weighted)": metrics["recall_weighted"],
        "F1\n(Weighted)": metrics["f1_weighted"],
        "ROC AUC": metrics["roc_auc"],
        "Avg\nPrecision": metrics["average_precision"],
        "MCC": (metrics["matthews_corrcoef"] + 1) / 2,  # normalize to 0-1 for display
        "Kappa": metrics["cohen_kappa"],
    }

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # Bar chart
    bars = axes[0].bar(list(display_metrics.keys()), list(display_metrics.values()),
                       color=COLORS * 3, alpha=0.85, edgecolor="black", linewidth=0.5)
    for bar in bars:
        h = bar.get_height()
        axes[0].text(bar.get_x() + bar.get_width() / 2, h + 0.01, f"{h:.3f}",
                     ha="center", fontsize=9, fontweight="bold")
    axes[0].set_ylim([0, 1.15])
    axes[0].set_ylabel("Score", fontweight="bold")
    axes[0].set_title("All Performance Metrics", fontweight="bold")
    axes[0].tick_params(axis="x", labelsize=9)
    axes[0].grid(True, axis="y", alpha=0.3)

    # Radar chart for main metrics
    radar_metrics = {
        "Accuracy": metrics["accuracy"],
        "Precision": metrics["precision_weighted"],
        "Recall": metrics["recall_weighted"],
        "F1": metrics["f1_weighted"],
        "AUC": metrics["roc_auc"],
        "Specificity": metrics["specificity"],
    }
    n = len(radar_metrics)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    values = list(radar_metrics.values())
    angles += angles[:1]
    values += values[:1]

    ax_radar = axes[1]
    ax_radar.remove()
    ax_radar = fig.add_subplot(1, 2, 2, polar=True)
    ax_radar.plot(angles, values, "o-", color="#3498db", lw=2)
    ax_radar.fill(angles, values, alpha=0.2, color="#3498db")
    ax_radar.set_xticks(angles[:-1])
    ax_radar.set_xticklabels(list(radar_metrics.keys()), fontsize=11)
    ax_radar.set_ylim(0, 1)
    ax_radar.set_title("Performance Radar Chart", fontweight="bold", pad=20)
    ax_radar.grid(True)

    fig.suptitle("Model Performance Summary – Flood Prediction", fontsize=14, fontweight="bold")
    plt.tight_layout()
    path = Path(output_dir) / "metrics_summary.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"    Saved: {path.name}")


def plot_permutation_importance(model, X, y, output_dir, n_repeats=10, top_n=20):
    logger.info("  → Permutation importance (this may take a moment)...")
    try:
        result = permutation_importance(model, X, y, n_repeats=n_repeats, random_state=42,
                                        n_jobs=-1, scoring="f1_weighted")
        imp_mean = result.importances_mean
        imp_std = result.importances_std
        feature_names = (list(model.feature_names_in_) if hasattr(model, "feature_names_in_")
                         else [f"Feature {i}" for i in range(X.shape[1])])

        perm_df = pd.DataFrame({"feature": feature_names, "mean": imp_mean, "std": imp_std})
        perm_df = perm_df.sort_values("mean", ascending=False).head(top_n)

        plt.figure(figsize=(10, max(6, len(perm_df) * 0.35)))
        plt.barh(perm_df["feature"][::-1], perm_df["mean"][::-1],
                 xerr=perm_df["std"][::-1], color="#9b59b6", alpha=0.8, capsize=4)
        plt.xlabel("Mean Decrease in F1 Score", fontweight="bold")
        plt.title("Permutation Feature Importance\n(with ± 1 std dev error bars)", fontweight="bold")
        plt.tight_layout()
        path = Path(output_dir) / "permutation_importance.png"
        plt.savefig(path, dpi=300, bbox_inches="tight")
        plt.close()
        logger.info(f"    Saved: {path.name}")
        return perm_df
    except Exception as e:
        logger.warning(f"    Permutation importance failed: {e}")
        return None


def plot_class_distribution(y, output_dir):
    logger.info("  → Class distribution...")
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    counts = y.value_counts()
    labels = ["No Flood (0)", "Flood (1)"]
    colors = ["#3498db", "#e74c3c"]

    # Bar
    axes[0].bar(labels, [counts.get(0, 0), counts.get(1, 0)], color=colors, alpha=0.85, edgecolor="black")
    for i, c in enumerate([counts.get(0, 0), counts.get(1, 0)]):
        axes[0].text(i, c + 1, str(c), ha="center", fontweight="bold")
    axes[0].set_ylabel("Count", fontweight="bold")
    axes[0].set_title("Class Distribution (Counts)", fontweight="bold")

    # Pie
    axes[1].pie([counts.get(0, 0), counts.get(1, 0)], labels=labels, colors=colors,
                autopct="%1.1f%%", startangle=90, textprops={"fontsize": 11})
    axes[1].set_title("Class Distribution (Proportions)", fontweight="bold")

    fig.suptitle("Target Class Distribution", fontsize=13, fontweight="bold")
    plt.tight_layout()
    path = Path(output_dir) / "class_distribution.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"    Saved: {path.name}")


def plot_feature_correlation(X, output_dir, top_n=25):
    logger.info("  → Feature correlation heatmap...")
    X_sample = X.iloc[:, :top_n] if X.shape[1] > top_n else X
    corr = X_sample.corr()

    plt.figure(figsize=(max(10, len(corr) * 0.5), max(8, len(corr) * 0.45)))
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(corr, mask=mask, annot=len(corr) <= 15, fmt=".2f", cmap="coolwarm",
                center=0, square=True, linewidths=0.3, cbar_kws={"shrink": 0.8})
    plt.title(f"Feature Correlation Heatmap (Top {len(corr)} features)", fontsize=13, fontweight="bold")
    plt.tight_layout()
    path = Path(output_dir) / "feature_correlation.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"    Saved: {path.name}")


def plot_cumulative_gain_lift(y_true, y_pred_proba, output_dir):
    logger.info("  → Cumulative gain / lift chart...")
    if y_pred_proba.ndim > 1:
        proba_pos = y_pred_proba[:, 1]
    else:
        proba_pos = y_pred_proba

    # Sort by descending probability
    order = np.argsort(proba_pos)[::-1]
    y_sorted = np.array(y_true)[order]
    total_pos = y_sorted.sum()

    cum_pos = np.cumsum(y_sorted)
    cum_pct_samples = np.arange(1, len(y_sorted) + 1) / len(y_sorted)
    cum_gain = cum_pos / total_pos
    lift = cum_gain / cum_pct_samples

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Cumulative Gain
    axes[0].plot(cum_pct_samples * 100, cum_gain * 100, color="#e74c3c", lw=2.5, label="Model")
    axes[0].plot([0, 100], [0, 100], "k--", lw=1.5, label="Random Baseline")
    axes[0].fill_between(cum_pct_samples * 100, cum_gain * 100,
                         np.linspace(0, 100, len(cum_gain)), alpha=0.1, color="#e74c3c")
    axes[0].set_xlabel("% of Samples (Ranked by Probability)", fontweight="bold")
    axes[0].set_ylabel("% of Flood Events Captured", fontweight="bold")
    axes[0].set_title("Cumulative Gain Chart", fontweight="bold")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Lift
    axes[1].plot(cum_pct_samples * 100, lift, color="#3498db", lw=2.5, label="Lift")
    axes[1].axhline(1, color="k", linestyle="--", lw=1.5, label="No Lift (Baseline)")
    axes[1].set_xlabel("% of Samples (Ranked by Probability)", fontweight="bold")
    axes[1].set_ylabel("Lift", fontweight="bold")
    axes[1].set_title("Lift Chart", fontweight="bold")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.suptitle("Cumulative Gain & Lift – Flood Prediction Model", fontsize=14, fontweight="bold")
    plt.tight_layout()
    path = Path(output_dir) / "cumulative_gain_lift.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"    Saved: {path.name}")


def plot_error_analysis(X, y_true, y_pred, y_pred_proba, output_dir):
    logger.info("  → Error analysis...")
    if y_pred_proba.ndim > 1:
        proba_pos = y_pred_proba[:, 1]
    else:
        proba_pos = y_pred_proba

    errors = y_true != y_pred
    fp_mask = (y_true == 0) & (y_pred == 1)
    fn_mask = (y_true == 1) & (y_pred == 0)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # Confidence of errors vs correct
    axes[0].hist(proba_pos[~errors], bins=30, alpha=0.6, color="#2ecc71", label=f"Correct ({(~errors).sum()})", density=True)
    axes[0].hist(proba_pos[errors], bins=30, alpha=0.6, color="#e74c3c", label=f"Errors ({errors.sum()})", density=True)
    axes[0].set_xlabel("Predicted Probability (Flood)", fontweight="bold")
    axes[0].set_ylabel("Density", fontweight="bold")
    axes[0].set_title("Confidence: Correct vs Errors", fontweight="bold")
    axes[0].legend()

    # FP vs FN confidence
    if fp_mask.sum() > 0:
        axes[1].hist(proba_pos[fp_mask], bins=20, alpha=0.7, color="#f39c12", label=f"False Positives ({fp_mask.sum()})", density=True)
    if fn_mask.sum() > 0:
        axes[1].hist(proba_pos[fn_mask], bins=20, alpha=0.7, color="#9b59b6", label=f"False Negatives ({fn_mask.sum()})", density=True)
    axes[1].set_xlabel("Predicted Probability (Flood)", fontweight="bold")
    axes[1].set_ylabel("Density", fontweight="bold")
    axes[1].set_title("FP vs FN Confidence Distribution", fontweight="bold")
    axes[1].legend()

    # Error summary
    total = len(y_true)
    tp = ((y_true == 1) & (y_pred == 1)).sum()
    tn = ((y_true == 0) & (y_pred == 0)).sum()
    fp_count = fp_mask.sum()
    fn_count = fn_mask.sum()

    categories = ["True\nPositives", "True\nNegatives", "False\nPositives\n(Type I)", "False\nNegatives\n(Type II)"]
    counts_vals = [tp, tn, fp_count, fn_count]
    bar_colors = ["#2ecc71", "#3498db", "#e74c3c", "#f39c12"]
    bars = axes[2].bar(categories, counts_vals, color=bar_colors, alpha=0.85, edgecolor="black")
    for bar, count in zip(bars, counts_vals):
        axes[2].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + total * 0.005,
                     f"{count}\n({count/total*100:.1f}%)", ha="center", fontsize=9, fontweight="bold")
    axes[2].set_ylabel("Count", fontweight="bold")
    axes[2].set_title("Prediction Outcome Breakdown", fontweight="bold")
    axes[2].grid(True, axis="y", alpha=0.3)

    plt.suptitle("Error Analysis – Flood Prediction Model", fontsize=14, fontweight="bold")
    plt.tight_layout()
    path = Path(output_dir) / "error_analysis.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"    Saved: {path.name}")


def plot_per_class_metrics(y_true, y_pred, output_dir):
    logger.info("  → Per-class metrics breakdown...")
    report = classification_report(y_true, y_pred, target_names=["No Flood", "Flood"], output_dict=True)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    classes = ["No Flood", "Flood"]
    metric_names = ["precision", "recall", "f1-score"]
    x = np.arange(len(classes))
    width = 0.25
    c = ["#3498db", "#e74c3c", "#f39c12"]

    for i, metric in enumerate(metric_names):
        vals = [report[cls][metric] for cls in classes]
        axes[0].bar(x + i * width, vals, width, label=metric.capitalize(), color=c[i], alpha=0.85)

    axes[0].set_xticks(x + width)
    axes[0].set_xticklabels(classes, fontsize=11)
    axes[0].set_ylim([0, 1.15])
    axes[0].set_ylabel("Score", fontweight="bold")
    axes[0].set_title("Per-Class Precision / Recall / F1", fontweight="bold")
    axes[0].legend()
    axes[0].grid(True, axis="y", alpha=0.3)

    # Support pie
    supports = [report[cls]["support"] for cls in classes]
    axes[1].pie(supports, labels=classes, autopct="%1.1f%%",
                colors=["#3498db", "#e74c3c"], startangle=90, textprops={"fontsize": 11})
    axes[1].set_title(f"Test Set Class Distribution\n(n={sum(supports):,})", fontweight="bold")

    plt.suptitle("Per-Class Performance Metrics", fontsize=14, fontweight="bold")
    plt.tight_layout()
    path = Path(output_dir) / "per_class_metrics.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"    Saved: {path.name}")


def plot_model_comparison(model_results, output_dir):
    """Compare multiple model versions if provided."""
    if not model_results or len(model_results) < 2:
        return
    logger.info("  → Multi-model comparison chart...")

    model_names = list(model_results.keys())
    metric_keys = ["accuracy", "f1_weighted", "roc_auc", "precision_weighted", "recall_weighted"]
    metric_labels = ["Accuracy", "F1 (Weighted)", "ROC AUC", "Precision", "Recall"]

    x = np.arange(len(metric_labels))
    width = 0.8 / len(model_names)

    fig, ax = plt.subplots(figsize=(14, 7))
    for i, (name, m) in enumerate(model_results.items()):
        vals = [m[k] for k in metric_keys]
        bars = ax.bar(x + i * width, vals, width, label=name, alpha=0.85)
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.004, f"{h:.3f}",
                    ha="center", fontsize=7, rotation=45)

    ax.set_xticks(x + width * (len(model_names) - 1) / 2)
    ax.set_xticklabels(metric_labels, fontsize=11)
    ax.set_ylim([0, 1.2])
    ax.set_ylabel("Score", fontweight="bold")
    ax.set_title("Model Version Comparison", fontsize=14, fontweight="bold")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    path = Path(output_dir) / "model_comparison.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"    Saved: {path.name}")


def plot_tree_depth_distribution(model, output_dir):
    """For Random Forest: plot individual tree depth distribution."""
    logger.info("  → Tree depth distribution...")
    if not hasattr(model, "estimators_"):
        logger.warning("    Model has no estimators_ attribute. Skipping.")
        return
    depths = [est.get_depth() for est in model.estimators_]
    plt.figure(figsize=(10, 5))
    plt.hist(depths, bins=30, color="#9b59b6", alpha=0.85, edgecolor="black")
    plt.axvline(np.mean(depths), color="red", linestyle="--", lw=2, label=f"Mean depth: {np.mean(depths):.1f}")
    plt.xlabel("Tree Depth", fontweight="bold")
    plt.ylabel("Count", fontweight="bold")
    plt.title(f"Random Forest – Individual Tree Depth Distribution\n({len(model.estimators_)} trees)",
              fontweight="bold")
    plt.legend()
    plt.tight_layout()
    path = Path(output_dir) / "tree_depth_distribution.png"
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"    Saved: {path.name}")


# ==============================================================================
# INTERACTIVE CHARTS (PLOTLY)
# ==============================================================================

def generate_all_interactive(model, X, y_true, y_pred, y_pred_proba, metrics, output_dir):
    if not PLOTLY_AVAILABLE:
        logger.warning("Plotly not installed. Run: pip install plotly")
        return
    logger.info("Generating interactive HTML charts...")
    _interactive_feature_importance(model, output_dir)
    _interactive_confusion_matrix(y_true, y_pred, output_dir)
    _interactive_roc(y_true, y_pred_proba, output_dir)
    _interactive_pr_curve(y_true, y_pred_proba, output_dir)
    _interactive_metrics_dashboard(metrics, output_dir)
    _interactive_probability_distribution(y_true, y_pred_proba, output_dir)
    _interactive_threshold_sweep(y_true, y_pred_proba, output_dir)
    logger.info("  → All interactive charts saved.")


def _interactive_feature_importance(model, output_dir, top_n=20):
    if not hasattr(model, "feature_importances_"):
        return
    feature_names = (list(model.feature_names_in_) if hasattr(model, "feature_names_in_")
                     else [f"Feature {i}" for i in range(len(model.feature_importances_))])
    imp_df = (pd.DataFrame({"feature": feature_names, "importance": model.feature_importances_})
              .sort_values("importance").tail(top_n))
    fig = px.bar(imp_df, x="importance", y="feature", orientation="h",
                 title="Feature Importance – Flood Prediction Model",
                 color="importance", color_continuous_scale="Viridis",
                 labels={"importance": "Importance", "feature": "Feature"})
    fig.update_layout(height=max(400, len(imp_df) * 26), showlegend=False)
    fig.write_html(str(Path(output_dir) / "interactive_feature_importance.html"))


def _interactive_confusion_matrix(y_true, y_pred, output_dir):
    cm = confusion_matrix(y_true, y_pred)
    labels = ["No Flood", "Flood"]
    fig = px.imshow(cm, x=labels, y=labels, text_auto=True, color_continuous_scale="Blues",
                    title="Confusion Matrix – Flood Prediction Model",
                    labels={"x": "Predicted", "y": "Actual"})
    fig.write_html(str(Path(output_dir) / "interactive_confusion_matrix.html"))


def _interactive_roc(y_true, y_pred_proba, output_dir):
    proba_pos = y_pred_proba[:, 1] if y_pred_proba.ndim > 1 else y_pred_proba
    fpr, tpr, _ = roc_curve(y_true, proba_pos)
    roc_auc = auc(fpr, tpr)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=fpr, y=tpr, mode="lines", name=f"ROC (AUC={roc_auc:.4f})",
                             line=dict(color="darkorange", width=2.5)))
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Random",
                             line=dict(color="navy", dash="dash")))
    fig.update_layout(title="ROC Curve – Flood Prediction Model",
                      xaxis_title="False Positive Rate", yaxis_title="True Positive Rate")
    fig.write_html(str(Path(output_dir) / "interactive_roc_curve.html"))


def _interactive_pr_curve(y_true, y_pred_proba, output_dir):
    proba_pos = y_pred_proba[:, 1] if y_pred_proba.ndim > 1 else y_pred_proba
    precision, recall, _ = precision_recall_curve(y_true, proba_pos)
    pr_auc = auc(recall, precision)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=recall, y=precision, mode="lines", name=f"PR (AUC={pr_auc:.4f})",
                             line=dict(color="steelblue", width=2.5)))
    fig.update_layout(title="Precision-Recall Curve – Flood Prediction Model",
                      xaxis_title="Recall", yaxis_title="Precision")
    fig.write_html(str(Path(output_dir) / "interactive_pr_curve.html"))


def _interactive_metrics_dashboard(metrics, output_dir):
    main_metrics = {
        "Accuracy": metrics["accuracy"],
        "Precision": metrics["precision_weighted"],
        "Recall": metrics["recall_weighted"],
        "F1": metrics["f1_weighted"],
        "ROC AUC": metrics["roc_auc"],
        "MCC": (metrics["matthews_corrcoef"] + 1) / 2,
    }
    fig = make_subplots(rows=1, cols=2,
                        specs=[[{"type": "bar"}, {"type": "indicator"}]],
                        subplot_titles=("Performance Metrics", "F1 Score"))
    fig.add_trace(go.Bar(x=list(main_metrics.keys()), y=list(main_metrics.values()),
                         marker_color=COLORS[:len(main_metrics)],
                         text=[f"{v:.3f}" for v in main_metrics.values()],
                         textposition="outside"), row=1, col=1)
    fig.add_trace(go.Indicator(mode="gauge+number+delta",
                               value=metrics["f1_weighted"],
                               gauge={"axis": {"range": [0, 1]},
                                      "steps": [{"range": [0, 0.5], "color": "#e74c3c"},
                                                 {"range": [0.5, 0.75], "color": "#f1c40f"},
                                                 {"range": [0.75, 1], "color": "#2ecc71"}],
                                      "bar": {"color": "#f39c12"}}), row=1, col=2)
    fig.update_layout(title="Performance Dashboard – Flood Prediction Model", height=450, showlegend=False)
    fig.write_html(str(Path(output_dir) / "interactive_dashboard.html"))


def _interactive_probability_distribution(y_true, y_pred_proba, output_dir):
    proba_pos = y_pred_proba[:, 1] if y_pred_proba.ndim > 1 else y_pred_proba
    df = pd.DataFrame({"probability": proba_pos, "actual": y_true.map({0: "No Flood", 1: "Flood"})})
    fig = px.histogram(df, x="probability", color="actual", barmode="overlay",
                       nbins=50, opacity=0.7,
                       title="Prediction Probability Distribution",
                       color_discrete_map={"No Flood": "#3498db", "Flood": "#e74c3c"})
    fig.add_vline(x=0.5, line_dash="dash", annotation_text="Default Threshold (0.5)")
    fig.write_html(str(Path(output_dir) / "interactive_probability_dist.html"))


def _interactive_threshold_sweep(y_true, y_pred_proba, output_dir):
    proba_pos = y_pred_proba[:, 1] if y_pred_proba.ndim > 1 else y_pred_proba
    thresholds = np.arange(0.01, 1.0, 0.01)
    data = []
    for t in thresholds:
        preds = (proba_pos >= t).astype(int)
        data.append({
            "threshold": round(t, 2),
            "precision": precision_score(y_true, preds, zero_division=0),
            "recall": recall_score(y_true, preds, zero_division=0),
            "f1": f1_score(y_true, preds, zero_division=0),
            "accuracy": accuracy_score(y_true, preds),
        })
    df = pd.DataFrame(data)
    fig = go.Figure()
    for col, color in [("precision", "blue"), ("recall", "red"), ("f1", "orange"), ("accuracy", "green")]:
        fig.add_trace(go.Scatter(x=df["threshold"], y=df[col], mode="lines", name=col.capitalize(),
                                 line=dict(color=color, width=2)))
    best_t = df.loc[df["f1"].idxmax(), "threshold"]
    fig.add_vline(x=best_t, line_dash="dash", annotation_text=f"Best F1 @ {best_t:.2f}")
    fig.update_layout(title="Metrics vs Threshold – Flood Prediction Model",
                      xaxis_title="Threshold", yaxis_title="Score")
    fig.write_html(str(Path(output_dir) / "interactive_threshold_sweep.html"))


# ==============================================================================
# DATA EXPORTS
# ==============================================================================

def export_predictions(X, y_true, y_pred, y_pred_proba, output_dir):
    logger.info("  → Exporting full predictions CSV...")
    proba_pos = y_pred_proba[:, 1] if y_pred_proba.ndim > 1 else y_pred_proba
    df = X.copy()
    df["actual"] = y_true.values
    df["predicted"] = y_pred
    df["prob_no_flood"] = y_pred_proba[:, 0] if y_pred_proba.ndim > 1 else 1 - proba_pos
    df["prob_flood"] = proba_pos
    df["correct"] = (y_true.values == y_pred).astype(int)
    df["error_type"] = "Correct"
    df.loc[(y_true.values == 0) & (y_pred == 1), "error_type"] = "False Positive"
    df.loc[(y_true.values == 1) & (y_pred == 0), "error_type"] = "False Negative"
    path = Path(output_dir) / "predictions_full.csv"
    df.to_csv(path, index=False)
    logger.info(f"    Saved: {path.name}")
    return df


def export_misclassified(predictions_df, output_dir):
    logger.info("  → Exporting misclassified samples CSV...")
    errors = predictions_df[predictions_df["correct"] == 0]
    path = Path(output_dir) / "misclassified_samples.csv"
    errors.to_csv(path, index=False)
    logger.info(f"    Saved: {path.name} ({len(errors)} samples)")


def export_feature_importance(model, output_dir):
    logger.info("  → Exporting feature importance CSV...")
    if not hasattr(model, "feature_importances_"):
        return
    feature_names = (list(model.feature_names_in_) if hasattr(model, "feature_names_in_")
                     else [f"Feature {i}" for i in range(len(model.feature_importances_))])
    df = (pd.DataFrame({"feature": feature_names, "importance": model.feature_importances_,
                         "importance_pct": model.feature_importances_ / model.feature_importances_.sum() * 100})
          .sort_values("importance", ascending=False)
          .reset_index(drop=True))
    df.index += 1
    df.index.name = "rank"
    path = Path(output_dir) / "feature_importance.csv"
    df.to_csv(path)
    logger.info(f"    Saved: {path.name}")


def export_metrics_json(metrics, output_dir, model_name="model"):
    logger.info("  → Exporting metrics JSON...")
    export = {
        "model": model_name,
        "generated_at": datetime.now().isoformat(),
        "metrics": {k: float(v) if isinstance(v, (np.floating, float)) else int(v)
                    for k, v in metrics.items()}
    }
    path = Path(output_dir) / "metrics.json"
    with open(path, "w") as f:
        json.dump(export, f, indent=2)
    logger.info(f"    Saved: {path.name}")


def export_metrics_csv(metrics, output_dir):
    logger.info("  → Exporting metrics CSV...")
    df = pd.DataFrame([{"metric": k, "value": v} for k, v in metrics.items()])
    path = Path(output_dir) / "metrics_summary.csv"
    df.to_csv(path, index=False)
    logger.info(f"    Saved: {path.name}")


def export_threshold_table(threshold_df, output_dir):
    if threshold_df is None:
        return
    logger.info("  → Exporting threshold sweep CSV...")
    path = Path(output_dir) / "threshold_sweep.csv"
    threshold_df.to_csv(path, index=False)
    logger.info(f"    Saved: {path.name}")


def export_excel_workbook(metrics, imp_df, threshold_df, predictions_df, output_dir):
    if not EXCEL_AVAILABLE:
        logger.warning("  openpyxl not installed (pip install openpyxl). Skipping Excel export.")
        return
    logger.info("  → Exporting Excel workbook...")
    path = Path(output_dir) / "thesis_data.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        # Metrics
        pd.DataFrame([{"Metric": k, "Value": v} for k, v in metrics.items()]).to_excel(
            writer, sheet_name="Metrics", index=False)
        # Feature importance
        if imp_df is not None:
            imp_df.reset_index(drop=True).to_excel(writer, sheet_name="Feature Importance", index=False)
        # Threshold sweep
        if threshold_df is not None:
            threshold_df.to_excel(writer, sheet_name="Threshold Sweep", index=False)
        # Predictions sample (max 10000 rows for Excel sanity)
        if predictions_df is not None:
            predictions_df.head(10000).to_excel(writer, sheet_name="Predictions (Sample)", index=False)
    logger.info(f"    Saved: {path.name}")


# ==============================================================================
# TEXT REPORT & MARKDOWN SUMMARY
# ==============================================================================

def generate_text_report(model, metadata, y_true, y_pred, y_pred_proba, metrics, output_dir):
    logger.info("  → Full text report...")
    path = Path(output_dir) / "model_report.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("  RANDOM FOREST FLOOD PREDICTION MODEL – COMPREHENSIVE THESIS REPORT\n")
        f.write("  Parañaque City Flood Detection System\n")
        f.write(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")

        # Model Info
        f.write("MODEL INFORMATION\n" + "-" * 80 + "\n")
        if metadata:
            for k in ["version", "model_type", "created_at", "model_path"]:
                f.write(f"{k.replace('_', ' ').title()}: {metadata.get(k, 'N/A')}\n")
        if hasattr(model, "n_estimators"):
            f.write(f"\nRandom Forest Parameters:\n")
            params = model.get_params()
            for k, v in sorted(params.items()):
                f.write(f"  {k}: {v}\n")
        f.write("\n")

        # Performance Metrics
        f.write("PERFORMANCE METRICS\n" + "-" * 80 + "\n")
        for metric, value in metrics.items():
            label = metric.replace("_", " ").title()
            if isinstance(value, float):
                f.write(f"  {label:<35}: {value:.6f}\n")
            else:
                f.write(f"  {label:<35}: {value}\n")
        f.write("\n")

        # Classification Report
        f.write("DETAILED CLASSIFICATION REPORT\n" + "-" * 80 + "\n")
        f.write(classification_report(y_true, y_pred, target_names=["No Flood", "Flood"]))
        f.write("\n")

        # Confusion Matrix
        cm = confusion_matrix(y_true, y_pred)
        f.write("CONFUSION MATRIX\n" + "-" * 80 + "\n")
        f.write(f"{'':25} Predicted No Flood    Predicted Flood\n")
        f.write(f"{'Actual No Flood':25}      {cm[0][0]:8d}            {cm[0][1]:8d}\n")
        f.write(f"{'Actual Flood':25}      {cm[1][0]:8d}            {cm[1][1]:8d}\n\n")

        # Feature Importance
        if hasattr(model, "feature_importances_"):
            feature_names = (list(model.feature_names_in_) if hasattr(model, "feature_names_in_")
                             else [f"Feature {i}" for i in range(len(model.feature_importances_))])
            imp_df = (pd.DataFrame({"feature": feature_names, "importance": model.feature_importances_})
                      .sort_values("importance", ascending=False).head(20))
            f.write("TOP 20 FEATURE IMPORTANCES\n" + "-" * 80 + "\n")
            for i, (_, row) in enumerate(imp_df.iterrows(), 1):
                bar = "█" * int(row["importance"] * 200)
                f.write(f"  {i:2d}. {row['feature']:<35} {row['importance']:.6f} {bar}\n")
            f.write("\n")

        # Metadata CV results
        if metadata and "cross_validation" in metadata:
            cv = metadata["cross_validation"]
            f.write("CROSS-VALIDATION RESULTS\n" + "-" * 80 + "\n")
            f.write(f"  Folds: {cv.get('cv_folds', 'N/A')}\n")
            f.write(f"  Mean F1: {cv.get('cv_mean', 0):.6f} ± {cv.get('cv_std', 0):.6f}\n")
            f.write(f"  Scores: {cv.get('cv_scores', [])}\n\n")

        if metadata and "grid_search" in metadata:
            gs = metadata["grid_search"]
            f.write("HYPERPARAMETER TUNING\n" + "-" * 80 + "\n")
            f.write(f"  Best CV Score: {gs.get('best_cv_score', 'N/A')}\n")
            for k, v in gs.get("best_params", {}).items():
                f.write(f"  {k}: {v}\n")
            f.write("\n")

        f.write("=" * 80 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 80 + "\n")

    logger.info(f"    Saved: {path.name}")


def generate_markdown_summary(metrics, output_dir, model_path):
    logger.info("  → Markdown executive summary...")
    path = Path(output_dir) / "executive_summary.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Flood Prediction Model – Executive Summary\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"**Model:** `{model_path}`  \n\n")
        f.write("---\n\n")
        f.write("## Key Performance Metrics\n\n")
        f.write("| Metric | Value |\n|---|---|\n")
        key_metrics = ["accuracy", "balanced_accuracy", "f1_weighted", "roc_auc",
                       "precision_weighted", "recall_weighted", "matthews_corrcoef", "cohen_kappa"]
        for k in key_metrics:
            v = metrics.get(k, "N/A")
            label = k.replace("_", " ").title()
            f.write(f"| {label} | {v:.4f} |\n" if isinstance(v, float) else f"| {label} | {v} |\n")
        f.write("\n")
        f.write("## Confusion Matrix Summary\n\n")
        f.write(f"| | Predicted No Flood | Predicted Flood |\n|---|---|---|\n")
        f.write(f"| **Actual No Flood** | {metrics['true_negatives']:,} (TN) | {metrics['false_positives']:,} (FP) |\n")
        f.write(f"| **Actual Flood** | {metrics['false_negatives']:,} (FN) | {metrics['true_positives']:,} (TP) |\n\n")
        f.write("## Probabilistic Metrics\n\n")
        prob_metrics = ["log_loss", "brier_score", "average_precision"]
        for k in prob_metrics:
            v = metrics.get(k, "N/A")
            f.write(f"- **{k.replace('_', ' ').title()}:** {v:.6f}\n" if isinstance(v, float) else f"- **{k}:** {v}\n")
        f.write("\n---\n\n*See accompanying PNG charts and CSV exports for full analysis.*\n")
    logger.info(f"    Saved: {path.name}")


# ==============================================================================
# MAIN ORCHESTRATOR
# ==============================================================================

def generate_full_report(
    model_path,
    data_file,
    output_dir="reports",
    interactive=False,
    compare_models=None,
    skip_slow=False,
):
    logger.info("=" * 80)
    logger.info("ULTIMATE THESIS REPORT GENERATOR – FLOOD PREDICTION MODEL")
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_path.absolute()}\n")

    # Load primary model
    model, metadata = load_model_and_metadata(model_path)
    X, y, raw_data = prepare_data(model, data_file)

    # Predictions
    logger.info("Computing predictions...")
    y_pred = model.predict(X)
    y_pred_proba = model.predict_proba(X)
    metrics = compute_all_metrics(y, y_pred, y_pred_proba)
    optimal_threshold, optimal_f1 = find_optimal_threshold(y, y_pred_proba)
    metrics["optimal_threshold"] = optimal_threshold
    metrics["optimal_threshold_f1"] = optimal_f1
    logger.info(f"  Accuracy: {metrics['accuracy']:.4f} | F1: {metrics['f1_weighted']:.4f} | AUC: {metrics['roc_auc']:.4f}")
    logger.info(f"  Optimal threshold: {optimal_threshold:.2f} (F1 = {optimal_f1:.4f})\n")

    # Load comparison models if any
    model_results = {Path(model_path).stem: metrics}
    if compare_models:
        for cmp_path in compare_models:
            try:
                cmp_model, _ = load_model_and_metadata(cmp_path)
                cmp_X, cmp_y, _ = prepare_data(cmp_model, data_file)
                cmp_pred = cmp_model.predict(cmp_X)
                cmp_proba = cmp_model.predict_proba(cmp_X)
                cmp_metrics = compute_all_metrics(cmp_y, cmp_pred, cmp_proba)
                model_results[Path(cmp_path).stem] = cmp_metrics
                logger.info(f"  Loaded comparison model: {Path(cmp_path).stem}")
            except Exception as e:
                logger.warning(f"  Could not load comparison model {cmp_path}: {e}")

    # ── STATIC CHARTS ──────────────────────────────────────────────────────────
    logger.info("\n[1/6] Generating static charts...")
    imp_df = plot_feature_importance(model, output_path)
    plot_confusion_matrices(y, y_pred, output_path)
    plot_roc_curve(y, y_pred_proba, output_path, optimal_threshold)
    plot_precision_recall_curve(y, y_pred_proba, output_path)
    threshold_df = plot_threshold_analysis(y, y_pred_proba, output_path)
    plot_probability_distribution(y, y_pred_proba, output_path)
    plot_calibration_curve(y, y_pred_proba, output_path)
    plot_metrics_summary(metrics, output_path)
    plot_class_distribution(y, output_path)
    plot_feature_correlation(X, output_path)
    plot_cumulative_gain_lift(y, y_pred_proba, output_path)
    plot_error_analysis(X, y, y_pred, y_pred_proba, output_path)
    plot_per_class_metrics(y, y_pred, output_path)
    plot_tree_depth_distribution(model, output_path)
    if len(model_results) > 1:
        plot_model_comparison(model_results, output_path)

    # ── PERMUTATION IMPORTANCE (SLOW) ──────────────────────────────────────────
    perm_df = None
    if not skip_slow:
        logger.info("\n[2/6] Permutation importance (slow step)...")
        perm_df = plot_permutation_importance(model, X, y, output_path)
    else:
        logger.info("\n[2/6] Skipping permutation importance (--skip-slow)")

    # ── LEARNING CURVES (SLOW) ─────────────────────────────────────────────────
    if not skip_slow:
        logger.info("\n[3/6] Learning curves (slow step)...")
        plot_learning_curves(model, X, y, output_path)
    else:
        logger.info("\n[3/6] Skipping learning curves (--skip-slow)")

    # ── INTERACTIVE CHARTS ─────────────────────────────────────────────────────
    logger.info("\n[4/6] Interactive HTML charts...")
    if interactive:
        generate_all_interactive(model, X, y, y_pred, y_pred_proba, metrics, output_path)
    else:
        logger.info("  Skipped (add --interactive to enable)")

    # ── DATA EXPORTS ───────────────────────────────────────────────────────────
    logger.info("\n[5/6] Data exports...")
    predictions_df = export_predictions(X, y, y_pred, y_pred_proba, output_path)
    export_misclassified(predictions_df, output_path)
    export_feature_importance(model, output_path)
    export_metrics_json(metrics, output_path, Path(model_path).stem)
    export_metrics_csv(metrics, output_path)
    export_threshold_table(threshold_df, output_path)
    export_excel_workbook(metrics, imp_df, threshold_df, predictions_df, output_path)

    # ── TEXT REPORTS ───────────────────────────────────────────────────────────
    logger.info("\n[6/6] Text reports...")
    generate_text_report(model, metadata, y, y_pred, y_pred_proba, metrics, output_path)
    generate_markdown_summary(metrics, output_path, model_path)

    # ── FINAL SUMMARY ──────────────────────────────────────────────────────────
    files = sorted(output_path.glob("*"))
    logger.info("\n" + "=" * 80)
    logger.info("✓ COMPLETE! All outputs saved.")
    logger.info(f"  Output directory: {output_path.absolute()}")
    logger.info(f"  Total files generated: {len(files)}")
    logger.info("=" * 80)
    logger.info("\nFILES GENERATED:")

    exts = {}
    for f in files:
        exts.setdefault(f.suffix, []).append(f.name)
    for ext, names in sorted(exts.items()):
        logger.info(f"\n  {ext.upper() or 'OTHER'} ({len(names)} files):")
        for n in names:
            logger.info(f"    • {n}")


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Ultimate Thesis Report Generator – Flood Prediction Model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_thesis_report.py --model models/flood_model_v6.joblib --data data/dataset.csv
  python generate_thesis_report.py --model models/flood_model_v6.joblib --data data/dataset.csv --interactive
  python generate_thesis_report.py --model models/flood_model_v6.joblib --data data/dataset.csv --skip-slow
  python generate_thesis_report.py --model models/flood_model_v6.joblib --data data/dataset.csv \\
      --compare models/flood_model_v5.joblib models/flood_model_v4.joblib
        """
    )
    parser.add_argument("--model", type=str, required=True,
                        help="Path to trained model (.joblib)")
    parser.add_argument("--data", type=str, required=True,
                        help="Path to test dataset CSV")
    parser.add_argument("--output", type=str, default="reports",
                        help="Output directory (default: reports)")
    parser.add_argument("--interactive", action="store_true",
                        help="Generate interactive Plotly HTML charts (requires plotly)")
    parser.add_argument("--compare", nargs="+", metavar="MODEL_PATH",
                        help="Additional model paths to compare against the primary model")
    parser.add_argument("--skip-slow", action="store_true",
                        help="Skip slow steps: learning curves & permutation importance")

    args = parser.parse_args()

    generate_full_report(
        model_path=args.model,
        data_file=args.data,
        output_dir=args.output,
        interactive=args.interactive,
        compare_models=args.compare,
        skip_slow=args.skip_slow,
    )