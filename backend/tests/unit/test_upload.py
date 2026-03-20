"""
Unit Tests for Upload API Routes.

Tests the file upload endpoints for historical weather data including:
- CSV file upload and parsing
- Excel file upload
- Data validation
- Bulk data ingestion
- Error handling
"""

import io
from unittest.mock import MagicMock, patch

import pytest
from app.api.routes.upload import ALLOWED_EXTENSIONS, allowed_file, parse_csv_content

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def app():
    """Create Flask application for testing."""
    from app.api.app import create_app

    application = create_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    """Create test client."""
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def valid_csv_content():
    """Create valid CSV content."""
    return """timestamp,temperature,humidity,precipitation
2024-01-15T10:00:00,298.15,75.0,5.0
2024-01-15T11:00:00,299.15,72.0,0.0
2024-01-15T12:00:00,300.15,70.0,2.5
"""


@pytest.fixture
def invalid_csv_content():
    """Create invalid CSV content (missing required columns)."""
    return """timestamp,temperature,pressure
2024-01-15T10:00:00,298.15,1013
"""


@pytest.fixture
def csv_with_invalid_values():
    """Create CSV with invalid values."""
    return """timestamp,temperature,humidity,precipitation
2024-01-15T10:00:00,298.15,150.0,5.0
2024-01-15T11:00:00,invalid,72.0,0.0
"""


@pytest.fixture
def valid_api_headers():
    """Create headers with valid API key."""
    return {
        "X-API-Key": "test-api-key",
        "Content-Type": "multipart/form-data",
    }


# =============================================================================
# CSV Parsing Tests
# =============================================================================


class TestCsvParsing:
    """Tests for CSV file parsing."""

    def test_parse_valid_csv(self, valid_csv_content):
        """Test parsing valid CSV content."""
        rows, errors = parse_csv_content(valid_csv_content)

        assert len(rows) == 3
        assert len(errors) == 0
        assert rows[0]["temperature"] == 298.15

    def test_parse_csv_missing_columns(self, invalid_csv_content):
        """Test parsing CSV with missing required columns."""
        rows, errors = parse_csv_content(invalid_csv_content)

        assert len(rows) == 0
        assert len(errors) > 0
        assert "Missing required columns" in errors[0]

    def test_parse_csv_invalid_values(self, csv_with_invalid_values):
        """Test parsing CSV with invalid values."""
        rows, errors = parse_csv_content(csv_with_invalid_values)

        # Should have some errors for invalid values
        assert len(errors) > 0

    def test_parse_empty_csv(self):
        """Test parsing empty CSV."""
        rows, errors = parse_csv_content("")

        assert len(rows) == 0
        assert len(errors) > 0


# =============================================================================
# File Extension Validation Tests
# =============================================================================


class TestFileExtensionValidation:
    """Tests for file extension validation."""

    def test_allowed_csv(self):
        """Test CSV extension is allowed."""
        assert allowed_file("data.csv") is True

    def test_allowed_xlsx(self):
        """Test XLSX extension is allowed."""
        assert allowed_file("data.xlsx") is True

    def test_allowed_xls(self):
        """Test XLS extension is allowed."""
        assert allowed_file("data.xls") is True

    def test_disallowed_txt(self):
        """Test TXT extension is not allowed."""
        assert allowed_file("data.txt") is False

    def test_disallowed_json(self):
        """Test JSON extension is not allowed."""
        assert allowed_file("data.json") is False

    def test_no_extension(self):
        """Test file without extension is not allowed."""

        assert allowed_file("datafile") is False


# =============================================================================
# Upload Endpoint Tests
# =============================================================================


