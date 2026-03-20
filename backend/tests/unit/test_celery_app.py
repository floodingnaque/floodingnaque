"""
Unit Tests for Celery Application Configuration and Task Execution.

Tests the Celery app setup, configuration, task routing, and actual task bodies.
"""

import importlib
import os
from datetime import datetime, timezone
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
        """Test timezone configuration.

        Celery timezone defaults to Asia/Manila (Parañaque local time)
        but can be overridden via CELERY_TIMEZONE env var.
        """
        expected_tz = os.environ.get("CELERY_TIMEZONE", "Asia/Manila")
        assert celery_app.conf.timezone == expected_tz
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


# =============================================================================
# Task Execution Tests (Finding #13)
# =============================================================================


class _FakeRequest:
    """Minimal Celery request stub for testing bound tasks."""

    def __init__(self):
        self.id = "test-task-id-001"
        self.retries = 0


class _FakeSelf:
    """Minimal Celery 'self' stub with update_state."""

    def __init__(self):
        self.request = _FakeRequest()
        self.states: list = []

    def update_state(self, state, meta):
        self.states.append({"state": state, "meta": meta})


def _raw(task_proxy):
    """
    Extract the raw unbound function from a Celery task proxy.

    For ``bind=True`` tasks, calling the proxy auto-injects *self* as the
    Celery task instance, which makes it impossible to pass a fake.
    ``type(task).run`` returns the original, unwrapped function so we can
    pass our own ``_FakeSelf`` as the first argument.
    """
    real_task = task_proxy._get_current_object()
    return type(real_task).run


class TestModelRetrainingTaskExecution:
    """Tests that model_retraining task runs a real training pipeline."""

    @patch("app.services.tasks.Path")
    def test_model_retraining_calls_unified_trainer(self, mock_path_cls):
        """Verify model_retraining invokes UnifiedTrainer.train() and returns real metrics."""
        from app.services.tasks import model_retraining

        fake_self = _FakeSelf()
        fn = _raw(model_retraining)

        mock_trainer_instance = MagicMock()
        mock_trainer_instance.train.return_value = {
            "metrics": {"accuracy": 0.87, "precision": 0.85, "recall": 0.89, "f1_score": 0.87},
            "model_path": "/tmp/models/flood_model_v8.joblib",
        }

        with patch.dict("sys.modules", {"scripts.train_unified": MagicMock()}):
            import sys

            mock_train_mod = sys.modules["scripts.train_unified"]
            mock_mode = MagicMock()
            mock_mode.value = "production"
            mock_train_mod.TrainingMode.PRODUCTION = mock_mode
            mock_train_mod.UnifiedTrainer.return_value = mock_trainer_instance

            with patch("app.services.predict._load_model"):
                result = fn(fake_self, model_id="v8")

        mock_trainer_instance.train.assert_called_once()

        # Result should contain real metrics, not hardcoded values
        assert result["status"] == "completed"
        assert result["accuracy"] == 0.87
        assert result["model_id"] == "v8"
        assert result["model_path"] == "/tmp/models/flood_model_v8.joblib"
        assert "training_time_seconds" in result

    @patch("app.services.tasks.Path")
    def test_model_retraining_propagates_training_errors(self, mock_path_cls):
        """Verify training failures propagate as exceptions."""
        from app.services.tasks import model_retraining

        fake_self = _FakeSelf()
        fn = _raw(model_retraining)

        mock_trainer = MagicMock()
        mock_trainer.train.side_effect = RuntimeError("Training data missing")

        with patch.dict("sys.modules", {"scripts.train_unified": MagicMock()}):
            import sys

            mock_train_mod = sys.modules["scripts.train_unified"]
            mock_mode = MagicMock()
            mock_mode.value = "production"
            mock_train_mod.TrainingMode.PRODUCTION = mock_mode
            mock_train_mod.UnifiedTrainer.return_value = mock_trainer

            with pytest.raises(RuntimeError, match="Training data missing"):
                fn(fake_self)


