"""
Unit tests for app/utils/startup_health.py.

Tests for startup health validation including environment checks,
model loading, database and Redis connections.
"""

import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from app.utils.startup_health import (
    HealthCheckResult,
    HealthCheckSeverity,
    HealthCheckStatus,
    StartupHealthReport,
    check_database,
    check_environment_variables,
    check_ml_model,
    check_model_directory,
    check_redis,
    validate_startup_health,
)


class TestHealthCheckStatus:
    """Tests for HealthCheckStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert HealthCheckStatus.HEALTHY == "healthy"
        assert HealthCheckStatus.DEGRADED == "degraded"
        assert HealthCheckStatus.UNHEALTHY == "unhealthy"
        assert HealthCheckStatus.SKIPPED == "skipped"

    def test_status_is_string_enum(self):
        """Test HealthCheckStatus inherits from str."""
        assert isinstance(HealthCheckStatus.HEALTHY, str)


class TestHealthCheckSeverity:
    """Tests for HealthCheckSeverity enum."""

    def test_severity_values(self):
        """Test all severity values exist."""
        assert HealthCheckSeverity.CRITICAL == "critical"
        assert HealthCheckSeverity.WARNING == "warning"
        assert HealthCheckSeverity.INFO == "info"


class TestHealthCheckResult:
    """Tests for HealthCheckResult dataclass."""

    def test_health_check_result_creation(self):
        """Test HealthCheckResult can be created."""
        result = HealthCheckResult(
            name="test_check",
            status=HealthCheckStatus.HEALTHY,
            message="Test passed",
        )

        assert result.name == "test_check"
        assert result.status == HealthCheckStatus.HEALTHY
        assert result.message == "Test passed"
        assert result.severity == HealthCheckSeverity.INFO
        assert result.details == {}
        assert result.latency_ms is None

    def test_is_healthy_property_healthy(self):
        """Test is_healthy returns True for healthy status."""
        result = HealthCheckResult(name="test", status=HealthCheckStatus.HEALTHY, message="OK")
        assert result.is_healthy is True

    def test_is_healthy_property_skipped(self):
        """Test is_healthy returns True for skipped status."""
        result = HealthCheckResult(name="test", status=HealthCheckStatus.SKIPPED, message="Skipped")
        assert result.is_healthy is True

    def test_is_healthy_property_unhealthy(self):
        """Test is_healthy returns False for unhealthy status."""
        result = HealthCheckResult(name="test", status=HealthCheckStatus.UNHEALTHY, message="Failed")
        assert result.is_healthy is False

    def test_is_healthy_property_degraded(self):
        """Test is_healthy returns False for degraded status."""
        result = HealthCheckResult(name="test", status=HealthCheckStatus.DEGRADED, message="Warning")
        assert result.is_healthy is False

    def test_is_critical_failure_critical(self):
        """Test is_critical_failure for critical unhealthy."""
        result = HealthCheckResult(
            name="test",
            status=HealthCheckStatus.UNHEALTHY,
            message="Critical failure",
            severity=HealthCheckSeverity.CRITICAL,
        )
        assert result.is_critical_failure is True

    def test_is_critical_failure_warning(self):
        """Test is_critical_failure for warning unhealthy."""
        result = HealthCheckResult(
            name="test",
            status=HealthCheckStatus.UNHEALTHY,
            message="Warning failure",
            severity=HealthCheckSeverity.WARNING,
        )
        assert result.is_critical_failure is False


class TestStartupHealthReport:
    """Tests for StartupHealthReport dataclass."""

    def test_empty_report_is_healthy(self):
        """Test empty report is considered healthy."""
        report = StartupHealthReport()
        assert report.is_healthy is True
        assert report.has_warnings is False

    def test_report_with_healthy_checks(self):
        """Test report with all healthy checks."""
        report = StartupHealthReport(
            checks=[
                HealthCheckResult(name="check1", status=HealthCheckStatus.HEALTHY, message="OK"),
                HealthCheckResult(name="check2", status=HealthCheckStatus.HEALTHY, message="OK"),
            ]
        )
        assert report.is_healthy is True
        assert report.has_warnings is False

    def test_report_with_critical_failure(self):
        """Test report with critical failure is not healthy."""
        report = StartupHealthReport(
            checks=[
                HealthCheckResult(name="check1", status=HealthCheckStatus.HEALTHY, message="OK"),
                HealthCheckResult(
                    name="check2",
                    status=HealthCheckStatus.UNHEALTHY,
                    message="Failed",
                    severity=HealthCheckSeverity.CRITICAL,
                ),
            ]
        )
        assert report.is_healthy is False

    def test_report_with_warnings(self):
        """Test report with warnings has_warnings property."""
        report = StartupHealthReport(
            checks=[
                HealthCheckResult(
                    name="check1",
                    status=HealthCheckStatus.DEGRADED,
                    message="Warning",
                    severity=HealthCheckSeverity.WARNING,
                ),
            ]
        )
        assert report.has_warnings is True

    def test_summary_property(self):
        """Test summary property returns readable summary."""
        report = StartupHealthReport(
            checks=[
                HealthCheckResult(name="check1", status=HealthCheckStatus.HEALTHY, message="OK"),
                HealthCheckResult(
                    name="check2",
                    status=HealthCheckStatus.UNHEALTHY,
                    message="Failed",
                    severity=HealthCheckSeverity.CRITICAL,
                ),
            ]
        )
        summary = report.summary

        assert "1/2" in summary  # 1 of 2 healthy
        assert "1 critical" in summary  # 1 critical failure

    def test_to_dict_method(self):
        """Test to_dict serialization."""
        report = StartupHealthReport(
            checks=[
                HealthCheckResult(
                    name="test_check",
                    status=HealthCheckStatus.HEALTHY,
                    message="OK",
                    latency_ms=10.5,
                ),
            ],
            timestamp="2025-01-15T10:00:00Z",
            total_latency_ms=15.0,
        )

        result = report.to_dict()

        assert "is_healthy" in result
        assert "has_warnings" in result
        assert "summary" in result
        assert "checks" in result
        assert len(result["checks"]) == 1
        assert result["checks"][0]["name"] == "test_check"


class TestCheckEnvironmentVariables:
    """Tests for check_environment_variables function."""

    @patch.dict(os.environ, {"APP_ENV": "development"}, clear=False)
    def test_development_environment_healthy(self):
        """Test development environment passes with minimal config."""
        result = check_environment_variables()

        # Development should be lenient
        assert result.status in [
            HealthCheckStatus.HEALTHY,
            HealthCheckStatus.DEGRADED,
        ]

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
    def test_production_missing_required_unhealthy(self):
        """Test production without required vars is unhealthy."""
        result = check_environment_variables()

        assert result.status == HealthCheckStatus.UNHEALTHY
        assert "missing" in result.message.lower() or len(result.details.get("missing_required", [])) > 0

    @patch.dict(
        os.environ,
        {
            "APP_ENV": "production",
            "SECRET_KEY": "a-secure-production-secret-key-that-is-long-enough",
            "JWT_SECRET_KEY": "another-secure-jwt-secret-key-long",
            "DATABASE_URL": "postgresql://user:pass@localhost/db",
        },
        clear=False,
    )
    def test_production_all_required_healthy(self):
        """Test production with all required vars is healthy."""
        result = check_environment_variables()

        assert result.status in [
            HealthCheckStatus.HEALTHY,
            HealthCheckStatus.DEGRADED,
        ]

    def test_result_has_latency(self):
        """Test result includes latency measurement."""
        result = check_environment_variables()
        assert result.latency_ms is not None
        assert result.latency_ms >= 0


class TestCheckMLModel:
    """Tests for check_ml_model function."""

    def test_model_loads_successfully(self):
        """Test ML model loading success."""
        with (
            patch("app.utils.ml_version_check.validate_ml_versions") as mock_versions,
            patch("app.utils.ml_version_check.check_model_training_versions") as mock_training,
            patch("app.services.predict.get_current_model_info") as mock_model_info,
        ):
            mock_versions.return_value = []
            mock_training.return_value = []
            mock_model_info.return_value = {
                "metadata": {"version": "1.0.0"},
                "checksum": "abc123",
            }

            result = check_ml_model()

            assert result.status == HealthCheckStatus.HEALTHY
            assert "1.0.0" in result.message

    def test_model_load_failure(self):
        """Test ML model loading failure."""
        with (
            patch("app.utils.ml_version_check.validate_ml_versions") as mock_versions,
            patch("app.services.predict.get_current_model_info") as mock_model_info,
        ):
            mock_versions.return_value = []
            mock_model_info.side_effect = Exception("Model file not found")

            result = check_ml_model()

            assert result.status == HealthCheckStatus.UNHEALTHY
            assert result.severity == HealthCheckSeverity.CRITICAL

    def test_import_error_handling(self):
        """Test handling of import errors."""
        with patch("app.utils.ml_version_check.validate_ml_versions") as mock_versions:
            mock_versions.side_effect = ImportError("No module named 'sklearn'")

            result = check_ml_model()

            assert result.status == HealthCheckStatus.UNHEALTHY
            assert "import" in result.message.lower()


class TestCheckDatabase:
    """Tests for check_database function."""

    def test_database_connection_success(self):
        """Test successful database connection."""
        with patch("app.models.db.get_db_session") as mock_session:
            mock_ctx = MagicMock()
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_session.return_value.__exit__ = MagicMock(return_value=None)
            mock_ctx.execute.return_value.fetchone.return_value = (1,)

            result = check_database()

            assert result.status == HealthCheckStatus.HEALTHY
            assert "successful" in result.message.lower()

    def test_database_connection_failure(self):
        """Test database connection failure."""
        with patch("app.models.db.get_db_session") as mock_session:
            mock_session.return_value.__enter__ = MagicMock(side_effect=Exception("Connection refused"))

            result = check_database()

            assert result.status == HealthCheckStatus.UNHEALTHY
            assert result.severity == HealthCheckSeverity.CRITICAL

    def test_database_has_latency(self):
        """Test database check includes latency."""
        with patch("app.models.db.get_db_session") as mock_session:
            mock_ctx = MagicMock()
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_session.return_value.__exit__ = MagicMock(return_value=None)
            mock_ctx.execute.return_value.fetchone.return_value = (1,)

            result = check_database()
            assert result.latency_ms is not None


class TestCheckRedis:
    """Tests for check_redis function."""

    @patch.dict(os.environ, {"RATE_LIMIT_STORAGE_URL": "memory://"}, clear=False)
    def test_redis_not_configured_skipped(self):
        """Test Redis check skipped when not configured."""
        result = check_redis()

        assert result.status == HealthCheckStatus.SKIPPED
        assert "not configured" in result.message.lower()

    @patch.dict(os.environ, {"RATE_LIMIT_STORAGE_URL": "redis://localhost:6379"}, clear=False)
    @patch("redis.Redis")
    def test_redis_connection_success(self, mock_redis_class):
        """Test successful Redis connection."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis_class.return_value = mock_redis

        result = check_redis()

        assert result.status == HealthCheckStatus.HEALTHY
        assert "successful" in result.message.lower()

    @patch.dict(os.environ, {"RATE_LIMIT_STORAGE_URL": "redis://localhost:6379"}, clear=False)
    @patch("redis.Redis")
    def test_redis_connection_failure(self, mock_redis_class):
        """Test Redis connection failure."""
        mock_redis_class.side_effect = Exception("Connection refused")

        result = check_redis()

        assert result.status == HealthCheckStatus.UNHEALTHY


