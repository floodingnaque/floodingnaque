"""
Unit tests for schemas.
"""

import pytest
from app.api.schemas.prediction import PredictRequestSchema
from app.api.schemas.weather import IngestRequestSchema, parse_json_safely


class TestIngestRequestSchema:
    """Tests for IngestRequestSchema validation."""

    def test_valid_coordinates(self):
        """Test valid coordinate values."""
        schema = IngestRequestSchema(lat=14.4793, lon=121.0198)
        errors = schema.validate()
        assert len(errors) == 0

    def test_invalid_latitude(self):
        """Test invalid latitude value."""
        schema = IngestRequestSchema(lat=91.0, lon=121.0198)
        errors = schema.validate()
        assert len(errors) > 0
        assert any("lat" in error for error in errors)

    def test_invalid_longitude(self):
        """Test invalid longitude value."""
        schema = IngestRequestSchema(lat=14.4793, lon=181.0)
        errors = schema.validate()
        assert len(errors) > 0
        assert any("lon" in error for error in errors)

    def test_optional_coordinates(self):
        """Test that coordinates are optional."""
        schema = IngestRequestSchema()
        errors = schema.validate()
        assert len(errors) == 0


class TestPredictRequestSchema:
    """Tests for PredictRequestSchema validation."""

    def test_valid_weather_data(self):
        """Test valid weather data."""
        schema = PredictRequestSchema(temperature=298.15, humidity=65.0, precipitation=10.5)
        errors = schema.validate()
        assert len(errors) == 0

    def test_invalid_humidity(self):
        """Test invalid humidity value."""
        schema = PredictRequestSchema(temperature=298.15, humidity=150.0, precipitation=10.5)  # Invalid: > 100
        errors = schema.validate()
        assert len(errors) > 0

    def test_negative_precipitation(self):
        """Test negative precipitation value."""
        schema = PredictRequestSchema(temperature=298.15, humidity=65.0, precipitation=-5.0)  # Invalid: negative
        errors = schema.validate()
        assert len(errors) > 0


class TestJsonParsing:
    """Tests for JSON parsing utilities."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON."""
        data = b'{"lat": 14.6, "lon": 120.98}'
        result = parse_json_safely(data)
        assert result is not None
        assert result["lat"] == 14.6
        assert result["lon"] == 120.98

    def test_parse_empty_bytes(self):
        """Test parsing empty bytes."""
        result = parse_json_safely(b"")
        assert result == {}

    def test_parse_none(self):
        """Test parsing None."""
        result = parse_json_safely(None)
        assert result == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