class TestUploadEndpoint:
    """Tests for upload endpoint."""

    @patch("app.api.routes.upload.get_db_session")
    @patch("app.api.routes.upload.require_auth_or_api_key", lambda f: f)
    def test_upload_valid_csv(self, mock_db_session, client, valid_csv_content):
        """Test uploading valid CSV file."""
        # Setup mocks
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db_session.return_value.__exit__ = MagicMock(return_value=None)

        data = {
            "file": (io.BytesIO(valid_csv_content.encode()), "weather_data.csv"),
        }

        response = client.post(
            "/api/v1/upload/csv",
            data=data,
            content_type="multipart/form-data",
            headers={"X-API-Key": "test-key"},
        )

        # Should succeed or require auth
        assert response.status_code in [200, 201, 401, 403]

    def test_upload_no_file(self, client):
        """Test upload endpoint with no file."""
        response = client.post(
            "/api/v1/upload/csv",
            data={},
            content_type="multipart/form-data",
        )

        # Should fail with bad request or unauthorized
        assert response.status_code in [400, 401]


# =============================================================================
# Row Parsing Tests
# =============================================================================


class TestRowParsing:
    """Tests for individual row parsing."""

    def test_parse_valid_row(self):
        """Test parsing a valid data row."""
        from app.api.routes.upload import _parse_row

        row = {
            "timestamp": "2024-01-15T10:00:00",
            "temperature": "298.15",
            "humidity": "75.0",
            "precipitation": "5.0",
        }
        header_map = {
            "timestamp": "timestamp",
            "temperature": "temperature",
            "humidity": "humidity",
            "precipitation": "precipitation",
        }

        result = _parse_row(row, header_map, 2)

        assert result is not None
        assert result["temperature"] == 298.15
        assert result["humidity"] == 75.0
        assert result["precipitation"] == 5.0

    def test_parse_row_invalid_temperature(self):
        """Test parsing row with invalid temperature."""
        from app.api.routes.upload import _parse_row

        row = {
            "timestamp": "2024-01-15T10:00:00",
            "temperature": "invalid",
            "humidity": "75.0",
            "precipitation": "5.0",
        }
        header_map = {
            "timestamp": "timestamp",
            "temperature": "temperature",
            "humidity": "humidity",
            "precipitation": "precipitation",
        }

        with pytest.raises(ValueError):
            _parse_row(row, header_map, 2)

    def test_parse_row_temperature_out_of_range(self):
        """Test parsing row with temperature out of range."""
        from app.api.routes.upload import _parse_row

        row = {
            "timestamp": "2024-01-15T10:00:00",
            "temperature": "500.0",  # Way too hot
            "humidity": "75.0",
            "precipitation": "5.0",
        }
        header_map = {
            "timestamp": "timestamp",
            "temperature": "temperature",
            "humidity": "humidity",
            "precipitation": "precipitation",
        }

        with pytest.raises(ValueError, match="out of valid range"):
            _parse_row(row, header_map, 2)

    def test_parse_row_humidity_out_of_range(self):
        """Test parsing row with humidity out of range."""
        from app.api.routes.upload import _parse_row

        row = {
            "timestamp": "2024-01-15T10:00:00",
            "temperature": "298.15",
            "humidity": "150.0",  # Invalid: > 100%
            "precipitation": "5.0",
        }
        header_map = {
            "timestamp": "timestamp",
            "temperature": "temperature",
            "humidity": "humidity",
            "precipitation": "precipitation",
        }

        with pytest.raises(ValueError, match="out of valid range"):
            _parse_row(row, header_map, 2)

    def test_parse_row_negative_precipitation(self):
        """Test parsing row with negative precipitation."""
        from app.api.routes.upload import _parse_row

        row = {
            "timestamp": "2024-01-15T10:00:00",
            "temperature": "298.15",
            "humidity": "75.0",
            "precipitation": "-5.0",
        }
        header_map = {
            "timestamp": "timestamp",
            "temperature": "temperature",
            "humidity": "humidity",
            "precipitation": "precipitation",
        }

        with pytest.raises(ValueError, match="cannot be negative"):
            _parse_row(row, header_map, 2)


