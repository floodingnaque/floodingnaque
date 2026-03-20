"""
Tests for Multi-Source Data Integration Services.

Covers:
- PAGASARainfallBulletinService
- MMDAFloodService
- ManilaBayTideService
- RiverWaterLevelService
- DataAggregationService (orchestrator, fallback, reliability scoring)
"""

import math
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from app.services.pagasa_bulletin_service import (
    PAGASARainfallBulletinService,
    RainfallAdvisoryLevel,
    RainfallBulletin,
    SevereWeatherBulletin,
    _affects_paranaque,
    _extract_rainfall_mm,
    _parse_advisory_level,
    get_pagasa_bulletin_service,
)

# ---------------------------------------------------------------------------
# PAGASA Rainfall Bulletin Service
# ---------------------------------------------------------------------------


class TestPAGASABulletinHelpers:
    """Test helper functions for PAGASA bulletin parsing."""

    def test_affects_paranaque_direct_mention(self):
        assert _affects_paranaque(["Parañaque City"], "")
        assert _affects_paranaque(["Paranaque"], "")

    def test_affects_paranaque_metro_manila(self):
        assert _affects_paranaque(["Metro Manila"], "")
        assert _affects_paranaque([], "NCR region affected")

    def test_affects_paranaque_southern_metro(self):
        assert _affects_paranaque([], "Southern Metro Manila experiencing rain")

    def test_not_affects_paranaque(self):
        assert not _affects_paranaque(["Quezon City"], "Northern Luzon")
        assert not _affects_paranaque([], "Visayas region")

    def test_parse_advisory_level_red(self):
        assert _parse_advisory_level("RED WARNING: torrential rainfall") == RainfallAdvisoryLevel.RED

    def test_parse_advisory_level_orange(self):
        assert _parse_advisory_level("ORANGE: heavy rain expected") == RainfallAdvisoryLevel.ORANGE

    def test_parse_advisory_level_yellow(self):
        assert _parse_advisory_level("Yellow advisory: moderate rain") == RainfallAdvisoryLevel.YELLOW

    def test_parse_advisory_level_unknown(self):
        assert _parse_advisory_level("weather update") == RainfallAdvisoryLevel.UNKNOWN

    def test_extract_rainfall_mm(self):
        assert _extract_rainfall_mm("30 mm accumulated") == 30.0
        assert _extract_rainfall_mm("15.5 millimeters per hour") == 15.5

    def test_extract_rainfall_mm_none(self):
        assert _extract_rainfall_mm("heavy rain today") is None


class TestRainfallBulletin:
    """Test RainfallBulletin data class."""

    def test_to_dict(self):
        b = RainfallBulletin(
            bulletin_id="test-1",
            title="Test Bulletin",
            advisory_level=RainfallAdvisoryLevel.ORANGE,
            issued_at=datetime(2026, 3, 2, 10, 0, tzinfo=timezone.utc),
            valid_until=None,
            affected_areas=["Metro Manila"],
            rainfall_mm_hr=12.5,
            description="Heavy rain",
            affects_paranaque=True,
            confidence=0.8,
        )
        d = b.to_dict()
        assert d["advisory_level"] == "orange"
        assert d["affects_paranaque"] is True
        assert d["rainfall_mm_hr"] == 12.5
        assert "2026-03-02" in d["issued_at"]


class TestPAGASABulletinService:
    """Test PAGASARainfallBulletinService singleton and public API."""

    def setup_method(self):
        PAGASARainfallBulletinService.reset_instance()

    def test_singleton(self):
        a = get_pagasa_bulletin_service()
        b = get_pagasa_bulletin_service()
        assert a is b

    def test_disabled_returns_status(self):
        with patch.dict("os.environ", {"PAGASA_BULLETIN_ENABLED": "False"}):
            PAGASARainfallBulletinService.reset_instance()
            svc = get_pagasa_bulletin_service()
            result = svc.get_active_advisories()
            assert result["status"] == "disabled"

    def test_caching(self):
        svc = get_pagasa_bulletin_service()
        svc._set_cached("advisories_pnq", {"status": "ok", "bulletins": [], "count": 0})
        result = svc.get_active_advisories(paranaque_only=True)
        assert result["status"] == "ok"

    def test_combined_status_keys(self):
        svc = get_pagasa_bulletin_service()
        # Inject cached data to avoid real HTTP calls
        svc._set_cached("advisories_pnq", {"status": "ok", "bulletins": [], "count": 0})
        svc._set_cached("severe_weather", {"status": "ok", "bulletins": [], "count": 0})
        result = svc.get_combined_status()
        assert "overall_advisory_level" in result
        assert "has_active_typhoon_signal" in result

    def test_parse_date_rfc822(self):
        dt = PAGASARainfallBulletinService._parse_date("Sun, 02 Mar 2026 10:00:00 +0800")
        assert dt is not None
        assert dt.year == 2026

    def test_parse_date_iso(self):
        dt = PAGASARainfallBulletinService._parse_date("2026-03-02T10:00:00+08:00")
        assert dt is not None

    def test_parse_date_invalid(self):
        assert PAGASARainfallBulletinService._parse_date("not a date") is None

    def test_extract_areas(self):
        areas = PAGASARainfallBulletinService._extract_areas("affecting Metro Manila, Cavite, and Laguna.")
        assert len(areas) >= 2
        assert any("Manila" in a for a in areas)


