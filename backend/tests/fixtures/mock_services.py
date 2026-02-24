"""Mock external service fixtures for test isolation."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(scope="function")
def mock_prediction_service():
    """
    Mock prediction service for tests.

    Provides consistent, predictable prediction results
    without requiring actual model loading.
    """
    with patch("app.services.predict.PredictionService", autospec=True) as mock_class:
        mock_instance = MagicMock()
        mock_instance.predict.return_value = {
            "prediction": 0,
            "probability": {"flood": 0.15, "no_flood": 0.85},
            "confidence": 0.85,
            "risk_level": 0,
        }
        mock_instance.model = MagicMock()
        mock_instance.is_model_loaded.return_value = True
        mock_instance.model_version = "1.0.0"
        mock_instance.model_path = "models/test_model.joblib"
        mock_class.get_instance.return_value = mock_instance
        yield mock_instance


@pytest.fixture(scope="function")
def mock_worldtides_service():
    """
    Mock WorldTides service for tide tests.

    Provides consistent tide data without requiring API calls.
    """
    with patch("app.api.routes.tides._get_worldtides_service") as mock_get:
        mock_service = MagicMock()
        mock_service.is_available.return_value = True
        mock_service.get_current_tide.return_value = {
            "height": 1.5,
            "timestamp": "2026-01-30T10:00:00Z",
            "type": "rising",
        }
        mock_service.get_extremes.return_value = {
            "data": [
                {"type": "high", "height": 2.1, "time": "2026-01-30T12:00:00Z"},
                {"type": "low", "height": 0.3, "time": "2026-01-30T18:00:00Z"},
            ]
        }
        mock_service.get_prediction.return_value = {
            "heights": [1.5, 1.8, 2.0, 1.9],
            "times": ["10:00", "11:00", "12:00", "13:00"],
        }
        mock_get.return_value = mock_service
        yield mock_service


@pytest.fixture(scope="function")
def mock_health_checks():
    """
    Mock all health check dependencies.

    This prevents tests from failing due to external service unavailability.
    """
    with (
        patch("app.api.routes.health.check_database") as mock_db,
        patch("app.api.routes.health.check_model") as mock_model,
        patch("app.api.routes.health.check_redis") as mock_redis,
    ):
        mock_db.return_value = {"status": "healthy", "latency_ms": 5}
        mock_model.return_value = {"status": "healthy", "loaded": True}
        mock_redis.return_value = {"status": "healthy", "connected": True}
        yield {
            "database": mock_db,
            "model": mock_model,
            "redis": mock_redis,
        }


# ============================================================================
# External API Mocking Fixtures
# ============================================================================


@pytest.fixture
def mock_weather_api():
    """Mock weather API responses."""
    return {
        "current": {
            "temperature": 298.15,
            "humidity": 75.0,
            "precipitation": 5.0,
            "wind_speed": 10.0,
            "pressure": 1013.25,
        },
        "forecast": [
            {"time": "2025-01-15T12:00:00Z", "temperature": 299.0, "precipitation": 2.0},
            {"time": "2025-01-15T15:00:00Z", "temperature": 301.0, "precipitation": 0.0},
            {"time": "2025-01-15T18:00:00Z", "temperature": 298.0, "precipitation": 10.0},
        ],
    }


@pytest.fixture
def mock_requests(mock_weather_api):
    """Mock requests library for external API calls."""
    with patch("requests.get") as mock_get:
        response_mock = MagicMock()
        response_mock.status_code = 200
        response_mock.json.return_value = mock_weather_api
        response_mock.text = '{"status": "ok"}'
        response_mock.headers = {"Content-Type": "application/json"}
        response_mock.raise_for_status = MagicMock()
        mock_get.return_value = response_mock
        yield mock_get


@pytest.fixture
def mock_httpx():
    """Mock httpx library for async HTTP calls."""
    with patch("httpx.AsyncClient") as mock_client:
        client_instance = MagicMock()
        response_mock = MagicMock()
        response_mock.status_code = 200
        response_mock.json.return_value = {"status": "ok"}
        client_instance.get = MagicMock(return_value=response_mock)
        client_instance.post = MagicMock(return_value=response_mock)
        mock_client.return_value.__aenter__ = MagicMock(return_value=client_instance)
        mock_client.return_value.__aexit__ = MagicMock(return_value=None)
        yield mock_client


# ============================================================================
# External API Mock Fixtures (Contract Testing)
# ============================================================================


@pytest.fixture
def mock_google_weather_response():
    """Mock Google Weather API response."""
    return {
        "currentConditions": {
            "temperature": {"value": 28.5},
            "humidity": {"value": 75},
            "precipitation": {"value": 5.0},
            "windSpeed": {"value": 15.0},
            "pressure": {"value": 1013.25},
            "uvIndex": {"value": 7},
            "cloudCover": {"value": 40},
        },
        "forecast": {
            "days": [
                {
                    "date": "2025-01-21",
                    "maxTemperature": {"value": 32.0},
                    "minTemperature": {"value": 24.0},
                    "precipitation": {"value": 10.0},
                },
                {
                    "date": "2025-01-22",
                    "maxTemperature": {"value": 30.0},
                    "minTemperature": {"value": 25.0},
                    "precipitation": {"value": 25.0},
                },
            ]
        },
    }


@pytest.fixture
def mock_meteostat_response():
    """Mock Meteostat API response."""
    return {
        "data": [
            {
                "date": "2025-01-20",
                "tavg": 27.5,
                "tmin": 24.0,
                "tmax": 31.0,
                "prcp": 5.2,
                "rhum": 78,
                "wspd": 12.5,
                "pres": 1012.0,
            },
            {
                "date": "2025-01-21",
                "tavg": 28.0,
                "tmin": 25.0,
                "tmax": 32.0,
                "prcp": 15.0,
                "rhum": 82,
                "wspd": 10.0,
                "pres": 1010.5,
            },
        ],
        "meta": {"generated": "2025-01-21T12:00:00Z", "stations": ["RPLL0"]},
    }


@pytest.fixture
def mock_worldtides_response():
    """Mock WorldTides API response."""
    return {
        "status": 200,
        "callCount": 1,
        "copyright": "WorldTides",
        "requestLat": 14.4793,
        "requestLon": 121.0198,
        "responseLat": 14.4793,
        "responseLon": 121.0198,
        "atlas": "TPXO",
        "station": "MANILA",
        "heights": [
            {"dt": 1737446400, "date": "2025-01-21T08:00+08:00", "height": 0.85},
            {"dt": 1737468000, "date": "2025-01-21T14:00+08:00", "height": 1.25},
            {"dt": 1737489600, "date": "2025-01-21T20:00+08:00", "height": 0.45},
        ],
        "extremes": [
            {"dt": 1737457200, "date": "2025-01-21T11:00+08:00", "height": 1.35, "type": "High"},
            {"dt": 1737500400, "date": "2025-01-21T23:00+08:00", "height": 0.25, "type": "Low"},
        ],
    }


@pytest.fixture
def mock_external_apis(mock_google_weather_response, mock_meteostat_response, mock_worldtides_response):
    """Mock all external API calls for integration testing."""
    with (
        patch("app.services.google_weather_service.requests.get") as mock_google,
        patch("app.services.meteostat_service.requests.get") as mock_meteostat,
        patch("app.services.worldtides_service.requests.get") as mock_tides,
    ):

        # Google Weather
        google_response = MagicMock()
        google_response.status_code = 200
        google_response.json.return_value = mock_google_weather_response
        google_response.raise_for_status = MagicMock()
        mock_google.return_value = google_response

        # Meteostat
        meteostat_response = MagicMock()
        meteostat_response.status_code = 200
        meteostat_response.json.return_value = mock_meteostat_response
        meteostat_response.raise_for_status = MagicMock()
        mock_meteostat.return_value = meteostat_response

        # WorldTides
        tides_response = MagicMock()
        tides_response.status_code = 200
        tides_response.json.return_value = mock_worldtides_response
        tides_response.raise_for_status = MagicMock()
        mock_tides.return_value = tides_response

        yield {"google": mock_google, "meteostat": mock_meteostat, "worldtides": mock_tides}
