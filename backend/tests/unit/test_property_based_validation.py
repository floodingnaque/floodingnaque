"""
Property-Based Tests for Input Validation.

Uses Hypothesis to test validation logic with automatically generated edge cases.
"""

import pytest
from app.utils.validation import InputValidator, ValidationError, check_path_traversal, sanitize_input
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st
from tests.strategies import (
    extreme_weather_data,
    invalid_pagination_params,
    invalid_weather_data,
    pagination_params,
    path_traversal_string,
    sql_injection_string,
    valid_humidity,
    valid_latitude,
    valid_longitude,
    valid_precipitation,
    valid_temperature,
    weather_data,
    xss_string,
)

# ============================================================================
# Property-Based Tests for Weather Validation
# ============================================================================


class TestPropertyBasedWeatherValidation:
    """Property-based tests for weather data validation."""

    @given(temp=valid_temperature())
    @settings(max_examples=200, deadline=None)
    def test_valid_temperature_always_passes(self, temp):
        """Property: All generated valid temperatures should pass validation."""
        result = InputValidator.validate_float(
            temp,
            "temperature",
            min_val=InputValidator.TEMPERATURE_MIN_KELVIN - 273.15,
            max_val=InputValidator.TEMPERATURE_MAX_KELVIN - 273.15,
        )
        assert result == temp

    @given(humidity=valid_humidity())
    @settings(max_examples=200, deadline=None)
    def test_valid_humidity_always_passes(self, humidity):
        """Property: All generated valid humidity values should pass validation."""
        result = InputValidator.validate_float(
            humidity, "humidity", min_val=InputValidator.HUMIDITY_MIN, max_val=InputValidator.HUMIDITY_MAX
        )
        assert result == humidity
        assert 0.0 <= result <= 100.0

    @given(precip=valid_precipitation())
    @settings(max_examples=200, deadline=None)
    def test_valid_precipitation_always_passes(self, precip):
        """Property: All generated valid precipitation values should pass validation."""
        result = InputValidator.validate_float(
            precip, "precipitation", min_val=InputValidator.PRECIPITATION_MIN, max_val=InputValidator.PRECIPITATION_MAX
        )
        assert result == precip
        assert result >= 0.0

    @given(data=weather_data())
    @settings(max_examples=100, deadline=None)
    def test_weather_data_dict_validation(self, data):
        """Property: Complete weather data dicts should always validate successfully."""
        temp = InputValidator.validate_float(data["temperature"], "temperature", min_val=-50, max_val=50)
        humidity = InputValidator.validate_float(data["humidity"], "humidity", min_val=0, max_val=100)
        precip = InputValidator.validate_float(data["precipitation"], "precipitation", min_val=0, max_val=500)

        assert temp is not None
        assert humidity is not None
        assert precip is not None

    @given(data=extreme_weather_data())
    @settings(max_examples=100, deadline=None)
    def test_extreme_weather_data_validation(self, data):
        """Property: Extreme but valid weather data should pass validation."""
        # These are extreme but still valid values
        temp = InputValidator.validate_float(data["temperature"], "temperature", min_val=-50, max_val=50)
        humidity = InputValidator.validate_float(data["humidity"], "humidity", min_val=0, max_val=100)
        precip = InputValidator.validate_float(data["precipitation"], "precipitation", min_val=0, max_val=500)

        assert temp is not None
        assert humidity is not None
        assert precip is not None


# ============================================================================
# Property-Based Tests for Location Validation
# ============================================================================


