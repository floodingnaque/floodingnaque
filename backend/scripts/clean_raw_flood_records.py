#!/usr/bin/env python3
"""
Clean and Standardize Raw Flood Records Format
==============================================

The official Parañaque flood records CSVs have irregular multi-row formats:
- Rows 1-4 contain metadata and multi-line headers
- Records span multiple rows due to merged cells in the original Excel
- Different years have different column layouts

This script produces cleaned, standardized versions while preserving originals.

Output:
    - data/cleaned/Floodingnaque_Flood_Records_YYYY_cleaned.csv

Usage:
    python scripts/clean_raw_flood_records.py
    python scripts/clean_raw_flood_records.py --year 2024
"""

import argparse
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
RAW_DIR = DATA_DIR / "raw" / "flood_records"
CLEANED_DIR = DATA_DIR / "cleaned"

# Source files pattern
SOURCE_FILES = {
    2022: "Floodingnaque_Paranaque_Official_Flood_Records_2022.csv",
    2023: "Floodingnaque_Paranaque_Official_Flood_Records_2023.csv",
    2024: "Floodingnaque_Paranaque_Official_Flood_Records_2024.csv",
    2025: "Floodingnaque_Paranaque_Official_Flood_Records_2025.csv",
}

# Standard output columns
STANDARD_COLUMNS = [
    "record_num",
    "date",
    "month",
    "day",
    "year",
    "barangay",
    "location",
    "latitude",
    "longitude",
    "flood_depth",
    "weather_disturbance",
    "remarks",
    "time_reported",
    "time_subsided",
]

# Flood depth standardization
DEPTH_ALIASES = {
    "gutter level": "gutter",
    "gutter": "gutter",
    "ankle level": "ankle",
    "ankle": "ankle",
    "knee level": "knee",
    "knee": "knee",
    "waist level": "waist",
    "waist": "waist",
    "chest level": "chest",
    "chest": "chest",
}


