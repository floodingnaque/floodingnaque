"""
Unit Tests for Evaluation Service.

Tests the SystemEvaluator class and thesis validation evaluation framework.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from app.services.evaluation import SystemEvaluator, evaluate_system_for_thesis


class TestSystemEvaluatorInit:
    """Test SystemEvaluator initialization."""

    def test_evaluator_creates_results_directory(self):
        """Test that evaluator creates results directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results_path = os.path.join(tmpdir, "test_results")

            evaluator = SystemEvaluator(results_dir=results_path)

            assert Path(results_path).exists()
            assert evaluator.results_dir == Path(results_path)

    def test_evaluator_initializes_empty_results(self):
        """Test that evaluator initializes with empty results list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            evaluator = SystemEvaluator(results_dir=tmpdir)

            assert evaluator.evaluation_results == []


class TestEvaluateAccuracy:
    """Test accuracy evaluation methods."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SystemEvaluator(results_dir=tmpdir)

    def test_accuracy_perfect_predictions(self, evaluator):
        """Test accuracy metrics with perfect predictions."""
        y_true = [0, 1, 0, 1, 0, 1]
        y_pred = [0, 1, 0, 1, 0, 1]

        metrics = evaluator.evaluate_accuracy(y_true, y_pred)

        assert metrics["accuracy"] == 1.0
        assert metrics["precision"] == 1.0
        assert metrics["recall"] == 1.0
        assert metrics["f1_score"] == 1.0

    def test_accuracy_all_wrong_predictions(self, evaluator):
        """Test accuracy metrics with all wrong predictions."""
        y_true = [0, 0, 0, 0]
        y_pred = [1, 1, 1, 1]

        metrics = evaluator.evaluate_accuracy(y_true, y_pred)

        assert metrics["accuracy"] == 0.0

    def test_accuracy_partial_predictions(self, evaluator):
        """Test accuracy metrics with partial correct predictions."""
        y_true = [0, 1, 0, 1]
        y_pred = [0, 0, 0, 1]  # 75% correct

        metrics = evaluator.evaluate_accuracy(y_true, y_pred)

        assert metrics["accuracy"] == 0.75

    def test_accuracy_returns_float_metrics(self, evaluator):
        """Test that all accuracy metrics are floats."""
        y_true = [0, 1, 0]
        y_pred = [0, 1, 1]

        metrics = evaluator.evaluate_accuracy(y_true, y_pred)

        assert isinstance(metrics["accuracy"], float)
        assert isinstance(metrics["precision"], float)
        assert isinstance(metrics["recall"], float)
        assert isinstance(metrics["f1_score"], float)


class TestEvaluateScalability:
    """Test scalability evaluation methods."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SystemEvaluator(results_dir=tmpdir)

    def test_scalability_with_custom_test_func(self, evaluator):
        """Test scalability evaluation with custom test function."""
        call_count = [0]

        def mock_test_func():
            call_count[0] += 1
            return (True, 10.0)  # success, 10ms

        metrics = evaluator.evaluate_scalability(num_requests=5, concurrent_requests=2, test_func=mock_test_func)

        assert metrics["total_requests"] == 5
        assert metrics["concurrent_requests"] == 2
        assert metrics["successful_requests"] == 5
        assert metrics["failed_requests"] == 0
        assert metrics["avg_response_time"] == 10.0
        assert call_count[0] == 5

    def test_scalability_with_failures(self, evaluator):
        """Test scalability evaluation handles failures correctly."""
        call_count = [0]

        def mock_test_func_with_failures():
            call_count[0] += 1
            if call_count[0] % 2 == 0:
                return (False, 15.0)  # Fail every other request
            return (True, 10.0)

        metrics = evaluator.evaluate_scalability(
            num_requests=4, concurrent_requests=1, test_func=mock_test_func_with_failures
        )

        assert metrics["total_requests"] == 4
        assert metrics["failed_requests"] == 2
        assert metrics["successful_requests"] == 2
        assert metrics["error_rate"] == 0.5

    def test_scalability_calculates_throughput(self, evaluator):
        """Test that throughput is calculated correctly."""

        def fast_test():
            return (True, 1.0)

        metrics = evaluator.evaluate_scalability(num_requests=10, concurrent_requests=5, test_func=fast_test)

        assert metrics["throughput"] > 0
        assert metrics["total_duration_seconds"] > 0

    def test_scalability_calculates_percentiles(self, evaluator):
        """Test that response time percentiles are calculated."""
        response_times = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        call_idx = [0]

        def mock_test():
            idx = call_idx[0]
            call_idx[0] += 1
            return (True, response_times[idx % len(response_times)])

        metrics = evaluator.evaluate_scalability(num_requests=10, concurrent_requests=1, test_func=mock_test)

        assert "p50_response_time" in metrics
        assert "p75_response_time" in metrics
        assert "p90_response_time" in metrics
        assert "p95_response_time" in metrics
        assert "p99_response_time" in metrics


class TestEvaluateReliability:
    """Test reliability evaluation methods."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SystemEvaluator(results_dir=tmpdir)

    def test_reliability_perfect_uptime(self, evaluator):
        """Test reliability with perfect uptime and no errors."""
        metrics = evaluator.evaluate_reliability(uptime_hours=24.0, total_requests=1000, failed_requests=0)

        assert metrics["success_rate"] == 1.0
        assert metrics["error_rate"] == 0.0
        assert metrics["uptime_hours"] == 24.0

    def test_reliability_with_failures(self, evaluator):
        """Test reliability with some failures."""
        metrics = evaluator.evaluate_reliability(uptime_hours=24.0, total_requests=100, failed_requests=5)

        assert metrics["success_rate"] == 0.95
        assert metrics["error_rate"] == 0.05
        assert metrics["failed_requests"] == 5

    def test_reliability_zero_requests(self, evaluator):
        """Test reliability with zero requests doesn't divide by zero."""
        metrics = evaluator.evaluate_reliability(uptime_hours=1.0, total_requests=0, failed_requests=0)

        assert metrics["success_rate"] == 0.0
        assert metrics["error_rate"] == 0.0