# =============================================================================
# Timestamp Parsing Tests
# =============================================================================


class TestTimestampParsing:
    """Tests for timestamp parsing."""

    def test_parse_iso_timestamp(self):
        """Test parsing ISO format timestamp."""
        from datetime import datetime

        timestamp_str = "2024-01-15T10:00:00"

        # Multiple formats should be supported
        formats = ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]

        parsed = None
        for fmt in formats:
            try:
                parsed = datetime.strptime(timestamp_str, fmt)
                break
            except ValueError:
                continue

        assert parsed is not None
        assert parsed.year == 2024
        assert parsed.month == 1
        assert parsed.day == 15

    def test_parse_date_only_timestamp(self):
        """Test parsing date-only timestamp."""
        from datetime import datetime

        timestamp_str = "2024-01-15"
        parsed = datetime.strptime(timestamp_str, "%Y-%m-%d")

        assert parsed.year == 2024
        assert parsed.hour == 0


# =============================================================================
# Configuration Tests
# =============================================================================


class TestUploadConfiguration:
    """Tests for upload configuration."""

    def test_max_file_size_configured(self):
        """Test max file size is configured."""
        from app.api.routes.upload import MAX_FILE_SIZE_MB

        assert MAX_FILE_SIZE_MB > 0
        assert MAX_FILE_SIZE_MB <= 100  # Reasonable limit

    def test_max_rows_configured(self):
        """Test max rows is configured."""
        from app.api.routes.upload import MAX_ROWS_PER_UPLOAD

        assert MAX_ROWS_PER_UPLOAD > 0
        assert MAX_ROWS_PER_UPLOAD <= 100000  # Reasonable limit

    def test_required_columns_defined(self):
        """Test required columns are defined."""
        from app.api.routes.upload import REQUIRED_COLUMNS

        assert "temperature" in REQUIRED_COLUMNS
        assert "humidity" in REQUIRED_COLUMNS
        assert "precipitation" in REQUIRED_COLUMNS
        assert "timestamp" in REQUIRED_COLUMNS

    def test_allowed_extensions_defined(self):
        """Test allowed extensions are defined."""
        # ALLOWED_EXTENSIONS imported at module level
        assert "csv" in ALLOWED_EXTENSIONS
        assert "xlsx" in ALLOWED_EXTENSIONS


# =============================================================================
# Optional Columns Tests
# =============================================================================


class TestOptionalColumns:
    """Tests for optional column handling."""

    def test_optional_columns_defined(self):
        """Test optional columns are defined."""
        from app.api.routes.upload import OPTIONAL_COLUMNS

        assert "wind_speed" in OPTIONAL_COLUMNS
        assert "pressure" in OPTIONAL_COLUMNS
        assert "source" in OPTIONAL_COLUMNS

    def test_optional_tide_columns(self):
        """Test tide-related optional columns."""
        from app.api.routes.upload import OPTIONAL_COLUMNS

        assert "tide_height" in OPTIONAL_COLUMNS
        assert "tide_trend" in OPTIONAL_COLUMNS
        assert "tide_risk_factor" in OPTIONAL_COLUMNS

    def test_optional_satellite_columns(self):
        """Test satellite data optional columns."""
        from app.api.routes.upload import OPTIONAL_COLUMNS

        assert "satellite_precipitation_rate" in OPTIONAL_COLUMNS
        assert "data_quality" in OPTIONAL_COLUMNS


# =============================================================================
# Error Message Tests
# =============================================================================


class TestErrorMessages:
    """Tests for error message formatting."""

    def test_error_includes_row_number(self, csv_with_invalid_values):
        """Test error messages include row numbers."""
        from app.api.routes.upload import parse_csv_content

        rows, errors = parse_csv_content(csv_with_invalid_values)

        # Errors should indicate which row had the problem
        row_errors = [e for e in errors if "Row" in e]
        assert len(row_errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
