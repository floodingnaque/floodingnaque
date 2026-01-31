"""
Unit tests for app/utils/env_validation.py.

Tests for environment variable validation including validators,
specifications, and validation report generation.
"""

import os
from unittest.mock import patch

import pytest
from app.utils.env_validation import (
    ENV_VAR_SPECS,
    EnvVarSpec,
    ValidationReport,
    ValidationResult,
    ValidationSeverity,
    is_boolean,
    is_email,
    is_hex_key,
    is_non_negative_int,
    is_percentage,
    is_positive_int,
    is_postgres_url,
    is_redis_url,
    is_url,
    validate_all_env_vars,
    validate_env_var,
)


class TestValidationSeverity:
    """Tests for ValidationSeverity enum."""

    def test_severity_values(self):
        """Test all severity values exist."""
        assert ValidationSeverity.CRITICAL.value == "critical"
        assert ValidationSeverity.ERROR.value == "error"
        assert ValidationSeverity.WARNING.value == "warning"
        assert ValidationSeverity.INFO.value == "info"


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test ValidationResult can be created."""
        result = ValidationResult(
            name="TEST_VAR",
            valid=True,
            severity=ValidationSeverity.INFO,
            message="Test passed",
        )

        assert result.name == "TEST_VAR"
        assert result.valid is True
        assert result.severity == ValidationSeverity.INFO
        assert result.message == "Test passed"
        assert result.value_preview is None

    def test_validation_result_with_preview(self):
        """Test ValidationResult with value preview."""
        result = ValidationResult(
            name="SECRET_KEY",
            valid=True,
            severity=ValidationSeverity.INFO,
            message="Key set",
            value_preview="abcd...wxyz",
        )

        assert result.value_preview == "abcd...wxyz"


class TestEnvVarSpec:
    """Tests for EnvVarSpec dataclass."""

    def test_env_var_spec_defaults(self):
        """Test EnvVarSpec default values."""
        spec = EnvVarSpec(name="TEST_VAR")

        assert spec.name == "TEST_VAR"
        assert spec.required is False
        assert spec.required_in_prod is False
        assert spec.default is None
        assert spec.description == ""
        assert spec.validator is None
        assert spec.sensitive is False

    def test_env_var_spec_with_validator(self):
        """Test EnvVarSpec with custom validator."""
        spec = EnvVarSpec(
            name="PORT",
            validator=is_positive_int,
            validator_message="Must be positive integer",
        )

        assert spec.validator is is_positive_int
        assert spec.validator_message == "Must be positive integer"


class TestBuiltInValidators:
    """Tests for built-in validator functions."""

    class TestIsUrl:
        """Tests for is_url validator."""

        def test_valid_https_url(self):
            """Test valid HTTPS URL."""
            assert is_url("https://example.com") is True

        def test_valid_http_url(self):
            """Test valid HTTP URL."""
            assert is_url("http://localhost:8080") is True

        def test_valid_url_with_path(self):
            """Test valid URL with path."""
            assert is_url("https://example.com/path/to/resource") is True

        def test_invalid_url_no_protocol(self):
            """Test invalid URL without protocol."""
            assert is_url("example.com") is False

        def test_invalid_url_empty(self):
            """Test empty string."""
            assert is_url("") is False

    class TestIsEmail:
        """Tests for is_email validator."""

        def test_valid_email(self):
            """Test valid email."""
            assert is_email("test@example.com") is True

        def test_valid_email_with_subdomain(self):
            """Test valid email with subdomain."""
            assert is_email("user@mail.example.com") is True

        def test_invalid_email_no_at(self):
            """Test invalid email without @."""
            assert is_email("testexample.com") is False

        def test_invalid_email_no_domain(self):
            """Test invalid email without domain."""
            assert is_email("test@") is False

    class TestIsPositiveInt:
        """Tests for is_positive_int validator."""

        def test_positive_number(self):
            """Test positive integer."""
            assert is_positive_int("42") is True
            assert is_positive_int("1") is True

        def test_zero(self):
            """Test zero is not positive."""
            assert is_positive_int("0") is False

        def test_negative_number(self):
            """Test negative number."""
            assert is_positive_int("-5") is False

        def test_non_numeric(self):
            """Test non-numeric string."""
            assert is_positive_int("abc") is False

    class TestIsNonNegativeInt:
        """Tests for is_non_negative_int validator."""

        def test_positive_number(self):
            """Test positive integer."""
            assert is_non_negative_int("42") is True

        def test_zero(self):
            """Test zero is non-negative."""
            assert is_non_negative_int("0") is True

        def test_negative_number(self):
            """Test negative number."""
            assert is_non_negative_int("-5") is False

    class TestIsPercentage:
        """Tests for is_percentage validator."""

        def test_valid_percentage(self):
            """Test valid percentage values."""
            assert is_percentage("0") is True
            assert is_percentage("50") is True
            assert is_percentage("100") is True
            assert is_percentage("99.5") is True

        def test_out_of_range(self):
            """Test out of range values."""
            assert is_percentage("-1") is False
            assert is_percentage("101") is False
            assert is_percentage("150") is False

    class TestIsBoolean:
        """Tests for is_boolean validator."""

        def test_true_values(self):
            """Test true-like values."""
            assert is_boolean("true") is True
            assert is_boolean("True") is True
            assert is_boolean("TRUE") is True
            assert is_boolean("1") is True
            assert is_boolean("yes") is True

        def test_false_values(self):
            """Test false-like values."""
            assert is_boolean("false") is True
            assert is_boolean("False") is True
            assert is_boolean("0") is True
            assert is_boolean("no") is True

        def test_invalid_values(self):
            """Test invalid boolean strings."""
            assert is_boolean("maybe") is False
            assert is_boolean("") is False

    class TestIsHexKey:
        """Tests for is_hex_key validator."""

        def test_valid_hex_key(self):
            """Test valid hex key."""
            assert is_hex_key("abcdef1234567890" * 2) is True

        def test_short_hex_key(self):
            """Test hex key too short."""
            assert is_hex_key("abc", min_length=32) is False

        def test_non_hex_chars(self):
            """Test non-hex characters."""
            assert is_hex_key("ghijklmnopqrstuvwxyz1234567890ab") is False

    class TestIsPostgresUrl:
        """Tests for is_postgres_url validator."""

        def test_valid_postgresql_url(self):
            """Test valid postgresql:// URL."""
            assert is_postgres_url("postgresql://user:pass@localhost:5432/db") is True

        def test_valid_postgres_url(self):
            """Test valid postgres:// URL."""
            assert is_postgres_url("postgres://user:pass@localhost/db") is True

        def test_invalid_url(self):
            """Test non-postgres URL."""
            assert is_postgres_url("mysql://user:pass@localhost/db") is False

    class TestIsRedisUrl:
        """Tests for is_redis_url validator."""

        def test_valid_redis_url(self):
            """Test valid redis:// URL."""
            assert is_redis_url("redis://localhost:6379") is True

        def test_valid_rediss_url(self):
            """Test valid rediss:// (TLS) URL."""
            assert is_redis_url("rediss://localhost:6379") is True

        def test_invalid_url(self):
            """Test non-redis URL."""
            assert is_redis_url("http://localhost:6379") is False


