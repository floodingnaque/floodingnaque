"""
Dataset Validator for DRRMO Flood CSV Files.

Validates raw CSV data against expected schema, value ranges, and
completeness requirements before it enters the ML training pipeline.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Expected column schema for DRRMO flood records
REQUIRED_COLUMNS = [
    "temperature",
    "humidity",
    "precipitation",
    "is_monsoon_season",
    "month",
    "flood_occurred",
]

# Valid ranges for numeric columns
COLUMN_RANGES: Dict[str, Dict[str, float]] = {
    "temperature": {"min": -10.0, "max": 55.0},
    "humidity": {"min": 0.0, "max": 100.0},
    "precipitation": {"min": 0.0, "max": 500.0},
    "is_monsoon_season": {"min": 0.0, "max": 1.0},
    "month": {"min": 1.0, "max": 12.0},
    "flood_occurred": {"min": 0.0, "max": 2.0},
}


@dataclass
class ValidationResult:
    """Result of a dataset validation run."""

    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    row_count: int = 0
    column_count: int = 0
    missing_columns: List[str] = field(default_factory=list)
    null_counts: Dict[str, int] = field(default_factory=dict)
    out_of_range: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "missing_columns": self.missing_columns,
            "null_counts": self.null_counts,
            "out_of_range": self.out_of_range,
        }


class DatasetValidator:
    """
    Validates DRRMO flood CSV datasets for training pipeline readiness.

    Checks:
    - Required columns are present
    - No excessive null values
    - Numeric values within expected ranges
    - Minimum row count for meaningful training
    - Target variable class balance
    """

    def __init__(self, min_rows: int = 50, max_null_pct: float = 0.10):
        self.min_rows = min_rows
        self.max_null_pct = max_null_pct

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        """
        Validate a DataFrame for training readiness.

        Args:
            df: The dataset to validate.

        Returns:
            ValidationResult with errors, warnings, and metadata.
        """
        result = ValidationResult(
            row_count=len(df),
            column_count=len(df.columns),
        )

        self._check_minimum_rows(df, result)
        self._check_required_columns(df, result)
        self._check_nulls(df, result)
        self._check_ranges(df, result)
        self._check_class_balance(df, result)

        result.is_valid = len(result.errors) == 0
        return result

    def _check_minimum_rows(self, df: pd.DataFrame, result: ValidationResult) -> None:
        if len(df) < self.min_rows:
            result.errors.append(
                f"Dataset has {len(df)} rows, minimum is {self.min_rows}"
            )

    def _check_required_columns(self, df: pd.DataFrame, result: ValidationResult) -> None:
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            result.missing_columns = missing
            result.errors.append(f"Missing required columns: {missing}")

    def _check_nulls(self, df: pd.DataFrame, result: ValidationResult) -> None:
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                continue
            null_count = int(df[col].isnull().sum())
            if null_count > 0:
                result.null_counts[col] = null_count
                null_pct = null_count / len(df)
                if null_pct > self.max_null_pct:
                    result.errors.append(
                        f"Column '{col}' has {null_pct:.1%} null values "
                        f"(max: {self.max_null_pct:.1%})"
                    )
                else:
                    result.warnings.append(
                        f"Column '{col}' has {null_count} null values ({null_pct:.1%})"
                    )

    def _check_ranges(self, df: pd.DataFrame, result: ValidationResult) -> None:
        for col, bounds in COLUMN_RANGES.items():
            if col not in df.columns:
                continue
            series = df[col].dropna()
            out_low = int((series < bounds["min"]).sum())
            out_high = int((series > bounds["max"]).sum())
            total_out = out_low + out_high
            if total_out > 0:
                result.out_of_range[col] = total_out
                if total_out / len(df) > 0.05:
                    result.errors.append(
                        f"Column '{col}' has {total_out} values outside "
                        f"[{bounds['min']}, {bounds['max']}]"
                    )
                else:
                    result.warnings.append(
                        f"Column '{col}' has {total_out} out-of-range values"
                    )

    def _check_class_balance(self, df: pd.DataFrame, result: ValidationResult) -> None:
        if "flood_occurred" not in df.columns:
            return
        counts = df["flood_occurred"].value_counts()
        if len(counts) < 2:
            result.warnings.append(
                "Target variable has only one class — model cannot learn"
            )
            return
        minority_pct = counts.min() / counts.sum()
        if minority_pct < 0.05:
            result.warnings.append(
                f"Severe class imbalance: minority class is {minority_pct:.1%}"
            )

    def validate_file(self, csv_path: str) -> ValidationResult:
        """
        Validate a CSV file directly.

        Args:
            csv_path: Path to the CSV file.

        Returns:
            ValidationResult.
        """
        try:
            df = pd.read_csv(csv_path)
        except Exception as exc:
            result = ValidationResult(is_valid=False)
            result.errors.append(f"Failed to read CSV: {exc}")
            return result
        return self.validate(df)