# ---------------------------------------------------------------------------
# MMDA Flood Service
# ---------------------------------------------------------------------------

from app.services.mmda_flood_service import (
    PARANAQUE_FLOOD_STATIONS,
    FloodAdvisory,
    FloodAlarmLevel,
    FloodStationReading,
    MMDAFloodService,
    _advisory_affects_paranaque,
    _classify_alarm,
    get_mmda_flood_service,
)


class TestMMDAHelpers:
    """Test MMDA helper functions."""

    def test_advisory_affects_paranaque(self):
        assert _advisory_affects_paranaque("Flooding at Sucat area")
        assert _advisory_affects_paranaque("BF Homes impassable")
        assert _advisory_affects_paranaque("Parañaque River overflowing")
        assert not _advisory_affects_paranaque("Quezon City flooding")

    def test_classify_alarm_normal(self):
        assert _classify_alarm(5.0, "paranaque_river_sucat") == FloodAlarmLevel.NORMAL

    def test_classify_alarm_alert(self):
        assert _classify_alarm(12.0, "paranaque_river_sucat") == FloodAlarmLevel.ALERT

    def test_classify_alarm_critical(self):
        assert _classify_alarm(15.5, "paranaque_river_sucat") == FloodAlarmLevel.CRITICAL

    def test_classify_alarm_overflow(self):
        assert _classify_alarm(18.0, "paranaque_river_sucat") == FloodAlarmLevel.OVERFLOW

    def test_classify_alarm_unknown_station(self):
        assert _classify_alarm(10.0, "nonexistent") == FloodAlarmLevel.UNKNOWN


class TestFloodAdvisory:
    """Test FloodAdvisory data class."""

    def test_to_dict(self):
        advisory = FloodAdvisory(
            advisory_id="adv-1",
            area="BF Homes, Parañaque",
            alarm_level=FloodAlarmLevel.CRITICAL,
            water_level_m=8.5,
            issued_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
            description="Knee-deep flooding",
            affects_paranaque=True,
            confidence=0.8,
        )
        d = advisory.to_dict()
        assert d["alarm_level"] == "critical"
        assert d["water_level_m"] == 8.5


class TestMMDAFloodService:
    """Test MMDAFloodService."""

    def setup_method(self):
        MMDAFloodService.reset_instance()

    def test_singleton(self):
        a = get_mmda_flood_service()
        b = get_mmda_flood_service()
        assert a is b

    def test_disabled(self):
        with patch.dict("os.environ", {"MMDA_FLOOD_ENABLED": "False"}):
            MMDAFloodService.reset_instance()
            svc = get_mmda_flood_service()
            assert svc.get_active_advisories()["status"] == "disabled"
            assert svc.get_station_readings()["status"] == "disabled"

    def test_cached_advisories(self):
        svc = get_mmda_flood_service()
        svc._set_cached(
            "advisories_pnq",
            {
                "status": "ok",
                "advisories": [],
                "count": 0,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "mmda_flood",
            },
        )
        result = svc.get_active_advisories(paranaque_only=True)
        assert result["status"] == "ok"

    def test_combined_status(self):
        svc = get_mmda_flood_service()
        svc._set_cached("advisories_pnq", {"status": "ok", "advisories": [], "count": 0})
        svc._set_cached(
            "station_readings",
            {
                "status": "ok",
                "stations": [],
                "highest_alarm": "normal",
            },
        )
        result = svc.get_combined_status()
        assert "flood_advisories" in result
        assert "station_readings" in result

    def test_infer_alarm_level(self):
        assert MMDAFloodService._infer_alarm_level("knee deep flooding") == FloodAlarmLevel.CRITICAL
        assert MMDAFloodService._infer_alarm_level("impassable road") == FloodAlarmLevel.OVERFLOW
        assert MMDAFloodService._infer_alarm_level("road passable") == FloodAlarmLevel.NORMAL

    def test_extract_water_level(self):
        assert MMDAFloodService._extract_water_level("1.5 meters deep") == 1.5
        assert MMDAFloodService._extract_water_level("no level") is None


