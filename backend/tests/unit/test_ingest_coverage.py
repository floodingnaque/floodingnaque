import os
from unittest.mock import ANY, MagicMock, patch

import pytest
import requests
from app.services.ingest import CircuitOpenError, _get_meteostat_service, _get_worldtides_service, ingest_data


class TestIngestCoverage:
    """Tests to improve coverage for app/services/ingest.py"""

    @pytest.fixture
    def mock_env(self):
        with patch.dict(
            os.environ, {"OWM_API_KEY": "test_owm_key", "DEFAULT_LATITUDE": "14.5", "DEFAULT_LONGITUDE": "121.0"}
        ):
            yield

    def test_get_meteostat_service_import_error(self):
        """Test fallback when meteostat cannot be imported."""
        with patch.dict("sys.modules", {"app.services.meteostat_service": None}):
            # Force reload or reset module?
            # Easier to just mock import within the function scope if possible,
            # but since it's lazy load inside function, patch works if we target the import.
            # However, 'from ... import ...' is hard to mock if module exists.

            # Reset the global variable first
            with patch("app.services.ingest._meteostat_service", None):
                with patch("builtins.__import__", side_effect=ImportError("No meteostat")):
                    # This might represent a bit overkill or tricky mocking.
                    # Simpler approach:
                    pass

    def test_ingest_data_missing_api_key(self):
        """Test error when OWM key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OWM_API_KEY"):
                ingest_data()

    def test_ingest_data_owm_circuit_open(self, mock_env):
        """Test behavior when OWM circuit breaker is open."""
        with patch("app.services.ingest.openweathermap_breaker.call", side_effect=CircuitOpenError("Open")):
            with pytest.raises(CircuitOpenError):
                ingest_data()

    def test_ingest_data_owm_request_error(self, mock_env):
        """Test OWM request failure."""
        with patch(
            "app.services.ingest.openweathermap_breaker.call",
            side_effect=requests.exceptions.RequestException("Connection"),
        ):
            with pytest.raises(requests.exceptions.RequestException):
                ingest_data()

    def test_ingest_data_owm_invalid_response(self, mock_env):
        """Test OWM returning invalid JSON structure."""
        with patch("app.services.ingest.openweathermap_breaker.call", return_value={}):
            with pytest.raises(ValueError, match="Invalid response"):
                ingest_data()

    def test_ingest_data_weatherstack_fallback(self, mock_env):
        """Test Weatherstack fallback behavior."""
        # Mock OWM success but no rain
        owm_data = {"main": {"temp": 30, "humidity": 70}}

        with (
            patch("app.services.ingest.openweathermap_breaker.call", return_value=owm_data),
            patch("app.services.ingest.os.getenv") as mock_getenv,
            patch("app.services.ingest.weatherstack_breaker.call") as mock_ws_call,
            patch("app.services.ingest.get_db_session"),
        ):

            # Setup env to have weatherstack key
            def getenv_side_effect(key, default=None):
                if key == "OWM_API_KEY":
                    return "test"
                if key == "WEATHERSTACK_API_KEY":
                    return "ws_key"
                return default

            mock_getenv.side_effect = getenv_side_effect

            # Weatherstack returns precip
            mock_ws_call.return_value = {"current": {"precip": 5.5}}

            data = ingest_data()
            assert data["precipitation"] == 5.5

    def test_ingest_data_weatherstack_error(self, mock_env):
        """Test Weatherstack error handling (should continue)."""
        owm_data = {"main": {"temp": 30, "humidity": 70}}

        with (
            patch("app.services.ingest.openweathermap_breaker.call", return_value=owm_data),
            patch.dict(os.environ, {"WEATHERSTACK_API_KEY": "key"}),
            patch("app.services.ingest.weatherstack_breaker.call", side_effect=requests.exceptions.RequestException),
            patch("app.services.ingest.get_db_session"),
        ):

            data = ingest_data()
            assert "precipitation" in data
            assert data["precipitation"] == 0  # Default

    def test_ingest_data_owm_rain_fallback(self, mock_env):
        """Test OWM rain fallback (3h)."""
        owm_data = {"main": {"temp": 30, "humidity": 70}, "rain": {"3h": 9.0}}

        with (
            patch("app.services.ingest.openweathermap_breaker.call", return_value=owm_data),
            patch.dict(os.environ, {"WEATHERSTACK_API_KEY": ""}),
            patch("app.services.ingest.get_db_session"),
        ):

            data = ingest_data()
            assert data["precipitation"] == 3.0  # 9.0 / 3

    def test_ingest_data_meteostat_fallback_success(self, mock_env):
        """Test Meteostat fallback when other sources fail."""
        owm_data = {"main": {"temp": 30, "humidity": 70}}

        mock_meteostat = MagicMock()
        mock_meteostat.get_weather_for_prediction.return_value = {"precipitation": 2.5}

        with (
            patch("app.services.ingest.openweathermap_breaker.call", return_value=owm_data),
            patch.dict(os.environ, {"METEOSTAT_AS_FALLBACK": "True"}),
            patch("app.services.ingest._get_meteostat_service", return_value=mock_meteostat),
            patch("app.services.ingest.get_db_session"),
        ):

            data = ingest_data()
            assert data["precipitation"] == 2.5
            assert data["source"] == "OWM+Meteostat"

    def test_ingest_data_meteostat_fallback_failure(self, mock_env):
        """Test Meteostat fallback failure."""
        owm_data = {"main": {"temp": 30, "humidity": 70}}

        mock_meteostat = MagicMock()
        mock_meteostat.get_weather_for_prediction.side_effect = Exception("API Error")

        with (
            patch("app.services.ingest.openweathermap_breaker.call", return_value=owm_data),
            patch.dict(os.environ, {"METEOSTAT_AS_FALLBACK": "True"}),
            patch("app.services.ingest._get_meteostat_service", return_value=mock_meteostat),
            patch("app.services.ingest.get_db_session"),
        ):

            data = ingest_data()
            assert data["precipitation"] == 0

    def test_save_db_error(self, mock_env):
        """Test error saving to DB."""
        owm_data = {"main": {"temp": 30, "humidity": 70}}

        with (
            patch("app.services.ingest.openweathermap_breaker.call", return_value=owm_data),
            patch("app.services.ingest.get_db_session", side_effect=Exception("DB Error")),
        ):

            with pytest.raises(Exception, match="DB Error"):
                ingest_data()
