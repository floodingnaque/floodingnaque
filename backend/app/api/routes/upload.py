"""
File Upload Routes.

Provides endpoints for uploading historical weather data via CSV/Excel files.
Supports bulk data ingestion with validation and error reporting.
"""

import csv
import io
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.api.middleware.auth import require_api_key
from app.api.middleware.rate_limit import limiter
from app.models.db import WeatherData, get_db_session
from app.utils.api_constants import (
    HTTP_BAD_REQUEST,
    HTTP_INTERNAL_ERROR,
    HTTP_OK,
)
from app.utils.api_responses import api_error
from flask import Blueprint, g, jsonify, request

logger = logging.getLogger(__name__)

upload_bp = Blueprint("upload", __name__)

# Configuration
MAX_FILE_SIZE_MB = int(os.getenv("UPLOAD_MAX_FILE_SIZE_MB", "10"))
MAX_ROWS_PER_UPLOAD = int(os.getenv("UPLOAD_MAX_ROWS", "10000"))
ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}

# Required and optional columns
REQUIRED_COLUMNS = {"temperature", "humidity", "precipitation", "timestamp"}
OPTIONAL_COLUMNS = {
    "wind_speed",
    "pressure",
    "source",
    "location_lat",
    "location_lon",
    "tide_height",
    "tide_trend",
    "tide_risk_factor",
    "hours_until_high_tide",
    "satellite_precipitation_rate",
    "precipitation_1h",
    "precipitation_3h",
    "precipitation_24h",
    "data_quality",
    "dataset",
}


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Magic bytes for MIME-type validation (prevents extension spoofing)
_MAGIC_SIGNATURES: Dict[str, List[bytes]] = {
    "csv": [],  # CSV has no fixed magic bytes; validated via content parsing
    "xlsx": [b"PK\x03\x04"],  # ZIP-based Office Open XML
    "xls": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],  # OLE2 Compound Document
}


def validate_file_content_type(file_storage, extension: str) -> bool:
    """
    Validate that the first bytes of the uploaded file match the
    expected file type, preventing extension-spoofing attacks.

    For CSV files the magic-byte check is skipped because plain text
    has no fixed signature; instead CSV validity is verified later
    during content parsing.
    """
    if extension == "csv":
        return True  # validated later during parsing
    expected = _MAGIC_SIGNATURES.get(extension, [])
    if not expected:
        return True
    header = file_storage.read(8)
    file_storage.seek(0)  # rewind for downstream consumers
    return any(header.startswith(sig) for sig in expected)


def _sanitize_error_messages(errors: List[str], max_errors: int = 50) -> List[str]:
    """
    Sanitize error messages to prevent information exposure.

    Ensures only safe, generic error messages are returned to clients.
    Truncates to max_errors to limit response size.
    """
    # Define allowed safe message patterns
    safe_patterns = [
        "Row ",
        "Data validation failed",
        "CSV parsing error",
        "Excel parsing error",
        "Missing required columns",
        "Maximum row limit",
        "Invalid CSV format",
        "Invalid file format",
        "is empty",
        "has no headers",
    ]

    sanitized = []
    for error in errors[:max_errors]:
        # Check if error matches safe patterns
        is_safe = any(pattern in error for pattern in safe_patterns)
        if is_safe:
            sanitized.append(error)
        else:
            # Replace with generic message for unknown error patterns
            sanitized.append("Data validation error")

    return sanitized