# ---------------------------------------------------------------------------
# Manila Bay Tide Service
# ---------------------------------------------------------------------------

from app.services.manila_bay_tide_service import (
    MSL_MANILA_BAY,
    ManilaBayTide,
    ManilaBayTideService,
    TideInfluence,
    _compute_astronomical_tide,
    _compute_tide_series,
    _find_extremes,
    get_manila_bay_tide_service,
)


class TestAstronomicalTide:
    """Test harmonic tide computation."""

    def test_tide_height_range(self):
        """Astronomical tide should be within a reasonable range."""
        now = datetime(2026, 3, 2, 12, 0, tzinfo=timezone.utc)
        height = _compute_astronomical_tide(now)
        # Manila Bay tides: roughly 0-1.5 m above chart datum
        assert -0.5 < height < 2.0

    def test_tide_varies_over_time(self):
        """Tide should change over a 6-hour period."""
        t1 = datetime(2026, 3, 2, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 3, 2, 6, 0, tzinfo=timezone.utc)
        h1 = _compute_astronomical_tide(t1)
        h2 = _compute_astronomical_tide(t2)
        assert h1 != h2

    def test_tide_series_length(self):
        now = datetime(2026, 3, 2, tzinfo=timezone.utc)
        series = _compute_tide_series(now, hours=24, step_minutes=15)
        # 24 * 60 / 15 = 96 points
        assert len(series) == 96

    def test_find_extremes_has_highs_and_lows(self):
        now = datetime(2026, 3, 2, tzinfo=timezone.utc)
        extremes = _find_extremes(now, hours=48)
        # Semi-diurnal tide → ~2 high and ~2 low per day → ~4 each in 48 hours
        assert len(extremes["highs"]) >= 2
        assert len(extremes["lows"]) >= 2


class TestManilaBayTide:
    """Test ManilaBayTide data class."""

    def test_to_dict(self):
        t = ManilaBayTide(
            height_m=0.85,
            height_above_msl_m=0.20,
            timestamp=datetime(2026, 3, 2, tzinfo=timezone.utc),
            confidence=0.7,
        )
        d = t.to_dict()
        assert d["height_m"] == 0.85
        assert "2026-03-02" in d["timestamp"]


class TestTideInfluence:
    """Test TideInfluence data class."""

    def test_to_dict(self):
        inf = TideInfluence(
            current_height_m=0.9,
            tide_phase="rising",
            drainage_reduction_pct=30.0,
            flood_risk_multiplier=1.3,
            next_high_tide=datetime(2026, 3, 2, 14, 0, tzinfo=timezone.utc),
            next_low_tide=datetime(2026, 3, 2, 20, 0, tzinfo=timezone.utc),
            is_king_tide=False,
            storm_surge_m=0.0,
            confidence=0.7,
        )
        d = inf.to_dict()
        assert d["tide_phase"] == "rising"
        assert d["drainage_reduction_pct"] == 30.0


class TestManilaBayTideService:
    """Test ManilaBayTideService."""

    def setup_method(self):
        ManilaBayTideService.reset_instance()

    def test_singleton(self):
        a = get_manila_bay_tide_service()
        b = get_manila_bay_tide_service()
        assert a is b

    def test_disabled(self):
        with patch.dict("os.environ", {"MANILA_TIDE_ENABLED": "False"}):
            ManilaBayTideService.reset_instance()
            svc = get_manila_bay_tide_service()
            assert svc.get_current_tide()["status"] == "disabled"

    def test_get_current_tide_harmonic_fallback(self):
        """When WorldTides/NAMRIA unavailable, should still return data."""
        svc = get_manila_bay_tide_service()
        svc._worldtides_available = False
        svc._namria_available = False
        result = svc.get_current_tide()
        assert result["status"] == "ok"
        assert "current" in result
        assert result["source"] == "harmonic_prediction"
        assert result["confidence"] >= 0.5

    def test_get_tide_forecast(self):
        svc = get_manila_bay_tide_service()
        result = svc.get_tide_forecast(hours=12)
        assert result["status"] == "ok"
        assert result["forecast_hours"] == 12
        assert len(result["series"]) > 0

    def test_get_tide_influence(self):
        svc = get_manila_bay_tide_service()
        result = svc.get_tide_influence(storm_surge_m=0.0)
        assert result["status"] == "ok"
        assert "influence" in result
        inf = result["influence"]
        assert 0 <= inf["drainage_reduction_pct"] <= 100
        assert inf["flood_risk_multiplier"] >= 1.0

    def test_tide_influence_with_storm_surge(self):
        svc = get_manila_bay_tide_service()
        result = svc.get_tide_influence(storm_surge_m=1.5)
        inf = result["influence"]
        assert inf["storm_surge_m"] == 1.5
        assert inf["flood_risk_multiplier"] > 1.5  # Storm surge increases risk