class TestCheckModelDirectory:
    """Tests for check_model_directory function."""

    @patch.dict(os.environ, {"MODELS_DIR": "/nonexistent/path"}, clear=False)
    def test_directory_not_found(self):
        """Test model directory not found."""
        result = check_model_directory()

        assert result.status == HealthCheckStatus.UNHEALTHY
        assert "not found" in result.message.lower()

    def test_directory_exists_with_models(self, tmp_path):
        """Test model directory with model files."""
        # Create temp model file
        model_file = tmp_path / "model.joblib"
        model_file.write_text("fake model")

        with patch.dict(os.environ, {"MODELS_DIR": str(tmp_path)}, clear=False):
            result = check_model_directory()

        assert result.status == HealthCheckStatus.HEALTHY
        assert "1" in result.message  # 1 model file

    def test_directory_exists_no_models(self, tmp_path):
        """Test model directory without model files."""
        with patch.dict(os.environ, {"MODELS_DIR": str(tmp_path)}, clear=False):
            result = check_model_directory()

        assert result.status == HealthCheckStatus.UNHEALTHY
        assert "no" in result.message.lower() or "not found" in result.message.lower()


class TestValidateStartupHealth:
    """Tests for validate_startup_health main function."""

    @patch("app.utils.startup_health.check_environment_variables")
    @patch("app.utils.startup_health.check_ml_model")
    @patch("app.utils.startup_health.check_database")
    @patch("app.utils.startup_health.check_redis")
    def test_all_checks_enabled(self, mock_redis, mock_db, mock_model, mock_env):
        """Test all checks are performed when enabled."""
        mock_env.return_value = HealthCheckResult(name="env", status=HealthCheckStatus.HEALTHY, message="OK")
        mock_model.return_value = HealthCheckResult(name="model", status=HealthCheckStatus.HEALTHY, message="OK")
        mock_db.return_value = HealthCheckResult(name="db", status=HealthCheckStatus.HEALTHY, message="OK")
        mock_redis.return_value = HealthCheckResult(
            name="redis", status=HealthCheckStatus.SKIPPED, message="Not configured"
        )

        report = validate_startup_health(
            check_env=True,
            check_model=True,
            check_database_conn=True,
            check_redis_conn=True,
        )

        assert len(report.checks) >= 3
        mock_env.assert_called_once()
        mock_model.assert_called_once()
        mock_db.assert_called_once()
        mock_redis.assert_called_once()

    @patch("app.utils.startup_health.check_environment_variables")
    @patch("app.utils.startup_health.check_ml_model")
    @patch("app.utils.startup_health.check_database")
    @patch("app.utils.startup_health.check_redis")
    def test_checks_can_be_disabled(self, mock_redis, mock_db, mock_model, mock_env):
        """Test individual checks can be disabled."""
        mock_env.return_value = HealthCheckResult(name="env", status=HealthCheckStatus.HEALTHY, message="OK")

        report = validate_startup_health(
            check_env=True,
            check_model=False,
            check_database_conn=False,
            check_redis_conn=False,
        )

        mock_env.assert_called_once()
        mock_model.assert_not_called()
        mock_db.assert_not_called()
        mock_redis.assert_not_called()

    @patch("app.utils.startup_health.check_environment_variables")
    def test_raise_on_failure_critical(self, mock_env):
        """Test raise_on_failure raises on critical failure."""
        mock_env.return_value = HealthCheckResult(
            name="env",
            status=HealthCheckStatus.UNHEALTHY,
            message="Missing required vars",
            severity=HealthCheckSeverity.CRITICAL,
        )

        with pytest.raises(RuntimeError):
            validate_startup_health(
                check_env=True,
                check_model=False,
                check_database_conn=False,
                check_redis_conn=False,
                raise_on_failure=True,
            )

    @patch("app.utils.startup_health.check_environment_variables")
    def test_no_raise_on_failure_returns_report(self, mock_env):
        """Test without raise_on_failure returns report."""
        mock_env.return_value = HealthCheckResult(
            name="env",
            status=HealthCheckStatus.UNHEALTHY,
            message="Missing required vars",
            severity=HealthCheckSeverity.CRITICAL,
        )

        report = validate_startup_health(
            check_env=True,
            check_model=False,
            check_database_conn=False,
            check_redis_conn=False,
            raise_on_failure=False,
        )

        assert isinstance(report, StartupHealthReport)
        assert report.is_healthy is False

    def test_report_includes_timestamp(self):
        """Test report includes timestamp."""
        with patch("app.utils.startup_health.check_environment_variables") as mock_env:
            mock_env.return_value = HealthCheckResult(name="env", status=HealthCheckStatus.HEALTHY, message="OK")

            report = validate_startup_health(
                check_env=True,
                check_model=False,
                check_database_conn=False,
                check_redis_conn=False,
            )

            assert report.timestamp  # Should have a timestamp

    def test_report_includes_total_latency(self):
        """Test report includes total latency."""
        with patch("app.utils.startup_health.check_environment_variables") as mock_env:
            mock_env.return_value = HealthCheckResult(
                name="env", status=HealthCheckStatus.HEALTHY, message="OK", latency_ms=5.0
            )

            report = validate_startup_health(
                check_env=True,
                check_model=False,
                check_database_conn=False,
                check_redis_conn=False,
            )

            assert report.total_latency_ms >= 0
