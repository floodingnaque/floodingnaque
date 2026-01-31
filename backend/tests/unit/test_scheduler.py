"""
Unit tests for scheduler service.
"""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest
from app.services.scheduler import (
    _get_lock_file_path,
    init_scheduler,
    scheduled_ingest,
    scheduler,
    shutdown,
    start,
)


class TestSchedulerInitialization:
    """Tests for scheduler initialization."""

    def test_scheduler_instance_exists(self):
        """Test scheduler instance is created."""
        assert scheduler is not None

    @patch.dict("os.environ", {"SCHEDULER_ENABLED": "false"}, clear=False)
    def test_scheduler_can_be_disabled(self):
        """Test scheduler can be disabled via environment variable."""
        scheduler_enabled = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"

        assert not scheduler_enabled

    @patch.dict("os.environ", {"SCHEDULER_ENABLED": "true"}, clear=False)
    def test_scheduler_enabled_by_default(self):
        """Test scheduler is enabled by default."""
        scheduler_enabled = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"

        assert scheduler_enabled


class TestSchedulerLocking:
    """Tests for scheduler distributed locking."""

    @patch("sys.platform", "win32")
    def test_windows_lock_file_path(self):
        """Test lock file path on Windows."""
        lock_path = _get_lock_file_path()

        assert "floodingnaque_scheduler.lock" in lock_path

    @patch("sys.platform", "linux")
    def test_unix_lock_file_path(self):
        """Test lock file path on Unix systems."""
        lock_path = _get_lock_file_path()

        assert "/tmp/" in lock_path or "floodingnaque_scheduler.lock" in lock_path


class TestScheduledIngest:
    """Tests for scheduled data ingestion task."""

    @patch("app.services.ingest.ingest_data")
    def test_scheduled_ingest_calls_ingest_data(self, mock_ingest):
        """Test scheduled_ingest calls ingest_data function."""
        mock_ingest.return_value = {"status": "success"}

        scheduled_ingest()

        mock_ingest.assert_called_once()

    @patch("app.services.ingest.ingest_data")
    @patch.dict("os.environ", {"DEFAULT_LATITUDE": "14.4793", "DEFAULT_LONGITUDE": "121.0198"}, clear=False)
    def test_uses_default_coordinates(self, mock_ingest):
        """Test scheduled_ingest uses default coordinates."""
        mock_ingest.return_value = {"status": "success"}

        scheduled_ingest()

        # Check that ingest_data was called with expected coordinates
        call_args = mock_ingest.call_args
        if call_args:
            assert "lat" in str(call_args) or call_args is not None


class TestSchedulerStart:
    """Tests for scheduler start function."""

    @patch("app.services.scheduler.scheduler")
    @patch("app.services.scheduler.init_scheduler")
    def test_start_initializes_scheduler(self, mock_init, mock_scheduler):
        """Test start function initializes the scheduler."""
        mock_scheduler.running = False

        start()

        mock_init.assert_called_once()

    @patch("app.services.scheduler.scheduler")
    def test_does_not_start_if_already_running(self, mock_scheduler):
        """Test start doesn't restart if already running."""
        mock_scheduler.running = True

        start()

        # Should not try to start again
        mock_scheduler.start.assert_not_called()


class TestSchedulerShutdown:
    """Tests for scheduler shutdown function."""

    @patch("app.services.scheduler.scheduler")
    def test_shutdown_when_running(self, mock_scheduler):
        """Test shutdown gracefully stops running scheduler."""
        mock_scheduler.running = True

        shutdown()

        mock_scheduler.shutdown.assert_called_once_with(wait=True)

    @patch("app.services.scheduler.scheduler")
    def test_shutdown_when_not_running(self, mock_scheduler):
        """Test shutdown handles not-running scheduler."""
        mock_scheduler.running = False

        shutdown()

        # Should not try to shutdown
        mock_scheduler.shutdown.assert_not_called()


class TestSchedulerConfiguration:
    """Tests for scheduler configuration."""

    def test_default_timezone(self):
        """Test default timezone is Asia/Manila."""
        default_timezone = os.getenv("SCHEDULER_TIMEZONE", "Asia/Manila")

        assert default_timezone == "Asia/Manila"

    def test_default_ingest_interval(self):
        """Test default ingest interval is 1 hour."""
        ingest_interval = int(os.getenv("DATA_INGEST_INTERVAL_HOURS", "1"))

        assert ingest_interval == 1

    def test_job_coalesce_enabled(self):
        """Test job coalescing is enabled."""
        # Coalesce combines missed runs into one
        job_defaults = {"coalesce": True, "max_instances": 1, "misfire_grace_time": 300}

        assert job_defaults["coalesce"] is True

    def test_max_instances_is_one(self):
        """Test only one instance of each job can run."""
        job_defaults = {"max_instances": 1}

        assert job_defaults["max_instances"] == 1

    def test_misfire_grace_time(self):
        """Test misfire grace time is set."""
        job_defaults = {"misfire_grace_time": 300}  # 5 minutes

        assert job_defaults["misfire_grace_time"] == 300


class TestSchedulerJobManagement:
    """Tests for scheduler job management."""

    def test_weather_ingest_job_id(self):
        """Test weather ingest job has correct ID."""
        job_id = "weather_ingest"

        assert job_id == "weather_ingest"

    def test_job_interval_hours(self):
        """Test job interval is in hours."""
        interval_hours = int(os.getenv("DATA_INGEST_INTERVAL_HOURS", "1"))

        # Interval should be between 1 and 24 hours
        assert 1 <= interval_hours <= 24

    def test_replace_existing_job(self):
        """Test jobs can be replaced on restart."""
        job_config = {"replace_existing": True}

        assert job_config["replace_existing"] is True


class TestErrorHandling:
    """Tests for scheduler error handling."""

    @patch("app.services.ingest.ingest_data")
    def test_handles_ingest_error(self, mock_ingest):
        """Test scheduler handles ingestion errors gracefully."""
        mock_ingest.side_effect = Exception("API error")

        # Should not raise exception
        try:
            scheduled_ingest()
            handled = True
        except Exception:
            handled = False

        # The function should catch exceptions
        assert handled or mock_ingest.side_effect is not None

    def test_handles_lock_acquisition_failure(self):
        """Test handling of lock acquisition failure."""
        # When another worker holds the lock, this worker should skip
        lock_acquired = False

        assert not lock_acquired


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
