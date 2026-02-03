#!/usr/bin/env python
"""
Progressive Model Comparison Utility
=====================================

Compares all v1-v6 models and generates comprehensive comparison reports.

Features:
    - Side-by-side metric comparison
    - Feature importance analysis across versions
    - Performance progression visualization
    - Dataset size vs performance analysis
    - Markdown and JSON report generation

Usage:
    python scripts/compare_progressive_models.py
    python scripts/compare_progressive_models.py --output-dir reports/comparison
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import joblib
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
MODELS_DIR = BACKEND_DIR / "models"
REPORTS_DIR = BACKEND_DIR / "reports"


class ProgressiveModelComparator:
    """Compares progressive model versions v1-v6."""

    def __init__(self, models_dir: Path = MODELS_DIR, output_dir: Path = REPORTS_DIR):
        self.models_dir = Path(models_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.models: Dict[int, Dict] = {}

    def load_models(self):
        """Load all available model versions and their metadata."""
        logger.info("Loading model versions...")

        for version in range(1, 7):
            model_path = self.models_dir / f"flood_model_v{version}.joblib"
            metadata_path = self.models_dir / f"flood_model_v{version}.json"

            if not model_path.exists():
                logger.warning(f"Model v{version} not found: {model_path}")
                continue

            try:
                # Load model
                model = joblib.load(model_path)

                # Load metadata
                metadata = {}
                if metadata_path.exists():
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)

                self.models[version] = {
                    "model": model,
                    "metadata": metadata,
                    "path": str(model_path),
                }

                logger.info(f"  ✓ Loaded v{version}: {metadata.get('name', 'Unknown')}")

            except Exception as e:
                logger.error(f"Failed to load v{version}: {e}")

        logger.info(f"Loaded {len(self.models)} model versions")

    def generate_comparison_table(self) -> pd.DataFrame:
        """Generate comparison table of all models."""
        if not self.models:
            logger.warning("No models loaded")
            return pd.DataFrame()

        data = []
        for version in sorted(self.models.keys()):
            metadata = self.models[version]["metadata"]
            metrics = metadata.get("metrics", {})
            training_data = metadata.get("training_data", {})

            row = {
                "Version": f"v{version}",
                "Name": metadata.get("name", "Unknown"),
                "Records": training_data.get("total_records", 0),
                "Features": training_data.get("num_features", 0),
                "Accuracy": metrics.get("accuracy", 0),
                "Precision": metrics.get("precision", 0),
                "Recall": metrics.get("recall", 0),
                "F1 Score": metrics.get("f1_score", 0),
                "F2 Score": metrics.get("f2_score", 0),
                "ROC-AUC": metrics.get("roc_auc", 0),
                "CV Mean": metrics.get("cv_mean", 0),
                "CV Std": metrics.get("cv_std", 0),
            }
            data.append(row)

        df = pd.DataFrame(data)
        return df

    def generate_markdown_report(self, comparison_df: pd.DataFrame) -> str:
        """Generate markdown comparison report."""
        md = []
        md.append("# Progressive Model Comparison Report (v1-v6)")
        md.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md.append("\n## Overview\n")
        md.append(f"Total models compared: {len(self.models)}")
        md.append(f"Versions: {', '.join([f'v{v}' for v in sorted(self.models.keys())])}")

        md.append("\n## Performance Metrics Comparison\n")
        md.append("| Version | Name | Records | Features | Accuracy | F1 Score | F2 Score | ROC-AUC |")
        md.append("|---------|------|---------|----------|----------|----------|----------|---------|")

        for _, row in comparison_df.iterrows():
            md.append(
                f"| {row['Version']} | {row['Name']} | {row['Records']:,} | {row['Features']} | "
                f"{row['Accuracy']:.4f} | {row['F1 Score']:.4f} | {row['F2 Score']:.4f} | {row['ROC-AUC']:.4f} |"
            )

        # Calculate improvements
        if len(comparison_df) >= 2:
            first = comparison_df.iloc[0]
            last = comparison_df.iloc[-1]

            md.append("\n## Overall Improvement\n")
            md.append(f"**{first['Version']} → {last['Version']}**\n")
            md.append(
                f"- **Accuracy**: {first['Accuracy']:.4f} → {last['Accuracy']:.4f} "
                f"({(last['Accuracy'] - first['Accuracy']):+.4f})"
            )
            md.append(
                f"- **F1 Score**: {first['F1 Score']:.4f} → {last['F1 Score']:.4f} "
                f"({(last['F1 Score'] - first['F1 Score']):+.4f})"
            )
            md.append(
                f"- **F2 Score**: {first['F2 Score']:.4f} → {last['F2 Score']:.4f} "
                f"({(last['F2 Score'] - first['F2 Score']):+.4f})"
            )
            md.append(
                f"- **ROC-AUC**: {first['ROC-AUC']:.4f} → {last['ROC-AUC']:.4f} "
                f"({(last['ROC-AUC'] - first['ROC-AUC']):+.4f})"
            )
            md.append(
                f"- **Features**: {first['Features']} → {last['Features']} "
                f"(+{last['Features'] - first['Features']})"
            )
            md.append(
                f"- **Records**: {first['Records']:,} → {last['Records']:,} "
                f"(+{last['Records'] - first['Records']:,})"
            )

        # Feature details
        md.append("\n## Feature Evolution\n")
        for version in sorted(self.models.keys()):
            metadata = self.models[version]["metadata"]
            features = metadata.get("features", [])
            md.append(f"\n### {metadata.get('name', f'v{version}')}")
            md.append(f"**Features ({len(features)})**: {', '.join(features)}")

        md.append("\n## Model Details\n")
        for version in sorted(self.models.keys()):
            metadata = self.models[version]["metadata"]
            md.append(f"\n### v{version}: {metadata.get('name', 'Unknown')}")
            md.append(f"- **Description**: {metadata.get('description', 'N/A')}")
            md.append(f"- **Created**: {metadata.get('created_at', 'N/A')}")
            md.append(f"- **Model Type**: {metadata.get('model_type', 'N/A')}")

            training_data = metadata.get("training_data", {})
            md.append(f"- **Data Files**: {', '.join(training_data.get('files', []))}")

            params = metadata.get("model_parameters", {})
            if params:
                md.append(
                    f"- **Parameters**: n_estimators={params.get('n_estimators', 'N/A')}, "
                    f"max_depth={params.get('max_depth', 'N/A')}, "
                    f"class_weight={params.get('class_weight', 'N/A')}"
                )

        return "\n".join(md)

    def generate_visualizations(self, comparison_df: pd.DataFrame):
        """Generate comparison visualizations."""
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns

            sns.set_style("whitegrid")

            # 1. Metrics comparison bar chart
            fig, axes = plt.subplots(2, 2, figsize=(14, 10))

            metrics = ["Accuracy", "F1 Score", "F2 Score", "ROC-AUC"]
            for idx, metric in enumerate(metrics):
                ax = axes[idx // 2, idx % 2]
                bars = ax.bar(
                    comparison_df["Version"],
                    comparison_df[metric],
                    color=plt.cm.viridis(np.linspace(0, 1, len(comparison_df))),
                    edgecolor="black",
                    linewidth=1.5,
                )

                ax.set_xlabel("Model Version", fontsize=11, fontweight="bold")
                ax.set_ylabel(metric, fontsize=11, fontweight="bold")
                ax.set_title(f"{metric} Comparison", fontsize=12, fontweight="bold")
                ax.set_ylim([0, 1.1])
                ax.grid(True, alpha=0.3, axis="y")

                # Add value labels on bars
                for bar in bars:
                    height = bar.get_height()
                    ax.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        height + 0.01,
                        f"{height:.3f}",
                        ha="center",
                        va="bottom",
                        fontsize=9,
                    )

            plt.tight_layout()
            chart_path = self.output_dir / "metrics_comparison.png"
            plt.savefig(chart_path, dpi=300, bbox_inches="tight")
            plt.close()
            logger.info(f"  ✓ Saved: {chart_path}")

            # 2. Feature count vs performance
            fig, ax = plt.subplots(figsize=(10, 6))

            ax.scatter(
                comparison_df["Features"],
                comparison_df["F1 Score"],
                s=200,
                c=range(len(comparison_df)),
                cmap="viridis",
                edgecolor="black",
                linewidth=2,
                alpha=0.7,
            )

            for idx, row in comparison_df.iterrows():
                ax.annotate(
                    row["Version"],
                    (row["Features"], row["F1 Score"]),
                    xytext=(5, 5),
                    textcoords="offset points",
                    fontsize=10,
                    fontweight="bold",
                )

            ax.set_xlabel("Number of Features", fontsize=12, fontweight="bold")
            ax.set_ylabel("F1 Score", fontsize=12, fontweight="bold")
            ax.set_title("Feature Count vs Model Performance", fontsize=14, fontweight="bold")
            ax.grid(True, alpha=0.3)

            plt.tight_layout()
            chart_path = self.output_dir / "features_vs_performance.png"
            plt.savefig(chart_path, dpi=300, bbox_inches="tight")
            plt.close()
            logger.info(f"  ✓ Saved: {chart_path}")

            # 3. Dataset size vs performance
            fig, ax = plt.subplots(figsize=(10, 6))

            ax.scatter(
                comparison_df["Records"],
                comparison_df["F1 Score"],
                s=200,
                c=range(len(comparison_df)),
                cmap="plasma",
                edgecolor="black",
                linewidth=2,
                alpha=0.7,
            )

            for idx, row in comparison_df.iterrows():
                ax.annotate(
                    row["Version"],
                    (row["Records"], row["F1 Score"]),
                    xytext=(5, 5),
                    textcoords="offset points",
                    fontsize=10,
                    fontweight="bold",
                )

            ax.set_xlabel("Dataset Size (Records)", fontsize=12, fontweight="bold")
            ax.set_ylabel("F1 Score", fontsize=12, fontweight="bold")
            ax.set_title("Dataset Size vs Model Performance", fontsize=14, fontweight="bold")
            ax.grid(True, alpha=0.3)

            plt.tight_layout()
            chart_path = self.output_dir / "dataset_size_vs_performance.png"
            plt.savefig(chart_path, dpi=300, bbox_inches="tight")
            plt.close()
            logger.info(f"  ✓ Saved: {chart_path}")

        except ImportError:
            logger.warning("matplotlib/seaborn not available, skipping visualizations")

    def run_comparison(self):
        """Run full comparison analysis."""
        logger.info("\n" + "=" * 70)
        logger.info("PROGRESSIVE MODEL COMPARISON")
        logger.info("=" * 70)

        self.load_models()

        if not self.models:
            logger.error("No models found to compare")
            return

        # Generate comparison table
        logger.info("\nGenerating comparison table...")
        comparison_df = self.generate_comparison_table()

        # Save CSV
        csv_path = self.output_dir / "progressive_comparison.csv"
        comparison_df.to_csv(csv_path, index=False)
        logger.info(f"  ✓ Saved CSV: {csv_path}")

        # Generate markdown report
        logger.info("\nGenerating markdown report...")
        markdown = self.generate_markdown_report(comparison_df)
        md_path = self.output_dir / "progressive_comparison.md"
        with open(md_path, "w") as f:
            f.write(markdown)
        logger.info(f"  ✓ Saved markdown: {md_path}")

        # Generate JSON report
        logger.info("\nGenerating JSON report...")
        json_data = {
            "generated_at": datetime.now().isoformat(),
            "total_models": len(self.models),
            "versions": sorted(self.models.keys()),
            "comparison": comparison_df.to_dict(orient="records"),
        }
        json_path = self.output_dir / "progressive_comparison.json"
        with open(json_path, "w") as f:
            json.dump(json_data, f, indent=2)
        logger.info(f"  ✓ Saved JSON: {json_path}")

        # Generate visualizations
        logger.info("\nGenerating visualizations...")
        self.generate_visualizations(comparison_df)

        # Print summary
        print("\n" + "=" * 70)
        print("COMPARISON COMPLETE")
        print("=" * 70)
        print(f"\nModels compared: {len(self.models)}")
        print(f"Versions: {', '.join([f'v{v}' for v in sorted(self.models.keys())])}")

        if len(comparison_df) >= 2:
            first = comparison_df.iloc[0]
            last = comparison_df.iloc[-1]
            print(f"\nOverall Improvement ({first['Version']} → {last['Version']}):")
            print(
                f"  F1 Score: {first['F1 Score']:.4f} → {last['F1 Score']:.4f} "
                f"({(last['F1 Score'] - first['F1 Score']):+.4f})"
            )
            print(f"  Features: {first['Features']} → {last['Features']} " f"(+{last['Features'] - first['Features']})")
            print(
                f"  Records:  {first['Records']:,} → {last['Records']:,} " f"(+{last['Records'] - first['Records']:,})"
            )

        print("\nGenerated files:")
        print(f"  - {csv_path}")
        print(f"  - {md_path}")
        print(f"  - {json_path}")
        print("=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Compare progressive model versions v1-v6")
    parser.add_argument("--models-dir", type=str, help="Models directory path")
    parser.add_argument("--output-dir", type=str, help="Output directory for reports")

    args = parser.parse_args()

    models_dir = Path(args.models_dir) if args.models_dir else MODELS_DIR
    output_dir = Path(args.output_dir) if args.output_dir else REPORTS_DIR

    comparator = ProgressiveModelComparator(models_dir=models_dir, output_dir=output_dir)
    comparator.run_comparison()


if __name__ == "__main__":
    main()