# ---------------------------------------------------------------------------
# River Water-Level Service
# ---------------------------------------------------------------------------

from app.services.river_water_level_service import (
    RIVER_STATIONS,
    RiverAlarmLevel,
    RiverReading,
    RiverSystemStatus,
    RiverWaterLevelService,
    _classify_river_alarm,
    _compute_flood_risk_score,
    get_river_water_level_service,
)


class TestRiverHelpers:
    """Test river service helper functions."""

    def test_classify_normal(self):
        info = RIVER_STATIONS["paranaque_river_upstream"]
        assert _classify_river_alarm(2.0, info) == RiverAlarmLevel.NORMAL

    def test_classify_alert(self):
        info = RIVER_STATIONS["paranaque_river_upstream"]
        assert _classify_river_alarm(7.0, info) == RiverAlarmLevel.ALERT

    def test_classify_critical(self):
        info = RIVER_STATIONS["paranaque_river_upstream"]
        assert _classify_river_alarm(10.0, info) == RiverAlarmLevel.CRITICAL

    def test_classify_overflow(self):
        info = RIVER_STATIONS["paranaque_river_upstream"]
        assert _classify_river_alarm(13.0, info) == RiverAlarmLevel.OVERFLOW

    def test_flood_risk_score_empty(self):
        assert _compute_flood_risk_score([]) == 0.0

    def test_flood_risk_score_normal(self):
        readings = [
            RiverReading(
                station_id="paranaque_river_upstream",
                station_name="Test",
                river="Parañaque River",
                lat=14.0,
                lon=121.0,
                water_level_m=2.5,  # normal
                alarm_level=RiverAlarmLevel.NORMAL,
                flow_rate_cms=None,
                trend="stable",
                timestamp=datetime.now(timezone.utc),
            ),
        ]
        score = _compute_flood_risk_score(readings)
        assert 0.0 <= score <= 0.2

    def test_flood_risk_score_overflow(self):
        readings = [
            RiverReading(
                station_id="paranaque_river_upstream",
                station_name="Test",
                river="Parañaque River",
                lat=14.0,
                lon=121.0,
                water_level_m=12.5,  # near overflow
                alarm_level=RiverAlarmLevel.OVERFLOW,
                flow_rate_cms=None,
                trend="rising",
                timestamp=datetime.now(timezone.utc),
            ),
        ]
        score = _compute_flood_risk_score(readings)
        assert score >= 0.8


class TestRiverReading:
    """Test RiverReading data class."""

    def test_to_dict(self):
        r = RiverReading(
            station_id="test",
            station_name="Test Station",
            river="Test River",
            lat=14.0,
            lon=121.0,
            water_level_m=5.0,
            alarm_level=RiverAlarmLevel.ALERT,
            flow_rate_cms=2.5,
            trend="rising",
            timestamp=datetime(2026, 3, 2, tzinfo=timezone.utc),
        )
        d = r.to_dict()
        assert d["alarm_level"] == "alert"
        assert d["trend"] == "rising"


class TestRiverWaterLevelService:
    """Test RiverWaterLevelService."""

    def setup_method(self):
        RiverWaterLevelService.reset_instance()

    def test_singleton(self):
        a = get_river_water_level_service()
        b = get_river_water_level_service()
        assert a is b

    def test_disabled(self):
        with patch.dict("os.environ", {"RIVER_MONITORING_ENABLED": "False"}):
            RiverWaterLevelService.reset_instance()
            svc = get_river_water_level_service()
            assert svc.get_all_readings()["status"] == "disabled"

    def test_station_not_found(self):
        svc = get_river_water_level_service()
        result = svc.get_station_reading("nonexistent_station")
        assert result["status"] == "not_found"

    def test_known_stations(self):
        """Verify all configured stations are present."""
        assert len(RIVER_STATIONS) == 5
        assert "paranaque_river_upstream" in RIVER_STATIONS
        assert "paranaque_river_downstream" in RIVER_STATIONS
        assert "bf_drainage_channel" in RIVER_STATIONS


