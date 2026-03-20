"""
Preprocess Official Parañaque Flood Records for Model Training
===============================================================

Processes official flood records from Parañaque City (2022-2025) and creates
cumulative training datasets for progressive model training.

Data Sources:
    - Floodingnaque_Paranaque_Official_Flood_Records_2022.csv
    - Floodingnaque_Paranaque_Official_Flood_Records_2023.csv
    - Floodingnaque_Paranaque_Official_Flood_Records_2024.csv
    - Floodingnaque_Paranaque_Official_Flood_Records_2025.csv

Output:
    - processed_flood_records_YYYY.csv (per year)
    - cumulative_up_to_YYYY.csv (cumulative datasets)
    - flood_records_merged.csv (all years combined)

Usage:
    python scripts/preprocess_official_flood_records.py
    python scripts/preprocess_official_flood_records.py --year 2024
    python scripts/preprocess_official_flood_records.py --cumulative
"""

import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"

# Available years
AVAILABLE_YEARS = [2022, 2023, 2024, 2025]


def get_flood_record_file(year: int) -> Path:
    """Get the path to flood record file for a specific year."""
    return DATA_DIR / f"Floodingnaque_Paranaque_Official_Flood_Records_{year}.csv"


def load_flood_records(year: int) -> Optional[pd.DataFrame]:
    """Load flood records for a specific year."""
    file_path = get_flood_record_file(year)

    if not file_path.exists():
        logger.warning(f"Flood records not found for {year}: {file_path}")
        return None

    try:
        df = pd.read_csv(file_path)
        logger.info(f"Loaded {len(df)} flood records for {year}")
        return df
    except Exception as e:
        logger.error(f"Error loading {year} flood records: {e}")
        return None


