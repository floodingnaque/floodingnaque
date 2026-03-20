"""
Preprocess Official Parañaque Flood Records for Model Training (V2)
====================================================================

REFACTORED VERSION: Uses real PAGASA weather data instead of synthetic generation.
Eliminates data leakage by properly joining flood events with actual weather observations.

Data Sources:
    - Floodingnaque_Paranaque_Official_Flood_Records_2022.csv
    - Floodingnaque_Paranaque_Official_Flood_Records_2023.csv
    - Floodingnaque_Paranaque_Official_Flood_Records_2024.csv
    - Floodingnaque_Paranaque_Official_Flood_Records_2025.csv
    - PAGASA weather station data (Port Area, NAIA, Science Garden)

Output:
    - processed_flood_records_v2_YYYY.csv (per year with full features)
    - cumulative_v2_up_to_YYYY.csv (cumulative datasets)
    - flood_weather_merged_v2.csv (final training dataset)

Changes from V1:
    - NO synthetic non-flood data generation
    - Uses real PAGASA weather data for all samples
    - Inverse-distance weighted weather from 3 stations
    - Extracts geolocation (lat/lon), barangay, flood_depth
    - Adds flood_severity (0-3), weather type flags
    - Stratified non-flood sampling from real PAGASA data
    - Exact date-level joining (not month-level)

Usage:
    python scripts/preprocess_official_flood_records_v2.py
    python scripts/preprocess_official_flood_records_v2.py --year 2024
    python scripts/preprocess_official_flood_records_v2.py --create-training
"""

import argparse
import logging
import re
from datetime import datetime
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
ARCHIVE_DIR = PROCESSED_DIR / "archive"

# Available years
AVAILABLE_YEARS = [2022, 2023, 2024, 2025]

# PAGASA Station metadata
STATIONS = {
    "port_area": {
        "file": "Floodingnaque_CADS-S0126006_Port Area Daily Data.csv",
        "latitude": 14.58841,
        "longitude": 120.967866,
        "elevation": 15,
        "name": "Port Area",
    },
    "naia": {
        "file": "Floodingnaque_CADS-S0126006_NAIA Daily Data.csv",
        "latitude": 14.5047,
        "longitude": 121.004751,
        "elevation": 21,
        "name": "NAIA",
    },
    "science_garden": {
        "file": "Floodingnaque_CADS-S0126006_Science Garden Daily Data.csv",
        "latitude": 14.645072,
        "longitude": 121.044282,
        "elevation": 42,
        "name": "Science Garden",
    },
}

# Flood depth mapping (text to numeric cm)
FLOOD_DEPTH_MAP = {
    "gutter": 20,  # ~8 inches
    "gutter level": 20,
    "knee": 48,  # ~19 inches
    "knee level": 48,
    "waist": 94,  # ~37 inches
    "waist level": 94,
    "chest": 114,  # ~45 inches
    "chest level": 114,
}

# Flood severity mapping (0-3)
FLOOD_SEVERITY_MAP = {
    "gutter": 1,
    "gutter level": 1,
    "knee": 2,
    "knee level": 2,
    "waist": 3,
    "waist level": 3,
    "chest": 3,
    "chest level": 3,
}