def parse_date_flexible(date_str: str, year: int) -> Optional[datetime]:
    """Parse date string with multiple format support."""
    if pd.isna(date_str) or not date_str:
        return None

    date_str = str(date_str).strip()

    formats = [
        "%d %b %Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%Y-%m-%d",
        "%m/%d/%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    month_map = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }

    date_lower = date_str.lower()
    for month_name, month_num in month_map.items():
        if month_name in date_lower:
            day_match = re.search(r"(\d{1,2})", date_str)
            if day_match:
                day = int(day_match.group(1))
                try:
                    return datetime(year, month_num, day)
                except ValueError:
                    continue
    return None


def standardize_flood_depth(depth_text: str) -> str:
    """Standardize flood depth text to consistent format."""
    if pd.isna(depth_text) or not depth_text:
        return ""

    depth_lower = str(depth_text).lower().strip()

    for alias, standard in DEPTH_ALIASES.items():
        if alias in depth_lower:
            return standard

    # Check for numeric inches
    inch_match = re.search(r'(\d+)["\']', depth_text)
    if inch_match:
        return f"{inch_match.group(1)} inches"

    return depth_text.strip()


def parse_2022_2023_format(file_path: Path, year: int) -> pd.DataFrame:
    """
    Parse 2022-2023 format with multi-row merged cells.

    Structure:
    - Row 0: *YEAR XXXX
    - Row 1-3: Multi-row header
    - Data rows: Record number in col 0, data spread across multiple lines

    2023 has coordinates in columns 8-9 (LATITUDE, LONGITUDE)
    2022 has coordinates in columns 5-6
    """
    records = []

    try:
        raw_df = pd.read_csv(file_path, header=None, dtype=str)
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return pd.DataFrame()

    current_record: Dict = {}
    last_date = None  # Track last known date for records without dates (2023 format)

    for idx, row in raw_df.iterrows():
        row_values = [str(v).strip() if pd.notna(v) else "" for v in row]
        row_text = " ".join(row_values).lower()

        # Skip header rows (but be careful not to skip data rows with coordinates)
        is_header = any(h in row_text for h in [f"year {year}", "# ,date", "depth ,disturbances"])
        has_coords = any(x in row_text for x in ["14.4", "14.5", "14.6", "120.9", "121.0"])
        if is_header and not has_coords:
            continue

        first_val = row_values[0] if row_values else ""
        is_new_record = first_val.isdigit()

        if is_new_record:
            if current_record and (current_record.get("latitude") or current_record.get("date")):
                records.append(current_record.copy())

            current_record = {
                "record_num": int(first_val),
                "year": year,
            }

        # Parse date - check column 1 first
        if row_values[1] and not current_record.get("date"):
            parsed_date = parse_date_flexible(row_values[1], year)
            if parsed_date:
                current_record["date"] = parsed_date.strftime("%Y-%m-%d")
                current_record["month"] = parsed_date.month
                current_record["day"] = parsed_date.day
                last_date = current_record["date"]

        # For 2023 format, many records don't have dates - use last known date
        if year == 2023 and not current_record.get("date") and last_date:
            current_record["date"] = last_date

        # Month name (column 2)
        if row_values[2] and not current_record.get("month_name"):
            month_text = row_values[2].upper()
            if month_text in [
                "JANUARY",
                "FEBRUARY",
                "MARCH",
                "APRIL",
                "MAY",
                "JUNE",
                "JULY",
                "AUGUST",
                "SEPTEMBER",
                "OCTOBER",
                "NOVEMBER",
                "DECEMBER",
            ]:
                current_record["month_name"] = month_text

        # Barangay (column 3)
        barangay = row_values[3] if len(row_values) > 3 else ""
        if barangay and barangay.upper() not in ["", "SAN", "MARCELO", "STO", "BF"]:
            if "barangay" not in current_record:
                current_record["barangay"] = barangay
            else:
                current_record["barangay"] += " " + barangay

        # Location (column 4)
        location = row_values[4] if len(row_values) > 4 else ""
        if location and location.upper() not in ["", "FLOOD"]:
            if "location" not in current_record:
                current_record["location"] = location
            else:
                current_record["location"] += " " + location

        # For 2022: Latitude in col 5, Longitude in col 6
        # For 2023: Latitude in col 8, Longitude in col 9
        lat_cols = [5, 8] if year == 2022 else [8, 5]
        lon_cols = [6, 9] if year == 2022 else [9, 6]

        for lat_col in lat_cols:
            if len(row_values) > lat_col and row_values[lat_col]:
                try:
                    lat = float(row_values[lat_col])
                    if 14 <= lat <= 15:
                        current_record["latitude"] = lat
                        break
                except (ValueError, TypeError):
                    pass

        for lon_col in lon_cols:
            if len(row_values) > lon_col and row_values[lon_col]:
                try:
                    lon = float(row_values[lon_col])
                    if 120 <= lon <= 122:
                        current_record["longitude"] = lon
                        break
                except (ValueError, TypeError):
                    pass

        # Flood depth - check columns 5 and 7 depending on format
        depth_cols = [7, 5] if year == 2022 else [5, 7]
        for depth_col in depth_cols:
            depth = row_values[depth_col] if len(row_values) > depth_col else ""
            if depth and depth.upper() not in ["FLOOD", "", "DEPTH"]:
                standardized = standardize_flood_depth(depth)
                if standardized:
                    if "flood_depth" not in current_record:
                        current_record["flood_depth"] = standardized
                    elif current_record["flood_depth"] != standardized:
                        # Append if different (e.g., "knee" + "level")
                        combined = current_record["flood_depth"] + " " + depth.lower()
                        current_record["flood_depth"] = standardize_flood_depth(combined)
                    break

        # Weather - check column 6 or 8
        weather_cols = [8, 6] if year == 2022 else [6, 8]
        for weather_col in weather_cols:
            weather = row_values[weather_col] if len(row_values) > weather_col else ""
            if (
                weather
                and weather.upper() not in ["WEATHER", "", "DISTURBANCES"]
                and not current_record.get("weather_disturbance")
            ):
                if "thunderstorm" in weather.lower() or "monsoon" in weather.lower() or "itcz" in weather.lower():
                    current_record["weather_disturbance"] = weather
                    break

        # Remarks - check column 7 or 9
        remarks_cols = [9, 7] if year == 2022 else [7, 9]
        for remarks_col in remarks_cols:
            remarks = row_values[remarks_col] if len(row_values) > remarks_col else ""
            if remarks and remarks.upper() not in ["REMARKS", ""]:
                if "remarks" not in current_record:
                    current_record["remarks"] = remarks
                else:
                    current_record["remarks"] += " " + remarks
                break

    # Last record
    if current_record and (current_record.get("latitude") or current_record.get("date")):
        records.append(current_record)

    return pd.DataFrame(records)


def parse_2024_format(file_path: Path, year: int = 2024) -> pd.DataFrame:
    """Parse 2024/2025 format with different column layout."""
    records = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return pd.DataFrame()

    lines = content.split("\n")
    current_record: Dict = {}

    for line in lines:
        line = line.strip().replace('"', "")
        if not line:
            continue

        line_lower = line.lower()
        if any(h in line_lower for h in [f"year {year}", "flood", "depth", "weather", "disturbances", "barangay"]):
            if "14." not in line and "121." not in line:
                continue

        coord_match = re.findall(r"(\d{2}\.\d{5,})", line)
        record_match = re.match(r"^(\d+)\s+", line)

        if record_match:
            if current_record and current_record.get("latitude"):
                records.append(current_record.copy())
            current_record = {"record_num": int(record_match.group(1)), "year": year}

        # Date
        date_match = re.search(
            r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2},?\s*" + str(year),
            line,
            re.IGNORECASE,
        )
        if date_match and not current_record.get("date"):
            parsed = parse_date_flexible(date_match.group(), 2024)
            if parsed:
                current_record["date"] = parsed.strftime("%Y-%m-%d")
                current_record["month"] = parsed.month
                current_record["day"] = parsed.day

        # Coordinates
        if coord_match and len(coord_match) >= 2:
            for coord in coord_match:
                val = float(coord)
                if 14 <= val <= 15:
                    current_record["latitude"] = val
                elif 120 <= val <= 122:
                    current_record["longitude"] = val

        # Flood depth
        depth_match = re.search(r"(gutter|knee|waist|chest|ankle)\s*(level)?", line, re.IGNORECASE)
        if depth_match and not current_record.get("flood_depth"):
            current_record["flood_depth"] = standardize_flood_depth(depth_match.group())

        # Location/Barangay extraction
        location_parts = re.findall(r"([A-Za-z][A-Za-z\s\.]+)", line)
        for part in location_parts:
            part = part.strip()
            if len(part) > 3 and part.upper() not in [
                "MAY",
                "JUNE",
                "JULY",
                "AUGUST",
                "SEPTEMBER",
                "OCTOBER",
                "LEVEL",
                "GUTTER",
                "KNEE",
                "WAIST",
                "CHEST",
            ]:
                if "location" not in current_record:
                    current_record["location"] = part

    if current_record and current_record.get("latitude"):
        records.append(current_record)

    return pd.DataFrame(records)


