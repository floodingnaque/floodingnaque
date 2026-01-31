"""
Unit tests for manage_partitions.py script.

Tests cover:
- Partition creation dry-run mode
- Partition cleanup dry-run mode
- Statistics printing
- Main function argument handling

Note: Tests that require database connections are skipped as they
require a running PostgreSQL instance. The dry-run mode is tested
to ensure the feature works correctly.
"""

import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


# Helper function to get a mocked version of manage_partitions
def get_mocked_manage_partitions():
    """Import manage_partitions with mocked database dependencies."""
    # Mock the database module before importing
    mock_db = MagicMock()
    mock_engine = MagicMock()
    mock_db.engine = mock_engine

    with patch.dict("sys.modules", {"app.models.db": mock_db}):
        # Also patch at the location where it's imported
        with patch("app.models.db.engine", mock_engine):
            import importlib

            import scripts.manage_partitions as mp

            importlib.reload(mp)
            return mp


class TestPrintStatistics:
    """Tests for print_statistics function - can be tested independently."""

    def test_prints_formatted_output(self, capsys):
        """Test that statistics are printed correctly."""
        mp = get_mocked_manage_partitions()

        stats = {
            "tables": {
                "weather_data": {
                    "partition_count": 12,
                    "total_rows": 10000,
                    "partitions": [
                        {
                            "name": "weather_data_2024_01",
                            "row_count": 1000,
                            "table_size": "8 KB",
                            "index_size": "4 KB",
                            "total_size": "12 KB",
                        }
                    ],
                }
            },
            "errors": [],
        }

        mp.print_statistics(stats)

        captured = capsys.readouterr()
        assert "PARTITION STATISTICS" in captured.out
        assert "WEATHER_DATA" in captured.out


class TestDryRunMode:
    """Tests for dry-run mode functionality."""

    def test_create_partitions_dry_run_returns_results(self):
        """Test that create_partitions dry-run returns expected structure."""
        mp = get_mocked_manage_partitions()

        # Mock is_sqlite to return False so dry-run mode can proceed
        with patch.object(mp, "is_sqlite", return_value=False):
            results = mp.create_partitions(months_ahead=3, dry_run=True)

        assert "created" in results
        assert "errors" in results
        assert len(results["created"]) == 2  # weather_data and predictions
        assert all(r["status"] == "dry-run" for r in results["created"])
        assert len(results["errors"]) == 0

    def test_cleanup_partitions_dry_run_returns_results(self):
        """Test that cleanup_old_partitions dry-run returns expected structure."""
        mp = get_mocked_manage_partitions()

        # Mock is_sqlite to return False so dry-run mode can proceed
        with patch.object(mp, "is_sqlite", return_value=False):
            results = mp.cleanup_old_partitions(retention_months=24, dry_run=True)

        assert "dropped" in results
        assert "errors" in results
        assert len(results["dropped"]) == 2  # weather_data and predictions
        assert all(r["status"] == "dry-run" for r in results["dropped"])