# Weather disturbance patterns
WEATHER_PATTERNS = {
    "typhoon": r"(?:typhoon|bagyo|storm|super\s*typhoon)",
    "itcz": r"(?:itcz|inter[\s-]*tropical|convergence)",
    "sw_monsoon": r"(?:habagat|southwest\s*monsoon|sw\s*monsoon)",
    "ne_monsoon": r"(?:amihan|northeast\s*monsoon|ne\s*monsoon)",
    "easterlies": r"(?:easterlies|easterly)",
    "thunderstorm": r"(?:thunderstorm|localized\s*thunderstorm|lightning)",
    "lpa": r"(?:lpa|low\s*pressure\s*area)",
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth.

    Args:
        lat1, lon1: First point coordinates (degrees)
        lat2, lon2: Second point coordinates (degrees)

    Returns:
        Distance in kilometers
    """
    R = 6371  # Earth's radius in km

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))

    return R * c


def get_station_distances(lat: float, lon: float) -> Dict[str, float]:
    """Calculate distances from a point to all PAGASA stations."""
    distances = {}
    for key, station in STATIONS.items():
        dist = haversine_distance(lat, lon, station["latitude"], station["longitude"])
        distances[key] = dist
    return distances


def get_nearest_station(lat: float, lon: float) -> Tuple[str, float]:
    """Find the nearest PAGASA station to a given point."""
    distances = get_station_distances(lat, lon)
    nearest = min(distances.keys(), key=lambda k: distances[k])
    return nearest, distances[nearest]


def inverse_distance_weight(distances: Dict[str, float], power: float = 2) -> Dict[str, float]:
    """
    Calculate inverse-distance weights for stations.

    Args:
        distances: Dictionary of station_key -> distance_km
        power: Power parameter for IDW (default: 2)

    Returns:
        Dictionary of station_key -> weight (sums to 1.0)
    """
    # Avoid division by zero for very close points
    distances = {k: max(v, 0.01) for k, v in distances.items()}

    inv_distances = {k: 1.0 / (v**power) for k, v in distances.items()}
    total = sum(inv_distances.values())
    weights = {k: v / total for k, v in inv_distances.items()}

    return weights


def parse_flood_depth(depth_str: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Parse flood depth string to numeric cm and severity level.

    Args:
        depth_str: Flood depth description (e.g., "Knee Level", "8\"")

    Returns:
        Tuple of (depth_cm, severity_level)
    """
    if pd.isna(depth_str) or not depth_str:
        return None, None

    depth_str = str(depth_str).lower().strip()

    # Check for text-based depth
    for pattern, cm in FLOOD_DEPTH_MAP.items():
        if pattern in depth_str:
            severity = FLOOD_SEVERITY_MAP.get(pattern, 1)
            return cm, severity

    # Check for numeric depth (inches)
    inch_match = re.search(r'(\d+)["\']?', depth_str)
    if inch_match:
        inches = int(inch_match.group(1))
        cm = int(inches * 2.54)
        # Map to severity based on cm
        if cm < 30:
            severity = 1  # Gutter-level
        elif cm < 60:
            severity = 2  # Knee-level
        else:
            severity = 3  # Waist/Chest-level
        return cm, severity

    return None, None


def parse_weather_disturbance(weather_str: str) -> Dict[str, int]:
    """
    Extract weather type flags from disturbance description.

    Args:
        weather_str: Weather disturbance description

    Returns:
        Dictionary of weather type flags
    """
    flags = {f"is_{key}": 0 for key in WEATHER_PATTERNS}

    if pd.isna(weather_str) or not weather_str:
        return flags

    weather_lower = str(weather_str).lower()

    for key, pattern in WEATHER_PATTERNS.items():
        if re.search(pattern, weather_lower, re.IGNORECASE):
            flags[f"is_{key}"] = 1

    return flags


def parse_date_flexible(date_str: str, year: int) -> Optional[datetime]:
    """
    Parse date string with multiple format support.

    Args:
        date_str: Date string (e.g., "14 Mar 2022", "May 6, 2025")
        year: Default year if not in string

    Returns:
        Parsed datetime or None
    """
    if pd.isna(date_str) or not date_str:
        return None

    date_str = str(date_str).strip()

    # Common date formats in the data
    formats = [
        "%d %b %Y",  # "14 Mar 2022"
        "%B %d, %Y",  # "March 14, 2022"
        "%b %d, %Y",  # "Mar 14, 2022"
        "%d %B %Y",  # "14 March 2022"
        "%Y-%m-%d",  # "2022-03-14"
        "%m/%d/%Y",  # "03/14/2022"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    # Try to extract month and day, use provided year
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
            # Try to find day
            day_match = re.search(r"(\d{1,2})", date_str)
            if day_match:
                day = int(day_match.group(1))
                try:
                    return datetime(year, month_num, day)
                except ValueError:
                    continue

    return None


def parse_time_to_hours(time_str: str) -> Optional[float]:
    """
    Parse time string to hours (24h format).

    Args:
        time_str: Time string (e.g., "1600H", "21:30")

    Returns:
        Hours as float (e.g., 16.0, 21.5) or None
    """
    if pd.isna(time_str) or not time_str:
        return None

    time_str = str(time_str).strip().upper()

    # Format: "1600H" or "1630H"
    match = re.search(r"(\d{2})(\d{2})H?", time_str)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        return hours + minutes / 60

    # Format: "21:30" or "21:30:00"
    match = re.search(r"(\d{1,2}):(\d{2})", time_str)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        return hours + minutes / 60

    return None


def load_pagasa_all_stations() -> Dict[str, pd.DataFrame]:
    """
    Load PAGASA weather data from all stations.

    Returns:
        Dictionary of station_key -> DataFrame with processed weather data
    """
    station_data = {}

    for key, station in STATIONS.items():
        file_path = DATA_DIR / station["file"]
        if not file_path.exists():
            logger.warning(f"Station data not found: {file_path}")
            continue

        df = pd.read_csv(file_path)

        # Create date column
        df["date"] = pd.to_datetime(df[["YEAR", "MONTH", "DAY"]])

        # Handle PAGASA special values (-999 = missing, -1 = trace)
        for col in ["RAINFALL", "TMAX", "TMIN", "RH", "WIND_SPEED", "WIND_DIRECTION"]:
            if col in df.columns:
                df[col] = df[col].replace([-999, -999.0], np.nan)

        if "RAINFALL" in df.columns:
            df["RAINFALL"] = df["RAINFALL"].replace([-1, -1.0], 0.05)  # Trace rainfall

        # Rename columns
        df = df.rename(
            columns={
                "RAINFALL": "precipitation",
                "RH": "humidity",
                "WIND_SPEED": "wind_speed",
                "WIND_DIRECTION": "wind_direction",
                "YEAR": "year",
                "MONTH": "month",
                "DAY": "day",
                "TMAX": "temp_max",
                "TMIN": "temp_min",
            }
        )

        # Calculate average temperature
        if "temp_max" in df.columns and "temp_min" in df.columns:
            df["temperature"] = (df["temp_max"] + df["temp_min"]) / 2
            df["temp_range"] = df["temp_max"] - df["temp_min"]

        # Add station metadata
        df["station_key"] = key
        df["station_lat"] = station["latitude"]
        df["station_lon"] = station["longitude"]
        df["elevation"] = station["elevation"]

        station_data[key] = df
        logger.info(f"Loaded {len(df)} records from {station['name']}")

    return station_data


def get_idw_weather_for_date(
    station_data: Dict[str, pd.DataFrame], date: datetime, lat: float, lon: float
) -> Optional[Dict[str, float]]:
    """
    Get inverse-distance weighted weather values for a specific date and location.

    Args:
        station_data: Dictionary of station DataFrames
        date: Target date
        lat, lon: Location coordinates

    Returns:
        Dictionary of weighted weather values or None if data unavailable
    """
    # Get distances and weights
    distances = get_station_distances(lat, lon)
    weights = inverse_distance_weight(distances)

    # Collect values from each station
    weather_values = {
        "precipitation": [],
        "temperature": [],
        "humidity": [],
        "wind_speed": [],
        "wind_direction": [],
        "temp_max": [],
        "temp_min": [],
    }
    station_weights = []

    for key, df in station_data.items():
        day_data = df[df["date"] == pd.Timestamp(date)]
        if day_data.empty:
            continue

        row = day_data.iloc[0]
        weight = weights[key]

        for col in weather_values:
            if col in row and pd.notna(row[col]):
                weather_values[col].append((row[col], weight))

        station_weights.append((key, weight))

    if not station_weights:
        return None

    # Calculate weighted averages
    result = {}
    for col, values_weights in weather_values.items():
        if values_weights:
            total_weight = sum(w for _, w in values_weights)
            if total_weight > 0:
                result[col] = sum(v * w for v, w in values_weights) / total_weight

    # Add nearest station info
    nearest = max(station_weights, key=lambda x: x[1])
    result["nearest_station"] = nearest[0]
    result["distance_to_nearest_km"] = distances[nearest[0]]

    return result


def parse_flood_record_2022_2023(file_path: Path, year: int) -> pd.DataFrame:
    """
    Parse flood records for 2022-2023 format (multi-row merged cells).

    The raw CSV has a complex structure with merged cells spanning multiple rows.
    This function handles the parsing by combining related rows.
    """
    records = []

    try:
        # Read with minimal processing
        raw_df = pd.read_csv(file_path, header=None, dtype=str)
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return pd.DataFrame()

    current_record = {}
    row_count = 0

    for idx, row in raw_df.iterrows():
        row_values = [str(v).strip() if pd.notna(v) else "" for v in row]
        row_text = " ".join(row_values).lower()

        # Skip header rows
        if any(
            h in row_text
            for h in [
                "year 2022",
                "year 2023",
                "date",
                "month",
                "barangay",
                "remarks",
                "flood",
                "weather",
                "depth",
                "disturbances",
            ]
        ):
            continue

        # Check if this row starts a new record (has a record number in first column)
        first_val = row_values[0] if row_values else ""
        is_new_record = first_val.isdigit()

        if is_new_record:
            # Save previous record if exists
            if current_record and current_record.get("date"):
                records.append(current_record.copy())

            # Start new record
            current_record = {
                "record_num": int(first_val),
                "year": year,
            }
            row_count = 0

        # Parse row content based on position
        # Typical structure: #, DATE, MONTH, BARANGAY, LOCATION, LATITUDE, LONGITUDE, DEPTH, WEATHER, REMARKS
        if len(row_values) >= 10:
            # Date (column 1)
            if row_values[1] and not current_record.get("date"):
                parsed_date = parse_date_flexible(row_values[1], year)
                if parsed_date:
                    current_record["date"] = parsed_date  # type: ignore[assignment]
                    current_record["month"] = parsed_date.month
                    current_record["day"] = parsed_date.day

            # Month name (column 2) - backup for month
            if row_values[2] and not current_record.get("month_name"):
                current_record["month_name"] = row_values[2]  # type: ignore[assignment]

            # Barangay (column 3)
            if row_values[3] and row_values[3].upper() not in ["", "SAN", "MARCELO", "STO", "BF"]:
                if "barangay" not in current_record:
                    current_record["barangay"] = row_values[3]  # type: ignore[assignment]
                else:
                    current_record["barangay"] = str(current_record["barangay"]) + " " + row_values[3]  # type: ignore[assignment]

            # Location (column 4)
            if row_values[4]:
                if "location" not in current_record:
                    current_record["location"] = row_values[4]  # type: ignore[assignment]
                else:
                    current_record["location"] = str(current_record["location"]) + " " + row_values[4]  # type: ignore[assignment]

            # Latitude (column 5)
            try:
                lat = float(row_values[5])
                if 13 < lat < 16:  # Valid Manila latitude range
                    current_record["latitude"] = lat  # type: ignore[assignment]
            except (ValueError, TypeError):
                pass

            # Longitude (column 6)
            try:
                lon = float(row_values[6])
                if 119 < lon < 122:  # Valid Manila longitude range
                    current_record["longitude"] = lon  # type: ignore[assignment]
            except (ValueError, TypeError):
                pass

            # Flood depth (column 7)
            if row_values[7]:
                depth_cm, severity = parse_flood_depth(row_values[7])
                if depth_cm:
                    current_record["flood_depth_cm"] = depth_cm  # type: ignore[assignment]
                    current_record["flood_severity"] = severity  # type: ignore[assignment]
                elif row_values[7].upper() not in ["FLOOD", ""]:
                    if "flood_depth_text" not in current_record:
                        current_record["flood_depth_text"] = row_values[7]  # type: ignore[assignment]
                    else:
                        current_record["flood_depth_text"] = str(current_record["flood_depth_text"]) + " " + row_values[7]  # type: ignore[assignment]

            # Weather disturbance (column 8)
            if row_values[8] and row_values[8].upper() not in ["WEATHER", ""]:
                current_record["weather_disturbance"] = row_values[8]  # type: ignore[assignment]

            # Remarks (column 9)
            if row_values[9]:
                if "remarks" not in current_record:
                    current_record["remarks"] = row_values[9]  # type: ignore[assignment]
                else:
                    current_record["remarks"] = str(current_record["remarks"]) + " " + row_values[9]  # type: ignore[assignment]

        row_count += 1

    # Don't forget the last record
    if current_record and current_record.get("date"):
        records.append(current_record)

    df = pd.DataFrame(records)

    # Post-process flood depth from text if not numeric
    if "flood_depth_text" in df.columns and "flood_depth_cm" not in df.columns:
        for idx, row in df.iterrows():
            if pd.isna(row.get("flood_depth_cm")) and pd.notna(row.get("flood_depth_text")):
                depth_cm, severity = parse_flood_depth(row["flood_depth_text"])
                if depth_cm:
                    df.at[idx, "flood_depth_cm"] = depth_cm  # type: ignore[index]
                    df.at[idx, "flood_severity"] = severity  # type: ignore[index]

    logger.info(f"Parsed {len(df)} flood records from {year}")
    return df


def parse_flood_record_2024(file_path: Path) -> pd.DataFrame:
    """
    Parse flood records for 2024 format.

    2024 format has a different structure with varying column positions.
    Records span multiple lines and have coordinates at the end.
    """
    records = []

    try:
        # Read entire file as text for more flexible parsing
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return pd.DataFrame()

    # Split into lines and combine multi-line records
    lines = content.split("\n")

    current_record = {}

    for line in lines:
        line = line.strip().replace('"', "")
        if not line:
            continue

        # Skip header rows
        line_lower = line.lower()
        if any(
            h in line_lower
            for h in [
                "year 2024",
                "flood",
                "depth",
                "weather",
                "disturbances",
                "latitude",
                "longitude",
                "barangay",
                "remarks",
            ]
        ):
            if "14." not in line and "121." not in line and "120." not in line:
                continue

        # Look for coordinates - indicates end of a record
        coord_match = re.findall(r"(\d{2}\.\d{5,})", line)

        # Check if line has a record number at the start
        record_match = re.match(r"^(\d+)\s+", line)

        if record_match:
            # Save previous record if it has coordinates
            if current_record and current_record.get("latitude"):
                records.append(current_record.copy())

            # Start new record
            current_record = {
                "record_num": int(record_match.group(1)),
                "year": 2024,
            }

        # Parse date from line (e.g., "June 7, 2024", "July 24, 2024")
        date_match = re.search(
            r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2},?\s*2024", line, re.IGNORECASE
        )
        if date_match and not current_record.get("date"):
            parsed = parse_date_flexible(date_match.group(), 2024)
            if parsed:
                current_record["date"] = parsed  # type: ignore[assignment]
                current_record["month"] = parsed.month  # type: ignore[assignment]
                current_record["day"] = parsed.day  # type: ignore[assignment]

        # Extract month name
        month_match = re.search(
            r"\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b",
            line,
            re.IGNORECASE,
        )
        if month_match and not current_record.get("month_name"):
            current_record["month_name"] = month_match.group()  # type: ignore[assignment]

        # Extract coordinates
        if coord_match and len(coord_match) >= 2:
            for coord in coord_match:
                num = float(coord)
                if 14 <= num <= 15:
                    current_record["latitude"] = num  # type: ignore[assignment]
                elif 120 <= num <= 122:
                    current_record["longitude"] = num  # type: ignore[assignment]

        # Flood depth
        depth_match = re.search(r"(gutter|knee|waist|chest)\s*level", line, re.IGNORECASE)
        if depth_match:
            depth_text = depth_match.group()
            depth_cm, severity = parse_flood_depth(depth_text)
            if depth_cm:
                current_record["flood_depth_cm"] = depth_cm  # type: ignore[assignment]
                current_record["flood_severity"] = severity  # type: ignore[assignment]
            current_record["flood_depth_text"] = depth_text  # type: ignore[assignment]

        # Weather disturbance
        weather_match = re.search(
            r"(monsoon|typhoon|carina|habagat|southwest|easterlies|thunderstorm|itcz)", line, re.IGNORECASE
        )
        if weather_match:
            if "weather_disturbance" not in current_record:
                current_record["weather_disturbance"] = weather_match.group()  # type: ignore[assignment]
            else:
                current_record["weather_disturbance"] = str(current_record["weather_disturbance"]) + " " + weather_match.group()  # type: ignore[assignment]

        # Barangay names
        barangay_pattern = r"\b(San Dionisio|San Isidro|San Antonio|Vitalez|Sun Valley|Marcelo Green|Sto\.?\s*Niño|Moonwalk|Merville|Don\s*Bosco|La Huerta|Baclaran|BF Homes|Tambo|Sucat|San Martin|Porres|Coastal)\b"
        barangay_match = re.search(barangay_pattern, line, re.IGNORECASE)
        if barangay_match and not current_record.get("barangay"):
            current_record["barangay"] = barangay_match.group()  # type: ignore[assignment]

        # Location (various place indicators)
        if any(
            loc in line.lower()
            for loc in [
                "ave",
                "street",
                "st.",
                "blvd",
                "drive",
                "sitio",
                "extension",
                "compound",
                "bridge",
                "school",
                "village",
                "subdivision",
            ]
        ):
            # Extract meaningful location parts
            loc_parts = re.findall(
                r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s*(?:Ave|Street|St\.|Blvd|Drive|Village|Subdivision|Compound|Extension|Bridge|School)",
                line,
                re.IGNORECASE,
            )
            if loc_parts and not current_record.get("location"):
                current_record["location"] = loc_parts[0]  # type: ignore[assignment]

    # Don't forget the last record
    if current_record and current_record.get("latitude"):
        records.append(current_record)

    df = pd.DataFrame(records)

    # Fill in missing dates from month_name
    if not df.empty and "month_name" in df.columns:
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
        for idx, row in df.iterrows():
            if pd.isna(row.get("date")) and pd.notna(row.get("month_name")):
                month_name = str(row["month_name"]).lower().strip()
                if month_name in month_map:
                    df.at[idx, "month"] = month_map[month_name]  # type: ignore[index]
                    df.at[idx, "day"] = 1  # type: ignore[index]
                    try:
                        df.at[idx, "date"] = datetime(2024, month_map[month_name], 1)  # type: ignore[index]
                    except (ValueError, KeyError, TypeError):
                        pass  # Skip invalid date parsing silently

    logger.info(f"Parsed {len(df)} flood records from 2024")
    return df


def parse_flood_record_2025(file_path: Path) -> pd.DataFrame:
    """
    Parse flood records for 2025 format (includes time fields).

    2025 format has additional columns: TIME REPORTED, TIME SUBSIDED, DEPTH (METERS), TEMPERATURE, ACTIONS TAKEN
    """
    records = []

    try:
        raw_df = pd.read_csv(file_path, header=None, dtype=str)
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return pd.DataFrame()

    current_record = {}

    for idx, row in raw_df.iterrows():
        row_values = [str(v).strip() if pd.notna(v) else "" for v in row]
        row_text = " ".join(row_values).lower()

        # Skip header rows
        if any(
            h in row_text
            for h in [
                "year 2025",
                "floo flood",
                "time",
                "baran",
                "date",
                "repo",
                "month",
                "weather",
                "dept",
                "latitude",
                "longitude",
                "take",
            ]
        ):
            continue

        # Check for new record (has record number and date pattern)
        first_val = row_values[0] if row_values else ""
        is_new_record = first_val.isdigit()

        if is_new_record:
            # Save previous record
            if current_record and current_record.get("date"):
                records.append(current_record.copy())

            current_record = {
                "record_num": int(first_val),
                "year": 2025,
            }

        # Parse content - 2025 format is more complex with different column positions
        # Look for key patterns in the row
        for i, val in enumerate(row_values):
            if not val:
                continue

            # Date patterns (e.g., "May 6, 2025", "May 12,")
            if "2025" in val or re.match(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", val.lower()):
                parsed_date = parse_date_flexible(val, 2025)
                if parsed_date and not current_record.get("date"):
                    current_record["date"] = parsed_date  # type: ignore[assignment]
                    current_record["month"] = parsed_date.month  # type: ignore[assignment]
                    current_record["day"] = parsed_date.day  # type: ignore[assignment]

            # Time patterns (e.g., "1600H", "2130H")
            if re.match(r"\d{4}H", val.upper()):
                hours = parse_time_to_hours(val)
                if hours is not None:
                    if "time_reported" not in current_record:
                        current_record["time_reported"] = hours  # type: ignore[assignment]
                    elif "time_subsided" not in current_record:
                        current_record["time_subsided"] = hours  # type: ignore[assignment]

            # Month name
            if val.upper() in [
                "JAN",
                "FEB",
                "MAR",
                "APR",
                "MAY",
                "JUN",
                "JUL",
                "AUG",
                "SEP",
                "OCT",
                "NOV",
                "DEC",
                "JANUARY",
                "FEBRUARY",
                "MARCH",
                "APRIL",
                "JUNE",
                "JULY",
                "AUGUST",
                "SEPTEMBER",
                "OCTOBER",
                "NOVEMBER",
                "DECEMBER",
            ]:
                current_record["month_name"] = val  # type: ignore[assignment]

            # Latitude (14.xxx format)
            try:
                num = float(val)
                if 14 <= num <= 15:
                    current_record["latitude"] = num  # type: ignore[assignment]
                elif 120 <= num <= 122:
                    current_record["longitude"] = num  # type: ignore[assignment]
            except (ValueError, TypeError):
                pass

            # Flood depth with inches (e.g., '8"', '19"', '45"')
            if '"' in val or re.match(r'^\d+["\']?$', val):
                depth_cm, severity = parse_flood_depth(val)
                if depth_cm:
                    current_record["flood_depth_cm"] = depth_cm  # type: ignore[assignment]
                    current_record["flood_severity"] = severity  # type: ignore[assignment]

            # Flood level text
            if any(level in val.lower() for level in ["gutter", "knee", "waist", "chest"]):
                depth_cm, severity = parse_flood_depth(val)
                if depth_cm:
                    current_record["flood_depth_cm"] = depth_cm  # type: ignore[assignment]
                    current_record["flood_severity"] = severity  # type: ignore[assignment]
                current_record["flood_depth_text"] = val  # type: ignore[assignment]

            # Weather disturbance
            if any(
                w in val.lower() for w in ["easterlies", "thunderstorm", "typhoon", "habagat", "monsoon", "itcz", "lpa"]
            ):
                current_record["weather_disturbance"] = val  # type: ignore[assignment]

            # Barangay names (known barangays in Parañaque)
            barangay_names = [
                "san dionisio",
                "san isidro",
                "san antonio",
                "vitalez",
                "sun valley",
                "marcelo green",
                "sto. niño",
                "sto niño",
                "moonwalk",
                "merville",
                "don bosco",
                "la huerta",
                "baclaran",
                "bf homes",
                "tambo",
                "sucat",
            ]
            if any(b in val.lower() for b in barangay_names):
                current_record["barangay"] = val  # type: ignore[assignment]

            # Location (streets, avenues)
            if any(
                loc in val.lower()
                for loc in ["ave", "street", "st.", "blvd", "drive", "road", "corner", "infront", "sitio"]
            ):
                if "location" not in current_record:
                    current_record["location"] = val  # type: ignore[assignment]
                else:
                    current_record["location"] = str(current_record["location"]) + " " + val  # type: ignore[assignment]

    # Don't forget the last record
    if current_record and current_record.get("date"):
        records.append(current_record)

    df = pd.DataFrame(records)

    # Calculate flood duration if both times present
    if "time_reported" in df.columns and "time_subsided" in df.columns:

        def calc_duration(row: pd.Series) -> Optional[float]:  # type: ignore[type-arg]
            if pd.notna(row.get("time_reported")) and pd.notna(row.get("time_subsided")):
                return float(row["time_subsided"]) - float(row["time_reported"])
            return None

        df["flood_duration_hours"] = df.apply(calc_duration, axis=1)  # type: ignore[call-overload]

    logger.info(f"Parsed {len(df)} flood records from 2025")
    return df


def load_and_parse_flood_records(year: int) -> Optional[pd.DataFrame]:
    """Load and parse flood records for a specific year."""
    file_path = DATA_DIR / f"Floodingnaque_Paranaque_Official_Flood_Records_{year}.csv"

    if not file_path.exists():
        logger.warning(f"Flood records not found: {file_path}")
        return None

    if year == 2025:
        df = parse_flood_record_2025(file_path)
    elif year == 2024:
        df = parse_flood_record_2024(file_path)
    else:
        df = parse_flood_record_2022_2023(file_path, year)

    if df.empty:
        return None

    # Add common columns
    df["flood"] = 1  # All records are flood events

    # Extract weather type flags
    if "weather_disturbance" in df.columns:
        weather_flags = df["weather_disturbance"].apply(lambda x: pd.Series(parse_weather_disturbance(x)))
        df = pd.concat([df, weather_flags], axis=1)

    # Set default severity if not parsed
    if "flood_severity" not in df.columns:
        df["flood_severity"] = 1
    df["flood_severity"] = df["flood_severity"].fillna(1).astype(int)

    # Set default depth if not parsed
    if "flood_depth_cm" not in df.columns:
        df["flood_depth_cm"] = 20  # Default to gutter level
    df["flood_depth_cm"] = df["flood_depth_cm"].fillna(20).astype(int)

    return df


def get_flood_dates_set(flood_records: List[pd.DataFrame]) -> Set[Tuple[int, int, int]]:
    """
    Get set of (year, month, day) tuples for all flood events.

    This is used to identify non-flood days in PAGASA data.
    """
    flood_dates = set()

    for df in flood_records:
        if df is None or df.empty:
            continue

        for _, row in df.iterrows():
            if pd.notna(row.get("date")):
                date = pd.Timestamp(row["date"])
                flood_dates.add((date.year, date.month, date.day))

    return flood_dates


def sample_non_flood_days(
    station_data: Dict[str, pd.DataFrame],
    flood_dates: Set[Tuple[int, int, int]],
    target_ratio: float = 1.0,
    n_flood_records: int = 0,
) -> pd.DataFrame:
    """
    Sample non-flood days from PAGASA data with stratification.

    Strategy:
    - Uses real PAGASA weather data only (no synthetic generation)
    - Stratifies 50/50 between monsoon (Jun-Nov) and dry season (Dec-May)
    - Excludes all dates with recorded flood events

    Args:
        station_data: Dictionary of station DataFrames
        flood_dates: Set of (year, month, day) tuples to exclude
        target_ratio: Ratio of non-flood to flood samples (default 1.0 for balanced)
        n_flood_records: Number of flood records to balance against

    Returns:
        DataFrame of non-flood samples with weather data
    """
    # Use NAIA as primary station (closest to Parañaque)
    if "naia" not in station_data:
        # Fall back to any available station
        primary_key = list(station_data.keys())[0]
    else:
        primary_key = "naia"

    primary_df = station_data[primary_key].copy()

    # Filter out flood dates
    primary_df["date_tuple"] = primary_df.apply(
        lambda row: (int(row["year"]), int(row["month"]), int(row["day"])), axis=1
    )
    non_flood_df = primary_df[~primary_df["date_tuple"].isin(flood_dates)].copy()
    non_flood_df = non_flood_df.drop("date_tuple", axis=1)

    logger.info(f"Total non-flood days available: {len(non_flood_df)}")

    # Add monsoon indicator
    non_flood_df["is_monsoon_season"] = non_flood_df["month"].isin([6, 7, 8, 9, 10, 11]).astype(int)

    # Calculate target sample size
    target_n = int(n_flood_records * target_ratio) if n_flood_records > 0 else len(non_flood_df)
    samples_per_season = target_n // 2

    # Stratified sampling
    monsoon_df = non_flood_df[non_flood_df["is_monsoon_season"] == 1]
    dry_df = non_flood_df[non_flood_df["is_monsoon_season"] == 0]

    # Sample from each season
    monsoon_sample = monsoon_df.sample(n=min(samples_per_season, len(monsoon_df)), random_state=42)
    dry_sample = dry_df.sample(n=min(samples_per_season, len(dry_df)), random_state=42)

    # Combine samples
    sampled = pd.concat([monsoon_sample, dry_sample], ignore_index=True)

    # Add non-flood labels
    sampled["flood"] = 0
    sampled["flood_severity"] = 0
    sampled["flood_depth_cm"] = 0

    # Add placeholder for weather flags
    for flag in [
        "is_typhoon",
        "is_itcz",
        "is_sw_monsoon",
        "is_ne_monsoon",
        "is_easterlies",
        "is_thunderstorm",
        "is_lpa",
    ]:
        if flag not in sampled.columns:
            sampled[flag] = 0

    logger.info(f"Sampled {len(sampled)} non-flood days (monsoon: {len(monsoon_sample)}, dry: {len(dry_sample)})")

    return sampled


def merge_flood_records_with_weather(
    flood_records: pd.DataFrame, station_data: Dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """
    Merge flood records with PAGASA weather data using exact date and IDW.

    For each flood event:
    1. Matches by exact date
    2. Uses inverse-distance weighting from flood location to stations
    3. Falls back to nearest station if IDW fails
    """
    merged_records = []

    for idx, row in flood_records.iterrows():
        record = row.to_dict()

        # Get date
        if pd.isna(row.get("date")):
            # Try to construct date from year/month/day
            if all(pd.notna(row.get(c)) for c in ["year", "month", "day"]):
                record["date"] = datetime(int(row["year"]), int(row["month"]), int(row["day"]))
            else:
                continue  # Skip records without valid date

        date = pd.Timestamp(record["date"])

        # Get location
        lat = row.get("latitude")
        lon = row.get("longitude")

        if pd.notna(lat) and pd.notna(lon):
            # Use IDW for weather
            weather = get_idw_weather_for_date(station_data, date, lat, lon)
        else:
            # Use NAIA (closest to Parañaque center)
            lat, lon = 14.48, 121.02  # Approximate Parañaque center
            weather = get_idw_weather_for_date(station_data, date, lat, lon)

        if weather:
            record.update(weather)
        else:
            # Fall back to any available data for that date
            for key, df in station_data.items():
                day_data = df[df["date"] == date]
                if not day_data.empty:
                    for col in [
                        "precipitation",
                        "temperature",
                        "humidity",
                        "wind_speed",
                        "wind_direction",
                        "temp_max",
                        "temp_min",
                    ]:
                        if col in day_data.columns and pd.notna(day_data.iloc[0][col]):
                            record[col] = day_data.iloc[0][col]
                    record["nearest_station"] = key
                    break

        # Ensure latitude/longitude are set
        if pd.isna(record.get("latitude")):
            record["latitude"] = lat if lat else 14.48
        if pd.isna(record.get("longitude")):
            record["longitude"] = lon if lon else 121.02

        merged_records.append(record)

    result = pd.DataFrame(merged_records)
    logger.info(f"Merged {len(result)} flood records with weather data")

    return result


def add_rolling_features(df: pd.DataFrame, station_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Add rolling precipitation features using PAGASA data.

    For flood events, calculates rolling sums/averages from the preceding days.
    """
    df = df.copy()

    # Use NAIA as reference station for rolling calculations
    if "naia" in station_data:
        ref_df = station_data["naia"].set_index("date").sort_index()
    else:
        ref_df = list(station_data.values())[0].set_index("date").sort_index()

    # Pre-calculate rolling features for the reference station
    ref_df["precip_3day_sum"] = ref_df["precipitation"].rolling(window=3, min_periods=1).sum()
    ref_df["precip_7day_sum"] = ref_df["precipitation"].rolling(window=7, min_periods=1).sum()
    ref_df["precip_3day_avg"] = ref_df["precipitation"].rolling(window=3, min_periods=1).mean()
    ref_df["precip_7day_avg"] = ref_df["precipitation"].rolling(window=7, min_periods=1).mean()
    ref_df["precip_max_3day"] = ref_df["precipitation"].rolling(window=3, min_periods=1).max()
    ref_df["precip_max_7day"] = ref_df["precipitation"].rolling(window=7, min_periods=1).max()
    ref_df["precip_lag1"] = ref_df["precipitation"].shift(1)
    ref_df["precip_lag2"] = ref_df["precipitation"].shift(2)

    # Rain streak
    ref_df["is_rain"] = (ref_df["precipitation"] > 0.1).astype(int)
    ref_df["rain_streak"] = (
        ref_df["is_rain"].groupby((ref_df["is_rain"] != ref_df["is_rain"].shift()).cumsum()).cumcount() + 1
    )
    ref_df.loc[ref_df["is_rain"] == 0, "rain_streak"] = 0

    # Humidity rolling
    ref_df["humidity_3day_avg"] = ref_df["humidity"].rolling(window=3, min_periods=1).mean()
    ref_df["humidity_lag1"] = ref_df["humidity"].shift(1)

    # Map rolling features to main dataframe by date
    rolling_cols = [
        "precip_3day_sum",
        "precip_7day_sum",
        "precip_3day_avg",
        "precip_7day_avg",
        "precip_max_3day",
        "precip_max_7day",
        "precip_lag1",
        "precip_lag2",
        "rain_streak",
        "humidity_3day_avg",
        "humidity_lag1",
    ]

    for col in rolling_cols:
        df[col] = df["date"].apply(
            lambda d, c=col: ref_df.loc[pd.Timestamp(d), c] if pd.Timestamp(d) in ref_df.index else np.nan
        )

    return df


def add_interaction_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add interaction features for model training."""
    df = df.copy()

    # Temperature-Humidity interaction
    if all(c in df.columns for c in ["temperature", "humidity"]):
        df["temp_humidity_interaction"] = df["temperature"] * df["humidity"] / 100

    # Precipitation-Humidity interaction
    if all(c in df.columns for c in ["humidity", "precipitation"]):
        df["humidity_precip_interaction"] = df["humidity"] * np.log1p(df["precipitation"])

    # Temperature-Precipitation interaction
    if all(c in df.columns for c in ["temperature", "precipitation"]):
        df["temp_precip_interaction"] = df["temperature"] * np.log1p(df["precipitation"])

    # Monsoon-Precipitation interaction
    if all(c in df.columns for c in ["is_monsoon_season", "precipitation"]):
        df["monsoon_precip_interaction"] = df["is_monsoon_season"] * df["precipitation"]

    # Saturation risk
    if all(c in df.columns for c in ["humidity", "precipitation"]):
        df["saturation_risk"] = ((df["humidity"] > 85) & (df["precipitation"] > 20)).astype(int)

    # Heat index
    if all(c in df.columns for c in ["temperature", "humidity"]):
        temp_f = df["temperature"] * 9 / 5 + 32
        hi = 0.5 * (temp_f + 61.0 + ((temp_f - 68.0) * 1.2) + (df["humidity"] * 0.094))
        df["heat_index"] = (hi - 32) * 5 / 9

    return df


def encode_barangay(df: pd.DataFrame) -> pd.DataFrame:
    """Add barangay encoding (label encoding for now)."""
    df = df.copy()

    if "barangay" not in df.columns:
        df["barangay_encoded"] = 0
        return df

    # Clean barangay names
    df["barangay_clean"] = df["barangay"].fillna("unknown").str.lower().str.strip()

    # Create encoding
    unique_barangays = df["barangay_clean"].unique()
    barangay_map = {b: i for i, b in enumerate(sorted(unique_barangays))}

    df["barangay_encoded"] = df["barangay_clean"].map(barangay_map)

    return df


def create_training_dataset_v2(output_path: Optional[Path] = None) -> pd.DataFrame:
    """
    Create the final training dataset using real PAGASA data.

    This replaces the synthetic data generation approach with:
    1. Parsed flood records with full metadata
    2. Real PAGASA weather data for flood dates
    3. Stratified sampling of non-flood days
    4. Proper spatial joining (IDW)
    5. Comprehensive feature engineering
    """
    logger.info("=" * 60)
    logger.info("CREATING TRAINING DATASET V2 (Real PAGASA Data)")
    logger.info("=" * 60)

    # Step 1: Load PAGASA station data
    logger.info("\nStep 1: Loading PAGASA station data...")
    station_data = load_pagasa_all_stations()

    if not station_data:
        raise ValueError("No PAGASA station data available")

    # Step 2: Parse all flood records
    logger.info("\nStep 2: Parsing flood records...")
    flood_records = []
    for year in AVAILABLE_YEARS:
        df = load_and_parse_flood_records(year)
        if df is not None and not df.empty:
            flood_records.append(df)

    if not flood_records:
        raise ValueError("No flood records could be parsed")

    all_floods = pd.concat(flood_records, ignore_index=True)
    logger.info(f"Total flood records: {len(all_floods)}")

    # Step 3: Merge flood records with weather data
    logger.info("\nStep 3: Merging flood records with PAGASA weather...")
    floods_with_weather = merge_flood_records_with_weather(all_floods, station_data)

    # Step 4: Sample non-flood days
    logger.info("\nStep 4: Sampling non-flood days (stratified)...")
    flood_dates = get_flood_dates_set([all_floods])
    non_flood_samples = sample_non_flood_days(
        station_data, flood_dates, target_ratio=1.0, n_flood_records=len(all_floods)  # Balanced 1:1 ratio
    )

    # Step 5: Combine flood and non-flood samples
    logger.info("\nStep 5: Combining datasets...")

    # Ensure consistent columns
    common_cols = [
        "date",
        "year",
        "month",
        "day",
        "latitude",
        "longitude",
        "precipitation",
        "temperature",
        "humidity",
        "wind_speed",
        "wind_direction",
        "flood",
        "flood_severity",
        "flood_depth_cm",
        "is_monsoon_season",
        "nearest_station",
        "barangay",
        "location",
        "weather_disturbance",
        "is_typhoon",
        "is_itcz",
        "is_sw_monsoon",
        "is_ne_monsoon",
        "is_easterlies",
        "is_thunderstorm",
        "is_lpa",
    ]

    # Add missing columns to non-flood samples
    for col in common_cols:
        if col not in non_flood_samples.columns:
            non_flood_samples[col] = None

    # Add missing columns to flood samples
    for col in common_cols:
        if col not in floods_with_weather.columns:
            floods_with_weather[col] = None

    # Combine
    combined = pd.concat([floods_with_weather, non_flood_samples], ignore_index=True)

    # Step 6: Add rolling features
    logger.info("\nStep 6: Adding rolling features...")
    combined = add_rolling_features(combined, station_data)

    # Step 7: Add interaction features
    logger.info("\nStep 7: Adding interaction features...")
    combined = add_interaction_features(combined)

    # Step 8: Encode categorical features
    logger.info("\nStep 8: Encoding categorical features...")
    combined = encode_barangay(combined)

    # Fill missing values
    combined["is_monsoon_season"] = combined["month"].isin([6, 7, 8, 9, 10, 11]).astype(int)
    combined["precipitation"] = combined["precipitation"].fillna(0)
    combined["temperature"] = combined["temperature"].fillna(combined["temperature"].median())
    combined["humidity"] = combined["humidity"].fillna(combined["humidity"].median())

    # Enhanced temporal features
    dates = pd.to_datetime(combined["date"], errors="coerce")
    combined["day_of_week"] = dates.dt.dayofweek  # 0=Monday, 6=Sunday
    # Season: 0=dry (Dec-Feb), 1=pre-monsoon (Mar-May), 2=monsoon (Jun-Sep), 3=post-monsoon (Oct-Nov)
    combined["season"] = (
        combined["month"]
        .map({12: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1, 6: 2, 7: 2, 8: 2, 9: 2, 10: 3, 11: 3})
        .fillna(0)
        .astype(int)
    )

    # Ensure numeric types
    numeric_cols = [
        "flood",
        "flood_severity",
        "flood_depth_cm",
        "precipitation",
        "temperature",
        "humidity",
        "wind_speed",
        "is_monsoon_season",
        "day_of_week",
        "season",
    ]
    for col in numeric_cols:
        if col in combined.columns:
            combined[col] = pd.to_numeric(combined[col], errors="coerce")

    # Sort by date
    combined = combined.sort_values("date").reset_index(drop=True)

    # Save to file
    if output_path is None:
        output_path = PROCESSED_DIR / "training_dataset_v2.csv"

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output_path, index=False)

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("TRAINING DATASET V2 CREATED")
    logger.info("=" * 60)
    logger.info(f"Output: {output_path}")
    logger.info(f"Total records: {len(combined)}")
    logger.info(f"Flood events: {combined['flood'].sum()} ({combined['flood'].mean()*100:.1f}%)")
    logger.info(f"Non-flood: {len(combined) - combined['flood'].sum()} ({(1-combined['flood'].mean())*100:.1f}%)")
    logger.info(f"Date range: {combined['date'].min()} to {combined['date'].max()}")
    logger.info(f"Features: {len(combined.columns)}")

    if "flood_severity" in combined.columns:
        logger.info(f"\nFlood severity distribution:")
        for sev in sorted(combined["flood_severity"].unique()):
            count = (combined["flood_severity"] == sev).sum()
            logger.info(f"  Level {sev}: {count} ({count/len(combined)*100:.1f}%)")

    logger.info("=" * 60)

    return combined


def create_cumulative_datasets_v2() -> Dict[int, pd.DataFrame]:
    """
    Create cumulative datasets for progressive training using real PAGASA data.

    Returns dictionary mapping end_year to cumulative DataFrame.
    """
    logger.info("Creating cumulative datasets (V2)...")

    # Load PAGASA data once
    station_data = load_pagasa_all_stations()

    cumulative_datasets = {}
    all_records = []

    for year in AVAILABLE_YEARS:
        logger.info(f"\nProcessing {year}...")

        # Parse flood records for this year
        flood_df = load_and_parse_flood_records(year)
        if flood_df is None or flood_df.empty:
            logger.warning(f"No flood records for {year}")
            continue

        # Merge with weather
        year_floods = merge_flood_records_with_weather(flood_df, station_data)

        # Sample non-flood days for this year only
        year_flood_dates = get_flood_dates_set([flood_df])

        # Filter station data to this year
        year_station_data = {k: df[df["year"] == year].copy() for k, df in station_data.items()}

        # Sample non-flood days
        year_non_flood = sample_non_flood_days(
            year_station_data if any(len(df) > 0 for df in year_station_data.values()) else station_data,
            year_flood_dates,
            target_ratio=1.0,
            n_flood_records=len(flood_df),
        )

        # Combine year data
        year_data = pd.concat([year_floods, year_non_flood], ignore_index=True)
        year_data = add_rolling_features(year_data, station_data)
        year_data = add_interaction_features(year_data)
        year_data = encode_barangay(year_data)

        # Save year file
        year_output = PROCESSED_DIR / f"processed_flood_records_v2_{year}.csv"
        year_data.to_csv(year_output, index=False)
        logger.info(f"Saved: {year_output} ({len(year_data)} records)")

        # Add to cumulative
        all_records.append(year_data)

        # Create cumulative dataset up to this year
        cumulative = pd.concat(all_records, ignore_index=True)
        cumulative_datasets[year] = cumulative

        # Save cumulative file
        cum_output = PROCESSED_DIR / f"cumulative_v2_up_to_{year}.csv"
        cumulative.to_csv(cum_output, index=False)
        logger.info(f"Saved: {cum_output} ({len(cumulative)} records)")

    return cumulative_datasets


def print_summary_v2(datasets: Dict[int, pd.DataFrame]):
    """Print processing summary."""
    print("\n" + "=" * 60)
    print("FLOOD RECORDS PREPROCESSING V2 COMPLETE")
    print("(Using Real PAGASA Weather Data)")
    print("=" * 60)

    for year, df in sorted(datasets.items()):
        flood_count = df["flood"].sum()
        non_flood_count = len(df) - flood_count
        print(f"\nCumulative up to {year}:")
        print(f"  Total records: {len(df):,}")
        print(f"  Flood events:  {flood_count:,} ({flood_count/len(df)*100:.1f}%)")
        print(f"  Non-flood:     {non_flood_count:,} ({non_flood_count/len(df)*100:.1f}%)")

        if "flood_severity" in df.columns:
            print(f"  Severity distribution:")
            for sev in sorted(df["flood_severity"].unique()):
                count = (df["flood_severity"] == sev).sum()
                print(f"    Level {sev}: {count:,}")

    print("\n" + "=" * 60)
    print(f"Output directory: {PROCESSED_DIR}")
    print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Preprocess official Parañaque flood records (V2 - Real PAGASA Data)")
    parser.add_argument("--year", type=int, choices=AVAILABLE_YEARS, help="Process single year only")
    parser.add_argument("--cumulative", action="store_true", help="Create cumulative datasets")
    parser.add_argument("--create-training", action="store_true", help="Create final training dataset")
    parser.add_argument("--archive-old", action="store_true", help="Archive old V1 processed files")

    args = parser.parse_args()

    # Ensure output directories exist
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    if args.archive_old:
        # Move old files to archive
        old_files = list(PROCESSED_DIR.glob("processed_flood_records_*.csv"))
        old_files += list(PROCESSED_DIR.glob("cumulative_up_to_*.csv"))
        for f in old_files:
            if "_v2_" not in f.name:
                dest = ARCHIVE_DIR / f.name
                f.rename(dest)
                logger.info(f"Archived: {f.name}")

    if args.create_training:
        create_training_dataset_v2()
    elif args.cumulative or not args.year:
        datasets = create_cumulative_datasets_v2()
        print_summary_v2(datasets)
    elif args.year:
        df = load_and_parse_flood_records(args.year)
        if df is not None:
            station_data = load_pagasa_all_stations()
            merged = merge_flood_records_with_weather(df, station_data)
            output = PROCESSED_DIR / f"processed_flood_records_v2_{args.year}.csv"
            merged.to_csv(output, index=False)
            logger.info(f"Processed {args.year}: {len(merged)} records -> {output}")

    logger.info("Preprocessing complete!")


if __name__ == "__main__":
    main()