# ---------------------------------------------------------------------------
# Data Aggregation Service
# ---------------------------------------------------------------------------

from app.services.data_aggregation_service import (
    AggregatedData,
    DataAggregationService,
    FallbackChain,
    SourceQuality,
    SourceResult,
    compute_global_reliability,
    compute_source_confidence,
    cross_check_consistency,
    get_aggregation_service,
)


class TestSourceConfidence:
    """Test confidence scoring."""

    def test_authoritative_fresh(self):
        score = compute_source_confidence(SourceQuality.AUTHORITATIVE, 0)
        assert score == 1.0

    def test_authoritative_stale(self):
        score = compute_source_confidence(SourceQuality.AUTHORITATIVE, 900)
        assert score == 0.5  # Half due to max staleness

    def test_fallback_quality(self):
        score = compute_source_confidence(SourceQuality.FALLBACK, 0)
        assert score == 0.4

    def test_unavailable(self):
        score = compute_source_confidence(SourceQuality.UNAVAILABLE, 0)
        assert score == 0.0

    def test_consistency_reduces_score(self):
        score = compute_source_confidence(SourceQuality.PRIMARY, 0, consistency_score=0.5)
        assert score < 0.85  # Full primary = 0.85, halved by consistency

    def test_intermediate_freshness(self):
        score = compute_source_confidence(SourceQuality.PRIMARY, 450)
        # 450s out of 900s max → 50% age → freshness = 0.75
        assert 0.5 < score < 0.85


class TestGlobalReliability:
    """Test global reliability scoring."""

    def test_empty(self):
        assert compute_global_reliability([]) == 0.0

    def test_all_authoritative(self):
        results = [
            SourceResult("src1", "rainfall", SourceQuality.AUTHORITATIVE, {}, 1.0, 0, 10),
            SourceResult("src2", "tide", SourceQuality.AUTHORITATIVE, {}, 1.0, 0, 10),
            SourceResult("src3", "river", SourceQuality.AUTHORITATIVE, {}, 1.0, 0, 10),
        ]
        score = compute_global_reliability(results)
        assert score >= 0.9

    def test_mixed_quality(self):
        results = [
            SourceResult("src1", "rainfall", SourceQuality.AUTHORITATIVE, {}, 1.0, 0, 10),
            SourceResult("src2", "tide", SourceQuality.UNAVAILABLE, None, 0.0, 0, 0),
        ]
        score = compute_global_reliability(results)
        assert 0.3 < score < 0.8

    def test_multi_source_bonus(self):
        """Having more sources should slightly boost reliability."""
        few = [
            SourceResult("src1", "rainfall", SourceQuality.PRIMARY, {}, 0.85, 0, 10),
        ]
        many = [
            SourceResult("src1", "rainfall", SourceQuality.PRIMARY, {}, 0.85, 0, 10),
            SourceResult("src2", "tide", SourceQuality.PRIMARY, {}, 0.85, 0, 10),
            SourceResult("src3", "river", SourceQuality.PRIMARY, {}, 0.85, 0, 10),
            SourceResult("src4", "flood_advisory", SourceQuality.PRIMARY, {}, 0.85, 0, 10),
        ]
        s_few = compute_global_reliability(few)
        s_many = compute_global_reliability(many)
        assert s_many > s_few


class TestCrossCheckConsistency:
    """Test cross-source consistency checking."""

    def test_consistent_data(self):
        score = cross_check_consistency(25.0, "red", "critical")
        assert score == 1.0

    def test_inconsistent_rain_vs_advisory(self):
        score = cross_check_consistency(25.0, "normal", "normal")
        assert score < 1.0

    def test_inconsistent_low_rain_high_advisory(self):
        score = cross_check_consistency(1.0, "red", "normal")
        assert score < 1.0

    def test_no_data(self):
        score = cross_check_consistency(None, None, None)
        assert score == 1.0


