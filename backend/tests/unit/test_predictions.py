"""
Unit tests for predictions routes.

Tests prediction history CRUD operations.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

# Row-like object returned by SQLAlchemy when add_columns() is used.
# row[0] = the Prediction model instance, row._total = windowed count.


class _Row:
    """Mimics SQLAlchemy's Row object from add_columns() queries."""

    __slots__ = ("_data", "_total")

    def __init__(self, pred, total):
        self._data = (pred, total)
        self._total = total

    def __getitem__(self, idx):
        return self._data[idx]

    def __len__(self):
        return len(self._data)


def _wrap_as_rows(predictions, total=None):
    """Wrap prediction mocks into (pred, _total) rows that mimic add_columns output."""
    count = total if total is not None else len(predictions)
    return [_Row(p, count) for p in predictions]


# API version prefix constant
API_V1_PREFIX = "/api/v1"


class TestGetPredictions:
    """Tests for listing predictions endpoint."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        with patch("app.api.routes.predictions.get_db_session") as mock:
            session = MagicMock()
            mock.return_value.__enter__ = Mock(return_value=session)
            mock.return_value.__exit__ = Mock(return_value=False)
            yield session

    @pytest.fixture
    def mock_predictions(self):
        """Create mock prediction records."""
        predictions = []
        for i in range(5):
            pred = MagicMock()
            pred.id = i + 1
            pred.weather_data_id = i + 100
            pred.prediction = i % 2
            pred.risk_level = i % 3
            pred.risk_label = ["Safe", "Alert", "Critical"][i % 3]
            pred.confidence = 0.85 + (i * 0.01)
            pred.model_version = "1.0.0"
            pred.model_name = "flood_predictor"
            pred.created_at = datetime.now(timezone.utc) - timedelta(hours=i)
            predictions.append(pred)
        return predictions

    def test_get_predictions_default(self, client, mock_db_session, mock_predictions):
        """Test get predictions with default parameters."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = len(mock_predictions)
        mock_query.order_by.return_value = mock_query
        mock_query.add_columns.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = _wrap_as_rows(mock_predictions)
        mock_db_session.query.return_value = mock_query

        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            response = client.get(f"{API_V1_PREFIX}/predictions")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "data" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data

    def test_get_predictions_with_limit(self, client, mock_db_session, mock_predictions):
        """Test get predictions with custom limit."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = len(mock_predictions)
        mock_query.order_by.return_value = mock_query
        mock_query.add_columns.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = _wrap_as_rows(mock_predictions[:2], total=len(mock_predictions))
        mock_db_session.query.return_value = mock_query

        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            response = client.get(f"{API_V1_PREFIX}/predictions?limit=2")

        assert response.status_code == 200
        data = response.get_json()
        assert data["limit"] == 2

    def test_get_predictions_invalid_limit(self, client):
        """Test get predictions with invalid limit (less than 1)."""
        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            response = client.get(f"{API_V1_PREFIX}/predictions?limit=0")

        assert response.status_code == 400

    def test_get_predictions_with_offset(self, client, mock_db_session, mock_predictions):
        """Test get predictions with offset pagination."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = len(mock_predictions)
        mock_query.order_by.return_value = mock_query
        mock_query.add_columns.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = _wrap_as_rows(mock_predictions[2:], total=len(mock_predictions))
        mock_db_session.query.return_value = mock_query

        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            response = client.get(f"{API_V1_PREFIX}/predictions?offset=2")

        assert response.status_code == 200
        data = response.get_json()
        assert data["offset"] == 2

    def test_get_predictions_filter_risk_level(self, client, mock_db_session, mock_predictions):
        """Test get predictions filtered by risk level."""
        filtered = [p for p in mock_predictions if p.risk_level == 0]

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = len(filtered)
        mock_query.order_by.return_value = mock_query
        mock_query.add_columns.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = _wrap_as_rows(filtered)
        mock_db_session.query.return_value = mock_query

        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            response = client.get(f"{API_V1_PREFIX}/predictions?risk_level=0")

        assert response.status_code == 200

    def test_get_predictions_invalid_risk_level(self, client, mock_db_session):
        """Test get predictions with invalid risk level."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_db_session.query.return_value = mock_query

        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            response = client.get(f"{API_V1_PREFIX}/predictions?risk_level=5")

        assert response.status_code == 400

    def test_get_predictions_filter_prediction(self, client, mock_db_session, mock_predictions):
        """Test get predictions filtered by prediction result."""
        filtered = [p for p in mock_predictions if p.prediction == 1]
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 2
        mock_query.order_by.return_value = mock_query
        mock_query.add_columns.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = _wrap_as_rows(filtered, total=2)
        mock_db_session.query.return_value = mock_query

        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            response = client.get(f"{API_V1_PREFIX}/predictions?prediction=1")

        assert response.status_code == 200

    def test_get_predictions_invalid_prediction_filter(self, client, mock_db_session):
        """Test get predictions with invalid prediction filter."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_db_session.query.return_value = mock_query

        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            response = client.get(f"{API_V1_PREFIX}/predictions?prediction=5")

        assert response.status_code == 400

    def test_get_predictions_sort_by(self, client, mock_db_session, mock_predictions):
        """Test get predictions with sorting."""
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = len(mock_predictions)
        mock_query.order_by.return_value = mock_query
        mock_query.add_columns.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = _wrap_as_rows(mock_predictions)
        mock_db_session.query.return_value = mock_query

        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            response = client.get(f"{API_V1_PREFIX}/predictions?sort_by=confidence&order=asc")

        assert response.status_code == 200

    def test_get_predictions_invalid_sort_by(self, client):
        """Test get predictions with invalid sort field."""
        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            response = client.get(f"{API_V1_PREFIX}/predictions?sort_by=invalid_field")

        assert response.status_code == 400

    def test_get_predictions_invalid_order(self, client):
        """Test get predictions with invalid order."""
        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            response = client.get(f"{API_V1_PREFIX}/predictions?order=invalid")

        assert response.status_code == 400