def parse_2025_format(file_path: Path) -> pd.DataFrame:
    """
    Parse 2025 format.

    The 2025 CSV (Excel export with merged cells) splits each record's date
    across lines:
      - A preceding context line contains the month+day in either
        "Month DD" (e.g. "May 6,") or "DD Month" (e.g. "19 July") order.
      - The record line starts with the 1-3 digit record number.
        Early records (May-June): "N   2025   TIME   MONTH ..."
        Later records (July+):    "N   [spaces]   depth_inches   [spaces]   2025   ...coords"

    Strategy: detect record lines by 1-3 digit record number at line start
    (avoids confusing the 4-digit year "2025" with a record number), then
    look back up to LOOK_BACK lines for a month+day date fragment.
    """
    records = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return pd.DataFrame()

    lines = [line.strip().replace('"', "") for line in content.split("\n")]

    record_re = re.compile(r"^([1-9]\d{0,2})\s+")  # 1-3 digit record numbers only
    month_day_re = re.compile(
        r"(?:(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+(\d{1,2}),?)"  # "May 6," or "June 7"
        r"|(?:(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*)",  # "19 July"
        re.IGNORECASE,
    )
    coord_re = re.compile(r"(\d{2}\.\d{5,})")
    depth_re = re.compile(r"(gutter|knee|waist|chest|ankle)\s*(level)?", re.IGNORECASE)
    weather_re = re.compile(r"(easterlies|thunderstorm|monsoon|itcz|habagat|amihan|localized)", re.IGNORECASE)

    LOOK_BACK = 15

    def _extract_date_from_match(md_match) -> Optional[Tuple]:
        """Return (date_str, month_int, day_int) or None from a month_day_re match."""
        if not md_match:
            return None
        if md_match.group(1):  # "Month DD" format — groups 1 & 2
            month_str, day_str = md_match.group(1), md_match.group(2)
        else:  # "DD Month" format — groups 3 & 4
            day_str, month_str = md_match.group(3), md_match.group(4)
        parsed = parse_date_flexible(f"{month_str} {day_str}, 2025", 2025)
        if parsed:
            return parsed.strftime("%Y-%m-%d"), parsed.month, parsed.day
        return None

    current_record: Dict = {}

    for i, line in enumerate(lines):
        if not line:
            continue

        record_match = record_re.match(line)

        if record_match:
            # Save completed previous record
            if current_record and current_record.get("latitude"):
                records.append(current_record.copy())

            current_record = {
                "record_num": int(record_match.group(1)),
                "year": 2025,
            }

            # --- Date: look backwards for a month+day fragment ---
            look_back_start = max(0, i - LOOK_BACK)
            for prev_line in reversed(lines[look_back_start:i]):
                result = _extract_date_from_match(month_day_re.search(prev_line))
                if result:
                    current_record["date"], current_record["month"], current_record["day"] = result
                    break

            # Fallback: check the current record line itself
            if not current_record.get("date"):
                result = _extract_date_from_match(month_day_re.search(line))
                if result:
                    current_record["date"], current_record["month"], current_record["day"] = result

            # --- Coordinates ---
            for coord in coord_re.findall(line):
                val = float(coord)
                if 14 <= val <= 15:
                    current_record["latitude"] = val
                elif 120 <= val <= 122:
                    current_record["longitude"] = val

            # --- Flood depth ---
            depth_m = depth_re.search(line)
            if depth_m and not current_record.get("flood_depth"):
                current_record["flood_depth"] = standardize_flood_depth(depth_m.group())

            # --- Weather ---
            weather_m = weather_re.search(line)
            if weather_m and not current_record.get("weather_disturbance"):
                current_record["weather_disturbance"] = weather_m.group()

            # --- Location: first meaningful text on the record line after stripping coords/fields ---
            loc_line = re.sub(r"\d{2}\.\d{5,}", "", line)
            loc_line = re.sub(r"^\d+\s+2025\s+\d{4}H?\s+[A-Z]+\s*", "", loc_line)
            loc_line = loc_line.strip()
            if loc_line and not current_record.get("location"):
                loc_line = re.sub(r"\s{2,}", " ", loc_line)
                if len(loc_line) > 2:
                    current_record["location"] = loc_line[:80].strip()

        elif current_record:
            # Continuation lines — pick up coordinates and depth if missing
            if not current_record.get("latitude"):
                for coord in coord_re.findall(line):
                    val = float(coord)
                    if 14 <= val <= 15:
                        current_record["latitude"] = val
                    elif 120 <= val <= 122:
                        current_record["longitude"] = val

            if not current_record.get("flood_depth"):
                depth_m = depth_re.search(line)
                if depth_m:
                    current_record["flood_depth"] = standardize_flood_depth(depth_m.group())

    # Last record
    if current_record and current_record.get("latitude"):
        records.append(current_record)

    return pd.DataFrame(records)