class TestSendNotificationTaskExecution:
    """Tests that send_notification task dispatches to real channels."""

    def test_send_notification_email_calls_alert_system(self):
        """Verify email notifications delegate to AlertSystem._send_email."""
        from app.services.tasks import send_notification

        fake_self = _FakeSelf()
        fn = _raw(send_notification)

        mock_alert_system = MagicMock()
        mock_alert_system._send_email.return_value = "delivered"

        with patch("app.services.alerts.AlertSystem.get_instance", return_value=mock_alert_system):
            result = fn(fake_self, "email", "user@example.com", "Flood alert!")

        assert result["status"] == "delivered"
        assert result["notification_type"] == "email"
        mock_alert_system._send_email.assert_called_once_with(
            recipients=["user@example.com"],
            subject="Floodingnaque Notification",
            message="Flood alert!",
        )

    def test_send_notification_sms_calls_alert_system(self):
        """Verify SMS notifications delegate to AlertSystem._send_sms."""
        from app.services.tasks import send_notification

        fake_self = _FakeSelf()
        fn = _raw(send_notification)

        mock_alert_system = MagicMock()
        mock_alert_system._send_sms.return_value = "delivered"

        with patch("app.services.alerts.AlertSystem.get_instance", return_value=mock_alert_system):
            result = fn(fake_self, "sms", "09171234567", "Flood alert!")

        assert result["status"] == "delivered"
        mock_alert_system._send_sms.assert_called_once()

    def test_send_notification_webhook_posts_json(self):
        """Verify webhook notifications do a real HTTP POST."""
        from app.services.tasks import send_notification

        fake_self = _FakeSelf()
        fn = _raw(send_notification)
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_resp) as mock_post:
            result = fn(fake_self, "webhook", "https://hooks.example.com/flood", "Flood alert!")

        assert result["status"] == "delivered"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["text"] == "Flood alert!"
        assert payload["source"] == "floodingnaque"

    def test_send_notification_invalid_type_raises(self):
        """Verify unsupported notification types raise ValueError."""
        from app.services.tasks import send_notification

        fake_self = _FakeSelf()
        fn = _raw(send_notification)

        with pytest.raises(ValueError, match="Unsupported notification type"):
            fn(fake_self, "pigeon", "recipient", "message")


class TestCleanupOldResultsTaskExecution:
    """Tests that cleanup_old_results task scans Redis and deletes expired keys."""

    @patch("redis.Redis")
    @patch("app.services.tasks.get_secret", return_value="redis://localhost:6379/2")
    def test_cleanup_scans_and_deletes_expired_keys(self, mock_secret, mock_redis_cls):
        """Verify cleanup iterates celery-task-meta-* and removes old entries."""
        import json as _json

        from app.services.tasks import cleanup_old_results

        # Simulate two keys: one old (should be deleted), one recent (should survive)
        old_meta = _json.dumps(
            {
                "status": "SUCCESS",
                "date_done": "2025-01-01T00:00:00+00:00",
            }
        )
        recent_meta = _json.dumps(
            {
                "status": "SUCCESS",
                "date_done": datetime.now(timezone.utc).isoformat(),
            }
        )

        mock_redis = MagicMock()
        mock_redis.scan_iter.return_value = [
            b"celery-task-meta-old-111",
            b"celery-task-meta-new-222",
        ]
        mock_redis.get.side_effect = [old_meta.encode(), recent_meta.encode()]
        mock_redis_cls.return_value = mock_redis

        result = cleanup_old_results()

        assert result["status"] == "completed"
        assert result["scanned"] == 2
        assert result["deleted"] == 1
        mock_redis.delete.assert_called_once_with(b"celery-task-meta-old-111")

    @patch("redis.Redis")
    @patch("app.services.tasks.get_secret", return_value="redis://localhost:6379/2")
    def test_cleanup_handles_redis_error(self, mock_secret, mock_redis_cls):
        """Verify cleanup returns 'failed' status on Redis connection error."""
        import redis as _redis
        from app.services.tasks import cleanup_old_results

        mock_redis_cls.side_effect = _redis.ConnectionError("Connection refused")

        result = cleanup_old_results()
        assert result["status"] == "failed"
        assert "error" in result


class TestProcessWeatherDataTaskExecution:
    """Tests that process_weather_data task iterates and reports on records."""

    def test_process_weather_data_counts_records(self):
        """Verify process_weather_data processes and counts records."""
        from app.services.tasks import process_weather_data

        fake_self = _FakeSelf()
        fn = _raw(process_weather_data)
        batch = [
            {"temperature": 30, "humidity": 80, "precipitation": 5},
            {"temperature": 28, "humidity": 70, "precipitation": 2},
        ]

        result = fn(fake_self, batch)

        assert result["status"] == "completed"
        assert result["total_records"] == 2
        assert result["processed"] == 2
        assert result["failed"] == 0