class TestValidationReport:
    """Tests for ValidationReport dataclass."""

    def test_empty_report_is_valid(self):
        """Test empty report is considered valid."""
        report = ValidationReport()
        assert report.is_valid is True
        assert report.has_errors is False
        assert report.has_warnings is False

    def test_add_result_increments_counts(self):
        """Test add_result increments appropriate count."""
        report = ValidationReport()

        report.add_result(
            ValidationResult(
                name="test1",
                valid=False,
                severity=ValidationSeverity.CRITICAL,
                message="Critical error",
            )
        )
        assert report.critical_count == 1
        assert report.is_valid is False

        report.add_result(
            ValidationResult(
                name="test2",
                valid=False,
                severity=ValidationSeverity.ERROR,
                message="Error",
            )
        )
        assert report.error_count == 1
        assert report.has_errors is True

        report.add_result(
            ValidationResult(
                name="test3",
                valid=True,
                severity=ValidationSeverity.WARNING,
                message="Warning",
            )
        )
        assert report.warning_count == 1
        assert report.has_warnings is True

        report.add_result(
            ValidationResult(
                name="test4",
                valid=True,
                severity=ValidationSeverity.INFO,
                message="Info",
            )
        )
        assert report.info_count == 1

    def test_get_summary(self):
        """Test get_summary returns readable string."""
        report = ValidationReport()
        report.add_result(
            ValidationResult(
                name="test",
                valid=False,
                severity=ValidationSeverity.CRITICAL,
                message="Critical",
            )
        )
        report.add_result(
            ValidationResult(
                name="test2",
                valid=True,
                severity=ValidationSeverity.WARNING,
                message="Warning",
            )
        )

        summary = report.get_summary()
        assert "1 critical" in summary
        assert "1 warning" in summary


