"""
Unit tests for dataset_validation, label_consistency, and dataset_transition.

Tests the three-phase Real Dataset Transition Plan:
  Phase 1 – Synthetic dataset
  Phase 2 – Semi-supervised learning
  Phase 3 – Fully labeled historical flood records
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.services.dataset_validation import (
    DatasetPhase,
    DatasetValidator,
    Severity,
    ValidationReport,
    validate_dataset,
)
from app.services.label_consistency import (
    ConsistencyReport,
    InconsistencyType,
    LabelConsistencyChecker,
    check_label_consistency,
    compare_label_sources,
)
from app.services.dataset_transition import (
    DatasetTransitionPlan,
    TransitionPhase,
    evaluate_dataset_transition,
)


# =====================================================================
# Fixtures
# =====================================================================


@pytest.fixture
def synthetic_df() -> pd.DataFrame:
    """Minimal synthetic dataset (Phase 1)."""
    np.random.seed(42)
    n = 100
    return pd.DataFrame(
        {
            "temperature": np.random.uniform(20, 38, n),
            "humidity": np.random.uniform(40, 95, n),
            "precipitation": np.random.uniform(0, 150, n),
            "wind_speed": np.random.uniform(0, 25, n),
            "flood": np.random.choice([0, 1], n, p=[0.7, 0.3]),
        }
    )


@pytest.fixture
def semi_supervised_df() -> pd.DataFrame:
    """Semi-supervised dataset with confidence scores (Phase 2)."""
    np.random.seed(42)
    n = 200
    return pd.DataFrame(
        {
            "temperature": np.random.uniform(22, 36, n),
            "humidity": np.random.uniform(50, 98, n),
            "precipitation": np.random.uniform(0, 200, n),
            "is_monsoon_season": np.random.choice([0, 1], n),
            "month": np.random.randint(1, 13, n),
            "flood": np.random.choice([0, 1], n, p=[0.65, 0.35]),
            "label_confidence": np.random.uniform(0.3, 1.0, n),
            "label_source": np.random.choice(
                ["pseudo", "official", "manual"], n, p=[0.6, 0.25, 0.15]
            ),
        }
    )


@pytest.fixture
def historical_df() -> pd.DataFrame:
    """Fully labeled historical dataset (Phase 3)."""
    np.random.seed(42)
    n = 300
    dates = pd.date_range("2022-01-01", periods=n, freq="D")
    barangays = np.random.choice(
        ["San Isidro", "La Huerta", "Tambo", "BF Homes", "Moonwalk"], n
    )
    return pd.DataFrame(
        {
            "temperature": np.random.uniform(24, 35, n),
            "humidity": np.random.uniform(55, 98, n),
            "precipitation": np.random.uniform(0, 120, n),
            "is_monsoon_season": [
                1 if d.month in range(6, 12) else 0 for d in dates
            ],
            "month": [d.month for d in dates],
            "date": [str(d.date()) for d in dates],
            "barangay": barangays,
            "flood": np.random.choice([0, 1], n, p=[0.6, 0.4]),
            "flood_depth_cm": np.random.choice(
                [0, 0, 0, 8, 15, 48, 100], n
            ),
        }
    )


# =====================================================================
# DatasetValidation tests
# =====================================================================


class TestDatasetValidation:
    """Tests for the DatasetValidator."""

    def test_synthetic_valid(self, synthetic_df: pd.DataFrame) -> None:
        report = validate_dataset(synthetic_df, phase="synthetic")
        assert isinstance(report, ValidationReport)
        assert report.total_rows == 100
        assert report.data_hash is not None

    def test_empty_dataset(self) -> None:
        report = validate_dataset(pd.DataFrame(), phase="synthetic")
        assert not report.passed
        assert any(i.check == "empty_dataset" for i in report.issues)

    def test_missing_columns_error(self) -> None:
        df = pd.DataFrame({"temperature": [25.0], "humidity": [70.0]})
        report = validate_dataset(df, phase="synthetic")
        missing_issues = [i for i in report.issues if i.check == "missing_columns"]
        assert len(missing_issues) == 1
        assert "precipitation" in missing_issues[0].message

    def test_missing_values_warning(self, synthetic_df: pd.DataFrame) -> None:
        df = synthetic_df.copy()
        df.loc[0:4, "temperature"] = np.nan
        report = validate_dataset(df, phase="synthetic")
        mv_issues = [
            i for i in report.issues
            if i.check == "missing_values" and i.column == "temperature"
        ]
        assert len(mv_issues) == 1

    def test_out_of_range_values(self, synthetic_df: pd.DataFrame) -> None:
        df = synthetic_df.copy()
        df.loc[0, "temperature"] = 100.0  # above max 45
        report = validate_dataset(df, phase="synthetic")
        oor = [
            i for i in report.issues
            if i.check == "out_of_range" and i.column == "temperature"
        ]
        assert len(oor) >= 1

    def test_invalid_flood_values(self) -> None:
        df = pd.DataFrame(
            {
                "temperature": [28.0, 30.0],
                "humidity": [70.0, 80.0],
                "precipitation": [10.0, 50.0],
                "flood": [0, 5],  # 5 is invalid
            }
        )
        report = validate_dataset(df, phase="synthetic")
        bad = [
            i for i in report.issues
            if i.check == "invalid_values" and i.column == "flood"
        ]
        assert len(bad) == 1

    def test_single_class_target(self) -> None:
        df = pd.DataFrame(
            {
                "temperature": [28.0] * 10,
                "humidity": [70.0] * 10,
                "precipitation": [10.0] * 10,
                "flood": [0] * 10,
            }
        )
        report = validate_dataset(df, phase="synthetic")
        single = [i for i in report.issues if i.check == "target_single_class"]
        assert len(single) == 1

    def test_class_imbalance_warning(self) -> None:
        df = pd.DataFrame(
            {
                "temperature": [28.0] * 100,
                "humidity": [70.0] * 100,
                "precipitation": [10.0] * 100,
                "flood": [0] * 98 + [1] * 2,
            }
        )
        report = validate_dataset(
            df, phase="synthetic", max_class_imbalance_ratio=10.0
        )
        imb = [i for i in report.issues if i.check == "class_imbalance"]
        assert len(imb) == 1

    def test_zero_variance_warning(self) -> None:
        df = pd.DataFrame(
            {
                "temperature": [25.0] * 50,
                "humidity": [70.0] * 50,
                "precipitation": [0.0] * 50,
                "flood": [0] * 25 + [1] * 25,
            }
        )
        report = validate_dataset(df, phase="synthetic")
        zv = [i for i in report.issues if i.check == "zero_variance"]
        assert len(zv) >= 1

    def test_duplicate_rows_warning(self, synthetic_df: pd.DataFrame) -> None:
        df = pd.concat([synthetic_df, synthetic_df.iloc[:5]], ignore_index=True)
        report = validate_dataset(df, phase="synthetic")
        dup = [i for i in report.issues if i.check == "duplicate_rows"]
        assert len(dup) == 1

    def test_wrong_dtype_error(self) -> None:
        df = pd.DataFrame(
            {
                "temperature": ["hot", "cold"],
                "humidity": [70.0, 80.0],
                "precipitation": [10.0, 20.0],
                "flood": [0, 1],
            }
        )
        report = validate_dataset(df, phase="synthetic")
        dtype_issues = [
            i for i in report.issues if i.check == "wrong_dtype"
        ]
        assert len(dtype_issues) == 1

    def test_semi_supervised_confidence_check(
        self, semi_supervised_df: pd.DataFrame
    ) -> None:
        report = validate_dataset(semi_supervised_df, phase="semi_supervised")
        assert isinstance(report, ValidationReport)

    def test_semi_supervised_missing_confidence(self) -> None:
        df = pd.DataFrame(
            {
                "temperature": [28.0] * 50,
                "humidity": [70.0] * 50,
                "precipitation": [10.0] * 50,
                "is_monsoon_season": [1] * 50,
                "month": [7] * 50,
                "flood": [0] * 25 + [1] * 25,
            }
        )
        report = validate_dataset(df, phase="semi_supervised")
        conf = [i for i in report.issues if i.check == "missing_confidence"]
        assert len(conf) == 1

    def test_historical_temporal_coverage(
        self, historical_df: pd.DataFrame
    ) -> None:
        report = validate_dataset(historical_df, phase="historical")
        assert "date_range" in report.statistics

    def test_historical_spatial_coverage(
        self, historical_df: pd.DataFrame
    ) -> None:
        report = validate_dataset(historical_df, phase="historical")
        assert "unique_barangays" in report.statistics
        assert report.statistics["unique_barangays"] >= 3

    def test_report_to_dict(self, synthetic_df: pd.DataFrame) -> None:
        report = validate_dataset(synthetic_df, phase="synthetic")
        d = report.to_dict()
        assert "phase" in d
        assert "passed" in d
        assert "issues" in d
        assert "statistics" in d

    def test_statistics_computed(self, synthetic_df: pd.DataFrame) -> None:
        report = validate_dataset(synthetic_df, phase="synthetic")
        assert "shape" in report.statistics
        assert "numeric_summary" in report.statistics
        assert "target_distribution" in report.statistics


# =====================================================================
# LabelConsistency tests
# =====================================================================


class TestLabelConsistency:
    """Tests for the LabelConsistencyChecker."""

    def test_clean_labels(self) -> None:
        df = pd.DataFrame(
            {
                "temperature": [28.0, 30.0, 25.0],
                "humidity": [80.0, 90.0, 60.0],
                "precipitation": [50.0, 100.0, 0.0],
                "flood": [1, 1, 0],
            }
        )
        report = check_label_consistency(df)
        assert isinstance(report, ConsistencyReport)
        assert report.total_rows == 3

    def test_empty_dataframe(self) -> None:
        report = check_label_consistency(pd.DataFrame())
        assert len(report.recommendations) > 0

    def test_no_flood_column(self) -> None:
        df = pd.DataFrame({"temperature": [25.0]})
        report = check_label_consistency(df)
        assert len(report.recommendations) > 0

    def test_dry_day_flood_flagged(self) -> None:
        """Flood on a dry day should be flagged."""
        df = pd.DataFrame(
            {
                "precipitation": [0.0, 100.0, 0.5],
                "flood": [1, 1, 1],  # First and third are dry-day floods
            }
        )
        report = check_label_consistency(df)
        meteo = [
            i for i in report.inconsistencies
            if i.inconsistency_type == InconsistencyType.METEOROLOGICAL
        ]
        assert len(meteo) >= 1
        # Should flag at least one dry-day flood
        total_flagged = sum(len(i.row_indices) for i in meteo)
        assert total_flagged >= 1

    def test_low_humidity_flood(self) -> None:
        df = pd.DataFrame(
            {
                "precipitation": [80.0, 80.0],
                "humidity": [30.0, 90.0],
                "flood": [1, 1],
            }
        )
        report = check_label_consistency(df)
        hum = [
            i for i in report.inconsistencies
            if "humidity" in i.message.lower()
        ]
        assert len(hum) >= 1

    def test_depth_label_mismatch_positive_depth_no_flood(self) -> None:
        """flood=0 but depth > 0 is suspicious."""
        df = pd.DataFrame(
            {
                "flood": [0, 1, 0],
                "flood_depth_cm": [48, 100, 15],  # first and third flagged
                "precipitation": [50.0, 100.0, 50.0],
            }
        )
        report = check_label_consistency(df)
        depth = [
            i for i in report.inconsistencies
            if i.inconsistency_type == InconsistencyType.DEPTH_LABEL_MISMATCH
        ]
        assert len(depth) >= 1

    def test_depth_label_mismatch_flood_zero_depth(self) -> None:
        """flood=1 but depth=0."""
        df = pd.DataFrame(
            {
                "flood": [1, 1, 0],
                "flood_depth_cm": [0, 48, 0],
                "precipitation": [100.0, 100.0, 0.0],
            }
        )
        report = check_label_consistency(df)
        depth = [
            i for i in report.inconsistencies
            if i.inconsistency_type == InconsistencyType.DEPTH_LABEL_MISMATCH
        ]
        assert len(depth) >= 1

    def test_spatial_consistency_conflict(self) -> None:
        """Same date + barangay with different labels."""
        df = pd.DataFrame(
            {
                "date": ["2023-07-15", "2023-07-15", "2023-07-16"],
                "barangay": ["Tambo", "Tambo", "Tambo"],
                "flood": [0, 1, 1],
                "precipitation": [50.0, 50.0, 100.0],
            }
        )
        report = check_label_consistency(df)
        spatial = [
            i for i in report.inconsistencies
            if i.inconsistency_type == InconsistencyType.SPATIAL
        ]
        assert len(spatial) == 1

    def test_duplicate_conflict(self) -> None:
        """Identical features with different labels."""
        df = pd.DataFrame(
            {
                "temperature": [28.0, 28.0, 30.0],
                "humidity": [70.0, 70.0, 80.0],
                "precipitation": [10.0, 10.0, 50.0],
                "month": [7, 7, 8],
                "flood": [0, 1, 1],
            }
        )
        report = check_label_consistency(df)
        dup = [
            i for i in report.inconsistencies
            if i.inconsistency_type == InconsistencyType.DUPLICATE_CONFLICT
        ]
        assert len(dup) == 1

    def test_cross_source_comparison(self) -> None:
        """Compare two sources with disagreements."""
        source_a = pd.DataFrame(
            {
                "date": ["2023-07-15", "2023-07-16", "2023-07-17"],
                "flood": [1, 0, 1],
            }
        )
        source_b = pd.DataFrame(
            {
                "date": ["2023-07-15", "2023-07-16", "2023-07-17"],
                "flood": [1, 1, 0],  # two disagreements
            }
        )
        report = compare_label_sources(
            source_a,
            source_b,
            source_a_name="synthetic",
            source_b_name="official",
        )
        cross = [
            i for i in report.inconsistencies
            if i.inconsistency_type == InconsistencyType.CROSS_SOURCE
        ]
        assert len(cross) == 1
        assert cross[0].details["disagreement_count"] == 2

    def test_cross_source_no_overlap(self) -> None:
        source_a = pd.DataFrame(
            {"date": ["2023-01-01"], "flood": [1]}
        )
        source_b = pd.DataFrame(
            {"date": ["2024-01-01"], "flood": [0]}
        )
        report = compare_label_sources(source_a, source_b)
        assert len(report.recommendations) > 0

    def test_recommendations_generated(self) -> None:
        df = pd.DataFrame(
            {
                "precipitation": [0.0],
                "flood": [1],
            }
        )
        report = check_label_consistency(df)
        assert len(report.recommendations) >= 1

    def test_report_to_dict(self) -> None:
        df = pd.DataFrame(
            {
                "temperature": [28.0],
                "humidity": [80.0],
                "precipitation": [50.0],
                "flood": [1],
            }
        )
        report = check_label_consistency(df)
        d = report.to_dict()
        assert "consistent" in d
        assert "total_issues" in d
        assert "recommendations" in d

    def test_non_monsoon_flood_flagged(self) -> None:
        """Flood outside monsoon season without typhoon."""
        df = pd.DataFrame(
            {
                "precipitation": [50.0, 100.0],
                "month": [2, 3],  # dry season
                "flood": [1, 1],
            }
        )
        report = check_label_consistency(df)
        monsoon = [
            i for i in report.inconsistencies
            if "monsoon" in i.message.lower()
        ]
        assert len(monsoon) >= 1


# =====================================================================
# DatasetTransition tests
# =====================================================================


class TestDatasetTransition:
    """Tests for the DatasetTransitionPlan orchestrator."""

    def test_phase1_evaluation(self, synthetic_df: pd.DataFrame) -> None:
        report = evaluate_dataset_transition(
            synthetic_df, TransitionPhase.PHASE_1_SYNTHETIC
        )
        d = report.to_dict()
        assert d["phase"] == "phase_1_synthetic"
        assert d["validation"] is not None
        assert d["consistency"] is not None
        assert d["readiness"] is not None

    def test_phase2_evaluation(
        self, semi_supervised_df: pd.DataFrame
    ) -> None:
        report = evaluate_dataset_transition(
            semi_supervised_df, TransitionPhase.PHASE_2_SEMI_SUPERVISED
        )
        d = report.to_dict()
        assert d["phase"] == "phase_2_semi_supervised"

    def test_phase3_evaluation(self, historical_df: pd.DataFrame) -> None:
        report = evaluate_dataset_transition(
            historical_df, TransitionPhase.PHASE_3_HISTORICAL
        )
        d = report.to_dict()
        assert d["phase"] == "phase_3_historical"

    def test_phase1_readiness_pass(self) -> None:
        """Large enough synthetic dataset should be ready for Phase 2."""
        np.random.seed(42)
        n = 250
        df = pd.DataFrame(
            {
                "temperature": np.random.uniform(22, 35, n),
                "humidity": np.random.uniform(50, 95, n),
                "precipitation": np.random.uniform(0, 150, n),
                "flood": np.random.choice([0, 1], n, p=[0.7, 0.3]),
            }
        )
        report = evaluate_dataset_transition(
            df, TransitionPhase.PHASE_1_SYNTHETIC
        )
        readiness = report.readiness
        assert readiness["ready"] is True
        assert readiness["next_phase"] == "phase_2_semi_supervised"

    def test_phase1_readiness_fail_too_small(self) -> None:
        df = pd.DataFrame(
            {
                "temperature": [28.0] * 10,
                "humidity": [70.0] * 10,
                "precipitation": [10.0] * 10,
                "flood": [0] * 5 + [1] * 5,
            }
        )
        report = evaluate_dataset_transition(
            df, TransitionPhase.PHASE_1_SYNTHETIC
        )
        readiness = report.readiness
        assert readiness["ready"] is False
        assert any("rows" in b.lower() for b in readiness["blockers"])

    def test_phase2_readiness_checks_confidence(self) -> None:
        np.random.seed(42)
        n = 600
        df = pd.DataFrame(
            {
                "temperature": np.random.uniform(22, 35, n),
                "humidity": np.random.uniform(50, 95, n),
                "precipitation": np.random.uniform(0, 150, n),
                "is_monsoon_season": np.random.choice([0, 1], n),
                "month": np.random.randint(1, 13, n),
                "flood": np.random.choice([0, 1], n, p=[0.65, 0.35]),
                "label_confidence": np.random.uniform(0.8, 1.0, n),
                "label_source": ["official"] * n,
            }
        )
        report = evaluate_dataset_transition(
            df, TransitionPhase.PHASE_2_SEMI_SUPERVISED
        )
        assert "mean_confidence" in report.readiness["metrics"]

    def test_phase3_readiness_final(self, historical_df: pd.DataFrame) -> None:
        report = evaluate_dataset_transition(
            historical_df, TransitionPhase.PHASE_3_HISTORICAL
        )
        readiness = report.readiness
        assert readiness["next_phase"] is None  # final phase

    def test_phase_metadata(self) -> None:
        plan = DatasetTransitionPlan()
        for phase in TransitionPhase:
            meta = plan.generate_phase_summary(phase)
            assert "name" in meta
            assert "description" in meta
            assert "key_activities" in meta
            assert "exit_criteria" in meta

    def test_cross_source_reference(self) -> None:
        """Evaluate with a reference dataset for cross-source comparison."""
        np.random.seed(42)
        n = 60
        dates = [f"2023-07-{d:02d}" for d in range(1, n + 1) if d <= 31] * 2
        dates = dates[:n]

        main = pd.DataFrame(
            {
                "date": dates,
                "temperature": np.random.uniform(25, 35, n),
                "humidity": np.random.uniform(60, 95, n),
                "precipitation": np.random.uniform(0, 100, n),
                "is_monsoon_season": [1] * n,
                "month": [7] * n,
                "flood": np.random.choice([0, 1], n),
                "label_confidence": np.random.uniform(0.5, 1.0, n),
                "label_source": ["pseudo"] * n,
            }
        )
        reference = pd.DataFrame(
            {
                "date": dates,
                "flood": np.random.choice([0, 1], n),
            }
        )
        report = evaluate_dataset_transition(
            main,
            TransitionPhase.PHASE_2_SEMI_SUPERVISED,
            reference_df=reference,
        )
        # Should include cross-source findings in consistency
        assert report.consistency is not None

    def test_string_phase_argument(self, synthetic_df: pd.DataFrame) -> None:
        """Accept phase as a plain string."""
        report = evaluate_dataset_transition(
            synthetic_df, "phase_1_synthetic"
        )
        assert report.phase == "phase_1_synthetic"

    def test_report_structure(self, synthetic_df: pd.DataFrame) -> None:
        report = evaluate_dataset_transition(
            synthetic_df, TransitionPhase.PHASE_1_SYNTHETIC
        )
        d = report.to_dict()
        assert set(d.keys()) == {
            "phase",
            "timestamp",
            "validation",
            "consistency",
            "readiness",
            "phase_metadata",
        }
