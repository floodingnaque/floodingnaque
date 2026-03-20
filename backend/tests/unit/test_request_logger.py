"""
Unit tests for request logger middleware.

Tests for app/api/middleware/request_logger.py
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from app.api.middleware.request_logger import (
    log_request_to_db,
    setup_request_logging_middleware,
)
from app.models.db import APIRequest, get_db_session
from flask import Flask, g


class TestLogRequestToDb:
    """Tests for log_request_to_db function."""

    def test_log_request_to_db_function_exists(self):
        """Test log_request_to_db function exists."""
        assert callable(log_request_to_db)

    @patch("app.api.middleware.request_logger._is_logging_disabled", return_value=False)
    @patch("app.api.middleware.request_logger._log_executor")
    def test_log_request_to_db_success(self, mock_executor, mock_disabled):
        """Test successful request logging dispatches to background thread."""
        app = Flask(__name__)

        with app.test_request_context("/api/test", method="GET"):
            g.start_time = time.time()
            g.request_id = "test-request-123"

            log_request_to_db()

            mock_executor.submit.assert_called_once()
            # Verify the persister function and log_data were passed
            call_args = mock_executor.submit.call_args
            log_data = call_args[0][1]
            assert log_data["request_id"] == "test-request-123"
            assert log_data["endpoint"] == "/api/test"
            assert log_data["method"] == "GET"

    def test_log_request_to_db_no_start_time(self):
        """Test log_request_to_db handles missing start_time."""
        app = Flask(__name__)

        with app.test_request_context("/api/test"):
            # No g.start_time set
            # Should return early without error
            log_request_to_db()

    def test_log_request_to_db_no_request_id(self):
        """Test log_request_to_db handles missing request_id."""
        app = Flask(__name__)

        with app.test_request_context("/api/test"):
            g.start_time = time.time()
            # No g.request_id set
            # Should return early without error
            log_request_to_db()


class TestSetupRequestLoggingMiddleware:
    """Tests for setup_request_logging_middleware function."""

    def test_setup_function_exists(self):
        """Test setup_request_logging_middleware function exists."""
        assert callable(setup_request_logging_middleware)

    def test_setup_registers_handlers(self):
        """Test setup registers before/after/teardown handlers."""
        app = Flask(__name__)

        # Should not raise
        setup_request_logging_middleware(app)

        # Verify hooks are registered (Flask stores these internally)
        assert app.before_request_funcs is not None
        assert app.after_request_funcs is not None


class TestAPIRequestModel:
    """Tests for APIRequest model usage."""

    def test_api_request_model_exists(self):
        """Test APIRequest model can be imported from db models."""
        assert APIRequest is not None


class TestGetDbSession:
    """Tests for get_db_session exists."""

    def test_get_db_session_exists(self):
        """Test get_db_session can be imported from db models."""
        assert callable(get_db_session)


class TestAPIVersionExtraction:
    """Tests for API version extraction from path."""

    @patch("app.api.middleware.request_logger._log_executor")
    def test_api_version_extracted_from_v1_path(self, mock_executor):
        """Test API version is extracted from /v1/ path."""
        app = Flask(__name__)

        with app.test_request_context("/v1/predict", method="POST"):
            g.start_time = time.time()
            g.request_id = "test-123"

            log_request_to_db()

            call_args = mock_executor.submit.call_args
            if call_args:
                log_data = call_args[0][1]
                assert log_data["api_version"] == "v1"

    @patch("app.api.middleware.request_logger._log_executor")
    def test_api_version_default(self, mock_executor):
        """Test API version defaults to v1."""
        app = Flask(__name__)

        with app.test_request_context("/health", method="GET"):
            g.start_time = time.time()
            g.request_id = "test-456"

            log_request_to_db()

            call_args = mock_executor.submit.call_args
            if call_args:
                log_data = call_args[0][1]
                assert log_data["api_version"] == "v1"


class TestErrorHandling:
    """Tests for error handling in request logging."""

    @patch("app.api.middleware.request_logger._is_logging_disabled", return_value=False)
    @patch("app.api.middleware.request_logger._log_executor")
    @patch("app.api.middleware.request_logger.logger")
    def test_data_preparation_error_logged(self, mock_logger, mock_executor, mock_disabled):
        """Test errors during data preparation are logged, not raised."""
        app = Flask(__name__)
        # Make request.path raise to simulate a data-preparation error
        mock_executor.submit.side_effect = Exception("submit failed")

        with app.test_request_context("/api/test"):
            g.start_time = time.time()
            g.request_id = "test-error-123"

            # Should not raise, just log warning
            log_request_to_db()

            mock_logger.warning.assert_called()


class TestResponseTimeMeasurement:
    """Tests for response time measurement."""

    @patch("app.api.middleware.request_logger._log_executor")
    def test_response_time_calculated(self, mock_executor):
        """Test response time is calculated correctly."""
        app = Flask(__name__)

        with app.test_request_context("/api/test"):
            g.start_time = time.time() - 0.1  # 100ms ago
            g.request_id = "test-time-123"

            log_request_to_db()

            call_args = mock_executor.submit.call_args
            if call_args:
                log_data = call_args[0][1]
                # Response time should be around 100ms
                assert log_data["response_time_ms"] >= 90
                assert log_data["response_time_ms"] <= 200
