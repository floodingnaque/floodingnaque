"""
Real Dataset Transition Plan – Orchestrator.

Manages the three-phase progression from synthetic data to fully labeled
historical flood records for the Floodingnaque flood prediction system:

  Phase 1: **Synthetic dataset** – generated or rule-based labels for
           bootstrapping model development.
  Phase 2: **Semi-supervised learning** – blends a teacher model's
           pseudo-labels on unlabeled data with a growing set of
           verified labels; includes confidence filtering.
  Phase 3: **Fully labeled historical flood records** – official DRRMO
           records cross-referenced with PAGASA weather data.

Each phase is self-contained: it validates its input, checks label
consistency, and emits a readiness assessment for the *next* phase. This
lets the team incrementally upgrade data quality without breaking the
training pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from app.services.dataset_validation import (
    DatasetPhase,
    DatasetValidator,
    ValidationReport,
)
from app.services.label_consistency import (
    ConsistencyReport,
    LabelConsistencyChecker,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase definitions
# ---------------------------------------------------------------------------


class TransitionPhase(str, Enum):
    PHASE_1_SYNTHETIC = "phase_1_synthetic"
    PHASE_2_SEMI_SUPERVISED = "phase_2_semi_supervised"
    PHASE_3_HISTORICAL = "phase_3_historical"


# Map transition phases → validation phases
_VALIDATION_PHASE_MAP = {
    TransitionPhase.PHASE_1_SYNTHETIC: DatasetPhase.SYNTHETIC,
    TransitionPhase.PHASE_2_SEMI_SUPERVISED: DatasetPhase.SEMI_SUPERVISED,
    TransitionPhase.PHASE_3_HISTORICAL: DatasetPhase.HISTORICAL,
}


@dataclass
class PhaseReadiness:
    """Whether the current dataset is ready to advance to the next phase."""

    current_phase: str
    next_phase: Optional[str]
    ready: bool
    blockers: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_phase": self.current_phase,
            "next_phase": self.next_phase,
            "ready": self.ready,
            "blockers": self.blockers,
            "warnings": self.warnings,
            "improvements": self.improvements,
            "metrics": self.metrics,
        }


@dataclass
class TransitionReport:
    """Full report for a dataset transition audit."""

    phase: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    validation: Optional[Dict[str, Any]] = None
    consistency: Optional[Dict[str, Any]] = None
    readiness: Optional[Dict[str, Any]] = None
    phase_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "timestamp": self.timestamp,
            "validation": self.validation,
            "consistency": self.consistency,
            "readiness": self.readiness,
            "phase_metadata": self.phase_metadata,
        }


# ---------------------------------------------------------------------------
# Readiness criteria per phase
# ---------------------------------------------------------------------------

# Phase 1 → Phase 2 criteria
PHASE_1_TO_2_MIN_ROWS = 200
PHASE_1_TO_2_MAX_MISSING_RATIO = 0.05
PHASE_1_TO_2_MIN_CLASSES = 2

# Phase 2 → Phase 3 criteria
PHASE_2_TO_3_MIN_ROWS = 500
PHASE_2_TO_3_MIN_CONFIDENCE = 0.7
PHASE_2_TO_3_MIN_LABELED_RATIO = 0.3
PHASE_2_TO_3_MAX_CROSS_SOURCE_DISAGREEMENT = 0.15

# Phase 3 final quality criteria
PHASE_3_MIN_ROWS = 1000
PHASE_3_MIN_MONTHS = 12
PHASE_3_MIN_BARANGAYS = 5


# ---------------------------------------------------------------------------
# Core orchestrator
# ---------------------------------------------------------------------------


class DatasetTransitionPlan:
    """Orchestrates dataset evaluation across transition phases.

    Combines :class:`DatasetValidator` and :class:`LabelConsistencyChecker`
    to produce a unified assessment with readiness indicators.

    Usage::

        plan = DatasetTransitionPlan()
        report = plan.evaluate(df, TransitionPhase.PHASE_1_SYNTHETIC)
        print(report.to_dict())
    """

    def __init__(
        self,
        *,
        data_dir: str | Path = "data",
        processed_dir: str | Path = "data/processed",
    ) -> None:
        self.data_dir = Path(data_dir)
        self.processed_dir = Path(processed_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        df: pd.DataFrame,
        phase: TransitionPhase,
        *,
        reference_df: Optional[pd.DataFrame] = None,
    ) -> TransitionReport:
        """Run validation + consistency checks and assess readiness.

        Args:
            df: The dataset to evaluate.
            phase: Current transition phase.
            reference_df: Optional reference dataset for cross-source
                comparison (e.g. official records vs. pseudo-labels).

        Returns:
            A :class:`TransitionReport`.
        """
        report = TransitionReport(
            phase=phase.value,
            phase_metadata=self._phase_metadata(phase),
        )

        # 1. Dataset validation
        val_phase = _VALIDATION_PHASE_MAP[phase]
        validator = DatasetValidator(phase=val_phase)
        val_report = validator.validate(df)
        report.validation = val_report.to_dict()

        # 2. Label consistency
        checker = LabelConsistencyChecker()
        con_report = checker.check(df)

        # Optional cross-source comparison
        if reference_df is not None:
            cross_report = checker.check_cross_source(
                df,
                reference_df,
                source_a_name=phase.value,
                source_b_name="reference",
            )
            # Merge cross-source findings into the main consistency report
            for inc in cross_report.inconsistencies:
                con_report.add(inc)
            con_report.recommendations.extend(cross_report.recommendations)

        report.consistency = con_report.to_dict()

        # 3. Readiness assessment
        readiness = self._assess_readiness(df, phase, val_report, con_report)
        report.readiness = readiness.to_dict()

        return report

    def evaluate_file(
        self,
        path: str | Path,
        phase: TransitionPhase,
        **kwargs: Any,
    ) -> TransitionReport:
        """Convenience: load CSV and evaluate."""
        df = pd.read_csv(path)
        return self.evaluate(df, phase, **kwargs)

    def generate_phase_summary(
        self, phase: TransitionPhase
    ) -> Dict[str, Any]:
        """Return a description of what a phase entails."""
        return self._phase_metadata(phase)

    # ------------------------------------------------------------------
    # Readiness assessment
    # ------------------------------------------------------------------

    def _assess_readiness(
        self,
        df: pd.DataFrame,
        phase: TransitionPhase,
        val_report: ValidationReport,
        con_report: ConsistencyReport,
    ) -> PhaseReadiness:
        """Determine if the dataset can advance to the next phase."""
        if phase == TransitionPhase.PHASE_1_SYNTHETIC:
            return self._assess_phase1(df, val_report, con_report)
        elif phase == TransitionPhase.PHASE_2_SEMI_SUPERVISED:
            return self._assess_phase2(df, val_report, con_report)
        else:
            return self._assess_phase3(df, val_report, con_report)

    def _assess_phase1(
        self,
        df: pd.DataFrame,
        val_report: ValidationReport,
        con_report: ConsistencyReport,
    ) -> PhaseReadiness:
        """Phase 1 (Synthetic) → Phase 2 (Semi-supervised) readiness."""
        readiness = PhaseReadiness(
            current_phase=TransitionPhase.PHASE_1_SYNTHETIC.value,
            next_phase=TransitionPhase.PHASE_2_SEMI_SUPERVISED.value,
            ready=True,
        )

        # Check row count
        if len(df) < PHASE_1_TO_2_MIN_ROWS:
            readiness.blockers.append(
                f"Need ≥ {PHASE_1_TO_2_MIN_ROWS} rows, have {len(df)}."
            )
            readiness.ready = False

        # Check validation passed
        if not val_report.passed:
            readiness.blockers.append(
                f"Validation failed with {val_report.error_count} errors."
            )
            readiness.ready = False

        # Check class count
        if "flood" in df.columns:
            n_classes = df["flood"].nunique()
            if n_classes < PHASE_1_TO_2_MIN_CLASSES:
                readiness.blockers.append(
                    "Target 'flood' has only one class."
                )
                readiness.ready = False

        # Warnings
        if con_report.total_issues > 0:
            readiness.warnings.append(
                f"{con_report.total_issues} label consistency issues found."
            )

        # Improvement suggestions
        readiness.improvements = [
            "Train a teacher model on synthetic data to generate pseudo-labels.",
            "Collect unlabeled weather data from Meteostat/PAGASA for pseudo-labeling.",
            "Prepare confidence thresholds for pseudo-label filtering.",
        ]

        readiness.metrics = {
            "row_count": len(df),
            "validation_passed": val_report.passed,
            "consistency_issues": con_report.total_issues,
        }

        return readiness

    def _assess_phase2(
        self,
        df: pd.DataFrame,
        val_report: ValidationReport,
        con_report: ConsistencyReport,
    ) -> PhaseReadiness:
        """Phase 2 (Semi-supervised) → Phase 3 (Historical) readiness."""
        readiness = PhaseReadiness(
            current_phase=TransitionPhase.PHASE_2_SEMI_SUPERVISED.value,
            next_phase=TransitionPhase.PHASE_3_HISTORICAL.value,
            ready=True,
        )

        if len(df) < PHASE_2_TO_3_MIN_ROWS:
            readiness.blockers.append(
                f"Need ≥ {PHASE_2_TO_3_MIN_ROWS} rows, have {len(df)}."
            )
            readiness.ready = False

        if not val_report.passed:
            readiness.blockers.append(
                f"Validation failed with {val_report.error_count} errors."
            )
            readiness.ready = False

        # Check confidence scores
        if "label_confidence" in df.columns:
            mean_conf = float(df["label_confidence"].mean())
            if mean_conf < PHASE_2_TO_3_MIN_CONFIDENCE:
                readiness.blockers.append(
                    f"Mean label confidence {mean_conf:.2f} < {PHASE_2_TO_3_MIN_CONFIDENCE}."
                )
                readiness.ready = False
            readiness.metrics["mean_confidence"] = round(mean_conf, 4)

        # Check labeled ratio
        if "label_source" in df.columns:
            verified = df["label_source"].isin(
                ["official", "manual", "drrmo", "verified"]
            )
            labeled_ratio = float(verified.mean())
            if labeled_ratio < PHASE_2_TO_3_MIN_LABELED_RATIO:
                readiness.warnings.append(
                    f"Only {labeled_ratio:.0%} of labels are verified "
                    f"(target: {PHASE_2_TO_3_MIN_LABELED_RATIO:.0%})."
                )
            readiness.metrics["verified_label_ratio"] = round(labeled_ratio, 4)

        # High consistency issues → warning
        if not con_report.consistent:
            readiness.warnings.append(
                "Label consistency check flagged high-severity issues."
            )

        readiness.improvements = [
            "Obtain official DRRMO flood records for all target years.",
            "Cross-validate pseudo-labels against official records.",
            "Add spatial features (barangay elevation, drainage scores).",
            "Ensure date and barangay columns are complete.",
        ]

        readiness.metrics.update(
            {
                "row_count": len(df),
                "validation_passed": val_report.passed,
                "consistency_issues": con_report.total_issues,
            }
        )

        return readiness

    def _assess_phase3(
        self,
        df: pd.DataFrame,
        val_report: ValidationReport,
        con_report: ConsistencyReport,
    ) -> PhaseReadiness:
        """Phase 3 (Historical) – final quality gate."""
        readiness = PhaseReadiness(
            current_phase=TransitionPhase.PHASE_3_HISTORICAL.value,
            next_phase=None,  # Final phase
            ready=True,
        )

        if len(df) < PHASE_3_MIN_ROWS:
            readiness.blockers.append(
                f"Need ≥ {PHASE_3_MIN_ROWS} rows, have {len(df)}."
            )
            readiness.ready = False

        if not val_report.passed:
            readiness.blockers.append(
                f"Validation failed with {val_report.error_count} errors."
            )
            readiness.ready = False

        # Check temporal breadth
        if "date" in df.columns:
            try:
                dates = pd.to_datetime(df["date"], errors="coerce").dropna()
                unique_months = dates.dt.to_period("M").nunique()
                readiness.metrics["unique_months"] = int(unique_months)
                if unique_months < PHASE_3_MIN_MONTHS:
                    readiness.warnings.append(
                        f"Only {unique_months} unique months "
                        f"(recommend ≥ {PHASE_3_MIN_MONTHS} for seasonal coverage)."
                    )
            except Exception:
                readiness.warnings.append("Could not parse date column.")

        # Check spatial breadth
        if "barangay" in df.columns:
            n_bar = df["barangay"].nunique()
            readiness.metrics["unique_barangays"] = n_bar
            if n_bar < PHASE_3_MIN_BARANGAYS:
                readiness.warnings.append(
                    f"Only {n_bar} unique barangays "
                    f"(recommend ≥ {PHASE_3_MIN_BARANGAYS})."
                )

        if not con_report.consistent:
            readiness.warnings.append(
                "Label consistency issues remain – resolve before production."
            )

        readiness.improvements = [
            "Dataset is at production quality – proceed with progressive training.",
            "Consider augmenting with ENSO indices and tidal data.",
            "Run full progressive training pipeline (phases 1-8).",
        ]

        readiness.metrics.update(
            {
                "row_count": len(df),
                "validation_passed": val_report.passed,
                "consistency_issues": con_report.total_issues,
            }
        )

        return readiness

    # ------------------------------------------------------------------
    # Phase metadata
    # ------------------------------------------------------------------

    @staticmethod
    def _phase_metadata(phase: TransitionPhase) -> Dict[str, Any]:
        """Return descriptive metadata for human consumption."""
        metadata = {
            TransitionPhase.PHASE_1_SYNTHETIC: {
                "name": "Phase 1 – Synthetic Dataset",
                "description": (
                    "Bootstrap model development with rule-based or "
                    "synthetically generated flood labels. Validates basic "
                    "schema, feature ranges, and target distribution."
                ),
                "data_sources": ["Synthetic generator", "weather-based rules"],
                "key_activities": [
                    "Generate synthetic flood labels using meteorological thresholds",
                    "Validate feature distributions match real-world ranges",
                    "Train baseline model for pseudo-label generation",
                    "Establish validation pipeline and CI checks",
                ],
                "exit_criteria": [
                    f"≥ {PHASE_1_TO_2_MIN_ROWS} training samples",
                    "Dataset passes schema validation",
                    "Both flood and no-flood classes represented",
                    "Baseline model achieves > 0.6 F1 on synthetic test set",
                ],
            },
            TransitionPhase.PHASE_2_SEMI_SUPERVISED: {
                "name": "Phase 2 – Semi-Supervised Learning",
                "description": (
                    "Blend teacher-model pseudo-labels on unlabeled data "
                    "with a growing set of verified/official labels. "
                    "Confidence filtering ensures only high-quality "
                    "pseudo-labels enter the training set."
                ),
                "data_sources": [
                    "Teacher model pseudo-labels",
                    "Partial DRRMO verified labels",
                    "PAGASA weather observations",
                    "Meteostat historical data",
                ],
                "key_activities": [
                    "Generate pseudo-labels with confidence scores",
                    "Filter pseudo-labels below confidence threshold",
                    "Cross-validate pseudo vs. verified labels",
                    "Iteratively retrain teacher with verified corrections",
                    "Monitor label agreement rate between sources",
                ],
                "exit_criteria": [
                    f"≥ {PHASE_2_TO_3_MIN_ROWS} samples",
                    f"Mean label confidence ≥ {PHASE_2_TO_3_MIN_CONFIDENCE}",
                    f"≥ {PHASE_2_TO_3_MIN_LABELED_RATIO:.0%} verified labels",
                    f"Cross-source disagreement ≤ {PHASE_2_TO_3_MAX_CROSS_SOURCE_DISAGREEMENT:.0%}",
                ],
            },
            TransitionPhase.PHASE_3_HISTORICAL: {
                "name": "Phase 3 – Fully Labeled Historical Flood Records",
                "description": (
                    "Training on complete, verified historical flood records "
                    "from the Parañaque CDRRMO crossed with multi-source "
                    "weather data. Final production-quality dataset."
                ),
                "data_sources": [
                    "Official CDRRMO flood records (2022-2025)",
                    "PAGASA weather stations (Port Area, NAIA, Science Garden)",
                    "Meteostat API historical data",
                    "Google Earth Engine satellite data",
                    "WorldTides tidal data",
                    "ENSO climate indices (ONI, SOI)",
                ],
                "key_activities": [
                    "Merge all verified flood records with weather data",
                    "Engineer temporal, spatial, and interaction features",
                    "Run progressive training pipeline (8 phases)",
                    "Deploy ensemble model with calibrated probabilities",
                ],
                "exit_criteria": [
                    f"≥ {PHASE_3_MIN_ROWS} samples",
                    f"≥ {PHASE_3_MIN_MONTHS} months of temporal coverage",
                    f"≥ {PHASE_3_MIN_BARANGAYS} unique barangays",
                    "All label consistency checks pass",
                    "Model F2 ≥ 0.85 on cross-validated test set",
                ],
            },
        }
        return metadata.get(phase, {})


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


def evaluate_dataset_transition(
    df: pd.DataFrame,
    phase: str | TransitionPhase = TransitionPhase.PHASE_1_SYNTHETIC,
    **kwargs: Any,
) -> TransitionReport:
    """One-shot transition evaluation.

    Args:
        df: Dataset to evaluate.
        phase: Transition phase as string or enum.
        **kwargs: Forwarded to :meth:`DatasetTransitionPlan.evaluate`.

    Returns:
        A :class:`TransitionReport`.
    """
    if isinstance(phase, str):
        phase = TransitionPhase(phase)
    plan = DatasetTransitionPlan()
    return plan.evaluate(df, phase, **kwargs)