class TestGetPredictionById:
    """Tests for getting single prediction by ID."""

    @pytest.fixture
    def mock_prediction(self):
        """Create mock prediction."""
        pred = MagicMock()
        pred.id = 1
        pred.weather_data_id = 100
        pred.prediction = 0
        pred.risk_level = 0
        pred.risk_label = "Safe"
        pred.confidence = 0.85
        pred.model_version = "1.0.0"
        pred.model_name = "flood_predictor"
        pred.created_at = datetime.now(timezone.utc)
        return pred

    @pytest.fixture
    def mock_weather(self):
        """Create mock weather data."""
        weather = MagicMock()
        weather.id = 100
        weather.temperature = 298.15
        weather.humidity = 75.0
        weather.precipitation = 5.0
        weather.wind_speed = 10.0
        weather.pressure = 1013.25
        weather.timestamp = datetime.now(timezone.utc)
        return weather

    def test_get_prediction_by_id_success(self, client, mock_prediction, mock_weather):
        """Test successful retrieval of prediction by ID."""
        mock_prediction.weather_data = mock_weather
        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.predictions.get_db_session") as mock_session:
                session = MagicMock()
                mock_session.return_value.__enter__ = Mock(return_value=session)
                mock_session.return_value.__exit__ = Mock(return_value=False)

                mock_query = MagicMock()
                mock_query.options.return_value = mock_query
                mock_query.filter.return_value = mock_query
                mock_query.first.return_value = mock_prediction
                session.query.return_value = mock_query

                response = client.get(f"{API_V1_PREFIX}/predictions/1")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["id"] == 1

    def test_get_prediction_by_id_not_found(self, client):
        """Test retrieval of non-existent prediction."""
        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.predictions.get_db_session") as mock_session:
                session = MagicMock()
                mock_session.return_value.__enter__ = Mock(return_value=session)
                mock_session.return_value.__exit__ = Mock(return_value=False)

                mock_query = MagicMock()
                mock_query.options.return_value = mock_query
                mock_query.filter.return_value = mock_query
                mock_query.first.return_value = None
                session.query.return_value = mock_query

                response = client.get(f"{API_V1_PREFIX}/predictions/999")

        assert response.status_code == 404

    def test_get_prediction_includes_weather_data(self, client, mock_prediction, mock_weather):
        """Test prediction includes associated weather data."""
        mock_prediction.weather_data = mock_weather
        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.predictions.get_db_session") as mock_session:
                session = MagicMock()
                mock_session.return_value.__enter__ = Mock(return_value=session)
                mock_session.return_value.__exit__ = Mock(return_value=False)

                mock_query = MagicMock()
                mock_query.options.return_value = mock_query
                mock_query.filter.return_value = mock_query
                mock_query.first.return_value = mock_prediction
                session.query.return_value = mock_query

                response = client.get(f"{API_V1_PREFIX}/predictions/1")

        assert response.status_code == 200
        data = response.get_json()
        assert "weather_data" in data["data"]


