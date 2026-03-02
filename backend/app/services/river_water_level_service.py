"""
River Water-Level Service.

Fetches water-level data for rivers and waterways relevant to Parañaque City
flood prediction.  Primary focus on the Parañaque River and connecting
tributaries/channels.

Data Sources:
- DPWH (Department of Public Works and Highways) river monitoring
- EFCOS (Effective Flood Control and Operation System) — managed by DPWH
- MMDA flood monitoring stations (complementary)
- PAGASA hydrometric stations

River System Context (Parañaque):
- Parañaque River (~8 km length) drains most of Parañaque City
- Tributaries: San Dionisio Creek, BF Homes drainage channels
- Outflow: Manila Bay (tide-influenced)
- Critical points: Sucat Bridge, BF Homes Bridge, La Huerta outfall
"""

import logging
import os
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import requests
from app.core.constants import DEFAULT_LATITUDE, DEFAULT_LONGITUDE
from app.utils.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    retry_with_backoff,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

EFCOS_API_URL = os.getenv(
    "EFCOS_API_URL",
    "https://efcos.dpwh.gov.ph/api/v1",
)
DPWH_HYDRO_URL = os.getenv(
    "DPWH_HYDRO_URL",
    "https://hydro.dpwh.gov.ph/api",
)

RIVER_CACHE_TTL = int(os.getenv("RIVER_CACHE_TTL", "300"))   # 5 min
RIVER_TIMEOUT = int(os.getenv("RIVER_TIMEOUT", "15"))

river_level_breaker = CircuitBreaker(
    failure_threshold=4,
    recovery_timeout=120,
    name="river_water_level",
)

# ---------------------------------------------------------------------------
# Parañaque River Monitoring Stations
# ---------------------------------------------------------------------------

RIVER_STATIONS: Dict[str, Dict[str, Any]] = {
    "paranaque_river_upstream": {
        "name": "Parañaque River – Upstream (Sucat)",
        "lat": 14.4630,
        "lon": 121.0460,
        "river": "Parañaque River",
        "type": "upstream",
        "normal_level_m": 2.5,
        "alert_level_m": 6.0,
        "critical_level_m": 9.0,
        "overflow_level_m": 12.0,
        "description": "Upstream gauge near Sucat Road, Parañaque River",
    },
    "paranaque_river_midstream": {
        "name": "Parañaque River – Midstream (BF Homes)",
        "lat": 14.4560,
        "lon": 121.0240,
        "river": "Parañaque River",
        "type": "midstream",
        "normal_level_m": 2.0,
        "alert_level_m": 5.0,
        "critical_level_m": 8.0,
        "overflow_level_m": 10.0,
        "description": "Midstream gauge near BF Homes, Parañaque River",
    },
    "paranaque_river_downstream": {
        "name": "Parañaque River – Downstream (La Huerta)",
        "lat": 14.4890,
        "lon": 120.9880,
        "river": "Parañaque River",
        "type": "downstream",
        "normal_level_m": 1.5,
        "alert_level_m": 4.0,
        "critical_level_m": 6.0,
        "overflow_level_m": 8.0,
        "description": "Downstream gauge near La Huerta / Manila Bay outfall",
    },
    "san_dionisio_creek": {
        "name": "San Dionisio Creek",
        "lat": 14.5060,
        "lon": 121.0060,
        "river": "San Dionisio Creek",
        "type": "tributary",
        "normal_level_m": 0.8,
        "alert_level_m": 2.0,
        "critical_level_m": 3.0,
        "overflow_level_m": 4.0,
        "description": "Tributary creek at San Dionisio barangay",
    },
    "bf_drainage_channel": {
        "name": "BF Homes Drainage Channel",
        "lat": 14.4540,
        "lon": 121.0200,
        "river": "BF Drainage",
        "type": "channel",
        "normal_level_m": 0.5,
        "alert_level_m": 1.5,
        "critical_level_m": 2.5,
        "overflow_level_m": 3.5,
        "description": "Main drainage channel serving BF Homes subdivision",
    },
}


# ---------------------------------------------------------------------------
# Enums & Data Classes
# ---------------------------------------------------------------------------


class RiverAlarmLevel(str, Enum):
    NORMAL = "normal"
    ALERT = "alert"
    CRITICAL = "critical"
    OVERFLOW = "overflow"
    UNKNOWN = "unknown"