class TestEvaluateUsability:
    """Test usability evaluation methods."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SystemEvaluator(results_dir=tmpdir)

    def test_usability_endpoint_count(self, evaluator):
        """Test usability counts endpoints correctly."""
        endpoints = ["/health", "/predict", "/data", "/ingest"]
        response_times = {ep: 0.05 for ep in endpoints}

        metrics = evaluator.evaluate_usability(endpoints, response_times)

        assert metrics["total_endpoints"] == 4

    def test_usability_avg_response_time(self, evaluator):
        """Test usability calculates average response time."""
        endpoints = ["/a", "/b"]
        response_times = {"/a": 0.1, "/b": 0.2}  # 100ms and 200ms

        metrics = evaluator.evaluate_usability(endpoints, response_times)

        assert metrics["avg_response_time_ms"] == pytest.approx(150.0)  # (100 + 200) / 2

    def test_usability_documentation_quality(self, evaluator):
        """Test usability captures documentation quality."""
        metrics = evaluator.evaluate_usability(
            api_endpoints=["/test"], response_times={"/test": 0.05}, documentation_quality="excellent"
        )

        assert metrics["documentation_quality"] == "excellent"


class TestGenerateEvaluationReport:
    """Test evaluation report generation."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield SystemEvaluator(results_dir=tmpdir)

    def test_report_contains_all_metrics(self, evaluator):
        """Test that generated report contains all metric categories."""
        accuracy_metrics = {"accuracy": 0.95, "precision": 0.9, "recall": 0.9, "f1_score": 0.9}
        scalability_metrics = {"throughput": 100, "avg_response_time": 50}
        reliability_metrics = {"success_rate": 0.99, "uptime_hours": 24}
        usability_metrics = {"total_endpoints": 5, "avg_response_time_ms": 50}

        report = evaluator.generate_evaluation_report(
            accuracy_metrics, scalability_metrics, reliability_metrics, usability_metrics
        )

        assert "metrics" in report
        assert "accuracy" in report["metrics"]
        assert "scalability" in report["metrics"]
        assert "reliability" in report["metrics"]
        assert "usability" in report["metrics"]

    def test_report_contains_smart_objectives(self, evaluator):
        """Test that report contains S.M.A.R.T. research objectives."""
        report = evaluator.generate_evaluation_report(
            {"accuracy": 0.9, "precision": 0.9, "recall": 0.9, "f1_score": 0.9},
            {"throughput": 100},
            {"success_rate": 0.99},
            {"total_endpoints": 5},
        )

        assert "research_objectives_alignment" in report
        smart = report["research_objectives_alignment"]
        assert "specific" in smart
        assert "measurable" in smart
        assert "achievable" in smart
        assert "relevant" in smart
        assert "time_bound" in smart

    def test_report_saves_to_file(self, evaluator):
        """Test that report is saved to JSON file."""
        report = evaluator.generate_evaluation_report(
            {"accuracy": 0.9, "precision": 0.9, "recall": 0.9, "f1_score": 0.9},
            {"throughput": 100},
            {"success_rate": 0.99},
            {"total_endpoints": 5},
        )

        # Check that a file was created
        report_files = list(evaluator.results_dir.glob("evaluation_report_*.json"))
        assert len(report_files) >= 1

        # Verify file content
        with open(report_files[0], "r") as f:
            saved_report = json.load(f)
        assert saved_report["metrics"]["accuracy"]["accuracy"] == 0.9


class TestEvaluateSystemForThesis:
    """Test the main thesis evaluation function."""

    def test_evaluate_system_returns_report(self):
        """Test that evaluate_system_for_thesis returns a complete report."""
        with patch("app.services.evaluation.SystemEvaluator") as MockEvaluator:
            mock_instance = MagicMock()
            mock_instance.evaluate_accuracy.return_value = {
                "accuracy": 1.0,
                "precision": 1.0,
                "recall": 1.0,
                "f1_score": 1.0,
            }
            mock_instance.evaluate_scalability.return_value = {"throughput": 100}
            mock_instance.evaluate_reliability.return_value = {"success_rate": 0.99}
            mock_instance.evaluate_usability.return_value = {"total_endpoints": 5}
            mock_instance.generate_evaluation_report.return_value = {"status": "complete"}
            MockEvaluator.return_value = mock_instance

            report = evaluate_system_for_thesis()

            assert report == {"status": "complete"}
            mock_instance.evaluate_accuracy.assert_called_once()
            mock_instance.evaluate_scalability.assert_called_once()
            mock_instance.evaluate_reliability.assert_called_once()
            mock_instance.evaluate_usability.assert_called_once()
            mock_instance.generate_evaluation_report.assert_called_once()