class TestDeletePrediction:
    """Tests for deleting prediction endpoint."""

    # Valid API key meeting minimum length (32 chars)
    TEST_API_KEY = "test-api-key-12345-valid-32chars"

    def test_delete_prediction_success(self, client):
        """Test successful prediction deletion."""
        mock_prediction = MagicMock()
        mock_prediction.id = 1

        with patch(
            "app.api.middleware.auth.validate_api_key",
            return_value=(True, ""),
        ):
            with patch(
                "app.api.middleware.auth._hash_api_key_pbkdf2",
                return_value="mock_hash",
            ):
                with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
                    with patch("app.api.routes.predictions.get_db_session") as mock_session:
                        session = MagicMock()
                        mock_session.return_value.__enter__ = Mock(return_value=session)
                        mock_session.return_value.__exit__ = Mock(return_value=False)

                        mock_query = MagicMock()
                        mock_query.filter.return_value = mock_query
                        mock_query.first.return_value = mock_prediction
                        session.query.return_value = mock_query

                        response = client.delete(
                            f"{API_V1_PREFIX}/predictions/1",
                            headers={"X-API-Key": self.TEST_API_KEY},
                        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "deleted successfully" in data["message"]

    def test_delete_prediction_not_found(self, client):
        """Test deleting non-existent prediction."""
        with patch(
            "app.api.middleware.auth.validate_api_key",
            return_value=(True, ""),
        ):
            with patch(
                "app.api.middleware.auth._hash_api_key_pbkdf2",
                return_value="mock_hash",
            ):
                with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
                    with patch("app.api.routes.predictions.get_db_session") as mock_session:
                        session = MagicMock()
                        mock_session.return_value.__enter__ = Mock(return_value=session)
                        mock_session.return_value.__exit__ = Mock(return_value=False)

                        mock_query = MagicMock()
                        mock_query.filter.return_value = mock_query
                        mock_query.first.return_value = None
                        session.query.return_value = mock_query

                        response = client.delete(
                            f"{API_V1_PREFIX}/predictions/999",
                            headers={"X-API-Key": self.TEST_API_KEY},
                        )

        assert response.status_code == 404


class TestPredictionStats:
    """Tests for prediction statistics endpoint."""

    def test_get_stats_default_days(self, client):
        """Test prediction stats with default days."""
        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.predictions.get_db_session") as mock_session:
                session = MagicMock()
                mock_session.return_value.__enter__ = Mock(return_value=session)
                mock_session.return_value.__exit__ = Mock(return_value=False)

                mock_query = MagicMock()
                mock_query.filter.return_value = mock_query
                mock_query.count.return_value = 100
                mock_query.scalar.return_value = 0.85
                session.query.return_value = mock_query

                response = client.get(f"{API_V1_PREFIX}/predictions/stats")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "stats" in data
        assert data["stats"]["period_days"] == 30

    def test_get_stats_custom_days(self, client):
        """Test prediction stats with custom days."""
        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.predictions.get_db_session") as mock_session:
                session = MagicMock()
                mock_session.return_value.__enter__ = Mock(return_value=session)
                mock_session.return_value.__exit__ = Mock(return_value=False)

                mock_query = MagicMock()
                mock_query.filter.return_value = mock_query
                mock_query.count.return_value = 50
                mock_query.scalar.return_value = 0.80
                session.query.return_value = mock_query

                response = client.get(f"{API_V1_PREFIX}/predictions/stats?days=7")

        assert response.status_code == 200
        data = response.get_json()
        assert data["stats"]["period_days"] == 7

    def test_get_stats_invalid_days(self, client):
        """Test prediction stats with invalid days."""
        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            response = client.get(f"{API_V1_PREFIX}/predictions/stats?days=0")

        assert response.status_code == 400

    def test_get_stats_structure(self, client):
        """Test prediction stats response structure."""
        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.predictions.get_db_session") as mock_session:
                session = MagicMock()
                mock_session.return_value.__enter__ = Mock(return_value=session)
                mock_session.return_value.__exit__ = Mock(return_value=False)

                mock_query = MagicMock()
                mock_query.filter.return_value = mock_query
                mock_query.count.side_effect = [100, 30, 60, 30, 10]
                mock_query.scalar.return_value = 0.85
                session.query.return_value = mock_query

                response = client.get(f"{API_V1_PREFIX}/predictions/stats")

        assert response.status_code == 200
        data = response.get_json()
        stats = data["stats"]

        assert "total_predictions" in stats
        assert "flood_predictions" in stats
        assert "no_flood_predictions" in stats
        assert "flood_percentage" in stats
        assert "risk_distribution" in stats
        assert "average_confidence" in stats


class TestRecentPredictions:
    """Tests for recent predictions endpoint."""

    @pytest.fixture
    def mock_recent_predictions(self):
        """Create mock recent predictions."""
        predictions = []
        for i in range(10):
            pred = MagicMock()
            pred.id = i + 1
            pred.prediction = i % 2
            pred.risk_level = i % 3
            pred.risk_label = ["Safe", "Alert", "Critical"][i % 3]
            pred.confidence = 0.85
            pred.created_at = datetime.now(timezone.utc) - timedelta(hours=i)
            predictions.append(pred)
        return predictions

    def test_get_recent_default_limit(self, client, mock_recent_predictions):
        """Test recent predictions with default limit."""
        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.predictions.get_db_session") as mock_session:
                session = MagicMock()
                mock_session.return_value.__enter__ = Mock(return_value=session)
                mock_session.return_value.__exit__ = Mock(return_value=False)

                mock_query = MagicMock()
                mock_query.filter.return_value = mock_query
                mock_query.order_by.return_value = mock_query
                mock_query.limit.return_value = mock_query
                mock_query.all.return_value = mock_recent_predictions[:10]
                session.query.return_value = mock_query

                response = client.get(f"{API_V1_PREFIX}/predictions/recent")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "data" in data
        assert "count" in data

    def test_get_recent_custom_limit(self, client, mock_recent_predictions):
        """Test recent predictions with custom limit."""
        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.predictions.get_db_session") as mock_session:
                session = MagicMock()
                mock_session.return_value.__enter__ = Mock(return_value=session)
                mock_session.return_value.__exit__ = Mock(return_value=False)

                mock_query = MagicMock()
                mock_query.filter.return_value = mock_query
                mock_query.order_by.return_value = mock_query
                mock_query.limit.return_value = mock_query
                mock_query.all.return_value = mock_recent_predictions[:5]
                session.query.return_value = mock_query

                response = client.get(f"{API_V1_PREFIX}/predictions/recent?limit=5")

        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] <= 5


