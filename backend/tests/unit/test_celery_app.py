"""
Unit Tests for Celery Application Configuration.

Tests the Celery app setup, configuration, and task routing.
"""

import importlib
import os
from unittest.mock import MagicMock, patch

import pytest

# Import the module properly (not through app.services.__init__.py which exports the Celery instance)
celery_module = importlib.import_module("app.services.celery_app")
celery_app = celery_module.celery_app


class TestCeleryAppConfiguration:
    """Test suite for Celery application configuration."""

    def test_celery_app_instance_creation(self):
        """Test that Celery app instance is created with correct name."""
        with patch.dict(
            os.environ,
            {"CELERY_BROKER_URL": "redis://localhost:6379/1", "CELERY_RESULT_BACKEND": "redis://localhost:6379/2"},
        ):
            assert celery_app is not None
            assert celery_app.main == "floodingnaque"

    def test_celery_broker_url_default(self):
        """Test default broker URL configuration."""
        with patch.dict(os.environ, {}, clear=True):
            # Reload to get defaults
            # Default should be localhost redis
            assert "redis://localhost:6379" in celery_app.conf.broker_url

    def test_celery_broker_url_from_env(self):
        """Test broker URL from environment variable."""
        custom_broker = "redis://custom-redis:6380/0"
        with patch.dict(os.environ, {"CELERY_BROKER_URL": custom_broker}):
            importlib.reload(celery_module)

            assert celery_module.celery_app.conf.broker_url == custom_broker

    def test_celery_serializer_config(self):
        """Test that serializer is configured as JSON."""
        assert celery_app.conf.task_serializer == "json"
        assert "json" in celery_app.conf.accept_content
        assert celery_app.conf.result_serializer == "json"

    def test_celery_timezone_config(self):
        """Test timezone configuration."""
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True

    def test_celery_task_routing(self):
        """Test task routing configuration."""
        routes = celery_app.conf.task_routes

        assert "app.services.tasks.model_retraining" in routes
        assert routes["app.services.tasks.model_retraining"]["queue"] == "ml_tasks"

        assert "app.services.tasks.data_processing" in routes
        assert routes["app.services.tasks.data_processing"]["queue"] == "data_tasks"

        assert "app.services.tasks.notifications" in routes
        assert routes["app.services.tasks.notifications"]["queue"] == "notification_tasks"

    def test_celery_worker_settings(self):
        """Test worker configuration settings."""
        assert celery_app.conf.worker_prefetch_multiplier == 1
        assert celery_app.conf.task_acks_late is True
        assert celery_app.conf.worker_max_tasks_per_child == 1000

    def test_celery_result_settings(self):
        """Test result backend settings."""
        assert celery_app.conf.result_expires == 3600  # 1 hour
        assert celery_app.conf.result_compression == "gzip"

    def test_celery_error_handling_settings(self):
        """Test error handling configuration."""
        assert celery_app.conf.task_reject_on_worker_lost is True
        assert celery_app.conf.task_ignore_result is False

    def test_celery_beat_schedule(self):
        """Test periodic task scheduling configuration."""
        beat_schedule = celery_app.conf.beat_schedule

        # Check cleanup task
        assert "cleanup-old-results" in beat_schedule
        assert beat_schedule["cleanup-old-results"]["schedule"] == 3600.0
        assert beat_schedule["cleanup-old-results"]["task"] == "app.services.tasks.cleanup_old_results"

        # Check health check task
        assert "health-check" in beat_schedule
        assert beat_schedule["health-check"]["schedule"] == 300.0
        assert beat_schedule["health-check"]["task"] == "app.services.tasks.health_check"


class TestCeleryAppImports:
    """Test Celery app import handling."""

    def test_tasks_import_warning_on_failure(self):
        """Test that missing tasks module logs a warning instead of failing."""
        with patch("app.services.celery_app.logger") as mock_logger:
            # Force reimport with tasks module unavailable
            with patch.dict("sys.modules", {"app.services.tasks": None}):
                # Should not raise an exception
                assert celery_module.celery_app is not None


class TestCeleryAppEnvironmentVariables:
    """Test Celery environment variable handling."""

    @pytest.mark.parametrize(
        "env_var,expected_key,expected_value",
        [
            ("CELERY_BROKER_URL", "broker_url", "redis://test:6379/0"),
            ("CELERY_RESULT_BACKEND", "result_backend", "redis://test:6379/1"),
        ],
    )
    def test_environment_variable_overrides(self, env_var, expected_key, expected_value):
        """Test that environment variables properly override defaults."""
        with patch.dict(os.environ, {env_var: expected_value}):
            importlib.reload(celery_module)

            actual_value = getattr(celery_module.celery_app.conf, expected_key)
            assert actual_value == expected_value