def parse_csv_content(content: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parse CSV content and validate rows.

    Returns:
        Tuple of (valid_rows, error_messages)
    """
    errors = []
    valid_rows = []

    try:
        reader = csv.DictReader(io.StringIO(content))
        headers = reader.fieldnames

        if not headers:
            return [], ["CSV file is empty or has no headers"]

        # Normalize headers (lowercase, strip whitespace)
        header_map = {h.lower().strip(): h for h in headers}

        # Check required columns
        missing_required = REQUIRED_COLUMNS - set(header_map.keys())
        if missing_required:
            return [], [f'Missing required columns: {", ".join(missing_required)}']

        for row_num, row in enumerate(reader, start=2):  # Start from 2 (header is row 1)
            if row_num > MAX_ROWS_PER_UPLOAD + 1:
                errors.append(f"Maximum row limit ({MAX_ROWS_PER_UPLOAD}) exceeded")
                break

            try:
                parsed_row = _parse_row(row, header_map, row_num)
                if parsed_row:
                    valid_rows.append(parsed_row)
            except ValueError:
                # Use generic message to avoid exposing exception details
                errors.append(f"Row {row_num}: Data validation failed")

    except csv.Error:
        # Use generic message to avoid exposing exception details
        errors.append("CSV parsing error: Invalid CSV format")

    return valid_rows, errors


def _parse_row(row: Dict[str, str], header_map: Dict[str, str], row_num: int) -> Optional[Dict[str, Any]]:
    """Parse and validate a single row."""
    parsed = {}

    # Parse required fields
    try:
        temp_key = header_map.get("temperature", "temperature")
        parsed["temperature"] = float(row.get(temp_key, "").strip())
        if parsed["temperature"] < 173.15 or parsed["temperature"] > 333.15:
            raise ValueError(f'Temperature {parsed["temperature"]} out of valid range (173.15K - 333.15K)')
    except ValueError as e:
        if "could not convert" in str(e).lower():
            raise ValueError("Invalid temperature value")
        raise

    try:
        humidity_key = header_map.get("humidity", "humidity")
        parsed["humidity"] = float(row.get(humidity_key, "").strip())
        if parsed["humidity"] < 0 or parsed["humidity"] > 100:
            raise ValueError(f'Humidity {parsed["humidity"]} out of valid range (0-100)')
    except ValueError as e:
        if "could not convert" in str(e).lower():
            raise ValueError("Invalid humidity value")
        raise

    try:
        precip_key = header_map.get("precipitation", "precipitation")
        parsed["precipitation"] = float(row.get(precip_key, "").strip())
        if parsed["precipitation"] < 0:
            raise ValueError("Precipitation cannot be negative")
    except ValueError as e:
        if "could not convert" in str(e).lower():
            raise ValueError("Invalid precipitation value")
        raise

    # Parse timestamp
    try:
        ts_key = header_map.get("timestamp", "timestamp")
        ts_str = row.get(ts_key, "").strip()
        # Try multiple date formats
        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"]:
            try:
                parsed["timestamp"] = datetime.strptime(ts_str.replace("Z", ""), fmt)
                break
            except ValueError:
                continue
        else:
            # Try ISO format with timezone
            try:
                parsed["timestamp"] = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except ValueError:
                raise ValueError(f"Invalid timestamp format: {ts_str}")
    except ValueError:
        raise ValueError("Invalid timestamp format")

    # Parse optional fields
    for field in OPTIONAL_COLUMNS:
        key = header_map.get(field, field)
        value = row.get(key, "").strip() if key in row else ""

        if value:
            try:
                if field in (
                    "wind_speed",
                    "pressure",
                    "location_lat",
                    "location_lon",
                    "tide_height",
                    "tide_risk_factor",
                    "hours_until_high_tide",
                    "satellite_precipitation_rate",
                    "precipitation_1h",
                    "precipitation_3h",
                    "precipitation_24h",
                    "data_quality",
                ):
                    parsed[field] = float(value)
                elif field in ("source", "tide_trend", "dataset"):
                    parsed[field] = value
            except ValueError:
                # Skip invalid optional values
                pass

    return parsed


def parse_excel_content(file_content: bytes) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parse Excel file content and validate rows.

    Returns:
        Tuple of (valid_rows, error_messages)
    """
    errors = []
    valid_rows = []

    try:
        import pandas as pd

        # Read Excel file
        df = pd.read_excel(io.BytesIO(file_content))

        if df.empty:
            return [], ["Excel file is empty"]

        # Normalize column names
        df.columns = df.columns.str.lower().str.strip()

        # Check required columns
        missing_required = REQUIRED_COLUMNS - set(df.columns)
        if missing_required:
            return [], [f'Missing required columns: {", ".join(missing_required)}']

        # Limit rows
        if len(df) > MAX_ROWS_PER_UPLOAD:
            errors.append(
                f"Maximum row limit ({MAX_ROWS_PER_UPLOAD}) exceeded, processing first {MAX_ROWS_PER_UPLOAD} rows"
            )
            df = df.head(MAX_ROWS_PER_UPLOAD)

        for row_num, row in df.iterrows():
            try:
                parsed_row = _parse_excel_row(row, row_num + 2)  # +2 for 1-indexing and header
                if parsed_row:
                    valid_rows.append(parsed_row)
            except ValueError:
                # Use generic message to avoid exposing exception details
                errors.append(f"Row {row_num + 2}: Data validation failed")

    except ImportError:
        errors.append("Excel processing requires pandas and openpyxl. Install with: pip install pandas openpyxl")
    except Exception:
        # Use generic message to avoid exposing exception details
        errors.append("Excel parsing error: Invalid file format or corrupted data")

    return valid_rows, errors


def _parse_excel_row(row, row_num: int) -> Optional[Dict[str, Any]]:
    """Parse and validate a single Excel row."""
    import pandas as pd

    parsed = {}

    # Parse required fields
    try:
        temp = row.get("temperature")
        if pd.isna(temp):
            raise ValueError("Temperature is required")
        parsed["temperature"] = float(temp)
        if parsed["temperature"] < 173.15 or parsed["temperature"] > 333.15:
            raise ValueError("Temperature out of valid range (173.15K - 333.15K)")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid temperature: {e}")

    try:
        humidity = row.get("humidity")
        if pd.isna(humidity):
            raise ValueError("Humidity is required")
        parsed["humidity"] = float(humidity)
        if parsed["humidity"] < 0 or parsed["humidity"] > 100:
            raise ValueError("Humidity out of valid range (0-100)")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid humidity: {e}")

    try:
        precip = row.get("precipitation")
        if pd.isna(precip):
            raise ValueError("Precipitation is required")
        parsed["precipitation"] = float(precip)
        if parsed["precipitation"] < 0:
            raise ValueError("Precipitation cannot be negative")
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid precipitation: {e}")

    # Parse timestamp
    try:
        ts = row.get("timestamp")
        if pd.isna(ts):
            raise ValueError("Timestamp is required")
        if isinstance(ts, (datetime, pd.Timestamp)):
            parsed["timestamp"] = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
        else:
            parsed["timestamp"] = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except Exception as e:
        raise ValueError(f"Invalid timestamp: {e}")

    # Parse optional fields
    for field in OPTIONAL_COLUMNS:
        value = row.get(field)
        if not pd.isna(value):
            try:
                if field in (
                    "wind_speed",
                    "pressure",
                    "location_lat",
                    "location_lon",
                    "tide_height",
                    "tide_risk_factor",
                    "hours_until_high_tide",
                    "satellite_precipitation_rate",
                    "precipitation_1h",
                    "precipitation_3h",
                    "precipitation_24h",
                    "data_quality",
                ):
                    parsed[field] = float(value)
                elif field in ("source", "tide_trend", "dataset"):
                    parsed[field] = str(value)
            except (ValueError, TypeError):
                pass  # Skip invalid optional values

    return parsed


@upload_bp.route("/csv", methods=["POST"])
@require_api_key
@limiter.limit("10 per hour")
def upload_csv():
    """
    Upload historical weather data via CSV file.

    Required columns: temperature, humidity, precipitation, timestamp
    Optional columns: wind_speed, pressure, source, location_lat, location_lon,
                     tide_height, tide_trend, tide_risk_factor, hours_until_high_tide,
                     satellite_precipitation_rate, precipitation_1h, precipitation_3h,
                     precipitation_24h, data_quality, dataset

    Temperature must be in Kelvin (173.15K - 333.15K)
    Humidity as percentage (0-100)
    Precipitation in mm (>= 0)
    Timestamp in ISO format or common date formats

    Returns:
        200: Upload successful with summary
        400: Validation errors
    ---
    tags:
      - Upload
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: file
        type: file
        required: true
        description: CSV file with weather data
      - in: formData
        name: skip_errors
        type: boolean
        default: false
        description: Continue processing even if some rows have errors
    responses:
      200:
        description: Upload results
      400:
        description: Validation errors
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        # Check if file is present
        if "file" not in request.files:
            return api_error("ValidationError", "No file provided", HTTP_BAD_REQUEST, request_id)

        file = request.files["file"]

        if file.filename == "":
            return api_error("ValidationError", "No file selected", HTTP_BAD_REQUEST, request_id)

        if not file.filename.lower().endswith(".csv"):
            return api_error("ValidationError", "File must be a CSV file", HTTP_BAD_REQUEST, request_id)

        # Validate content type via magic bytes (prevents extension spoofing)
        if not validate_file_content_type(file, "csv"):
            return api_error("ValidationError", "File content does not match CSV format", HTTP_BAD_REQUEST, request_id)

        # Check file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Seek back to start

        if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
            return api_error(
                "ValidationError", f"File exceeds maximum size of {MAX_FILE_SIZE_MB}MB", HTTP_BAD_REQUEST, request_id
            )

        # Read and parse CSV
        skip_errors = request.form.get("skip_errors", "false").lower() == "true"
        content = file.read().decode("utf-8")

        valid_rows, errors = parse_csv_content(content)

        if not valid_rows and errors:
            return api_error(
                "ValidationError",
                "No valid rows found",
                HTTP_BAD_REQUEST,
                request_id,
                details={"errors": _sanitize_error_messages(errors)},
            )

        if errors and not skip_errors:
            return api_error(
                "ValidationError",
                "Validation errors found",
                HTTP_BAD_REQUEST,
                request_id,
                details={"errors": _sanitize_error_messages(errors), "valid_rows": len(valid_rows)},
            )

        # Insert valid rows into database
        inserted_count = 0
        with get_db_session() as session:
            for row_data in valid_rows:
                weather_data = WeatherData(
                    temperature=row_data["temperature"],
                    humidity=row_data["humidity"],
                    precipitation=row_data["precipitation"],
                    timestamp=row_data["timestamp"],
                    wind_speed=row_data.get("wind_speed"),
                    pressure=row_data.get("pressure"),
                    source=row_data.get("source", "CSV_Upload"),
                    location_lat=row_data.get("location_lat"),
                    location_lon=row_data.get("location_lon"),
                    tide_height=row_data.get("tide_height"),
                    tide_trend=row_data.get("tide_trend"),
                    tide_risk_factor=row_data.get("tide_risk_factor"),
                    hours_until_high_tide=row_data.get("hours_until_high_tide"),
                    satellite_precipitation_rate=row_data.get("satellite_precipitation_rate"),
                    precipitation_1h=row_data.get("precipitation_1h"),
                    precipitation_3h=row_data.get("precipitation_3h"),
                    precipitation_24h=row_data.get("precipitation_24h"),
                    data_quality=row_data.get("data_quality"),
                    dataset=row_data.get("dataset"),
                )
                session.add(weather_data)
                inserted_count += 1

        logger.info(f"CSV upload completed: {inserted_count} rows inserted [{request_id}]")

        return (
            jsonify(
                {
                    "success": True,
                    "message": f"Successfully uploaded {inserted_count} weather data records",
                    "summary": {
                        "total_rows_processed": len(valid_rows) + len(errors),
                        "rows_inserted": inserted_count,
                        "rows_skipped": len(errors),
                        "errors": _sanitize_error_messages(errors) if skip_errors and errors else [],
                    },
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception:
        logger.error(f"CSV upload failed [{request_id}]")
        return api_error("UploadFailed", "Failed to process CSV file", HTTP_INTERNAL_ERROR, request_id)


@upload_bp.route("/excel", methods=["POST"])
@require_api_key
@limiter.limit("10 per hour")
def upload_excel():
    """
    Upload historical weather data via Excel file (.xlsx, .xls).

    Required columns: temperature, humidity, precipitation, timestamp
    Optional columns: wind_speed, pressure, source, location_lat, location_lon,
                     tide_height, tide_trend, tide_risk_factor, hours_until_high_tide,
                     satellite_precipitation_rate, precipitation_1h, precipitation_3h,
                     precipitation_24h, data_quality, dataset

    Returns:
        200: Upload successful with summary
        400: Validation errors
    ---
    tags:
      - Upload
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: file
        type: file
        required: true
        description: Excel file with weather data
      - in: formData
        name: skip_errors
        type: boolean
        default: false
        description: Continue processing even if some rows have errors
    responses:
      200:
        description: Upload results
      400:
        description: Validation errors
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        # Check if file is present
        if "file" not in request.files:
            return api_error("ValidationError", "No file provided", HTTP_BAD_REQUEST, request_id)

        file = request.files["file"]

        if file.filename == "":
            return api_error("ValidationError", "No file selected", HTTP_BAD_REQUEST, request_id)

        if not (file.filename.lower().endswith(".xlsx") or file.filename.lower().endswith(".xls")):
            return api_error(
                "ValidationError", "File must be an Excel file (.xlsx or .xls)", HTTP_BAD_REQUEST, request_id
            )

        # Validate content type via magic bytes (prevents extension spoofing)
        ext = "xlsx" if file.filename.lower().endswith(".xlsx") else "xls"
        if not validate_file_content_type(file, ext):
            return api_error(
                "ValidationError",
                "File content does not match the expected Excel format",
                HTTP_BAD_REQUEST,
                request_id,
            )

        # Check file size
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
            return api_error(
                "ValidationError", f"File exceeds maximum size of {MAX_FILE_SIZE_MB}MB", HTTP_BAD_REQUEST, request_id
            )

        # Read and parse Excel
        skip_errors = request.form.get("skip_errors", "false").lower() == "true"
        content = file.read()

        valid_rows, errors = parse_excel_content(content)

        if not valid_rows and errors:
            return api_error(
                "ValidationError",
                "No valid rows found",
                HTTP_BAD_REQUEST,
                request_id,
                details={"errors": _sanitize_error_messages(errors)},
            )

        if errors and not skip_errors:
            return api_error(
                "ValidationError",
                "Validation errors found",
                HTTP_BAD_REQUEST,
                request_id,
                details={"errors": _sanitize_error_messages(errors), "valid_rows": len(valid_rows)},
            )

        # Insert valid rows
        inserted_count = 0
        with get_db_session() as session:
            for row_data in valid_rows:
                weather_data = WeatherData(
                    temperature=row_data["temperature"],
                    humidity=row_data["humidity"],
                    precipitation=row_data["precipitation"],
                    timestamp=row_data["timestamp"],
                    wind_speed=row_data.get("wind_speed"),
                    pressure=row_data.get("pressure"),
                    source=row_data.get("source", "Excel_Upload"),
                    location_lat=row_data.get("location_lat"),
                    location_lon=row_data.get("location_lon"),
                    tide_height=row_data.get("tide_height"),
                    tide_trend=row_data.get("tide_trend"),
                    tide_risk_factor=row_data.get("tide_risk_factor"),
                    hours_until_high_tide=row_data.get("hours_until_high_tide"),
                    satellite_precipitation_rate=row_data.get("satellite_precipitation_rate"),
                    precipitation_1h=row_data.get("precipitation_1h"),
                    precipitation_3h=row_data.get("precipitation_3h"),
                    precipitation_24h=row_data.get("precipitation_24h"),
                    data_quality=row_data.get("data_quality"),
                    dataset=row_data.get("dataset"),
                )
                session.add(weather_data)
                inserted_count += 1

        logger.info(f"Excel upload completed: {inserted_count} rows inserted [{request_id}]")

        return (
            jsonify(
                {
                    "success": True,
                    "message": f"Successfully uploaded {inserted_count} weather data records",
                    "summary": {
                        "total_rows_processed": len(valid_rows) + len(errors),
                        "rows_inserted": inserted_count,
                        "rows_skipped": len(errors),
                        "errors": _sanitize_error_messages(errors) if skip_errors and errors else [],
                    },
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception:
        logger.error(f"Excel upload failed [{request_id}]")
        return api_error("UploadFailed", "Failed to process Excel file", HTTP_INTERNAL_ERROR, request_id)


@upload_bp.route("/template", methods=["GET"])
@limiter.limit("30 per minute")
def get_upload_template():
    """
    Get a CSV template for data upload.

    Returns:
        200: CSV template with headers and sample row
    ---
    tags:
      - Upload
    responses:
      200:
        description: CSV template
    """
    request_id = getattr(g, "request_id", "unknown")

    template = (
        "temperature,humidity,precipitation,timestamp,wind_speed,pressure,source,location_lat,location_lon\n"
        "298.15,75.5,10.2,2024-01-15T10:00:00,5.5,1013.25,Manual,14.4793,121.0198\n"
    )

    return (
        jsonify(
            {
                "success": True,
                "template": template,
                "required_columns": list(REQUIRED_COLUMNS),
                "optional_columns": list(OPTIONAL_COLUMNS),
                "notes": {
                    "temperature": "Temperature in Kelvin (173.15K - 333.15K)",
                    "humidity": "Humidity percentage (0-100)",
                    "precipitation": "Precipitation in mm (>= 0)",
                    "timestamp": "ISO format (YYYY-MM-DDTHH:MM:SS) or common date formats",
                },
                "request_id": request_id,
            }
        ),
        HTTP_OK,
    )


@upload_bp.route("/validate", methods=["POST"])
@require_api_key
@limiter.limit("30 per minute")
def validate_upload():
    """
    Validate a CSV/Excel file without inserting data.

    Returns:
        200: Validation results
    ---
    tags:
      - Upload
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: file
        type: file
        required: true
    responses:
      200:
        description: Validation results
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        if "file" not in request.files:
            return api_error("ValidationError", "No file provided", HTTP_BAD_REQUEST, request_id)

        file = request.files["file"]

        if file.filename == "":
            return api_error("ValidationError", "No file selected", HTTP_BAD_REQUEST, request_id)

        filename = file.filename.lower()
        content = file.read()

        if filename.endswith(".csv"):
            valid_rows, errors = parse_csv_content(content.decode("utf-8"))
        elif filename.endswith(".xlsx") or filename.endswith(".xls"):
            valid_rows, errors = parse_excel_content(content)
        else:
            return api_error(
                "ValidationError", "Unsupported file format. Use CSV or Excel files.", HTTP_BAD_REQUEST, request_id
            )

        return (
            jsonify(
                {
                    "success": True,
                    "validation": {
                        "valid": len(errors) == 0,
                        "total_rows": len(valid_rows) + len(errors),
                        "valid_rows": len(valid_rows),
                        "invalid_rows": len(errors),
                        "errors": _sanitize_error_messages(errors),  # Sanitize to prevent info exposure
                        "errors_truncated": len(errors) > 50,
                    },
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception:
        logger.error(f"File validation failed [{request_id}]")
        return api_error("ValidationFailed", "Failed to validate file", HTTP_INTERNAL_ERROR, request_id)
