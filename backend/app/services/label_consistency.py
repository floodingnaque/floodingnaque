"""
Label Consistency Checking Module for Floodingnaque.

Detects inconsistencies, contradictions and annotation drift across:
  - Spatial labels  (same location, same date → same label)
  - Temporal labels (sudden label flips without weather justification)
  - Cross-source labels (synthetic vs. pseudo vs. official)
  - Meteorological plausibility (flood=1 with 0 mm precipitation)

Designed to work across all three transition phases so that the project
can progressively improve label quality as it moves from synthetic data
to fully labeled historical records.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Physical plausibility thresholds (Metro Manila)
# ---------------------------------------------------------------------------

# If precipitation is below this AND no antecedent rainfall,
# a flood label is suspicious.
DRY_DAY_THRESHOLD_MM = 2.0

# Minimum humidity typically associated with rainfall
MIN_FLOOD_HUMIDITY = 50.0

# Minimum antecedent rainfall (3-day sum) for flood-plausible conditions
MIN_ANTECEDENT_PRECIP_3D = 5.0

# Monsoon months (June-November) where flooding is climatologically expected
MONSOON_MONTHS: Set[int] = {6, 7, 8, 9, 10, 11}


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class InconsistencyType(str, Enum):
    SPATIAL = "spatial"
    TEMPORAL = "temporal"
    CROSS_SOURCE = "cross_source"
    METEOROLOGICAL = "meteorological"
    DEPTH_LABEL_MISMATCH = "depth_label_mismatch"
    DUPLICATE_CONFLICT = "duplicate_conflict"


class InconsistencySeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class LabelInconsistency:
    """A single label-consistency finding."""

    inconsistency_type: InconsistencyType
    severity: InconsistencySeverity
    message: str
    row_indices: List[int] = field(default_factory=list)
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.inconsistency_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "affected_rows": len(self.row_indices),
            "sample_indices": self.row_indices[:10],
            "details": self.details,
        }


@dataclass
class ConsistencyReport:
    """Result of a full label-consistency audit."""

    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    total_rows: int = 0
    consistent: bool = True
    inconsistencies: List[LabelInconsistency] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    def add(self, finding: LabelInconsistency) -> None:
        self.inconsistencies.append(finding)
        if finding.severity in (
            InconsistencySeverity.HIGH,
            InconsistencySeverity.CRITICAL,
        ):
            self.consistent = False

    @property
    def total_issues(self) -> int:
        return len(self.inconsistencies)

    @property
    def affected_rows(self) -> int:
        seen: Set[int] = set()
        for inc in self.inconsistencies:
            seen.update(inc.row_indices)
        return len(seen)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_rows": self.total_rows,
            "consistent": self.consistent,
            "total_issues": self.total_issues,
            "affected_rows": self.affected_rows,
            "summary": self.summary,
            "recommendations": self.recommendations,
            "inconsistencies": [i.to_dict() for i in self.inconsistencies],
        }


# ---------------------------------------------------------------------------
# Core checker
# ---------------------------------------------------------------------------


class LabelConsistencyChecker:
    """Check flood-label consistency across multiple dimensions.

    Usage::

        checker = LabelConsistencyChecker()
        report = checker.check(df)
        print(report.to_dict())
    """

    def __init__(
        self,
        *,
        dry_day_threshold: float = DRY_DAY_THRESHOLD_MM,
        min_flood_humidity: float = MIN_FLOOD_HUMIDITY,
        min_antecedent_precip: float = MIN_ANTECEDENT_PRECIP_3D,
        date_column: str = "date",
        location_columns: Optional[List[str]] = None,
    ) -> None:
        self.dry_day_threshold = dry_day_threshold
        self.min_flood_humidity = min_flood_humidity
        self.min_antecedent_precip = min_antecedent_precip
        self.date_col = date_column
        self.location_cols = location_columns or ["barangay"]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, df: pd.DataFrame) -> ConsistencyReport:
        """Run all consistency checks on *df* and return a report."""
        report = ConsistencyReport(total_rows=len(df))

        if df.empty or "flood" not in df.columns:
            report.recommendations.append(
                "Dataset is empty or missing 'flood' column – nothing to check."
            )
            return report

        self._check_meteorological_plausibility(df, report)
        self._check_depth_label_mismatch(df, report)
        self._check_spatial_consistency(df, report)
        self._check_temporal_consistency(df, report)
        self._check_duplicate_conflicts(df, report)

        # Build summary counts by type
        type_counts: Dict[str, int] = defaultdict(int)
        for inc in report.inconsistencies:
            type_counts[inc.inconsistency_type.value] += 1
        report.summary = dict(type_counts)

        # Auto-generate recommendations
        report.recommendations = self._generate_recommendations(report)

        logger.info(
            "Label consistency %s: rows=%d issues=%d affected=%d",
            "OK" if report.consistent else "ISSUES",
            len(df),
            report.total_issues,
            report.affected_rows,
        )
        return report

    def check_cross_source(
        self,
        source_a: pd.DataFrame,
        source_b: pd.DataFrame,
        *,
        source_a_name: str = "source_a",
        source_b_name: str = "source_b",
        join_on: Optional[List[str]] = None,
    ) -> ConsistencyReport:
        """Compare labels between two datasets (e.g., synthetic vs. official).

        Joins on ``join_on`` columns (default: date + location) and flags
        rows where the flood label disagrees.
        """
        report = ConsistencyReport(
            total_rows=len(source_a) + len(source_b),
        )

        if join_on is None:
            join_on = [self.date_col] + self.location_cols
            join_on = [c for c in join_on if c in source_a.columns and c in source_b.columns]

        if not join_on:
            report.recommendations.append(
                "No common join columns found between the two sources."
            )
            return report

        merged = source_a.merge(
            source_b,
            on=join_on,
            how="inner",
            suffixes=(f"_{source_a_name}", f"_{source_b_name}"),
        )

        if merged.empty:
            report.recommendations.append(
                "No overlapping records between the two sources."
            )
            return report

        col_a = f"flood_{source_a_name}"
        col_b = f"flood_{source_b_name}"

        if col_a not in merged.columns or col_b not in merged.columns:
            report.recommendations.append(
                "Could not find flood columns after merge."
            )
            return report

        disagreements = merged[merged[col_a] != merged[col_b]]
        if len(disagreements) > 0:
            n = len(disagreements)
            pct = n / len(merged) * 100
            report.add(
                LabelInconsistency(
                    inconsistency_type=InconsistencyType.CROSS_SOURCE,
                    severity=(
                        InconsistencySeverity.HIGH
                        if pct > 10
                        else InconsistencySeverity.MEDIUM
                    ),
                    message=(
                        f"{n} label disagreements ({pct:.1f}%) between "
                        f"'{source_a_name}' and '{source_b_name}'."
                    ),
                    row_indices=disagreements.index.tolist()[:100],
                    details={
                        "overlap_size": len(merged),
                        "disagreement_count": n,
                        "disagreement_pct": round(pct, 2),
                    },
                )
            )

        return report

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_meteorological_plausibility(
        self, df: pd.DataFrame, report: ConsistencyReport
    ) -> None:
        """Flag flood=1 under dry, low-humidity conditions."""
        if "precipitation" not in df.columns:
            return

        flood_mask = df["flood"] == 1

        # Dry-day floods (no same-day or antecedent precipitation)
        dry_mask = df["precipitation"] <= self.dry_day_threshold
        antecedent_ok = True

        if "precip_3day_sum" in df.columns:
            antecedent_mask = (
                df["precip_3day_sum"] <= self.min_antecedent_precip
            )
            suspicious = flood_mask & dry_mask & antecedent_mask
            antecedent_ok = False
        else:
            suspicious = flood_mask & dry_mask

        indices = df.index[suspicious].tolist()
        if indices:
            msg = (
                f"{len(indices)} flood labels on dry days "
                f"(precipitation ≤ {self.dry_day_threshold} mm"
            )
            if not antecedent_ok:
                msg += f", 3-day sum ≤ {self.min_antecedent_precip} mm"
            msg += ")."

            report.add(
                LabelInconsistency(
                    inconsistency_type=InconsistencyType.METEOROLOGICAL,
                    severity=InconsistencySeverity.MEDIUM,
                    message=msg,
                    row_indices=indices,
                )
            )

        # Low-humidity floods
        if "humidity" in df.columns:
            low_hum = flood_mask & (df["humidity"] < self.min_flood_humidity)
            low_indices = df.index[low_hum].tolist()
            if low_indices:
                report.add(
                    LabelInconsistency(
                        inconsistency_type=InconsistencyType.METEOROLOGICAL,
                        severity=InconsistencySeverity.LOW,
                        message=(
                            f"{len(low_indices)} flood labels with humidity "
                            f"< {self.min_flood_humidity}% – unusual but possible."
                        ),
                        row_indices=low_indices,
                    )
                )

        # Non-monsoon floods without typhoon
        if "month" in df.columns:
            non_monsoon = flood_mask & ~df["month"].isin(MONSOON_MONTHS)
            if "is_typhoon" in df.columns:
                non_monsoon = non_monsoon & (df["is_typhoon"] != 1)
            non_monsoon_idx = df.index[non_monsoon].tolist()
            if non_monsoon_idx:
                report.add(
                    LabelInconsistency(
                        inconsistency_type=InconsistencyType.METEOROLOGICAL,
                        severity=InconsistencySeverity.LOW,
                        message=(
                            f"{len(non_monsoon_idx)} flood labels outside monsoon season "
                            "(without typhoon flag) – verify manually."
                        ),
                        row_indices=non_monsoon_idx,
                    )
                )

    def _check_depth_label_mismatch(
        self, df: pd.DataFrame, report: ConsistencyReport
    ) -> None:
        """Flag records where flood_depth > 0 but flood=0, or vice versa."""
        depth_col = None
        for candidate in ("flood_depth_cm", "flood_depth"):
            if candidate in df.columns:
                depth_col = candidate
                break

        if depth_col is None:
            return

        if pd.api.types.is_numeric_dtype(df[depth_col]):
            # flood=0 but depth > 0
            false_neg = (df["flood"] == 0) & (df[depth_col] > 0)
            idx_fn = df.index[false_neg].tolist()
            if idx_fn:
                report.add(
                    LabelInconsistency(
                        inconsistency_type=InconsistencyType.DEPTH_LABEL_MISMATCH,
                        severity=InconsistencySeverity.HIGH,
                        message=(
                            f"{len(idx_fn)} rows have {depth_col} > 0 but flood=0. "
                            "These are likely mislabeled."
                        ),
                        row_indices=idx_fn,
                    )
                )

            # flood=1 but depth = 0
            false_pos = (df["flood"] == 1) & (df[depth_col] == 0)
            idx_fp = df.index[false_pos].tolist()
            if idx_fp:
                report.add(
                    LabelInconsistency(
                        inconsistency_type=InconsistencyType.DEPTH_LABEL_MISMATCH,
                        severity=InconsistencySeverity.MEDIUM,
                        message=(
                            f"{len(idx_fp)} rows have flood=1 but {depth_col}=0. "
                            "Missing depth data or labeling error?"
                        ),
                        row_indices=idx_fp,
                    )
                )

    def _check_spatial_consistency(
        self, df: pd.DataFrame, report: ConsistencyReport
    ) -> None:
        """Same date + same location → labels should agree."""
        loc_cols = [c for c in self.location_cols if c in df.columns]
        if not loc_cols or self.date_col not in df.columns:
            return

        group_cols = [self.date_col] + loc_cols
        grouped = df.groupby(group_cols, dropna=False)["flood"]

        conflict_indices: List[int] = []
        for _key, group in grouped:
            unique_labels = group.dropna().unique()
            if len(unique_labels) > 1:
                conflict_indices.extend(group.index.tolist())

        if conflict_indices:
            report.add(
                LabelInconsistency(
                    inconsistency_type=InconsistencyType.SPATIAL,
                    severity=InconsistencySeverity.HIGH,
                    message=(
                        f"{len(conflict_indices)} rows with conflicting flood "
                        f"labels for the same date + location."
                    ),
                    row_indices=conflict_indices,
                )
            )

    def _check_temporal_consistency(
        self, df: pd.DataFrame, report: ConsistencyReport
    ) -> None:
        """Flag sudden label flips for the same location (0→1→0 in 1 day
        without corresponding weather change)."""
        if self.date_col not in df.columns:
            return

        loc_cols = [c for c in self.location_cols if c in df.columns]
        if not loc_cols:
            # Fall back to whole-dataset temporal check
            self._check_temporal_global(df, report)
            return

        df_sorted = df.copy()
        try:
            df_sorted["_parsed_date"] = pd.to_datetime(
                df_sorted[self.date_col], errors="coerce"
            )
        except Exception:
            return

        df_sorted = df_sorted.dropna(subset=["_parsed_date"])
        if df_sorted.empty:
            return

        df_sorted = df_sorted.sort_values(loc_cols + ["_parsed_date"])

        flip_indices: List[int] = []
        for _loc, grp in df_sorted.groupby(loc_cols, dropna=False):
            if len(grp) < 3:
                continue
            labels = grp["flood"].values
            dates = grp["_parsed_date"].values
            precip = (
                grp["precipitation"].values
                if "precipitation" in grp.columns
                else None
            )

            for i in range(1, len(labels) - 1):
                # Check for 0→1→0 or 1→0→1 pattern
                if labels[i - 1] == labels[i + 1] and labels[i] != labels[i - 1]:
                    # Only flag if close in time and no big weather change
                    gap_before = (dates[i] - dates[i - 1]) / np.timedelta64(1, "D")
                    gap_after = (dates[i + 1] - dates[i]) / np.timedelta64(1, "D")
                    if gap_before <= 2 and gap_after <= 2:
                        if precip is not None:
                            # If precipitation didn't change much, suspicious
                            avg_surround = (precip[i - 1] + precip[i + 1]) / 2
                            if abs(precip[i] - avg_surround) < 10:
                                flip_indices.append(int(grp.index[i]))
                        else:
                            flip_indices.append(int(grp.index[i]))

        if flip_indices:
            report.add(
                LabelInconsistency(
                    inconsistency_type=InconsistencyType.TEMPORAL,
                    severity=InconsistencySeverity.MEDIUM,
                    message=(
                        f"{len(flip_indices)} suspicious single-day label flips "
                        "without corresponding weather changes."
                    ),
                    row_indices=flip_indices,
                )
            )

    def _check_temporal_global(
        self, df: pd.DataFrame, report: ConsistencyReport
    ) -> None:
        """Simplified temporal check without location grouping."""
        try:
            dates = pd.to_datetime(df[self.date_col], errors="coerce")
        except Exception:
            return

        df_sorted = df.loc[dates.notna()].sort_values(self.date_col)
        if len(df_sorted) < 3:
            return

        labels = df_sorted["flood"].values
        flips = 0
        for i in range(1, len(labels)):
            if labels[i] != labels[i - 1]:
                flips += 1

        flip_rate = flips / max(len(labels) - 1, 1)
        if flip_rate > 0.6:
            report.add(
                LabelInconsistency(
                    inconsistency_type=InconsistencyType.TEMPORAL,
                    severity=InconsistencySeverity.MEDIUM,
                    message=(
                        f"High label flip rate ({flip_rate:.0%}). Labels may be noisy "
                        "or the sort order may be wrong."
                    ),
                    details={"flip_rate": round(flip_rate, 3)},
                )
            )

    def _check_duplicate_conflicts(
        self, df: pd.DataFrame, report: ConsistencyReport
    ) -> None:
        """Find near-duplicate rows with conflicting labels."""
        feature_cols = [
            c
            for c in ["temperature", "humidity", "precipitation", "month"]
            if c in df.columns
        ]
        if not feature_cols:
            return

        # Group by feature values and check for label conflicts
        grouped = df.groupby(feature_cols, dropna=False)["flood"]
        conflict_indices: List[int] = []
        for _key, group in grouped:
            if len(group) < 2:
                continue
            unique_labels = group.dropna().unique()
            if len(unique_labels) > 1:
                conflict_indices.extend(group.index.tolist())

        if conflict_indices:
            report.add(
                LabelInconsistency(
                    inconsistency_type=InconsistencyType.DUPLICATE_CONFLICT,
                    severity=InconsistencySeverity.MEDIUM,
                    message=(
                        f"{len(conflict_indices)} rows with identical features but "
                        "conflicting flood labels."
                    ),
                    row_indices=conflict_indices,
                )
            )

    # ------------------------------------------------------------------
    # Recommendation engine
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_recommendations(report: ConsistencyReport) -> List[str]:
        """Auto-generate actionable recommendations from findings."""
        recs: List[str] = []
        type_counts = report.summary

        if type_counts.get("meteorological", 0) > 0:
            recs.append(
                "Review flood labels on dry days – cross-reference with "
                "official DRRMO records or satellite imagery."
            )

        if type_counts.get("depth_label_mismatch", 0) > 0:
            recs.append(
                "Reconcile flood_depth and flood columns – consider deriving "
                "the binary flood label from depth (depth > 0 → flood=1)."
            )

        if type_counts.get("spatial", 0) > 0:
            recs.append(
                "Resolve spatial conflicts (same date + location, different "
                "labels). Prefer official DRRMO records."
            )

        if type_counts.get("temporal", 0) > 0:
            recs.append(
                "Investigate rapid label flips – may indicate data entry "
                "errors or time-zone mismatches."
            )

        if type_counts.get("cross_source", 0) > 0:
            recs.append(
                "Label disagreements between sources detected. Create a "
                "reconciliation mapping and prefer higher-confidence source."
            )

        if type_counts.get("duplicate_conflict", 0) > 0:
            recs.append(
                "Identical feature rows with different labels found. "
                "Add distinguishing features (e.g. location, date) or "
                "resolve via majority vote."
            )

        if not recs:
            recs.append("No label inconsistencies detected – labels look clean.")

        return recs


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


def check_label_consistency(
    df: pd.DataFrame,
    **kwargs: Any,
) -> ConsistencyReport:
    """One-shot label consistency check.

    Args:
        df: DataFrame with at least a ``flood`` column.
        **kwargs: Forwarded to :class:`LabelConsistencyChecker`.

    Returns:
        A :class:`ConsistencyReport`.
    """
    checker = LabelConsistencyChecker(**kwargs)
    return checker.check(df)


def compare_label_sources(
    source_a: pd.DataFrame,
    source_b: pd.DataFrame,
    **kwargs: Any,
) -> ConsistencyReport:
    """Compare flood labels between two data sources.

    Args:
        source_a: First dataset (e.g. synthetic).
        source_b: Second dataset (e.g. official records).
        **kwargs: Forwarded to :meth:`LabelConsistencyChecker.check_cross_source`.

    Returns:
        A :class:`ConsistencyReport`.
    """
    checker = LabelConsistencyChecker()
    return checker.check_cross_source(source_a, source_b, **kwargs)