class TestFallbackChain:
    """Test FallbackChain execution."""

    def test_first_source_succeeds(self):
        chain = FallbackChain(
            "rainfall",
            [
                ("primary", SourceQuality.AUTHORITATIVE, lambda: {"status": "ok", "value": 42}),
                ("fallback", SourceQuality.SECONDARY, lambda: {"status": "ok", "value": 99}),
            ],
        )
        result = chain.execute()
        assert result.source_name == "primary"
        assert result.quality == SourceQuality.AUTHORITATIVE
        assert not result.is_fallback

    def test_fallback_on_first_failure(self):
        def fail():
            raise RuntimeError("boom")

        chain = FallbackChain(
            "rainfall",
            [
                ("primary", SourceQuality.AUTHORITATIVE, fail),
                ("fallback", SourceQuality.SECONDARY, lambda: {"status": "ok"}),
            ],
        )
        result = chain.execute()
        assert result.source_name == "fallback"
        assert result.is_fallback

    def test_all_sources_fail(self):
        def fail():
            raise RuntimeError("boom")

        chain = FallbackChain(
            "rainfall",
            [
                ("src1", SourceQuality.AUTHORITATIVE, fail),
                ("src2", SourceQuality.SECONDARY, fail),
            ],
        )
        result = chain.execute()
        assert result.quality == SourceQuality.UNAVAILABLE
        assert result.error is not None
        assert result.data is None

    def test_disabled_source_skipped(self):
        chain = FallbackChain(
            "tide",
            [
                ("disabled_src", SourceQuality.PRIMARY, lambda: {"status": "disabled"}),
                ("working_src", SourceQuality.SECONDARY, lambda: {"status": "ok"}),
            ],
        )
        result = chain.execute()
        assert result.source_name == "working_src"

    def test_error_status_skipped(self):
        chain = FallbackChain(
            "river",
            [
                ("error_src", SourceQuality.PRIMARY, lambda: {"status": "error", "message": "fail"}),
                ("ok_src", SourceQuality.SECONDARY, lambda: {"status": "ok"}),
            ],
        )
        result = chain.execute()
        assert result.source_name == "ok_src"


class TestDataAggregationService:
    """Test DataAggregationService."""

    def setup_method(self):
        DataAggregationService.reset_instance()

    def test_singleton(self):
        a = get_aggregation_service()
        b = get_aggregation_service()
        assert a is b

    def test_disabled(self):
        with patch.dict("os.environ", {"DATA_AGGREGATION_ENABLED": "False"}):
            DataAggregationService.reset_instance()
            svc = get_aggregation_service()
            assert svc.get_aggregated_data()["status"] == "disabled"

    def test_source_health_structure(self):
        svc = get_aggregation_service()
        health = svc.get_source_health()
        assert "overall" in health
        assert "sources" in health
        assert "healthy_count" in health
        assert health["overall"] in ("healthy", "degraded")

    def test_get_category_invalid(self):
        svc = get_aggregation_service()
        result = svc.get_category_data("nonexistent")
        assert "error" in result

    def test_aggregated_data_structure(self):
        """Aggregated data should have the expected envelope fields."""
        svc = get_aggregation_service()
        # Inject cache to avoid real HTTP calls
        svc._set_cached(
            "aggregated",
            {
                "sources": {},
                "reliability_score": 0.5,
                "source_count": 0,
                "sources_available": 0,
                "sources_failed": 0,
                "fetch_latency_ms": 10,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "warnings": [],
            },
        )
        result = svc.get_aggregated_data()
        assert "reliability_score" in result
        assert "sources" in result
        assert "timestamp" in result


class TestSourceResult:
    """Test SourceResult data class."""

    def test_to_dict(self):
        r = SourceResult(
            source_name="test",
            category="rainfall",
            quality=SourceQuality.PRIMARY,
            data={"value": 10},
            confidence=0.85,
            freshness_seconds=30.0,
            latency_ms=50.0,
        )
        d = r.to_dict()
        assert d["quality"] == "primary"
        assert d["confidence"] == 0.85


class TestAggregatedData:
    """Test AggregatedData data class."""

    def test_to_dict(self):
        a = AggregatedData(
            sources={"rainfall": {}},
            reliability_score=0.75,
            source_count=3,
            sources_available=2,
            sources_failed=1,
            fetch_latency_ms=120.5,
            timestamp="2026-03-02T12:00:00+00:00",
            warnings=["FALLBACK_USED: tide"],
        )
        d = a.to_dict()
        assert d["reliability_score"] == 0.75
        assert d["sources_failed"] == 1
        assert len(d["warnings"]) == 1
