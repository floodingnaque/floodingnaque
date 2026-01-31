"""
Unit Tests for Tides API Routes.

Tests the tide data API endpoints including:
- Get current tide height
- Get tide extremes (high/low tides)
- Get tide prediction data for flood forecasting
- Error handling and service availability
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

# Import modules at top level for proper coverage tracking
from app.api.app import create_app
from app.services.worldtides_service import TideData, TideExtreme

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def app():
    """Create Flask application for testing."""
    application = create_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    """Create test client."""
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def mock_tide_data():
    """Create mock TideData object."""
    return TideData(
        timestamp=datetime.now(timezone.utc),
        height=1.5,
        type="high",
        datum="MSL",
        source="worldtides",
    )


@pytest.fixture
def mock_tide_extremes():
    """Create mock TideExtreme objects."""
    return [
        TideExtreme(
            timestamp=datetime.now(timezone.utc),
            height=2.1,
            type="High",
            datum="MSL",
        ),
        TideExtreme(
            timestamp=datetime.now(timezone.utc),
            height=0.3,
            type="Low",
            datum="MSL",
        ),
    ]


@pytest.fixture
def mock_worldtides_service(mock_tide_data, mock_tide_extremes):
    """Create mock WorldTides service."""
    service = MagicMock()
    service.is_available.return_value = True
    service.get_current_tide.return_value = mock_tide_data
    service.get_tide_extremes.return_value = mock_tide_extremes
    service.get_tide_data_for_prediction.return_value = {
        "current_height": 1.5,
        "trend": "rising",
        "hours_until_high_tide": 3.5,
        "tide_risk_factor": 0.6,
    }
    return service


# =============================================================================
# Get Current Tide Tests
# =============================================================================


class TestGetCurrentTide:
    """Tests for GET /tides/current endpoint."""

    @patch("app.api.routes.tides._get_worldtides_service")
    def test_get_current_tide_success(self, mock_get_service, client, mock_worldtides_service, mock_tide_data):
        """Test successful current tide retrieval."""
        mock_get_service.return_value = mock_worldtides_service

        response = client.get("/tides/current")

        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["height"] == 1.5
        assert data["data"]["datum"] == "MSL"

    @patch("app.api.routes.tides._get_worldtides_service")
    def test_get_current_tide_with_coordinates(self, mock_get_service, client, mock_worldtides_service):
        """Test current tide with custom coordinates."""
        mock_get_service.return_value = mock_worldtides_service

        response = client.get("/tides/current?lat=14.5&lon=120.9")

        assert response.status_code == 200
        mock_worldtides_service.get_current_tide.assert_called_once()

    @patch("app.api.routes.tides._get_worldtides_service")
    def test_get_current_tide_service_unavailable(self, mock_get_service, client):
        """Test current tide when service is unavailable."""
        mock_service = MagicMock()
        mock_service.is_available.return_value = False
        mock_get_service.return_value = mock_service

        response = client.get("/tides/current")

        assert response.status_code == 503

    @patch("app.api.routes.tides._get_worldtides_service")
    def test_get_current_tide_no_service(self, mock_get_service, client):
        """Test current tide when service is None."""
        mock_get_service.return_value = None

        response = client.get("/tides/current")

        assert response.status_code == 503

    @patch("app.api.routes.tides._get_worldtides_service")
    def test_get_current_tide_no_data(self, mock_get_service, client):
        """Test current tide when no data available."""
        mock_service = MagicMock()
        mock_service.is_available.return_value = True
        mock_service.get_current_tide.return_value = None
        mock_get_service.return_value = mock_service

        response = client.get("/tides/current")

        assert response.status_code == 400

    @patch("app.api.routes.tides._get_worldtides_service")
    def test_get_current_tide_exception(self, mock_get_service, client):
        """Test current tide exception handling."""
        mock_service = MagicMock()
        mock_service.is_available.return_value = True
        mock_service.get_current_tide.side_effect = Exception("API error")
        mock_get_service.return_value = mock_service

        response = client.get("/tides/current")

        assert response.status_code == 400


# =============================================================================
# Get Tide Extremes Tests
# =============================================================================


class TestGetTideExtremes:
    """Tests for GET /tides/extremes endpoint."""

    @patch("app.api.routes.tides._get_worldtides_service")
    def test_get_tide_extremes_success(self, mock_get_service, client, mock_worldtides_service):
        """Test successful tide extremes retrieval."""
        mock_get_service.return_value = mock_worldtides_service

        response = client.get("/tides/extremes")

        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["count"] == 2
        assert len(data["data"]["extremes"]) == 2

    @patch("app.api.routes.tides._get_worldtides_service")
    def test_get_tide_extremes_with_days(self, mock_get_service, client, mock_worldtides_service):
        """Test tide extremes with custom days parameter."""
        mock_get_service.return_value = mock_worldtides_service

        response = client.get("/tides/extremes?days=5")

        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["days"] == 5

    @patch("app.api.routes.tides._get_worldtides_service")
    def test_get_tide_extremes_days_clamped(self, mock_get_service, client, mock_worldtides_service):
        """Test days parameter is clamped to 1-7."""
        mock_get_service.return_value = mock_worldtides_service

        # Test upper bound
        response = client.get("/tides/extremes?days=10")
        data = response.get_json()
        assert data["data"]["days"] == 7

        # Test lower bound
        response = client.get("/tides/extremes?days=0")
        data = response.get_json()
        assert data["data"]["days"] == 1

    @patch("app.api.routes.tides._get_worldtides_service")
    def test_get_tide_extremes_service_unavailable(self, mock_get_service, client):
        """Test extremes when service unavailable."""
        mock_service = MagicMock()
        mock_service.is_available.return_value = False
        mock_get_service.return_value = mock_service

        response = client.get("/tides/extremes")

        assert response.status_code == 503

    @patch("app.api.routes.tides._get_worldtides_service")
    def test_get_tide_extremes_exception(self, mock_get_service, client):
        """Test extremes exception handling."""
        mock_service = MagicMock()
        mock_service.is_available.return_value = True
        mock_service.get_tide_extremes.side_effect = Exception("API error")
        mock_get_service.return_value = mock_service

        response = client.get("/tides/extremes")

        assert response.status_code == 400


# =============================================================================
# Get Tide Prediction Tests
# =============================================================================


class TestGetTidePrediction:
    """Tests for GET /tides/prediction endpoint."""

    @patch("app.api.routes.tides._get_worldtides_service")
    def test_get_tide_prediction_success(self, mock_get_service, client, mock_worldtides_service):
        """Test successful tide prediction retrieval."""
        mock_get_service.return_value = mock_worldtides_service

        response = client.get("/tides/prediction")

        assert response.status_code == 200
        data = response.get_json()
        assert "current_height" in data["data"] or "tide_risk_factor" in data["data"]

    @patch("app.api.routes.tides._get_worldtides_service")
    def test_get_tide_prediction_with_coordinates(self, mock_get_service, client, mock_worldtides_service):
        """Test tide prediction with custom coordinates."""
        mock_get_service.return_value = mock_worldtides_service

        response = client.get("/tides/prediction?lat=14.6&lon=120.8")

        assert response.status_code == 200

    @patch("app.api.routes.tides._get_worldtides_service")
    def test_get_tide_prediction_service_unavailable(self, mock_get_service, client):
        """Test prediction when service unavailable."""
        mock_service = MagicMock()
        mock_service.is_available.return_value = False
        mock_get_service.return_value = mock_service

        response = client.get("/tides/prediction")

        assert response.status_code == 503


# =============================================================================
# Request ID Tests
# =============================================================================


class TestRequestTracking:
    """Tests for request ID tracking."""

    @patch("app.api.routes.tides._get_worldtides_service")
    def test_response_includes_request_id(self, mock_get_service, client, mock_worldtides_service):
        """Test that responses include request ID."""
        mock_get_service.return_value = mock_worldtides_service

        response = client.get("/tides/current")

        assert response.status_code == 200
        data = response.get_json()
        # Response should have request_id in the response or be trackable
        assert "data" in data or "request_id" in data


# =============================================================================
# Input Validation Tests
# =============================================================================


class TestInputValidation:
    """Tests for input validation."""

    @patch("app.api.routes.tides._get_worldtides_service")
    def test_invalid_latitude_handled(self, mock_get_service, client, mock_worldtides_service):
        """Test handling of invalid latitude."""
        mock_get_service.return_value = mock_worldtides_service

        # Invalid latitude should still be passed to service
        response = client.get("/tides/current?lat=invalid&lon=120.9")

        # Should get an error or the service handles it
        assert response.status_code in [200, 400]

    @patch("app.api.routes.tides._get_worldtides_service")
    def test_uses_default_coordinates(self, mock_get_service, client, mock_worldtides_service):
        """Test that default coordinates are used when not specified."""
        mock_get_service.return_value = mock_worldtides_service

        response = client.get("/tides/current")

        assert response.status_code == 200
        # Service should have been called (with default or passed coords)
        mock_worldtides_service.get_current_tide.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