@dataclass
class RiverReading:
    """Single water-level reading from a river station."""
    station_id: str
    station_name: str
    river: str
    lat: float
    lon: float
    water_level_m: float
    alarm_level: RiverAlarmLevel
    flow_rate_cms: Optional[float]  # cubic metres per second
    trend: str  # rising, falling, stable
    timestamp: datetime
    source: str = "river_monitoring"
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["alarm_level"] = self.alarm_level.value
        d["timestamp"] = self.timestamp.isoformat()
        return d


@dataclass
class RiverSystemStatus:
    """Aggregated status for an entire river system."""
    river_name: str
    overall_alarm: RiverAlarmLevel
    station_count: int
    highest_level_m: float
    average_level_m: float
    stations_at_alert: int
    stations_at_critical: int
    stations_at_overflow: int
    flood_risk_score: float  # 0-1
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["overall_alarm"] = self.overall_alarm.value
        d["timestamp"] = self.timestamp.isoformat()
        return d


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _classify_river_alarm(
    water_level: float, station_info: Dict[str, Any]
) -> RiverAlarmLevel:
    """Classify alarm level based on station thresholds."""
    if water_level >= station_info["overflow_level_m"]:
        return RiverAlarmLevel.OVERFLOW
    if water_level >= station_info["critical_level_m"]:
        return RiverAlarmLevel.CRITICAL
    if water_level >= station_info["alert_level_m"]:
        return RiverAlarmLevel.ALERT
    return RiverAlarmLevel.NORMAL


