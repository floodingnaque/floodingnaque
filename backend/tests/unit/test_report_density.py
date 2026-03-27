"""Unit tests for GET /api/v1/reports/density endpoint."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock


class TestReportDensityEndpoint:
    """Tests for the community report density GeoJSON endpoint."""

    DENSITY_URL = "/api/v1/reports/density"

    def _make_report(self, **overrides):
        """Create a mock CommunityReport object."""
        r = MagicMock()
        r.is_deleted = False
        r.latitude = overrides.get("latitude", 14.4793)
        r.longitude = overrides.get("longitude", 121.0198)
        r.credibility_score = overrides.get("credibility_score", 0.8)
        r.risk_label = overrides.get("risk_label", "Alert")
        r.flood_height_cm = overrides.get("flood_height_cm", 15.0)
        r.created_at = overrides.get(
            "created_at", datetime.now(timezone.utc) - timedelta(hours=1)
        )
        return r

    def test_density_empty(self, client):
        """No reports returns empty FeatureCollection."""
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        query = mock_session.query.return_value.filter.return_value
        query.all.return_value = []

        with patch("app.api.routes.community_reports.get_db_session", return_value=mock_session):
            response = client.get(self.DENSITY_URL)

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["type"] == "FeatureCollection"
        assert data["features"] == []
        assert data["meta"]["total_reports"] == 0
        assert data["meta"]["grid_cells"] == 0

    def test_density_single_report(self, client):
        """Single report produces one grid cell feature."""
        reports = [self._make_report(latitude=14.4793, longitude=121.0198)]

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        query = mock_session.query.return_value.filter.return_value
        query.all.return_value = reports

        with patch("app.api.routes.community_reports.get_db_session", return_value=mock_session):
            response = client.get(self.DENSITY_URL)

        assert response.status_code == 200
        data = response.get_json()
        assert len(data["features"]) == 1
        feat = data["features"][0]
        assert feat["type"] == "Feature"
        assert feat["geometry"]["type"] == "Point"
        assert len(feat["geometry"]["coordinates"]) == 2
        props = feat["properties"]
        assert props["count"] == 1
        assert props["weight"] == 1
        assert props["dominant_risk"] == "Alert"
        assert props["avg_credibility"] == 0.8

    def test_density_reports_same_cell(self, client):
        """Reports in the same grid cell are aggregated."""
        # Two reports very close together (same 0.001° cell)
        reports = [
            self._make_report(latitude=14.4793, longitude=121.0198, credibility_score=0.9, flood_height_cm=10.0),
            self._make_report(latitude=14.4794, longitude=121.0199, credibility_score=0.7, flood_height_cm=25.0),
        ]

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        query = mock_session.query.return_value.filter.return_value
        query.all.return_value = reports

        with patch("app.api.routes.community_reports.get_db_session", return_value=mock_session):
            response = client.get(self.DENSITY_URL)

        data = response.get_json()
        assert data["meta"]["grid_cells"] == 1
        assert data["meta"]["total_reports"] == 2
        props = data["features"][0]["properties"]
        assert props["count"] == 2
        assert props["max_flood_height_cm"] == 25.0
        assert props["avg_credibility"] == 0.8  # (0.9 + 0.7) / 2

    def test_density_reports_different_cells(self, client):
        """Reports in different grid cells produce separate features."""
        reports = [
            self._make_report(latitude=14.479, longitude=121.019),
            self._make_report(latitude=14.490, longitude=121.030),  # different cell
        ]

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        query = mock_session.query.return_value.filter.return_value
        query.all.return_value = reports

        with patch("app.api.routes.community_reports.get_db_session", return_value=mock_session):
            response = client.get(self.DENSITY_URL)

        data = response.get_json()
        assert data["meta"]["grid_cells"] == 2
        assert len(data["features"]) == 2

    def test_density_hours_param(self, client):
        """Custom hours parameter is accepted."""
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        query = mock_session.query.return_value.filter.return_value
        query.all.return_value = []

        with patch("app.api.routes.community_reports.get_db_session", return_value=mock_session):
            response = client.get(f"{self.DENSITY_URL}?hours=48")

        assert response.status_code == 200
        assert response.get_json()["meta"]["hours"] == 48

    def test_density_min_credibility_param(self, client):
        """min_credibility parameter is reflected in response meta."""
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        # The filter chain will have an extra .filter call for min_cred > 0
        query = mock_session.query.return_value.filter.return_value
        query.filter.return_value.all.return_value = []

        with patch("app.api.routes.community_reports.get_db_session", return_value=mock_session):
            response = client.get(f"{self.DENSITY_URL}?min_credibility=0.5")

        assert response.status_code == 200
        assert response.get_json()["meta"]["min_credibility"] == 0.5

    def test_density_null_coords_skipped(self, client):
        """Reports with null lat/lon are skipped (already filtered by query, but belt-and-suspenders)."""
        report_null = self._make_report()
        report_null.latitude = None
        report_null.longitude = None

        report_valid = self._make_report(latitude=14.479, longitude=121.019)

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        query = mock_session.query.return_value.filter.return_value
        query.all.return_value = [report_null, report_valid]

        with patch("app.api.routes.community_reports.get_db_session", return_value=mock_session):
            response = client.get(self.DENSITY_URL)

        data = response.get_json()
        # Only 1 valid report should produce a grid cell
        assert data["meta"]["grid_cells"] == 1
        assert data["meta"]["total_reports"] == 1

    def test_density_geojson_structure(self, client):
        """Response follows GeoJSON FeatureCollection spec."""
        reports = [self._make_report()]

        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        query = mock_session.query.return_value.filter.return_value
        query.all.return_value = reports

        with patch("app.api.routes.community_reports.get_db_session", return_value=mock_session):
            response = client.get(self.DENSITY_URL)

        data = response.get_json()
        assert data["type"] == "FeatureCollection"
        for feat in data["features"]:
            assert feat["type"] == "Feature"
            assert "geometry" in feat
            assert "properties" in feat
            assert feat["geometry"]["type"] == "Point"
            coords = feat["geometry"]["coordinates"]
            assert isinstance(coords, list)
            assert len(coords) == 2
            # GeoJSON: [longitude, latitude]
            assert 120 < coords[0] < 122  # longitude range for Parañaque
            assert 14 < coords[1] < 15  # latitude range for Parañaque

    def test_density_meta_grid_size(self, client):
        """Meta includes grid_size_degrees."""
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)
        query = mock_session.query.return_value.filter.return_value
        query.all.return_value = []

        with patch("app.api.routes.community_reports.get_db_session", return_value=mock_session):
            response = client.get(self.DENSITY_URL)

        assert response.get_json()["meta"]["grid_size_degrees"] == 0.001