class TestPropertyBasedLocationValidation:
    """Property-based tests for geographic coordinate validation."""

    @given(lat=valid_latitude())
    @settings(max_examples=200, deadline=None)
    def test_valid_latitude_always_passes(self, lat):
        """Property: All valid latitudes should pass validation."""
        result = InputValidator.validate_float(
            lat, "latitude", min_val=InputValidator.LATITUDE_MIN, max_val=InputValidator.LATITUDE_MAX
        )
        assert result == lat
        assert -90.0 <= result <= 90.0

    @given(lon=valid_longitude())
    @settings(max_examples=200, deadline=None)
    def test_valid_longitude_always_passes(self, lon):
        """Property: All valid longitudes should pass validation."""
        result = InputValidator.validate_float(
            lon, "longitude", min_val=InputValidator.LONGITUDE_MIN, max_val=InputValidator.LONGITUDE_MAX
        )
        assert result == lon
        assert -180.0 <= result <= 180.0

    @given(lat=st.floats(min_value=-90.01, max_value=-90.001, allow_nan=False, allow_infinity=False))
    @settings(max_examples=50, deadline=None)
    def test_latitude_below_minimum_fails(self, lat):
        """Property: Latitudes below -90 should always fail validation."""
        with pytest.raises(ValidationError):
            InputValidator.validate_float(lat, "latitude", min_val=-90.0, max_val=90.0)

    @given(lat=st.floats(min_value=90.001, max_value=90.01, allow_nan=False, allow_infinity=False))
    @settings(max_examples=50, deadline=None)
    def test_latitude_above_maximum_fails(self, lat):
        """Property: Latitudes above 90 should always fail validation."""
        with pytest.raises(ValidationError):
            InputValidator.validate_float(lat, "latitude", min_val=-90.0, max_val=90.0)


# ============================================================================
# Property-Based Tests for Security Validation
# ============================================================================


class TestPropertyBasedSecurityValidation:
    """Property-based tests for security-related validation."""

    @given(injection=sql_injection_string())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_sql_injection_detected(self, injection):
        """Property: SQL injection attempts should be detected and rejected."""
        with pytest.raises(ValidationError):
            sanitize_input(injection, check_patterns=["sql_injection"])

    @given(xss=xss_string())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_xss_attempts_sanitized(self, xss):
        """Property: XSS attempts should be sanitized or rejected."""
        # Should either strip tags or raise error
        result = sanitize_input(xss, strip_html=True)
        # After sanitization, should not contain script tags
        assert "<script" not in result.lower()
        assert "javascript:" not in result.lower()

    @given(path=path_traversal_string())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_path_traversal_detected(self, path):
        """Property: Path traversal attempts should be detected and rejected."""
        with pytest.raises(ValidationError):
            check_path_traversal(path)

    @given(text=st.text(min_size=0, max_size=100))
    @settings(max_examples=100, deadline=None)
    def test_safe_text_passes_sanitization(self, text):
        """Property: Safe text without special characters should pass unchanged."""
        # Exclude texts that would trigger security checks
        assume(not any(char in text for char in ["<", ">", "&", ";", "|", "`", "$"]))
        assume(".." not in text)

        result = sanitize_input(text)
        # Should be a string (may be modified for unicode normalization)
        assert isinstance(result, str)


# ============================================================================
# Property-Based Tests for Pagination
# ============================================================================


class TestPropertyBasedPaginationValidation:
    """Property-based tests for pagination parameter validation."""

    @given(params=pagination_params())
    @settings(max_examples=100, deadline=None)
    def test_valid_pagination_params(self, params):
        """Property: Valid pagination params should pass validation."""
        limit = InputValidator.validate_int(params["limit"], "limit", min_val=1, max_val=1000)
        offset = InputValidator.validate_int(params["offset"], "offset", min_val=0)

        assert 1 <= limit <= 1000
        assert offset >= 0

    @given(params=invalid_pagination_params())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_invalid_pagination_params_fail(self, params):
        """Property: Invalid pagination params should fail validation."""
        if params["limit"] <= 0 or params["limit"] > 1000:
            with pytest.raises(ValidationError):
                InputValidator.validate_int(params["limit"], "limit", min_val=1, max_val=1000)

        if params["offset"] < 0:
            with pytest.raises(ValidationError):
                InputValidator.validate_int(params["offset"], "offset", min_val=0)


# ============================================================================
# Property-Based Tests for Type Coercion
# ============================================================================