def _compute_flood_risk_score(readings: List[RiverReading]) -> float:
    """
    Compute a 0–1 flood risk score from river readings.

    Factors:
    - Proportion of stations at alert/critical/overflow
    - Average water level normalised against thresholds
    - Rising trend bonus
    """
    if not readings:
        return 0.0

    scores: List[float] = []
    for r in readings:
        station = RIVER_STATIONS.get(r.station_id, {})
        if not station:
            continue

        overflow = station.get("overflow_level_m", 10)
        normal = station.get("normal_level_m", 1)
        level_range = overflow - normal
        if level_range <= 0:
            continue

        normalised = max(0.0, (r.water_level_m - normal) / level_range)
        normalised = min(normalised, 1.0)

        # Boost for rising trend
        if r.trend == "rising":
            normalised = min(normalised + 0.1, 1.0)

        scores.append(normalised)

    return round(sum(scores) / len(scores), 3) if scores else 0.0


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class RiverWaterLevelService:
    """
    Service for fetching and monitoring river water levels in Parañaque.

    Data source priority:
    1. EFCOS (DPWH) real-time telemetry
    2. DPWH hydrometric API
    3. MMDA station data (cross-referenced)
    """

    _instance: Optional["RiverWaterLevelService"] = None
    _init_lock = threading.Lock()

    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()
        self._enabled = os.getenv("RIVER_MONITORING_ENABLED", "True").lower() == "true"
        self._api_key = os.getenv("EFCOS_API_KEY", "")
        self._headers = {
            "User-Agent": "Floodingnaque/2.0 (Thesis Flood Prediction – Parañaque City)",
            "Accept": "application/json",
        }
        if self._api_key:
            self._headers["Authorization"] = f"Bearer {self._api_key}"

    @classmethod
    def get_instance(cls) -> "RiverWaterLevelService":
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    # -- cache ---------------------------------------------------------------

    def _get_cached(self, key: str) -> Optional[Any]:
        with self._cache_lock:
            entry = self._cache.get(key)
            if entry and time.time() - entry["ts"] < RIVER_CACHE_TTL:
                return entry["data"]
        return None

    def _set_cached(self, key: str, data: Any) -> None:
        with self._cache_lock:
            self._cache[key] = {"data": data, "ts": time.time()}

    # -- public API ----------------------------------------------------------

    def is_enabled(self) -> bool:
        return self._enabled

    def get_all_readings(self) -> Dict[str, Any]:
        """
        Fetch latest water-level readings for all Parañaque river stations.

        Returns:
            Dict with readings, summary, and risk score.
        """
        if not self._enabled:
            return {"status": "disabled", "readings": []}

        cached = self._get_cached("all_readings")
        if cached is not None:
            return cached

        try:
            readings = self._fetch_all_stations()
            risk_score = _compute_flood_risk_score(readings)

            # Determine overall alarm
            alarm_priority = {
                RiverAlarmLevel.NORMAL: 0,
                RiverAlarmLevel.ALERT: 1,
                RiverAlarmLevel.CRITICAL: 2,
                RiverAlarmLevel.OVERFLOW: 3,
                RiverAlarmLevel.UNKNOWN: 0,
            }
            max_alarm = RiverAlarmLevel.NORMAL
            for r in readings:
                if alarm_priority.get(r.alarm_level, 0) > alarm_priority.get(max_alarm, 0):
                    max_alarm = r.alarm_level

            result = {
                "status": "ok",
                "overall_alarm": max_alarm.value,
                "flood_risk_score": risk_score,
                "station_count": len(readings),
                "readings": [r.to_dict() for r in readings],
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            self._set_cached("all_readings", result)
            return result

        except CircuitOpenError:
            return {"status": "circuit_open", "readings": []}
        except Exception as exc:
            logger.error(f"Failed to fetch river readings: {exc}", exc_info=True)
            return {"status": "error", "readings": [], "message": str(exc)}

    def get_station_reading(self, station_id: str) -> Dict[str, Any]:
        """Get reading for a specific station."""
        if station_id not in RIVER_STATIONS:
            return {"status": "not_found", "message": f"Unknown station: {station_id}"}

        all_data = self.get_all_readings()
        if all_data["status"] != "ok":
            return all_data

        for r in all_data["readings"]:
            if r["station_id"] == station_id:
                return {"status": "ok", "reading": r}

        return {"status": "not_found"}

    def get_river_system_status(self) -> Dict[str, Any]:
        """
        Get aggregated status per river system.

        Groups stations by river and computes per-river summaries.
        """
        if not self._enabled:
            return {"status": "disabled", "rivers": []}

        all_data = self.get_all_readings()
        if all_data["status"] != "ok":
            return all_data

        # Parse readings back into objects for grouping
        rivers: Dict[str, List[Dict[str, Any]]] = {}
        for r in all_data["readings"]:
            river = r.get("river", "unknown")
            rivers.setdefault(river, []).append(r)

        now = datetime.now(timezone.utc)
        summaries: List[Dict[str, Any]] = []

        for river_name, stations in rivers.items():
            levels = [s["water_level_m"] for s in stations]
            alarms = [s["alarm_level"] for s in stations]

            priority_map = {"normal": 0, "alert": 1, "critical": 2, "overflow": 3, "unknown": 0}
            max_alarm_str = max(alarms, key=lambda a: priority_map.get(a, 0))
            try:
                overall = RiverAlarmLevel(max_alarm_str)
            except ValueError:
                overall = RiverAlarmLevel.UNKNOWN

            summaries.append(RiverSystemStatus(
                river_name=river_name,
                overall_alarm=overall,
                station_count=len(stations),
                highest_level_m=max(levels) if levels else 0,
                average_level_m=round(sum(levels) / len(levels), 2) if levels else 0,
                stations_at_alert=sum(1 for a in alarms if a == "alert"),
                stations_at_critical=sum(1 for a in alarms if a == "critical"),
                stations_at_overflow=sum(1 for a in alarms if a == "overflow"),
                flood_risk_score=all_data.get("flood_risk_score", 0),
                timestamp=now,
            ).to_dict())

        return {
            "status": "ok",
            "river_systems": summaries,
            "timestamp": now.isoformat(),
        }

    def get_historical_readings(
        self, station_id: str, hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get historical water-level readings for a station.

        Args:
            station_id: Station identifier.
            hours: Number of hours of history to fetch.
        """
        if station_id not in RIVER_STATIONS:
            return {"status": "not_found", "message": f"Unknown station: {station_id}"}

        cache_key = f"history_{station_id}_{hours}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            history = self._fetch_station_history(station_id, hours)
            result = {
                "status": "ok",
                "station_id": station_id,
                "station_name": RIVER_STATIONS[station_id]["name"],
                "hours": hours,
                "readings": history,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            self._set_cached(cache_key, result)
            return result
        except Exception as exc:
            logger.error(f"Failed to fetch history for {station_id}: {exc}")
            return {"status": "error", "readings": [], "message": str(exc)}

    # -- internal fetchers ---------------------------------------------------

    def _fetch_all_stations(self) -> List[RiverReading]:
        """Fetch readings for all monitored stations."""
        readings: List[RiverReading] = []

        for station_id, info in RIVER_STATIONS.items():
            reading = self._fetch_single_station(station_id, info)
            readings.append(reading)

        return readings

    def _fetch_single_station(
        self, station_id: str, info: Dict[str, Any]
    ) -> RiverReading:
        """
        Fetch a reading for a single station.

        Tries EFCOS → DPWH → synthetic fallback.
        """
        # Try EFCOS first
        try:
            return self._fetch_efcos_station(station_id, info)
        except Exception:
            pass

        # Try DPWH hydro
        try:
            return self._fetch_dpwh_station(station_id, info)
        except Exception:
            pass

        # Synthetic fallback (station exists but data is unavailable)
        logger.warning(f"No data source available for station {station_id}, returning unknown")
        return RiverReading(
            station_id=station_id,
            station_name=info["name"],
            river=info["river"],
            lat=info["lat"],
            lon=info["lon"],
            water_level_m=info["normal_level_m"],
            alarm_level=RiverAlarmLevel.UNKNOWN,
            flow_rate_cms=None,
            trend="stable",
            timestamp=datetime.now(timezone.utc),
            source="fallback",
            confidence=0.0,
        )

    def _fetch_efcos_station(
        self, station_id: str, info: Dict[str, Any]
    ) -> RiverReading:
        """Fetch from EFCOS (DPWH) telemetry."""
        response = river_level_breaker.call(
            requests.get,
            f"{EFCOS_API_URL}/stations/{station_id}/latest",
            headers=self._headers,
            timeout=RIVER_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        level = float(data.get("water_level", data.get("level", 0)))
        alarm = _classify_river_alarm(level, info)

        return RiverReading(
            station_id=station_id,
            station_name=info["name"],
            river=info["river"],
            lat=info["lat"],
            lon=info["lon"],
            water_level_m=level,
            alarm_level=alarm,
            flow_rate_cms=data.get("flow_rate"),
            trend=data.get("trend", "stable"),
            timestamp=self._parse_ts(data.get("timestamp", "")),
            source="efcos",
            confidence=0.90,
        )

    def _fetch_dpwh_station(
        self, station_id: str, info: Dict[str, Any]
    ) -> RiverReading:
        """Fallback: DPWH hydrometric API."""
        response = river_level_breaker.call(
            requests.get,
            f"{DPWH_HYDRO_URL}/readings",
            params={"station": station_id, "lat": info["lat"], "lon": info["lon"]},
            headers=self._headers,
            timeout=RIVER_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        level = float(data.get("water_level", 0))
        alarm = _classify_river_alarm(level, info)

        return RiverReading(
            station_id=station_id,
            station_name=info["name"],
            river=info["river"],
            lat=info["lat"],
            lon=info["lon"],
            water_level_m=level,
            alarm_level=alarm,
            flow_rate_cms=data.get("discharge"),
            trend=data.get("trend", "stable"),
            timestamp=self._parse_ts(data.get("timestamp", "")),
            source="dpwh_hydro",
            confidence=0.80,
        )

    def _fetch_station_history(
        self, station_id: str, hours: int
    ) -> List[Dict[str, Any]]:
        """Fetch historical readings for a station."""
        try:
            now = datetime.now(timezone.utc)
            start = now - timedelta(hours=hours)

            response = river_level_breaker.call(
                requests.get,
                f"{EFCOS_API_URL}/stations/{station_id}/history",
                params={
                    "start": start.isoformat(),
                    "end": now.isoformat(),
                },
                headers=self._headers,
                timeout=RIVER_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

            readings = data if isinstance(data, list) else data.get("readings", [])
            return [
                {
                    "water_level_m": float(r.get("water_level", r.get("level", 0))),
                    "timestamp": r.get("timestamp", ""),
                    "trend": r.get("trend", "stable"),
                }
                for r in readings
            ]
        except Exception as exc:
            logger.warning(f"History fetch failed for {station_id}: {exc}")
            return []

    @staticmethod
    def _parse_ts(s: str) -> datetime:
        if not s:
            return datetime.now(timezone.utc)
        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y %I:%M %p",
        ):
            try:
                dt = datetime.strptime(s.strip(), fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
                return dt
            except ValueError:
                continue
        return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------


def get_river_water_level_service() -> RiverWaterLevelService:
    """Get the singleton river water-level service instance."""
    return RiverWaterLevelService.get_instance()