def preprocess_flood_record(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """
    Preprocess a single year's flood records.

    Standardizes columns, handles missing values, and adds derived features.
    This function mutates and returns the provided DataFrame.
    """

    # Standardize column names (lowercase, underscore)
    df.columns = [col.lower().strip().replace(" ", "_") for col in df.columns]

    # Ensure year column exists
    if "year" not in df.columns:
        df["year"] = year

    # Parse date columns if they exist
    date_cols = ["date", "flood_date", "event_date", "incident_date"]
    for col in date_cols:
        if col in df.columns:
            try:
                df["date"] = pd.to_datetime(df[col], errors="coerce")
                break
            except Exception as e:
                logger.error(f"Error parsing date column '{col}': {e}")

    # Extract month if date exists
    if "date" in df.columns:
        date_series: pd.Series = df["date"]
        df["month"] = df["date"].dt.month  # type: ignore
        df["day"] = df["date"].dt.day  # type: ignore

    # Map common flood severity/level columns
    severity_cols = ["severity", "flood_level", "risk_level", "level", "flood_severity"]
    for col in severity_cols:
        if col in df.columns:
            df["risk_level"] = df[col]
            break

    # Create binary flood indicator
    df["flood"] = 1  # All records are flood events

    # Handle precipitation if available
    precip_cols = ["rainfall", "precipitation", "rain_mm", "rainfall_mm"]
    for col in precip_cols:
        if col in df.columns:
            df["precipitation"] = pd.to_numeric(df[col], errors="coerce")
            break

    # Default precipitation values based on flood occurrence
    if "precipitation" not in df.columns:
        # Estimate based on flood severity if available
        if "risk_level" in df.columns:
            level_map = {0: 25, 1: 35, 2: 60}  # LOW/MODERATE/HIGH
            df["precipitation"] = df["risk_level"].map(level_map).fillna(40)
        else:
            df["precipitation"] = 40  # Default moderate flood precipitation

    # NOTE: Weather data (temperature, humidity) is NOT generated here.
    # Use preprocess_official_flood_records_v2.py which assigns real PAGASA
    # station data via IDW spatial interpolation.

    # Add monsoon season indicator
    if "month" in df.columns:
        df["is_monsoon_season"] = df["month"].isin([6, 7, 8, 9, 10, 11]).astype(int)

    return df


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived features for model training.

    This function mutates and returns the provided DataFrame.
    """

    # Ensure numeric columns
    numeric_cols = ["precipitation", "temperature", "humidity"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Fill missing values
    df["precipitation"] = df["precipitation"].fillna(df["precipitation"].median())
    df["temperature"] = df["temperature"].fillna(28)
    df["humidity"] = df["humidity"].fillna(75)

    # Temperature interactions
    if all(c in df.columns for c in ["temperature", "humidity"]):
        df["temp_humidity_interaction"] = df["temperature"] * df["humidity"] / 100

    # Precipitation interactions
    if "precipitation" in df.columns and "humidity" in df.columns:
        df["humidity_precip_interaction"] = df["humidity"] * np.log1p(df["precipitation"])

    if "precipitation" in df.columns and "temperature" in df.columns:
        df["temp_precip_interaction"] = df["temperature"] * np.log1p(df["precipitation"])

    # Monsoon interaction
    if "is_monsoon_season" in df.columns and "precipitation" in df.columns:
        df["monsoon_precip_interaction"] = df["is_monsoon_season"] * df["precipitation"]

    # Saturation risk
    if "humidity" in df.columns and "precipitation" in df.columns:
        df["saturation_risk"] = ((df["humidity"] > 85) & (df["precipitation"] > 20)).astype(int)

    return df


def create_cumulative_datasets() -> Dict[int, pd.DataFrame]:
    """
    Create cumulative datasets for progressive training.

    Returns:
        Dictionary mapping end_year to cumulative DataFrame
    """
    cumulative_datasets = {}
    all_records = []

    for year in AVAILABLE_YEARS:
        flood_df = load_flood_records(year)
        if flood_df is None:
            continue

        # Preprocess flood records (flood events only — no synthetic generation)
        processed = preprocess_flood_record(flood_df, year)
        year_data = add_derived_features(processed)

        all_records.append(year_data)

        # Create cumulative dataset up to this year
        cumulative = pd.concat(all_records, ignore_index=True)
        cumulative_datasets[year] = cumulative

        # Save processed year file
        year_output = PROCESSED_DIR / f"processed_flood_records_{year}.csv"
        year_data.to_csv(year_output, index=False)
        logger.info(f"Saved: {year_output} ({len(year_data)} records)")

        # Save cumulative file
        cum_output = PROCESSED_DIR / f"cumulative_up_to_{year}.csv"
        cumulative.to_csv(cum_output, index=False)
        logger.info(f"Saved: {cum_output} ({len(cumulative)} records)")

    return cumulative_datasets


def process_single_year(year: int) -> pd.DataFrame:
    """Process a single year's flood records."""
    flood_df = load_flood_records(year)
    if flood_df is None:
        raise FileNotFoundError(f"No flood records found for {year}")

    processed = preprocess_flood_record(flood_df, year)
    combined = add_derived_features(processed)

    output_path = PROCESSED_DIR / f"processed_flood_records_{year}.csv"
    combined.to_csv(output_path, index=False)
    logger.info(f"Saved: {output_path}")

    return combined


def print_summary(datasets: Dict[int, pd.DataFrame]):
    """Print processing summary."""
    print("\n" + "=" * 60)
    print("FLOOD RECORDS PREPROCESSING COMPLETE")
    print("=" * 60)

    for year, df in sorted(datasets.items()):
        flood_count = df["flood"].sum()
        non_flood_count = len(df) - flood_count
        print(f"\nCumulative up to {year}:")
        print(f"  Total records: {len(df):,}")
        print(f"  Flood events:  {flood_count:,} ({flood_count / len(df) * 100:.1f}%)")
        print(f"  Non-flood:     {non_flood_count:,} ({non_flood_count / len(df) * 100:.1f}%)")

    print("\n" + "=" * 60)
    print(f"Output directory: {PROCESSED_DIR}")
    print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Preprocess official Parañaque flood records")
    parser.add_argument("--year", type=int, choices=AVAILABLE_YEARS, help="Process single year only")
    parser.add_argument("--cumulative", action="store_true", help="Create cumulative datasets (default)")
    parser.add_argument("--output-dir", type=str, help="Custom output directory")

    args = parser.parse_args()

    # Ensure output directory exists
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if args.year:
        # Process single year
        df = process_single_year(args.year)
        print(f"\nProcessed {args.year}: {len(df)} records")
    else:
        # Create all cumulative datasets
        datasets = create_cumulative_datasets()
        print_summary(datasets)

    logger.info("Preprocessing complete!")


if __name__ == "__main__":
    main()
