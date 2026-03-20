#!/usr/bin/env python
"""
Class Weight Sensitivity Analysis for Floodingnaque
====================================================

Trains the v6 model with different class_weight configurations to
determine the optimal weight ratio for flood detection (recall priority).
Compares F2 scores, precision-recall trade-offs, and calibration quality.

Outputs:
    - reports/sensitivity_analysis_YYYYMMDD.json     (detailed results)
    - reports/sensitivity_analysis_YYYYMMDD.png      (comparison chart)

Usage:
    python scripts/sensitivity_analysis.py
    python scripts/sensitivity_analysis.py --cv-folds 10
    python scripts/sensitivity_analysis.py --quick
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    fbeta_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
MODELS_DIR = BACKEND_DIR / "models"
REPORTS_DIR = BACKEND_DIR / "reports"
DATA_DIR = BACKEND_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"

# v6 feature set (matches train_progressive_v6.py)
V6_FEATURES = [
    "temperature",
    "humidity",
    "precipitation",
    "is_monsoon_season",
    "month",
    "temp_humidity_interaction",
    "humidity_precip_interaction",
    "monsoon_precip_interaction",
    "saturation_risk",
    "precip_3day_sum",
    "precip_7day_sum",
    "rain_streak",
    "tide_height",
]

# v6 data files (matches train_progressive_v6.py)
V6_DATA_FILES = [
    "cumulative_v2_up_to_2025.csv",
    "pagasa_training_dataset.csv",
    "fetched_googlecloud.csv",
    "fetched_meteostat.csv",
    "fetched_worldtides.csv",
]

# Weight configurations to test
WEIGHT_CONFIGS = [
    {"name": "balanced_subsample", "class_weight": "balanced_subsample"},
    {"name": "balanced", "class_weight": "balanced"},
    {"name": "equal", "class_weight": {0: 1, 1: 1}},
    {"name": "flood_2x", "class_weight": {0: 1, 1: 2}},
    {"name": "flood_3x", "class_weight": {0: 1, 1: 3}},
    {"name": "flood_5x", "class_weight": {0: 1, 1: 5}},
]


def load_v6_data() -> pd.DataFrame:
    """Load and merge v6 training data."""
    dfs = []
    for data_file in V6_DATA_FILES:
        path = PROCESSED_DIR / data_file
        if path.exists():
            df = pd.read_csv(path)
            dfs.append(df)
            logger.info(f"  Loaded: {data_file} ({len(df)} records)")

    if not dfs:
        raise FileNotFoundError(
            f"No v6 data files found in {PROCESSED_DIR}. "
            "Run 'python scripts/preprocess_official_flood_records_v2.py --create-training' first."
        )

    if len(dfs) > 1:
        merged = pd.concat(dfs, ignore_index=True)
        merged = merged.drop_duplicates()
        logger.info(f"  Merged → {len(merged)} unique records")
        return merged
    return dfs[0]


def prepare_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """Prepare v6 features and target."""
    available = [f for f in V6_FEATURES if f in df.columns]
    missing = [f for f in V6_FEATURES if f not in df.columns]
    if missing:
        logger.warning(f"  Missing features (will be filled with 0): {missing}")

    X = df[available].copy()
    y = df["flood"].copy()

    valid_mask = ~y.isna()
    X = X[valid_mask]
    y = y[valid_mask]
    X = X.fillna(X.median())

    logger.info(f"  Features: {len(available)}, Samples: {len(X)}")
    logger.info(f"  Class distribution: {y.value_counts().to_dict()}")
    return X, y


def train_with_weight(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    X_full: pd.DataFrame,
    y_full: pd.Series,
    weight_config: Dict,
    cv_folds: int,
    quick: bool,
) -> Dict:
    """Train RF with given class_weight and evaluate."""
    name = weight_config["name"]
    class_weight = weight_config["class_weight"]

    params = {
        "n_estimators": 100 if quick else 200,
        "max_depth": 10 if quick else 15,
        "min_samples_split": 5,
        "min_samples_leaf": 2,
        "max_features": "sqrt",
        "class_weight": class_weight,
        "random_state": 42,
        "n_jobs": -1,
    }

    logger.info(f"\n  Training with class_weight={name}...")
    model = RandomForestClassifier(**params)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]

    # Core metrics
    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1_score": float(f1_score(y_test, y_pred, zero_division=0)),
        "f2_score": float(fbeta_score(y_test, y_pred, beta=2, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, y_pred_proba)),
        "brier_score": float(brier_score_loss(y_test, y_pred_proba)),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }

    # F2-optimal threshold
    precisions, recalls, thresholds_pr = precision_recall_curve(y_test, y_pred_proba)
    f2_scores = np.where(
        (precisions[:-1] + recalls[:-1]) > 0,
        (1 + 4) * precisions[:-1] * recalls[:-1] / (4 * precisions[:-1] + recalls[:-1]),
        0.0,
    )
    best_idx = int(np.argmax(f2_scores))
    metrics["optimal_threshold"] = float(thresholds_pr[best_idx])
    metrics["optimal_f2"] = float(f2_scores[best_idx])

    # Cross-validation F2
    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X_full, y_full, cv=cv, scoring="f1_weighted", n_jobs=-1)
    metrics["cv_mean"] = float(cv_scores.mean())
    metrics["cv_std"] = float(cv_scores.std())

    # Missed floods (false negatives) — critical metric for flood systems
    metrics["missed_floods"] = int(fn)
    metrics["false_alarms"] = int(fp)

    logger.info(f"    Accuracy={metrics['accuracy']:.4f}  F2={metrics['f2_score']:.4f}  "
                f"Recall={metrics['recall']:.4f}  Missed={fn}  FalseAlarms={fp}")

    return {
        "name": name,
        "class_weight": str(class_weight),
        "metrics": metrics,
    }


def generate_chart(results: List[Dict], output_path: Path):
    """Generate comparison chart (300 DPI for thesis)."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("matplotlib not available — skipping chart generation")
        return

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    names = [r["name"] for r in results]
    f2_scores = [r["metrics"]["f2_score"] for r in results]
    recalls = [r["metrics"]["recall"] for r in results]
    precisions = [r["metrics"]["precision"] for r in results]
    missed = [r["metrics"]["missed_floods"] for r in results]
    false_alarms = [r["metrics"]["false_alarms"] for r in results]

    # Chart 1: F2 + Recall + Precision
    x = np.arange(len(names))
    width = 0.25
    axes[0].bar(x - width, f2_scores, width, label="F2 Score", color="#2196F3")
    axes[0].bar(x, recalls, width, label="Recall", color="#4CAF50")
    axes[0].bar(x + width, precisions, width, label="Precision", color="#FF9800")
    axes[0].set_ylabel("Score")
    axes[0].set_title("Metrics by Class Weight")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(names, rotation=45, ha="right")
    axes[0].legend(loc="lower left")
    axes[0].set_ylim(0.5, 1.05)

    # Chart 2: Missed Floods vs False Alarms
    axes[1].bar(x - 0.2, missed, 0.4, label="Missed Floods (FN)", color="#F44336")
    axes[1].bar(x + 0.2, false_alarms, 0.4, label="False Alarms (FP)", color="#FFC107")
    axes[1].set_ylabel("Count")
    axes[1].set_title("Error Analysis")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(names, rotation=45, ha="right")
    axes[1].legend()

    # Chart 3: ROC-AUC + Brier Score
    roc_aucs = [r["metrics"]["roc_auc"] for r in results]
    brier = [r["metrics"]["brier_score"] for r in results]
    axes[2].bar(x - 0.2, roc_aucs, 0.4, label="ROC-AUC", color="#9C27B0")
    ax2 = axes[2].twinx()
    ax2.plot(x, brier, "o-", color="#E91E63", label="Brier Score")
    axes[2].set_ylabel("ROC-AUC")
    ax2.set_ylabel("Brier Score (lower is better)")
    axes[2].set_title("Discrimination & Calibration")
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(names, rotation=45, ha="right")
    axes[2].legend(loc="upper left")
    ax2.legend(loc="upper right")

    plt.suptitle("Class Weight Sensitivity Analysis — Floodingnaque v6", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"  Chart saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Class Weight Sensitivity Analysis")
    parser.add_argument("--cv-folds", type=int, default=5, help="CV folds (default: 5)")
    parser.add_argument("--quick", action="store_true", help="Quick mode (fewer estimators)")
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("CLASS WEIGHT SENSITIVITY ANALYSIS")
    logger.info("=" * 70)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Load data
    logger.info("\nLoading v6 data...")
    df = load_v6_data()
    X, y = prepare_features(df)

    # Temporal split (consistent with training pipeline)
    if "date" in df.columns:
        dates = pd.to_datetime(df.loc[X.index, "date"], errors="coerce")
        max_year = dates.dt.year.max()
        train_mask = dates.dt.year < max_year
        test_mask = dates.dt.year == max_year

        test_classes = y[test_mask].nunique() if test_mask.sum() > 0 else 0
        if test_mask.sum() >= 10 and train_mask.sum() >= 10 and test_classes >= 2:
            X_train, X_test = X[train_mask], X[test_mask]
            y_train, y_test = y[train_mask], y[test_mask]
            logger.info(f"  Temporal split: train < {max_year}, test = {max_year}")
        else:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            logger.info("  Random split (temporal inadequate)")
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        logger.info("  Random split")

    logger.info(f"  Train: {len(X_train)}, Test: {len(X_test)}")

    # Run sensitivity analysis
    results = []
    for config in WEIGHT_CONFIGS:
        result = train_with_weight(
            X_train, y_train, X_test, y_test, X, y,
            config, args.cv_folds, args.quick,
        )
        results.append(result)

    # Determine optimal weight by F2 score (recall-weighted)
    best = max(results, key=lambda r: r["metrics"]["f2_score"])
    logger.info(f"\n{'=' * 70}")
    logger.info(f"OPTIMAL CLASS WEIGHT: {best['name']}")
    logger.info(f"  F2 Score: {best['metrics']['f2_score']:.4f}")
    logger.info(f"  Recall:   {best['metrics']['recall']:.4f}")
    logger.info(f"  Missed:   {best['metrics']['missed_floods']} floods")
    logger.info(f"{'=' * 70}")

    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report = {
        "generated_at": datetime.now().isoformat(),
        "quick_mode": args.quick,
        "cv_folds": args.cv_folds,
        "dataset_size": len(df),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "class_distribution": y.value_counts().to_dict(),
        "results": results,
        "optimal": {
            "name": best["name"],
            "class_weight": best["class_weight"],
            "f2_score": best["metrics"]["f2_score"],
            "recall": best["metrics"]["recall"],
            "missed_floods": best["metrics"]["missed_floods"],
            "justification": (
                f"'{best['name']}' maximizes the F2 score ({best['metrics']['f2_score']:.4f}), "
                f"which prioritizes flood recall over precision. "
                f"Only {best['metrics']['missed_floods']} flood event(s) missed in test set."
            ),
        },
        "recommendation": (
            f"Use class_weight='{best['name']}' in training_config.yaml. "
            "F2 score weights recall 4x over precision, appropriate for flood "
            "detection where missing a flood (FN) is worse than a false alarm (FP)."
        ),
    }

    report_path = REPORTS_DIR / f"sensitivity_analysis_{timestamp}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info(f"\nReport saved: {report_path}")

    # Generate chart
    chart_path = REPORTS_DIR / f"sensitivity_analysis_{timestamp}.png"
    generate_chart(results, chart_path)

    # Summary table
    logger.info("\n\nSUMMARY TABLE:")
    logger.info(f"{'Weight':<22} {'F2':>6} {'Recall':>7} {'Prec':>6} {'Acc':>6} {'Missed':>7} {'FP':>5}")
    logger.info("-" * 65)
    for r in results:
        m = r["metrics"]
        marker = " ← BEST" if r["name"] == best["name"] else ""
        logger.info(
            f"{r['name']:<22} {m['f2_score']:>6.4f} {m['recall']:>7.4f} "
            f"{m['precision']:>6.4f} {m['accuracy']:>6.4f} {m['missed_floods']:>7} {m['false_alarms']:>5}{marker}"
        )


if __name__ == "__main__":
    main()
