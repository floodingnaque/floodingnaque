"""
Dataset Validation Pipeline for Floodingnaque.

Validates datasets across all three transition phases:
  Phase 1 – Synthetic dataset
  Phase 2 – Semi-supervised learning (mixed real + pseudo-labels)
  Phase 3 – Fully labeled historical flood records

Each phase applies domain-aware checks (schema, ranges, distributions,
target-class balance, temporal coverage) so that downstream training
pipelines always receive clean, trustworthy data.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants – aligned with config/training_config.yaml
# ---------------------------------------------------------------------------

FEATURE_RANGES: Dict[str, Dict[str, Any]] = {
    "temperature": {"min": 15.0, "max": 45.0, "unit": "°C"},
    "humidity": {"min": 0.0, "max": 100.0, "unit": "%"},
    "precipitation": {"min": 0.0, "max": 500.0, "unit": "mm"},
    "is_monsoon_season": {"values": [0, 1]},
    "month": {"min": 1, "max": 12},
    "precip_3day_sum": {"min": 0.0, "max": 1000.0, "unit": "mm"},
    "precip_7day_sum": {"min": 0.0, "max": 1500.0, "unit": "mm"},
    "wind_speed": {"min": 0.0, "max": 80.0, "unit": "m/s"},
    "flood": {"values": [0, 1]},
    "flood_severity": {"min": 0, "max": 3},
}

# Minimum expected columns for each phase
PHASE_REQUIRED_COLUMNS: Dict[str, List[str]] = {
    "synthetic": [
        "temperature",
        "humidity",
        "precipitation",
        "flood",
    ],
    "semi_supervised": [
        "temperature",
        "humidity",
        "precipitation",
        "flood",
        "is_monsoon_season",
        "month",
    ],
    "historical": [
        "temperature",
        "humidity",
        "precipitation",
        "flood",
        "is_monsoon_season",
        "month",
        "date",
        "barangay",
    ],
}


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class DatasetPhase(str, Enum):
    """Transition phases for the real-dataset roadmap."""

    SYNTHETIC = "synthetic"
    SEMI_SUPERVISED = "semi_supervised"
    HISTORICAL = "historical"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """A single validation finding."""

    check: str
    severity: Severity
    message: str
    column: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check": self.check,
            "severity": self.severity.value,
            "message": self.message,
            "column": self.column,
            "details": self.details,
        }


@dataclass
class ValidationReport:
    """Aggregated result of a full validation run."""

    phase: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    passed: bool = True
    total_rows: int = 0
    total_columns: int = 0
    issues: List[ValidationIssue] = field(default_factory=list)
    data_hash: Optional[str] = None
    statistics: Dict[str, Any] = field(default_factory=dict)

    def add_issue(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)
        if issue.severity in (Severity.ERROR, Severity.CRITICAL):
            self.passed = False

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity in (Severity.ERROR, Severity.CRITICAL))

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "timestamp": self.timestamp,
            "passed": self.passed,
            "total_rows": self.total_rows,
            "total_columns": self.total_columns,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "data_hash": self.data_hash,
            "statistics": self.statistics,
            "issues": [i.to_dict() for i in self.issues],
        }


# ---------------------------------------------------------------------------
# Core validator
# ---------------------------------------------------------------------------


class DatasetValidator:
    """Validates a pandas DataFrame according to its transition phase.

    Usage::

        validator = DatasetValidator(phase=DatasetPhase.SYNTHETIC)
        report = validator.validate(df)
        if not report.passed:
            for issue in report.issues:
                print(issue)
    """

    def __init__(
        self,
        phase: DatasetPhase = DatasetPhase.SYNTHETIC,
        *,
        custom_ranges: Optional[Dict[str, Dict[str, Any]]] = None,
        max_missing_ratio: float = 0.1,
        min_samples: int = 50,
        max_class_imbalance_ratio: float = 20.0,
    ) -> None:
        self.phase = phase
        self.feature_ranges = {**FEATURE_RANGES, **(custom_ranges or {})}
        self.max_missing_ratio = max_missing_ratio
        self.min_samples = min_samples
        self.max_class_imbalance_ratio = max_class_imbalance_ratio

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, df: pd.DataFrame) -> ValidationReport:
        """Run the full validation pipeline and return a report."""
        report = ValidationReport(
            phase=self.phase.value,
            total_rows=len(df),
            total_columns=len(df.columns),
        )

        if df.empty:
            report.add_issue(
                ValidationIssue(
                    check="empty_dataset",
                    severity=Severity.CRITICAL,
                    message="Dataset is empty – no rows to validate.",
                )
            )
            return report

        # Compute reproducibility hash
        report.data_hash = self._compute_hash(df)

        # Run checks in sequence; each appends issues to the report.
        self._check_schema(df, report)
        self._check_duplicates(df, report)
        self._check_missing_values(df, report)
        self._check_data_types(df, report)
        self._check_value_ranges(df, report)
        self._check_target_distribution(df, report)
        self._check_minimum_samples(df, report)
        self._check_feature_variance(df, report)

        # Phase-specific deep checks
        if self.phase == DatasetPhase.SEMI_SUPERVISED:
            self._check_confidence_scores(df, report)
        if self.phase == DatasetPhase.HISTORICAL:
            self._check_temporal_coverage(df, report)
            self._check_spatial_coverage(df, report)

        # Summary statistics (merge, don't overwrite phase-specific stats)
        report.statistics.update(self._compute_statistics(df))

        logger.info(
            "Validation %s: phase=%s rows=%d errors=%d warnings=%d",
            "PASSED" if report.passed else "FAILED",
            self.phase.value,
            len(df),
            report.error_count,
            report.warning_count,
        )
        return report

    def validate_file(self, path: str | Path, **read_kwargs: Any) -> ValidationReport:
        """Convenience helper: read a CSV and validate it."""
        path = Path(path)
        if not path.exists():
            report = ValidationReport(phase=self.phase.value)
            report.add_issue(
                ValidationIssue(
                    check="file_not_found",
                    severity=Severity.CRITICAL,
                    message=f"File not found: {path}",
                )
            )
            return report
        df = pd.read_csv(path, **read_kwargs)
        return self.validate(df)

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_schema(self, df: pd.DataFrame, report: ValidationReport) -> None:
        """Verify required columns are present for the current phase."""
        required = set(PHASE_REQUIRED_COLUMNS.get(self.phase.value, []))
        present = set(df.columns)
        missing = required - present
        if missing:
            report.add_issue(
                ValidationIssue(
                    check="missing_columns",
                    severity=Severity.ERROR,
                    message=f"Missing required columns for phase '{self.phase.value}': {sorted(missing)}",
                    details={"missing": sorted(missing)},
                )
            )

        # Warn about unexpected columns (nice-to-have)
        expected = set(PHASE_REQUIRED_COLUMNS.get(self.phase.value, []))
        extra = present - expected
        if extra and len(extra) < len(present):
            report.add_issue(
                ValidationIssue(
                    check="extra_columns",
                    severity=Severity.INFO,
                    message=f"{len(extra)} extra columns beyond required schema: {sorted(extra)[:5]}{'…' if len(extra) > 5 else ''}",
                    details={"count": len(extra)},
                )
            )

    def _check_duplicates(self, df: pd.DataFrame, report: ValidationReport) -> None:
        """Flag exact duplicate rows."""
        dup_count = int(df.duplicated().sum())
        if dup_count > 0:
            dup_ratio = dup_count / len(df)
            sev = Severity.ERROR if dup_ratio > 0.1 else Severity.WARNING
            report.add_issue(
                ValidationIssue(
                    check="duplicate_rows",
                    severity=sev,
                    message=f"{dup_count} duplicate rows ({dup_ratio:.1%} of dataset).",
                    details={"count": dup_count, "ratio": round(dup_ratio, 4)},
                )
            )

    def _check_missing_values(self, df: pd.DataFrame, report: ValidationReport) -> None:
        """Check per-column missing-value ratio."""
        for col in df.columns:
            missing = int(df[col].isna().sum())
            if missing == 0:
                continue
            ratio = missing / len(df)
            sev = Severity.ERROR if ratio > self.max_missing_ratio else Severity.WARNING
            report.add_issue(
                ValidationIssue(
                    check="missing_values",
                    severity=sev,
                    message=f"Column '{col}' has {missing} missing values ({ratio:.1%}).",
                    column=col,
                    details={"count": missing, "ratio": round(ratio, 4)},
                )
            )

    def _check_data_types(self, df: pd.DataFrame, report: ValidationReport) -> None:
        """Ensure numeric features are actually numeric."""
        numeric_expected = {
            "temperature",
            "humidity",
            "precipitation",
            "wind_speed",
            "flood",
            "flood_severity",
            "month",
            "is_monsoon_season",
        }
        for col in numeric_expected & set(df.columns):
            if not pd.api.types.is_numeric_dtype(df[col]):
                report.add_issue(
                    ValidationIssue(
                        check="wrong_dtype",
                        severity=Severity.ERROR,
                        message=f"Column '{col}' should be numeric but has dtype '{df[col].dtype}'.",
                        column=col,
                    )
                )

    def _check_value_ranges(self, df: pd.DataFrame, report: ValidationReport) -> None:
        """Validate that values fall within physically plausible ranges."""
        for col, spec in self.feature_ranges.items():
            if col not in df.columns:
                continue

            series = df[col].dropna()
            if series.empty:
                continue

            # Categorical / discrete values
            if "values" in spec:
                invalid_mask = ~series.isin(spec["values"])
                n_invalid = int(invalid_mask.sum())
                if n_invalid > 0:
                    bad_sample = series[invalid_mask].unique()[:5].tolist()
                    report.add_issue(
                        ValidationIssue(
                            check="invalid_values",
                            severity=Severity.ERROR,
                            message=f"Column '{col}' has {n_invalid} values outside {spec['values']}.",
                            column=col,
                            details={
                                "invalid_count": n_invalid,
                                "sample": bad_sample,
                            },
                        )
                    )

            # Continuous ranges – skip if column is not numeric
            if not pd.api.types.is_numeric_dtype(series):
                continue

            if "min" in spec:
                below = int((series < spec["min"]).sum())
                if below:
                    report.add_issue(
                        ValidationIssue(
                            check="out_of_range",
                            severity=Severity.WARNING,
                            message=f"Column '{col}': {below} values below minimum {spec['min']}.",
                            column=col,
                            details={
                                "count": below,
                                "actual_min": float(series.min()),
                            },
                        )
                    )
            if "max" in spec:
                above = int((series > spec["max"]).sum())
                if above:
                    report.add_issue(
                        ValidationIssue(
                            check="out_of_range",
                            severity=Severity.WARNING,
                            message=f"Column '{col}': {above} values above maximum {spec['max']}.",
                            column=col,
                            details={
                                "count": above,
                                "actual_max": float(series.max()),
                            },
                        )
                    )

    def _check_target_distribution(self, df: pd.DataFrame, report: ValidationReport) -> None:
        """Ensure the flood target column is reasonably distributed."""
        if "flood" not in df.columns:
            return
        counts = df["flood"].value_counts()
        if len(counts) < 2:
            report.add_issue(
                ValidationIssue(
                    check="target_single_class",
                    severity=Severity.ERROR,
                    message="Target 'flood' has only one class – model cannot learn.",
                    column="flood",
                    details={"value_counts": counts.to_dict()},
                )
            )
            return

        majority = int(counts.max())
        minority = int(counts.min())
        ratio = majority / max(minority, 1)
        if ratio > self.max_class_imbalance_ratio:
            report.add_issue(
                ValidationIssue(
                    check="class_imbalance",
                    severity=Severity.WARNING,
                    message=(
                        f"Severe class imbalance: majority/minority ratio = {ratio:.1f}:1 "
                        f"(threshold {self.max_class_imbalance_ratio}:1)."
                    ),
                    column="flood",
                    details={
                        "ratio": round(ratio, 2),
                        "value_counts": counts.to_dict(),
                    },
                )
            )

    def _check_minimum_samples(self, df: pd.DataFrame, report: ValidationReport) -> None:
        """Warn if the dataset is too small for reliable training."""
        if len(df) < self.min_samples:
            report.add_issue(
                ValidationIssue(
                    check="insufficient_samples",
                    severity=Severity.WARNING,
                    message=(
                        f"Dataset has {len(df)} rows, below minimum {self.min_samples} "
                        f"for phase '{self.phase.value}'."
                    ),
                    details={
                        "count": len(df),
                        "minimum": self.min_samples,
                    },
                )
            )

    def _check_feature_variance(self, df: pd.DataFrame, report: ValidationReport) -> None:
        """Flag numeric features with zero variance (constant columns)."""
        for col in df.select_dtypes(include=[np.number]).columns:
            if df[col].nunique(dropna=True) <= 1:
                report.add_issue(
                    ValidationIssue(
                        check="zero_variance",
                        severity=Severity.WARNING,
                        message=f"Column '{col}' has zero variance (constant value).",
                        column=col,
                    )
                )

    # Phase-specific ----------------------------------------------------------

    def _check_confidence_scores(self, df: pd.DataFrame, report: ValidationReport) -> None:
        """Semi-supervised phase: validate pseudo-label confidence scores."""
        if "label_confidence" not in df.columns:
            report.add_issue(
                ValidationIssue(
                    check="missing_confidence",
                    severity=Severity.WARNING,
                    message="Semi-supervised data should include 'label_confidence' column.",
                )
            )
            return

        conf = df["label_confidence"].dropna()
        out_of_range = int(((conf < 0.0) | (conf > 1.0)).sum())
        if out_of_range:
            report.add_issue(
                ValidationIssue(
                    check="confidence_range",
                    severity=Severity.ERROR,
                    message=f"{out_of_range} label_confidence values outside [0, 1].",
                    column="label_confidence",
                )
            )

        low_conf_ratio = float((conf < 0.5).mean())
        if low_conf_ratio > 0.5:
            report.add_issue(
                ValidationIssue(
                    check="low_confidence_labels",
                    severity=Severity.WARNING,
                    message=(
                        f"{low_conf_ratio:.0%} of pseudo-labels have confidence < 0.5. "
                        "Consider raising the threshold."
                    ),
                    column="label_confidence",
                )
            )

        # Check label source column
        if "label_source" in df.columns:
            sources = df["label_source"].value_counts().to_dict()
            report.statistics["label_sources"] = sources

    def _check_temporal_coverage(self, df: pd.DataFrame, report: ValidationReport) -> None:
        """Historical phase: verify date range and coverage."""
        if "date" not in df.columns:
            return

        try:
            dates = pd.to_datetime(df["date"], errors="coerce")
        except Exception:
            report.add_issue(
                ValidationIssue(
                    check="date_parse_error",
                    severity=Severity.ERROR,
                    message="Could not parse 'date' column.",
                    column="date",
                )
            )
            return

        valid_dates = dates.dropna()
        if valid_dates.empty:
            report.add_issue(
                ValidationIssue(
                    check="no_valid_dates",
                    severity=Severity.ERROR,
                    message="No parseable dates in 'date' column.",
                    column="date",
                )
            )
            return

        date_range_days = (valid_dates.max() - valid_dates.min()).days
        unique_months = valid_dates.dt.to_period("M").nunique()

        report.statistics["date_range"] = {
            "start": str(valid_dates.min().date()),
            "end": str(valid_dates.max().date()),
            "span_days": date_range_days,
            "unique_months": int(unique_months),
        }

        # Warn if coverage is thin
        if unique_months < 6:
            report.add_issue(
                ValidationIssue(
                    check="sparse_temporal_coverage",
                    severity=Severity.WARNING,
                    message=(
                        f"Only {unique_months} unique months in historical data. "
                        "Consider expanding time range for seasonal patterns."
                    ),
                    column="date",
                )
            )

    def _check_spatial_coverage(self, df: pd.DataFrame, report: ValidationReport) -> None:
        """Historical phase: verify barangay / location coverage."""
        if "barangay" not in df.columns:
            return

        n_barangays = df["barangay"].nunique()
        report.statistics["unique_barangays"] = n_barangays

        if n_barangays < 3:
            report.add_issue(
                ValidationIssue(
                    check="sparse_spatial_coverage",
                    severity=Severity.WARNING,
                    message=(f"Only {n_barangays} unique barangays. " "Spatial generalization may be poor."),
                    column="barangay",
                )
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_hash(df: pd.DataFrame) -> str:
        """SHA-256 of the DataFrame content for reproducibility tracking."""
        raw = pd.util.hash_pandas_object(df).values.tobytes()
        return hashlib.sha256(raw).hexdigest()[:16]

    @staticmethod
    def _compute_statistics(df: pd.DataFrame) -> Dict[str, Any]:
        """Collect summary statistics for the report."""
        stats: Dict[str, Any] = {
            "shape": list(df.shape),
            "columns": list(df.columns),
        }

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols:
            desc = df[numeric_cols].describe().to_dict()
            # Trim to reduce payload
            stats["numeric_summary"] = {col: {k: round(v, 4) for k, v in vals.items()} for col, vals in desc.items()}

        if "flood" in df.columns:
            stats["target_distribution"] = df["flood"].value_counts().to_dict()

        return stats


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


def validate_dataset(
    df: pd.DataFrame,
    phase: str | DatasetPhase = DatasetPhase.SYNTHETIC,
    **kwargs: Any,
) -> ValidationReport:
    """One-shot validation entry point.

    Args:
        df: The DataFrame to validate.
        phase: One of ``"synthetic"``, ``"semi_supervised"``, ``"historical"``
              or a :class:`DatasetPhase` enum member.
        **kwargs: Forwarded to :class:`DatasetValidator`.

    Returns:
        A :class:`ValidationReport`.
    """
    if isinstance(phase, str):
        phase = DatasetPhase(phase)
    validator = DatasetValidator(phase=phase, **kwargs)
    return validator.validate(df)
