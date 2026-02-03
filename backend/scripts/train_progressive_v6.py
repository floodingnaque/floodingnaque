#!/usr/bin/env python
"""
Progressive Model Training v1-v6 for Floodingnaque
===================================================

Trains six model versions progressively with incremental feature additions
and data improvements. Perfect for thesis demonstration of model evolution.

Version Progression:
    v1: Baseline 2022 - Core features only
    v2: Extended 2023 - Core + basic interactions
    v3: Extended 2024 - Core + all interactions
    v4: Full Official 2025 - Core + interactions + rolling features
    v5: PAGASA Merged - All features + PAGASA data
    v6: Ultimate Combined - All features + external APIs

Output:
    - flood_model_v1.joblib through flood_model_v6.joblib
    - flood_model_v1.json through flood_model_v6.json (metadata)
    - feature_names_v1.json through feature_names_v6.json
    - progressive_v6_report_YYYYMMDD.json (comprehensive comparison)
    - metrics_evolution_v6.png (visualization)
    - feature_importance_comparison.png

Usage:
    python scripts/train_progressive_v6.py
    python scripts/train_progressive_v6.py --quick
    python scripts/train_progressive_v6.py --cv-folds 10
    python scripts/train_progressive_v6.py --version 5  # Train only v5
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    fbeta_score,
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

# Progressive versions configuration with incremental features
PROGRESSIVE_VERSIONS = [
    {
        "version": 1,
        "name": "Baseline_2022",
        "description": "Official Records 2022 Only - Core Features",
        "data_files": ["cumulative_v2_up_to_2022.csv"],
        "fallback_files": ["cumulative_up_to_2022.csv"],
        "features": [
            "temperature",
            "humidity",
            "precipitation",
            "is_monsoon_season",
            "month",
        ],
    },
    {
        "version": 2,
        "name": "Extended_2023",
        "description": "Official Records 2022-2023 - Core + Basic Interactions",
        "data_files": ["cumulative_v2_up_to_2023.csv"],
        "fallback_files": ["cumulative_up_to_2023.csv"],
        "features": [
            "temperature",
            "humidity",
            "precipitation",
            "is_monsoon_season",
            "month",
            "temp_humidity_interaction",
            "humidity_precip_interaction",
            "saturation_risk",
        ],
    },
    {
        "version": 3,
        "name": "Extended_2024",
        "description": "Official Records 2022-2024 - Core + All Interactions",
        "data_files": ["cumulative_v2_up_to_2024.csv"],
        "fallback_files": ["cumulative_up_to_2024.csv"],
        "features": [
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
    },
    {
        "version": 4,
        "name": "Full_Official_2025",
        "description": "Official Records 2022-2025 - Core + Interactions + Rolling Features",
        "data_files": ["cumulative_v2_up_to_2025.csv"],
        "fallback_files": ["cumulative_up_to_2025.csv"],
        "features": [
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
            "precip_3day_sum",
            "precip_7day_sum",
            "rain_streak",
        ],
    },
    {
        "version": 5,
        "name": "PAGASA_Merged",
        "description": "Official + PAGASA Weather Data - Enhanced Features",
        "data_files": ["cumulative_v2_up_to_2025.csv", "pagasa_training_dataset.csv"],
        "fallback_files": ["cumulative_up_to_2025.csv", "pagasa_training_dataset.csv"],
        "features": [
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
            "precip_14day_sum",
            "rain_streak",
        ],
    },
    {
        "version": 6,
        "name": "Ultimate_Combined",
        "description": "All Sources + External APIs - Complete Feature Set",
        "data_files": [
            "cumulative_v2_up_to_2025.csv",
            "pagasa_training_dataset.csv",
            "fetched_googlecloud.csv",
            "fetched_meteostat.csv",
            "fetched_worldtides.csv",
        ],
        "fallback_files": [
            "cumulative_up_to_2025.csv",
            "pagasa_training_dataset.csv",
        ],
        "features": [
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
        ],
    },
]

# Default model parameters
DEFAULT_PARAMS = {
    "n_estimators": 200,
    "max_depth": 15,
    "min_samples_split": 5,
    "min_samples_leaf": 2,
    "max_features": "sqrt",
    "class_weight": "balanced_subsample",
    "random_state": 42,
    "n_jobs": -1,
}

# Quick mode parameters (faster training for testing)
QUICK_PARAMS = {
    "n_estimators": 100,
    "max_depth": 10,
    "min_samples_split": 5,
    "min_samples_leaf": 2,
    "max_features": "sqrt",
    "class_weight": "balanced_subsample",
    "random_state": 42,
    "n_jobs": -1,
}


class ProgressiveTrainerV6:
    """Trains models progressively from v1 to v6 with incremental features."""

    def __init__(
        self,
        models_dir: Path = MODELS_DIR,
        reports_dir: Path = REPORTS_DIR,
        quick_mode: bool = False,
    ):
        self.models_dir = Path(models_dir)
        self.reports_dir = Path(reports_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.quick_mode = quick_mode
        self.results: List[Dict] = []

    def load_data(self, data_files: List[str], fallback_files: List[str]) -> pd.DataFrame:
        """Load and merge training data from multiple files."""
        dfs = []
        files_loaded = []

        # Try primary files first
        for data_file in data_files:
            path = PROCESSED_DIR / data_file
            if path.exists():
                try:
                    df = pd.read_csv(path)
                    dfs.append(df)
                    files_loaded.append(data_file)
                    logger.info(f"  Loaded: {data_file} ({len(df)} records)")
                except Exception as e:
                    logger.warning(f"  Failed to load {data_file}: {e}")

        # If no primary files loaded, try fallbacks
        if not dfs:
            logger.warning("  Primary files not found, trying fallbacks...")
            for data_file in fallback_files:
                path = PROCESSED_DIR / data_file
                if path.exists():
                    try:
                        df = pd.read_csv(path)
                        dfs.append(df)
                        files_loaded.append(data_file)
                        logger.info(f"  Loaded (fallback): {data_file} ({len(df)} records)")
                    except Exception as e:
                        logger.warning(f"  Failed to load {data_file}: {e}")

        if not dfs:
            raise FileNotFoundError(f"No data files found. Tried: {data_files + fallback_files}")

        # Merge and deduplicate
        if len(dfs) > 1:
            merged = pd.concat(dfs, ignore_index=True)
            # Remove duplicates if there's a common identifier
            if "date" in merged.columns and "station_id" in merged.columns:
                merged = merged.drop_duplicates(subset=["date", "station_id"])
            else:
                merged = merged.drop_duplicates()
            logger.info(f"  Merged {len(dfs)} files → {len(merged)} unique records")
            return merged
        else:
            return dfs[0]

    def prepare_features(self, df: pd.DataFrame, feature_list: List[str]) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare features for training."""
        # Check which features are available
        available = [f for f in feature_list if f in df.columns]
        missing = [f for f in feature_list if f not in df.columns]

        if missing:
            logger.warning(f"  Missing features: {missing}")

        if not available:
            raise ValueError("No features available for training")

        # Prepare feature matrix and target
        X = df[available].copy()
        y = df["flood"].copy()

        # Remove rows with NaN in target variable
        valid_mask = ~y.isna()
        if not valid_mask.all():
            nan_count = (~valid_mask).sum()
            logger.warning(f"  Removing {nan_count} records with NaN target values")
            X = X[valid_mask]
            y = y[valid_mask]

        # Fill missing values in features with median
        X = X.fillna(X.median())

        logger.info(f"  Features ({len(available)}): {available}")
        logger.info(f"  Target distribution: {y.value_counts().to_dict()}")

        return X, y

    def train_version(self, version_config: Dict, cv_folds: int = 5) -> Tuple[RandomForestClassifier, Dict]:
        """Train a single model version."""
        version = version_config["version"]
        name = version_config["name"]
        description = version_config["description"]
        data_files = version_config["data_files"]
        fallback_files = version_config["fallback_files"]
        features = version_config["features"]

        logger.info(f"\n{'=' * 70}")
        logger.info(f"TRAINING v{version}: {name}")
        logger.info(f"{'=' * 70}")
        logger.info(f"Description: {description}")

        # Load data
        df = self.load_data(data_files, fallback_files)
        X, y = self.prepare_features(df, features)

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

        logger.info(f"  Train: {len(X_train)}, Test: {len(X_test)}")

        # Train model
        params = QUICK_PARAMS if self.quick_mode else DEFAULT_PARAMS
        model = RandomForestClassifier(**params)

        logger.info(f"  Training with {params['n_estimators']} estimators...")
        model.fit(X_train, y_train)

        # Evaluate
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]

        metrics = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision": float(precision_score(y_test, y_pred, average="weighted", zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, average="weighted", zero_division=0)),
            "f1_score": float(f1_score(y_test, y_pred, average="weighted", zero_division=0)),
            "f2_score": float(fbeta_score(y_test, y_pred, beta=2, average="weighted", zero_division=0)),
            "roc_auc": float(roc_auc_score(y_test, y_pred_proba)),
        }

        # Cross-validation
        logger.info(f"  Running {cv_folds}-fold cross-validation...")
        cv_scores = cross_val_score(model, X, y, cv=cv_folds, scoring="f1_weighted", n_jobs=-1)
        metrics["cv_mean"] = float(cv_scores.mean())
        metrics["cv_std"] = float(cv_scores.std())

        # Feature importance
        feature_importance = dict(zip(X.columns, model.feature_importances_))
        top_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:5]

        logger.info(f"\nv{version} Results:")
        logger.info(f"  Accuracy:  {metrics['accuracy']:.4f}")
        logger.info(f"  Precision: {metrics['precision']:.4f}")
        logger.info(f"  Recall:    {metrics['recall']:.4f}")
        logger.info(f"  F1 Score:  {metrics['f1_score']:.4f}")
        logger.info(f"  F2 Score:  {metrics['f2_score']:.4f}")
        logger.info(f"  ROC-AUC:   {metrics['roc_auc']:.4f}")
        logger.info(f"  CV Score:  {metrics['cv_mean']:.4f} (+/- {metrics['cv_std']*2:.4f})")
        logger.info(f"\nTop 5 Features:")
        for feat, imp in top_features:
            logger.info(f"    {feat}: {imp:.4f}")

        # Store result
        result = {
            "version": version,
            "name": name,
            "description": description,
            "data_files": data_files,
            "dataset_size": len(df),
            "num_features": len(X.columns),
            "features": list(X.columns),
            "metrics": metrics,
            "feature_importance": feature_importance,
            "model_params": params,
        }
        self.results.append(result)

        return model, result

    def save_model(self, model: RandomForestClassifier, result: Dict):
        """Save model, metadata, and feature names."""
        version = result["version"]

        # Save model
        model_path = self.models_dir / f"flood_model_v{version}.joblib"
        joblib.dump(model, model_path)
        logger.info(f"  Saved model: {model_path}")

        # Save metadata
        metadata = {
            "version": version,
            "name": result["name"],
            "model_type": "RandomForestClassifier",
            "created_at": datetime.now().isoformat(),
            "description": result["description"],
            "training_data": {
                "files": result["data_files"],
                "total_records": result["dataset_size"],
                "num_features": result["num_features"],
            },
            "features": result["features"],
            "metrics": result["metrics"],
            "model_parameters": result["model_params"],
            "cross_validation": {
                "cv_folds": 5,
                "cv_mean": result["metrics"].get("cv_mean"),
                "cv_std": result["metrics"].get("cv_std"),
            },
        }

        metadata_path = self.models_dir / f"flood_model_v{version}.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"  Saved metadata: {metadata_path}")

        # Save feature names
        feature_names_path = self.models_dir / f"feature_names_v{version}.json"
        with open(feature_names_path, "w") as f:
            json.dump(result["features"], f, indent=2)
        logger.info(f"  Saved features: {feature_names_path}")

        # Save as default model (for validation/evaluation scripts)
        default_path = self.models_dir / "flood_rf_model.joblib"
        joblib.dump(model, default_path)
        logger.info(f"  Saved as default: {default_path}")

    def train_all(self, cv_folds: int = 5, specific_version: Optional[int] = None):
        """Train all progressive versions or a specific version."""
        logger.info("\n" + "=" * 70)
        logger.info("PROGRESSIVE MODEL TRAINING v1-v6")
        logger.info("Training models with incremental feature additions")
        if self.quick_mode:
            logger.info("MODE: QUICK (reduced estimators for testing)")
        logger.info("=" * 70)

        versions_to_train = PROGRESSIVE_VERSIONS
        if specific_version:
            versions_to_train = [v for v in PROGRESSIVE_VERSIONS if v["version"] == specific_version]
            if not versions_to_train:
                raise ValueError(f"Invalid version: {specific_version}")

        for version_config in versions_to_train:
            try:
                model, result = self.train_version(version_config, cv_folds)
                self.save_model(model, result)
            except FileNotFoundError as e:
                logger.error(f"Skipping v{version_config['version']}: {e}")
                continue
            except Exception as e:
                logger.error(f"Error training v{version_config['version']}: {e}", exc_info=True)
                continue

        # Generate reports
        if not specific_version:  # Only generate comparison reports when training all versions
            self.generate_progression_report()
            self.generate_progression_chart()

    def generate_progression_report(self):
        """Generate comprehensive JSON report of progression results."""
        if not self.results:
            logger.warning("No results to report")
            return

        report = {
            "generated_at": datetime.now().isoformat(),
            "quick_mode": self.quick_mode,
            "versions": self.results,
            "progression_summary": self._calculate_progression_summary(),
        }

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.reports_dir / f"progressive_v6_report_{timestamp}.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"\n✓ Progression report saved: {report_path}")

        # Also save a latest version without timestamp
        latest_path = self.reports_dir / "progressive_v6_report_latest.json"
        with open(latest_path, "w") as f:
            json.dump(report, f, indent=2)

    def _calculate_progression_summary(self) -> Dict:
        """Calculate progression metrics across all versions."""
        if len(self.results) < 2:
            return {}

        first = self.results[0]
        last = self.results[-1]

        summary = {
            "first_version": first["version"],
            "last_version": last["version"],
            "total_versions_trained": len(self.results),
            "improvements": {
                "accuracy": last["metrics"]["accuracy"] - first["metrics"]["accuracy"],
                "f1_score": last["metrics"]["f1_score"] - first["metrics"]["f1_score"],
                "f2_score": last["metrics"]["f2_score"] - first["metrics"]["f2_score"],
                "roc_auc": last["metrics"]["roc_auc"] - first["metrics"]["roc_auc"],
            },
            "feature_growth": {
                "v1_features": first["num_features"],
                "v6_features": last["num_features"],
                "features_added": last["num_features"] - first["num_features"],
            },
            "data_growth": {
                "v1_records": first["dataset_size"],
                "v6_records": last["dataset_size"],
                "records_added": last["dataset_size"] - first["dataset_size"],
            },
        }

        return summary

    def generate_progression_chart(self):
        """Generate visualization of model progression."""
        try:
            import matplotlib.pyplot as plt

            if not self.results:
                return

            versions = [r["version"] for r in self.results]
            accuracy = [r["metrics"]["accuracy"] for r in self.results]
            f1_scores = [r["metrics"]["f1_score"] for r in self.results]
            f2_scores = [r["metrics"]["f2_score"] for r in self.results]
            roc_auc = [r["metrics"]["roc_auc"] for r in self.results]

            # Metrics evolution chart
            fig, ax = plt.subplots(figsize=(12, 7))

            ax.plot(versions, accuracy, "o-", label="Accuracy", linewidth=2.5, markersize=10)
            ax.plot(versions, f1_scores, "s-", label="F1 Score", linewidth=2.5, markersize=10)
            ax.plot(versions, f2_scores, "^-", label="F2 Score", linewidth=2.5, markersize=10)
            ax.plot(versions, roc_auc, "d-", label="ROC-AUC", linewidth=2.5, markersize=10)

            ax.set_xlabel("Model Version", fontsize=13, fontweight="bold")
            ax.set_ylabel("Score", fontsize=13, fontweight="bold")
            ax.set_title(
                "Model Performance Evolution\nProgressive Training v1-v6 (2022 → Ultimate)",
                fontsize=15,
                fontweight="bold",
            )
            ax.legend(loc="lower right", fontsize=12)
            ax.grid(True, alpha=0.3, linestyle="--")
            ax.set_ylim([0, 1.1])
            ax.set_xticks(versions)

            plt.tight_layout()
            chart_path = self.reports_dir / "metrics_evolution_v6.png"
            plt.savefig(chart_path, dpi=300, bbox_inches="tight")
            plt.close()

            logger.info(f"✓ Progression chart saved: {chart_path}")

            # Feature count vs performance
            self._generate_feature_chart()

        except ImportError:
            logger.warning("matplotlib not available, skipping chart generation")

    def _generate_feature_chart(self):
        """Generate chart showing feature count vs performance."""
        try:
            import matplotlib.pyplot as plt

            num_features = [r["num_features"] for r in self.results]
            f1_scores = [r["metrics"]["f1_score"] for r in self.results]
            versions = [f"v{r['version']}" for r in self.results]

            fig, ax = plt.subplots(figsize=(10, 6))

            colors = plt.cm.viridis(np.linspace(0, 1, len(versions)))
            bars = ax.bar(versions, f1_scores, color=colors, alpha=0.8, edgecolor="black", linewidth=1.5)

            # Add feature count labels on bars
            for i, (bar, feat_count) in enumerate(zip(bars, num_features)):
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height + 0.01,
                    f"{feat_count} features",
                    ha="center",
                    va="bottom",
                    fontsize=10,
                    fontweight="bold",
                )

            ax.set_xlabel("Model Version", fontsize=13, fontweight="bold")
            ax.set_ylabel("F1 Score", fontsize=13, fontweight="bold")
            ax.set_title("Feature Count vs Model Performance", fontsize=15, fontweight="bold")
            ax.set_ylim([0, 1.1])
            ax.grid(True, alpha=0.3, axis="y", linestyle="--")

            plt.tight_layout()
            chart_path = self.reports_dir / "feature_count_vs_performance.png"
            plt.savefig(chart_path, dpi=300, bbox_inches="tight")
            plt.close()

            logger.info(f"✓ Feature comparison chart saved: {chart_path}")

        except ImportError:
            pass


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Progressive model training v1-v6 for thesis demonstration")
    parser.add_argument("--quick", action="store_true", help="Quick mode (reduced estimators)")
    parser.add_argument("--cv-folds", type=int, default=5, help="Number of cross-validation folds")
    parser.add_argument("--version", type=int, help="Train specific version only (1-6)")

    args = parser.parse_args()

    if args.version and (args.version < 1 or args.version > 6):
        logger.error("Version must be between 1 and 6")
        return 1

    trainer = ProgressiveTrainerV6(quick_mode=args.quick)
    trainer.train_all(cv_folds=args.cv_folds, specific_version=args.version)

    # Print summary
    print("\n" + "=" * 70)
    print("PROGRESSIVE TRAINING COMPLETE")
    print("=" * 70)

    if trainer.results:
        print("\nVersion Summary:")
        for r in trainer.results:
            print(f"  v{r['version']}: {r['name']}")
            print(f"    Features: {r['num_features']}, Records: {r['dataset_size']}")
            print(
                f"    F1: {r['metrics']['f1_score']:.4f}, F2: {r['metrics']['f2_score']:.4f}, "
                f"Accuracy: {r['metrics']['accuracy']:.4f}"
            )

        if len(trainer.results) >= 2:
            summary = trainer._calculate_progression_summary()
            print(f"\nOverall Improvement (v{summary['first_version']} → v{summary['last_version']}):")
            print(f"  Accuracy: {summary['improvements']['accuracy']:+.4f}")
            print(f"  F1 Score: {summary['improvements']['f1_score']:+.4f}")
            print(f"  F2 Score: {summary['improvements']['f2_score']:+.4f}")
            print(f"  ROC-AUC:  {summary['improvements']['roc_auc']:+.4f}")
            print(
                f"\nFeature Growth: {summary['feature_growth']['v1_features']} → "
                f"{summary['feature_growth']['v6_features']} "
                f"(+{summary['feature_growth']['features_added']})"
            )
            print(
                f"Data Growth: {summary['data_growth']['v1_records']:,} → "
                f"{summary['data_growth']['v6_records']:,} records "
                f"(+{summary['data_growth']['records_added']:,})"
            )

    print("=" * 70)
    return 0


if __name__ == "__main__":
    exit(main())