class TestValidateEnvVar:
    """Tests for validate_env_var function."""

    def test_required_var_not_set_production(self):
        """Test required variable not set in production."""
        spec = EnvVarSpec(name="REQUIRED_VAR", required_in_prod=True)

        with patch.dict(os.environ, {"REQUIRED_VAR": ""}, clear=False):
            result = validate_env_var(spec, is_production=True)

        assert result.valid is False
        assert result.severity == ValidationSeverity.CRITICAL

    def test_required_var_not_set_development(self):
        """Test required variable not set in development."""
        spec = EnvVarSpec(name="REQUIRED_VAR", required=True)  # required=True, not just required_in_prod

        with patch.dict(os.environ, {"REQUIRED_VAR": ""}, clear=False):
            result = validate_env_var(spec, is_production=False)

        # Should be error in development for required=True
        assert result.severity == ValidationSeverity.ERROR

    def test_optional_var_uses_default(self):
        """Test optional variable uses default value."""
        spec = EnvVarSpec(name="OPTIONAL_VAR", default="default_value")

        with patch.dict(os.environ, {"OPTIONAL_VAR": ""}, clear=False):
            result = validate_env_var(spec, is_production=False)

        assert result.valid is True
        assert result.severity == ValidationSeverity.INFO
        assert "default" in result.message.lower()

    def test_min_length_validation(self):
        """Test minimum length validation."""
        spec = EnvVarSpec(name="SHORT_VAR", min_length=10)

        with patch.dict(os.environ, {"SHORT_VAR": "short"}, clear=False):
            result = validate_env_var(spec, is_production=True)

        assert result.valid is False
        assert "short" in result.message.lower()

    def test_allowed_values_validation(self):
        """Test allowed values validation."""
        spec = EnvVarSpec(name="ENV_VAR", allowed_values=["dev", "staging", "prod"])

        with patch.dict(os.environ, {"ENV_VAR": "invalid"}, clear=False):
            result = validate_env_var(spec, is_production=False)

        assert result.valid is False
        assert "invalid" in result.message.lower()

    def test_custom_validator(self):
        """Test custom validator function."""
        spec = EnvVarSpec(
            name="PORT_VAR",
            validator=is_positive_int,
            validator_message="Must be positive integer",
        )

        with patch.dict(os.environ, {"PORT_VAR": "-5"}, clear=False):
            result = validate_env_var(spec, is_production=False)

        assert result.valid is False
        assert "positive integer" in result.message.lower()

    def test_valid_value_passes(self):
        """Test valid value passes all checks."""
        spec = EnvVarSpec(name="VALID_VAR", min_length=5, allowed_values=["valid", "also_valid"])

        with patch.dict(os.environ, {"VALID_VAR": "valid"}, clear=False):
            result = validate_env_var(spec, is_production=True)

        assert result.valid is True


class TestValidateAllEnvVars:
    """Tests for validate_all_env_vars function."""

    @patch.dict(
        os.environ,
        {
            "APP_ENV": "development",
            "FLASK_DEBUG": "true",
        },
        clear=False,
    )
    def test_development_environment(self):
        """Test validation in development environment."""
        report = validate_all_env_vars(raise_on_critical=False, log_results=False)

        # Development should be lenient
        assert isinstance(report, ValidationReport)

    @patch.dict(
        os.environ,
        {
            "APP_ENV": "production",
            "SECRET_KEY": "",
            "JWT_SECRET_KEY": "",
            "DATABASE_URL": "",
        },
        clear=False,
    )
    def test_production_missing_required_raises(self):
        """Test production with missing required vars raises."""
        with pytest.raises(ValueError, match="Critical environment validation failed"):
            validate_all_env_vars(raise_on_critical=True, log_results=False)

    @patch.dict(
        os.environ,
        {
            "APP_ENV": "production",
            "SECRET_KEY": "",
        },
        clear=False,
    )
    def test_production_missing_required_no_raise(self):
        """Test production with missing required vars returns report."""
        report = validate_all_env_vars(raise_on_critical=False, log_results=False)

        assert report.is_valid is False
        assert report.critical_count > 0

    def test_additional_specs_included(self):
        """Test additional specs are validated."""
        additional = [
            EnvVarSpec(name="CUSTOM_VAR", required=True),
        ]

        with patch.dict(os.environ, {"CUSTOM_VAR": ""}, clear=False):
            report = validate_all_env_vars(additional_specs=additional, raise_on_critical=False, log_results=False)

        # Should include custom var in results
        var_names = [r.name for r in report.results]
        assert "CUSTOM_VAR" in var_names


class TestEnvVarSpecsExist:
    """Tests to verify ENV_VAR_SPECS contains expected variables."""

    def test_secret_key_spec_exists(self):
        """Test SECRET_KEY spec exists."""
        names = [spec.name for spec in ENV_VAR_SPECS]
        assert "SECRET_KEY" in names

    def test_database_url_spec_exists(self):
        """Test DATABASE_URL spec exists."""
        names = [spec.name for spec in ENV_VAR_SPECS]
        assert "DATABASE_URL" in names

    def test_app_env_spec_exists(self):
        """Test APP_ENV spec exists."""
        names = [spec.name for spec in ENV_VAR_SPECS]
        assert "APP_ENV" in names

    def test_sensitive_vars_marked(self):
        """Test sensitive variables are marked sensitive."""
        for spec in ENV_VAR_SPECS:
            if "KEY" in spec.name or "SECRET" in spec.name or "PASSWORD" in spec.name:
                assert spec.sensitive is True, f"{spec.name} should be marked sensitive"
