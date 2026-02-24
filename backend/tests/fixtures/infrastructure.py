"""Infrastructure mocking fixtures — Redis, Celery, metrics, logging, time, and file/IO."""

from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# Redis/Cache Mocking Fixtures
# ============================================================================


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value=None)
    redis_mock.set = MagicMock(return_value=True)
    redis_mock.setex = MagicMock(return_value=True)
    redis_mock.delete = MagicMock(return_value=1)
    redis_mock.exists = MagicMock(return_value=0)
    redis_mock.incr = MagicMock(return_value=1)
    redis_mock.expire = MagicMock(return_value=True)
    redis_mock.ttl = MagicMock(return_value=3600)
    redis_mock.keys = MagicMock(return_value=[])
    redis_mock.flushdb = MagicMock(return_value=True)
    redis_mock.pipeline = MagicMock(return_value=MagicMock())
    redis_mock.ping = MagicMock(return_value=True)
    # Sorted set operations for sliding window rate limiting
    redis_mock.zcard = MagicMock(return_value=0)
    redis_mock.zadd = MagicMock(return_value=1)
    redis_mock.zremrangebyscore = MagicMock(return_value=0)
    return redis_mock


@pytest.fixture
def mock_redis_client(mock_redis):
    """Patch Redis client globally for testing."""
    with patch("app.utils.cache.redis_client", mock_redis):
        with patch("app.utils.rate_limit.redis_client", mock_redis):
            with patch("app.api.middleware.rate_limit.redis_client", mock_redis):
                yield mock_redis


@pytest.fixture
def mock_cache():
    """Mock cache decorator/manager for testing."""
    cache_mock = MagicMock()
    cache_mock.get = MagicMock(return_value=None)
    cache_mock.set = MagicMock(return_value=True)
    cache_mock.delete = MagicMock(return_value=True)
    cache_mock.clear = MagicMock(return_value=True)
    cache_mock.mget = MagicMock(return_value=[])
    cache_mock.mset = MagicMock(return_value=True)
    return cache_mock


# ============================================================================
# Celery/Task Queue Mocking Fixtures
# ============================================================================


@pytest.fixture
def mock_celery():
    """Mock Celery app for testing."""
    celery_mock = MagicMock()
    celery_mock.send_task = MagicMock()
    celery_mock.AsyncResult = MagicMock()
    return celery_mock


@pytest.fixture
def mock_celery_task():
    """Mock Celery task for testing."""
    task_mock = MagicMock()
    task_mock.delay = MagicMock()
    task_mock.apply_async = MagicMock()
    task_mock.s = MagicMock()  # Signature shortcut

    # Task result
    result_mock = MagicMock()
    result_mock.id = "task-id-12345"
    result_mock.state = "PENDING"
    result_mock.result = None
    result_mock.ready = MagicMock(return_value=False)
    result_mock.successful = MagicMock(return_value=False)
    result_mock.failed = MagicMock(return_value=False)
    result_mock.get = MagicMock(return_value=None)

    task_mock.delay.return_value = result_mock
    task_mock.apply_async.return_value = result_mock

    return task_mock


@pytest.fixture
def mock_task_queue(mock_celery_task):
    """Patch task queue for testing."""
    with patch("app.tasks.prediction_tasks.predict_flood", mock_celery_task):
        with patch("app.tasks.data_tasks.ingest_weather_data", mock_celery_task):
            yield mock_celery_task


# ============================================================================
# Metrics/Monitoring Fixtures
# ============================================================================


@pytest.fixture
def mock_prometheus():
    """Mock Prometheus metrics for testing."""
    prometheus_mock = MagicMock()
    prometheus_mock.Counter = MagicMock(return_value=MagicMock())
    prometheus_mock.Histogram = MagicMock(return_value=MagicMock())
    prometheus_mock.Gauge = MagicMock(return_value=MagicMock())
    prometheus_mock.Summary = MagicMock(return_value=MagicMock())
    return prometheus_mock


@pytest.fixture
def mock_metrics(mock_prometheus):
    """Patch Prometheus metrics for testing."""
    with patch("app.utils.metrics.prometheus_client", mock_prometheus):
        yield mock_prometheus


# ============================================================================
# Logging Fixtures
# ============================================================================


@pytest.fixture
def mock_logger():
    """Mock logger for testing log output."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.critical = MagicMock()
    logger.exception = MagicMock()
    return logger


@pytest.fixture
def capture_logs(caplog):
    """Capture log output for assertions."""
    import logging

    caplog.set_level(logging.DEBUG)
    return caplog


# ============================================================================
# Time/Date Fixtures
# ============================================================================


@pytest.fixture
def freeze_time():
    """Fixture to freeze time for testing."""
    from datetime import datetime
    from unittest.mock import patch

    frozen_time = datetime(2025, 1, 15, 12, 0, 0)

    with patch("datetime.datetime") as mock_datetime:
        mock_datetime.now.return_value = frozen_time
        mock_datetime.utcnow.return_value = frozen_time
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        yield frozen_time


@pytest.fixture
def mock_time():
    """Mock time module for testing."""
    import time

    with patch("time.time") as mock_time_func:
        mock_time_func.return_value = 1736942400.0  # 2025-01-15 12:00:00 UTC
        yield mock_time_func


# ============================================================================
# File/IO Fixtures
# ============================================================================


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file for testing."""
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("test content")
    return file_path


@pytest.fixture
def temp_json_file(tmp_path):
    """Create a temporary JSON file for testing."""
    import json

    file_path = tmp_path / "test_data.json"
    data = {"key": "value", "nested": {"a": 1, "b": 2}}
    file_path.write_text(json.dumps(data))
    return file_path


@pytest.fixture
def temp_csv_file(tmp_path):
    """Create a temporary CSV file for testing."""
    file_path = tmp_path / "test_data.csv"
    content = "timestamp,temperature,humidity,precipitation\n"
    content += "2025-01-15T10:00:00Z,298.15,75.0,5.0\n"
    content += "2025-01-15T11:00:00Z,300.0,85.0,25.0\n"
    file_path.write_text(content)
    return file_path