def clean_and_standardize(df: pd.DataFrame) -> pd.DataFrame:
    """Apply final cleaning and standardization to parsed data."""
    if df.empty:
        return df

    # Standardize flood depth
    if "flood_depth" in df.columns:
        df["flood_depth"] = df["flood_depth"].apply(standardize_flood_depth)

    # Clean location and barangay text
    for col in ["location", "barangay"]:
        if col in df.columns:
            df[col] = df[col].str.strip().str.replace(r"\s+", " ", regex=True)

    # Ensure required columns exist
    for col in STANDARD_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # Reorder columns
    df = df[[c for c in STANDARD_COLUMNS if c in df.columns]]

    # Sort by date and record number
    if "date" in df.columns and "record_num" in df.columns:
        df = df.sort_values(["date", "record_num"]).reset_index(drop=True)

    return df


def clean_year(year: int) -> Optional[pd.DataFrame]:
    """Clean flood records for a specific year."""
    if year not in SOURCE_FILES:
        logger.error(f"No source file defined for year {year}")
        return None

    source_path = RAW_DIR / SOURCE_FILES[year]
    if not source_path.exists():
        logger.error(f"Source file not found: {source_path}")
        return None

    logger.info(f"Cleaning {year} flood records from {source_path.name}")

    # Parse based on year format
    if year in [2022, 2023]:
        df = parse_2022_2023_format(source_path, year)
    elif year == 2024:
        df = parse_2024_format(source_path)
    elif year == 2025:
        df = parse_2025_format(source_path)
    else:
        logger.error(f"No parser for year {year}")
        return None

    df = clean_and_standardize(df)
    logger.info(f"Extracted {len(df)} records for {year}")

    return df


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Clean and standardize raw flood records")
    parser.add_argument(
        "--year",
        type=int,
        choices=[2022, 2023, 2024, 2025],
        help="Process specific year only",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=CLEANED_DIR,
        help="Output directory for cleaned files",
    )
    args = parser.parse_args()

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    years = [args.year] if args.year else [2022, 2023, 2024, 2025]
    total_records = 0

    print("=" * 60)
    print("Raw Flood Records Cleaner")
    print("=" * 60)

    for year in years:
        df = clean_year(year)
        if df is not None and not df.empty:
            output_path = args.output_dir / f"Floodingnaque_Flood_Records_{year}_cleaned.csv"
            df.to_csv(output_path, index=False)
            print(f"  ✓ {year}: {len(df)} records -> {output_path.name}")
            total_records += len(df)
        else:
            print(f"  ✗ {year}: No records extracted")

    print("-" * 60)
    print(f"Total: {total_records} records cleaned")
    print(f"Output directory: {args.output_dir}")

    # Also create a combined file
    if not args.year:
        all_dfs = []
        for year in years:
            cleaned_path = args.output_dir / f"Floodingnaque_Flood_Records_{year}_cleaned.csv"
            if cleaned_path.exists():
                df = pd.read_csv(cleaned_path)
                all_dfs.append(df)

        if all_dfs:
            combined = pd.concat(all_dfs, ignore_index=True)
            combined_path = args.output_dir / "Floodingnaque_Flood_Records_All_cleaned.csv"
            combined.to_csv(combined_path, index=False)
            print(f"  ✓ Combined: {len(combined)} records -> {combined_path.name}")

    return 0


if __name__ == "__main__":
    exit(main())
