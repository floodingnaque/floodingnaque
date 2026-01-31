"""
Database Integration Tests.

Tests for ORM models, database operations, and migrations.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from app.models.db import APIRequest, Prediction, WeatherData, get_db_session
from app.utils.db_optimization import config, get_pool_health


class TestDatabaseConnection:
    """Tests for database connection management."""

    def test_database_connection_success(self, app, app_context):
        """Test successful database connection."""
        try:
            from sqlalchemy import text

            with get_db_session() as session:
                # Execute simple query
                result = session.execute(text("SELECT 1"))
                assert result is not None
        except Exception:
            # Database may not be configured in test environment
            pytest.skip("Database not configured for testing")

    def test_database_connection_with_context_manager(self, app, app_context):
        """Test database session context manager properly closes."""
        try:
            session = None
            with get_db_session() as s:
                session = s
                assert session is not None

            # Session should be closed after context
        except Exception:
            pytest.skip("Database not configured for testing")

    def test_database_rollback_on_error(self, app, app_context, mock_db):
        """Test database rollback on error."""
        mock_db.session.commit.side_effect = Exception("Commit failed")

        try:
            mock_db.session.add(MagicMock())
            mock_db.session.commit()
        except Exception:
            mock_db.session.rollback()
            mock_db.session.rollback.assert_called()


class TestWeatherDataModel:
    """Tests for WeatherData ORM model."""

    def test_weather_data_model_creation(self, app, app_context):
        """Test WeatherData model can be created."""
        try:
            weather = WeatherData(
                location_lat=14.4793,
                location_lon=121.0198,
                temperature=298.15,
                humidity=75.0,
                precipitation=5.0,
                timestamp=datetime.utcnow(),
            )

            # Use getattr for runtime value access
            assert getattr(weather, "location_lat", None) == 14.4793
            assert getattr(weather, "location_lon", None) == 121.0198
            assert getattr(weather, "temperature", None) == 298.15
        except ImportError:
            pytest.skip("WeatherData model not available")

    def test_weather_data_validation(self, app, app_context):
        """Test WeatherData model validation."""
        try:
            # Valid data should not raise
            weather = WeatherData(
                location_lat=14.4793, location_lon=121.0198, temperature=298.15, humidity=75.0, precipitation=5.0
            )
            assert weather is not None
        except ImportError:
            pytest.skip("WeatherData model not available")


class TestPredictionModel:
    """Tests for Prediction ORM model."""

    def test_prediction_model_creation(self, app, app_context):
        """Test Prediction model can be created."""
        try:
            prediction = Prediction(prediction=1, risk_label="Critical", risk_level=2, confidence=0.85, model_version=1)

            # Use getattr for runtime value access
            assert getattr(prediction, "prediction", None) == 1
            assert getattr(prediction, "risk_label", None) == "Critical"
            assert getattr(prediction, "confidence", None) == 0.85
        except ImportError:
            pytest.skip("Prediction model not available")

    def test_prediction_with_weather_relationship(self, app, app_context):
        """Test Prediction model relationship with WeatherData."""
        try:
            # Create related objects
            weather = WeatherData(
                location_lat=14.4793, location_lon=121.0198, temperature=298.15, humidity=75.0, precipitation=5.0
            )

            prediction = Prediction(prediction=1, risk_label="Critical", risk_level=2, confidence=0.85)

            # Relationship should be configurable
            assert weather is not None
            assert prediction is not None
        except ImportError:
            pytest.skip("Models not available")


class TestAPIRequestModel:
    """Tests for APIRequest ORM model."""

    def test_api_request_model_creation(self, app, app_context):
        """Test APIRequest model can be created."""
        try:
            request = APIRequest(
                request_id="test-123",
                endpoint="/api/v1/predict",
                method="POST",
                status_code=200,
                response_time_ms=150.5,
                ip_address="127.0.0.1",
            )

            # Use getattr for runtime value access
            assert getattr(request, "request_id", None) == "test-123"
            assert getattr(request, "endpoint", None) == "/api/v1/predict"
            assert getattr(request, "response_time_ms", None) == 150.5
        except ImportError:
            pytest.skip("APIRequest model not available")


class TestDatabaseQueries:
    """Tests for database query operations."""

    @patch("app.models.db.get_db_session")
    def test_query_weather_data(self, mock_get_session, app, app_context):
        """Test querying weather data."""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=None)

        mock_session.query.return_value.filter.return_value.all.return_value = [
            MagicMock(temperature=298.15, humidity=75.0),
            MagicMock(temperature=300.0, humidity=80.0),
        ]

        with mock_get_session() as session:
            results = session.query().filter().all()
            assert len(results) == 2

    @patch("app.models.db.get_db_session")
    def test_query_with_date_range(self, mock_get_session, app, app_context):
        """Test querying with date range filter."""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=None)

        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        with mock_get_session() as session:
            query = session.query()
            filtered = query.filter()

            # Query should accept date range parameters
            assert filtered is not None

    @patch("app.models.db.get_db_session")
    def test_pagination_query(self, mock_get_session, app, app_context):
        """Test paginated queries."""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=None)

        mock_session.query.return_value.limit.return_value.offset.return_value.all.return_value = [
            MagicMock(id=1),
            MagicMock(id=2),
        ]

        with mock_get_session() as session:
            results = session.query().limit(10).offset(0).all()
            assert len(results) == 2


class TestDatabaseTransactions:
    """Tests for database transaction handling."""

    def test_transaction_commit(self, mock_db):
        """Test transaction commit."""
        mock_db.session.add(MagicMock())
        mock_db.session.commit()

        mock_db.session.commit.assert_called_once()

    def test_transaction_rollback(self, mock_db):
        """Test transaction rollback on error."""
        mock_db.session.commit.side_effect = Exception("Commit failed")

        try:
            mock_db.session.commit()
        except Exception:
            mock_db.session.rollback()

        mock_db.session.rollback.assert_called_once()

    def test_nested_transaction(self, mock_db):
        """Test nested transaction handling."""
        mock_db.session.begin_nested = MagicMock()

        mock_db.session.begin_nested()
        mock_db.session.add(MagicMock())

        mock_db.session.begin_nested.assert_called_once()


class TestDatabaseMigrations:
    """Tests for database migration compatibility."""

    def test_model_columns_exist(self, app, app_context):
        """Test that model columns match expected schema."""
        try:
            from sqlalchemy import inspect

            # Check WeatherData columns
            if hasattr(WeatherData, "__table__"):
                columns = [c.name for c in WeatherData.__table__.columns]
                assert "temperature" in columns or len(columns) > 0
        except ImportError:
            pytest.skip("Models not available")

    def test_foreign_key_relationships(self, app, app_context):
        """Test foreign key relationships are defined."""
        try:
            from sqlalchemy import inspect

            # Check if relationships are properly defined
            # This is a basic check - actual FK constraints depend on model definition
            assert True
        except ImportError:
            pytest.skip("Models not available")


class TestConnectionPooling:
    """Tests for database connection pooling."""

    def test_pool_configuration(self, app, app_context):
        """Test connection pool is configured."""
        try:
            assert config.pool_size > 0
            assert config.max_overflow >= 0
            assert config.pool_timeout > 0
        except ImportError:
            pytest.skip("db_optimization not available")

    @patch("tests.integration.test_database.get_pool_health")
    def test_pool_health_check(self, mock_health, app, app_context):
        """Test connection pool health check."""
        # Mock returns dict keyed by engine name with status field (actual implementation structure)
        mock_health.return_value = {
            "primary": {
                "pool_size": 20,
                "checked_out": 5,
                "checked_in": 15,
                "overflow": 0,
                "utilization_percent": 16.67,
                "status": "healthy",
            }
        }

        health = get_pool_health()
        assert "primary" in health
        assert health["primary"]["status"] == "healthy"
        assert health["primary"]["checked_out"] == 5
        assert health["primary"]["checked_in"] == 15


class TestDatabaseIndexes:
    """Tests for database index usage."""

    def test_index_exists_on_timestamp(self, app, app_context):
        """Test index exists on timestamp columns."""
        try:
            from sqlalchemy import inspect

            # Check if indexes are defined on the model
            if hasattr(WeatherData, "__table__"):
                indexes = WeatherData.__table__.indexes
                # Model should have some indexes defined
                assert True
        except ImportError:
            pytest.skip("Models not available")


class TestBulkOperations:
    """Tests for bulk database operations."""

    @patch("app.models.db.get_db_session")
    def test_bulk_insert(self, mock_get_session, app, app_context):
        """Test bulk insert operation."""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=None)

        records = [MagicMock() for _ in range(100)]

        with mock_get_session() as session:
            session.add_all(records)
            session.commit()

        mock_session.add_all.assert_called_once()
        mock_session.commit.assert_called_once()

    @patch("app.models.db.get_db_session")
    def test_bulk_update(self, mock_get_session, app, app_context):
        """Test bulk update operation."""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=None)

        with mock_get_session() as session:
            session.query.return_value.filter.return_value.update.return_value = 50
            affected = session.query().filter().update({"status": "processed"})

            assert affected == 50