class TestPredictionsDateFilter:
    """Tests for date filtering in predictions."""

    def test_filter_by_start_date(self, client):
        """Test predictions filtered by start date."""
        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.predictions.get_db_session") as mock_session:
                session = MagicMock()
                mock_session.return_value.__enter__ = Mock(return_value=session)
                mock_session.return_value.__exit__ = Mock(return_value=False)

                mock_query = MagicMock()
                mock_query.filter.return_value = mock_query
                mock_query.count.return_value = 10
                mock_query.order_by.return_value = mock_query
                mock_query.add_columns.return_value = mock_query
                mock_query.offset.return_value = mock_query
                mock_query.limit.return_value = mock_query
                mock_query.all.return_value = []  # empty is fine for 0 results
                session.query.return_value = mock_query

                response = client.get(f"{API_V1_PREFIX}/predictions?start_date=2025-01-01T00:00:00Z")

        assert response.status_code == 200

    def test_filter_by_end_date(self, client):
        """Test predictions filtered by end date."""
        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.predictions.get_db_session") as mock_session:
                session = MagicMock()
                mock_session.return_value.__enter__ = Mock(return_value=session)
                mock_session.return_value.__exit__ = Mock(return_value=False)

                mock_query = MagicMock()
                mock_query.filter.return_value = mock_query
                mock_query.count.return_value = 10
                mock_query.order_by.return_value = mock_query
                mock_query.add_columns.return_value = mock_query
                mock_query.offset.return_value = mock_query
                mock_query.limit.return_value = mock_query
                mock_query.all.return_value = []  # empty is fine for 0 results
                session.query.return_value = mock_query

                response = client.get(f"{API_V1_PREFIX}/predictions?end_date=2025-12-31T23:59:59Z")

        assert response.status_code == 200

    def test_invalid_start_date_format(self, client):
        """Test predictions with invalid start date format."""
        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.predictions.get_db_session") as mock_session:
                session = MagicMock()
                mock_session.return_value.__enter__ = Mock(return_value=session)
                mock_session.return_value.__exit__ = Mock(return_value=False)

                mock_query = MagicMock()
                mock_query.filter.return_value = mock_query
                session.query.return_value = mock_query

                response = client.get(f"{API_V1_PREFIX}/predictions?start_date=invalid")

        assert response.status_code == 400


class TestPredictionsErrorHandling:
    """Tests for predictions error handling."""

    def test_database_error_on_list(self, client):
        """Test list predictions handles database errors."""
        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.predictions.get_db_session") as mock_session:
                mock_session.side_effect = Exception("Database error")

                response = client.get(f"{API_V1_PREFIX}/predictions")

        assert response.status_code == 500

    def test_database_error_on_get_by_id(self, client):
        """Test get prediction by ID handles database errors."""
        with patch("app.api.routes.predictions.limiter.limit", lambda x: lambda f: f):
            with patch("app.api.routes.predictions.get_db_session") as mock_session:
                mock_session.side_effect = Exception("Database error")

                response = client.get(f"{API_V1_PREFIX}/predictions/1")

        assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