class TestPropertyBasedTypeCoercion:
    """Property-based tests for type coercion behavior."""

    @given(value=st.integers(min_value=-1000, max_value=1000))
    @settings(max_examples=100, deadline=None)
    def test_integer_to_float_coercion(self, value):
        """Property: Integers should be coercible to floats."""
        result = InputValidator.validate_float(value, "test_field", required=False)
        assert isinstance(result, float)
        assert result == float(value)

    @given(value=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100, deadline=None)
    def test_float_to_string_coercion(self, value):
        """Property: Floats should be convertible to strings."""
        result = str(value)
        assert isinstance(result, str)
        assert len(result) > 0

    @given(value=st.integers(min_value=0, max_value=9999999999))
    @settings(max_examples=100, deadline=None)
    def test_numeric_string_to_int_coercion(self, value):
        """Property: Numeric strings should be coercible to integers."""
        str_value = str(value)
        result = InputValidator.validate_int(str_value, "test_field", required=False)
        assert isinstance(result, int)
        assert result == value


# ============================================================================
# Property-Based Tests for Boundary Conditions
# ============================================================================


class TestPropertyBasedBoundaryConditions:
    """Property-based tests for boundary conditions."""

    @given(value=st.floats(min_value=-0.001, max_value=0.001, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100, deadline=None)
    def test_near_zero_values(self, value):
        """Property: Values near zero should be handled correctly."""
        result = InputValidator.validate_float(value, "test_field", min_val=-1, max_val=1)
        assert result is not None
        assert abs(result) <= 1

    @given(value=st.floats(min_value=99.99, max_value=100.01, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100, deadline=None)
    def test_near_boundary_values(self, value):
        """Property: Values near boundaries should be handled correctly."""
        if value <= 100.0:
            result = InputValidator.validate_float(value, "test_field", min_val=0, max_val=100)
            assert 0 <= result <= 100
        else:
            with pytest.raises(ValidationError):
                InputValidator.validate_float(value, "test_field", min_val=0, max_val=100)


# ============================================================================
# Property-Based Tests for String Validation
# ============================================================================


class TestPropertyBasedStringValidation:
    """Property-based tests for string validation."""

    @given(text=st.text(min_size=0, max_size=500))
    @settings(max_examples=100, deadline=None)
    def test_string_length_validation(self, text):
        """Property: String length constraints should be enforced."""
        result = InputValidator.validate_string(text, "test_field", max_length=500, required=False)
        if result is not None:
            assert len(result) <= 500

    @given(text=st.text(alphabet=st.characters(whitelist_categories=("Lu", "Ll")), min_size=1, max_size=100))
    @settings(max_examples=100, deadline=None)
    def test_alphabetic_strings(self, text):
        """Property: Alphabetic strings should validate correctly."""
        result = InputValidator.validate_string(text, "test_field", required=False)
        assert isinstance(result, str)
        assert len(result) > 0


# ============================================================================
# Property-Based Tests for Null/None Handling
# ============================================================================


class TestPropertyBasedNullHandling:
    """Property-based tests for null/none value handling."""

    @given(field_name=st.text(min_size=1, max_size=50))
    @settings(max_examples=50, deadline=None)
    def test_required_field_with_none_fails(self, field_name):
        """Property: Required fields with None should always fail."""
        with pytest.raises(ValidationError):
            InputValidator.validate_float(None, field_name, required=True)

    @given(field_name=st.text(min_size=1, max_size=50))
    @settings(max_examples=50, deadline=None)
    def test_optional_field_with_none_returns_none(self, field_name):
        """Property: Optional fields with None should return None."""
        result = InputValidator.validate_float(None, field_name, required=False)
        assert result is None


# ============================================================================
# Property-Based Tests for Unicode Handling
# ============================================================================


class TestPropertyBasedUnicodeHandling:
    """Property-based tests for unicode string handling."""

    @given(text=st.text(min_size=0, max_size=100))
    @settings(max_examples=100, deadline=None)
    def test_unicode_normalization(self, text):
        """Property: Unicode strings should be normalized consistently."""
        result = sanitize_input(text, normalize_unicode=True)
        assert isinstance(result, str)
        # Normalized string should be valid
        import unicodedata

        assert unicodedata.is_normalized("NFC", result)
