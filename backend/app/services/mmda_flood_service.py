"""
MMDA Flood Advisory Service.

Integrates with MMDA (Metropolitan Manila Development Authority) flood
monitoring systems to provide real-time flood advisories and water-level
readings for Metro Manila, specifically Parañaque City.

Data Sources:
- MMDA Flood Report API / RSS Feed
- MMDA Flood Monitoring Stations Data (Parañaque River, etc.)
- MMDA FloodWatch Twitter/X Feed (structured fallback)

MMDA maintains monitoring stations along major waterways and pumping
stations.  Their flood report system issues area-based advisories when
water levels exceed thresholds.
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
from xml.etree import ElementTree  # nosec B405 - parsing MMDA public RSS feeds

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

MMDA_API_BASE = os.getenv(
    "MMDA_API_BASE_URL",
    "https://mmdatraffic.interaksyon.com/flood-advisories",
)
MMDA_FLOODMON_URL = os.getenv(
    "MMDA_FLOODMON_URL",
    "https://mmdaflood.info/api/v1",
)
MMDA_RSS_URL = os.getenv(
    "MMDA_RSS_URL",
    "https://mmdatraffic.interaksyon.com/flood-advisories/rss.xml",
)

MMDA_CACHE_TTL = int(os.getenv("MMDA_CACHE_TTL", "300"))  # 5 min
MMDA_TIMEOUT = int(os.getenv("MMDA_TIMEOUT", "15"))

mmda_flood_breaker = CircuitBreaker(
    failure_threshold=4,
    recovery_timeout=120,
    name="mmda_flood",
)


# ---------------------------------------------------------------------------
# MMDA Flood Monitoring Stations relevant to Parañaque
# ---------------------------------------------------------------------------

PARANAQUE_FLOOD_STATIONS: Dict[str, Dict[str, Any]] = {
    "paranaque_river_sucat": {
        "name": "Parañaque River – Sucat",
        "lat": 14.4620,
        "lon": 121.0450,
        "type": "river",
        "alarm_levels": {"normal": 0.0, "alert": 12.0, "critical": 15.0, "overflow": 18.0},
        "description": "Parañaque River gauge near Sucat Road bridge",
    },
    "paranaque_river_bf": {
        "name": "Parañaque River – BF Homes",
        "lat": 14.4550,
        "lon": 121.0230,
        "type": "river",
        "alarm_levels": {"normal": 0.0, "alert": 10.0, "critical": 13.0, "overflow": 16.0},
        "description": "Parañaque River gauge near BF Homes subdivision",
    },
    "san_dionisio_pumping": {
        "name": "San Dionisio Pumping Station",
        "lat": 14.5070,
        "lon": 121.0070,
        "type": "pumping_station",
        "alarm_levels": {"normal": 0.0, "alert": 8.0, "critical": 11.0, "overflow": 14.0},
        "description": "MMDA pumping station at San Dionisio, Parañaque",
    },
    "coastal_tambo": {
        "name": "Tambo Coastal Area",
        "lat": 14.5180,
        "lon": 120.9950,
        "type": "coastal",
        "alarm_levels": {"normal": 0.0, "alert": 1.5, "critical": 2.0, "overflow": 2.5},
        "description": "Coastal water-level gauge at Tambo, near Manila Bay",
    },
}


# ---------------------------------------------------------------------------
# Enums & Data Classes
# ---------------------------------------------------------------------------


class FloodAlarmLevel(str, Enum):
    """MMDA flood alarm levels."""

    NORMAL = "normal"
    ALERT = "alert"  # Water rising above normal
    CRITICAL = "critical"  # Water near overflow / minor flooding
    OVERFLOW = "overflow"  # Spillover / major flooding
    UNKNOWN = "unknown"


@dataclass
class FloodAdvisory:
    """Parsed MMDA flood advisory."""

    advisory_id: str
    area: str
    alarm_level: FloodAlarmLevel
    water_level_m: Optional[float]
    issued_at: datetime
    description: str
    station_id: Optional[str] = None
    source: str = "mmda_flood"
    affects_paranaque: bool = False
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["alarm_level"] = self.alarm_level.value
        d["issued_at"] = self.issued_at.isoformat()
        return d


@dataclass
class FloodStationReading:
    """Real-time water-level reading from an MMDA monitoring station."""

    station_id: str
    station_name: str
    lat: float
    lon: float
    water_level_m: float
    alarm_level: FloodAlarmLevel
    timestamp: datetime
    trend: str = "stable"  # rising, falling, stable
    source: str = "mmda_floodmon"
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["alarm_level"] = self.alarm_level.value
        d["timestamp"] = self.timestamp.isoformat()
        return d


# ---------------------------------------------------------------------------
# Area matching
# ---------------------------------------------------------------------------

_PARANAQUE_PATTERNS = [
    re.compile(r"\bpara[ñn]aque\b", re.IGNORECASE),
    re.compile(r"\bsucat\b", re.IGNORECASE),
    re.compile(r"\bbf\s*homes\b", re.IGNORECASE),
    re.compile(r"\bsan\s*dionisio\b", re.IGNORECASE),
    re.compile(r"\btambo\b", re.IGNORECASE),
    re.compile(r"\bla\s*huerta\b", re.IGNORECASE),
    re.compile(r"\bdon\s*galo\b", re.IGNORECASE),
    re.compile(r"\bbaclaran\b", re.IGNORECASE),
    re.compile(r"\bsouthern\s*metro\s*manila\b", re.IGNORECASE),
]


def _advisory_affects_paranaque(text: str) -> bool:
    return any(p.search(text) for p in _PARANAQUE_PATTERNS)


def _classify_alarm(water_level: float, station_id: str) -> FloodAlarmLevel:
    """Classify alarm level based on station thresholds."""
    station = PARANAQUE_FLOOD_STATIONS.get(station_id)
    if not station:
        return FloodAlarmLevel.UNKNOWN
    thresholds = station["alarm_levels"]

    if water_level >= thresholds["overflow"]:
        return FloodAlarmLevel.OVERFLOW
    elif water_level >= thresholds["critical"]:
        return FloodAlarmLevel.CRITICAL
    elif water_level >= thresholds["alert"]:
        return FloodAlarmLevel.ALERT
    return FloodAlarmLevel.NORMAL


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class MMDAFloodService:
    """
    Service for fetching MMDA flood advisories and station data.

    Provides:
    - Active flood advisories for Parañaque
    - Real-time water-level readings from monitoring stations
    - Station status summaries
    """

    _instance: Optional["MMDAFloodService"] = None
    _init_lock = threading.Lock()

    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()
        self._enabled = os.getenv("MMDA_FLOOD_ENABLED", "True").lower() == "true"
        self._api_key = os.getenv("MMDA_API_KEY", "")
        self._headers = {
            "User-Agent": "Floodingnaque/2.0 (Thesis Flood Prediction – Parañaque City)",
            "Accept": "application/json, application/xml",
        }
        if self._api_key:
            self._headers["Authorization"] = f"Bearer {self._api_key}"

    @classmethod
    def get_instance(cls) -> "MMDAFloodService":
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
            if entry and time.time() - entry["ts"] < MMDA_CACHE_TTL:
                return entry["data"]
        return None

    def _set_cached(self, key: str, data: Any) -> None:
        with self._cache_lock:
            self._cache[key] = {"data": data, "ts": time.time()}

    # -- public API ----------------------------------------------------------

    def is_enabled(self) -> bool:
        return self._enabled

    def get_active_advisories(self, paranaque_only: bool = True) -> Dict[str, Any]:
        """
        Fetch active MMDA flood advisories.

        Args:
            paranaque_only: Filter to Parañaque-relevant advisories.

        Returns:
            Dict with status, advisories list, metadata.
        """
        if not self._enabled:
            return {"status": "disabled", "advisories": []}

        cache_key = f"advisories_{'pnq' if paranaque_only else 'all'}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            advisories = self._fetch_advisories()
            if paranaque_only:
                advisories = [a for a in advisories if a.affects_paranaque]

            result = {
                "status": "ok",
                "count": len(advisories),
                "advisories": [a.to_dict() for a in advisories],
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "mmda_flood",
            }
            self._set_cached(cache_key, result)
            return result

        except CircuitOpenError:
            return {"status": "circuit_open", "advisories": [], "message": "Service temporarily unavailable"}
        except Exception as exc:
            logger.error(f"Failed to fetch MMDA advisories: {exc}", exc_info=True)
            return {"status": "error", "advisories": [], "message": str(exc)}

    def get_station_readings(self) -> Dict[str, Any]:
        """
        Fetch current water-level readings for Parañaque monitoring stations.

        Returns:
            Dict with station readings and summary.
        """
        if not self._enabled:
            return {"status": "disabled", "stations": []}

        cached = self._get_cached("station_readings")
        if cached is not None:
            return cached

        try:
            readings = self._fetch_station_readings()

            # Compute summary
            max_level = FloodAlarmLevel.NORMAL
            level_priority = {
                FloodAlarmLevel.NORMAL: 0,
                FloodAlarmLevel.ALERT: 1,
                FloodAlarmLevel.CRITICAL: 2,
                FloodAlarmLevel.OVERFLOW: 3,
                FloodAlarmLevel.UNKNOWN: 0,
            }
            for r in readings:
                if level_priority.get(r.alarm_level, 0) > level_priority.get(max_level, 0):
                    max_level = r.alarm_level

            result = {
                "status": "ok",
                "highest_alarm": max_level.value,
                "station_count": len(readings),
                "stations": [r.to_dict() for r in readings],
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            self._set_cached("station_readings", result)
            return result

        except CircuitOpenError:
            return {"status": "circuit_open", "stations": []}
        except Exception as exc:
            logger.error(f"Failed to fetch station readings: {exc}", exc_info=True)
            return {"status": "error", "stations": [], "message": str(exc)}

    def get_combined_status(self) -> Dict[str, Any]:
        """Get combined advisories + station readings."""
        advisories = self.get_active_advisories(paranaque_only=True)
        stations = self.get_station_readings()

        return {
            "flood_advisories": advisories,
            "station_readings": stations,
            "overall_status": stations.get("highest_alarm", "unknown"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # -- internal fetchers ---------------------------------------------------

    @retry_with_backoff(max_retries=2, base_delay=2.0, exceptions=(requests.RequestException,))
    def _fetch_advisories(self) -> List[FloodAdvisory]:
        """Fetch and parse MMDA flood advisories."""
        advisories: List[FloodAdvisory] = []

        # Try JSON API first
        try:
            advisories = self._fetch_advisories_json()
            if advisories:
                return advisories
        except Exception:
            logger.debug("MMDA JSON API unavailable, falling back to RSS")

        # Fallback to RSS
        try:
            advisories = self._fetch_advisories_rss()
        except Exception as exc:
            logger.error(f"MMDA RSS fallback also failed: {exc}")

        return advisories

    def _fetch_advisories_json(self) -> List[FloodAdvisory]:
        """Try MMDA JSON API."""
        response = mmda_flood_breaker.call(
            requests.get,
            f"{MMDA_FLOODMON_URL}/advisories",
            headers=self._headers,
            timeout=MMDA_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        advisories: List[FloodAdvisory] = []
        items = data if isinstance(data, list) else data.get("data", data.get("advisories", []))

        for item in items:
            area = item.get("area", item.get("location", ""))
            description = item.get("description", item.get("message", ""))
            combined = f"{area} {description}"

            level_str = item.get("alarm_level", item.get("level", "unknown")).lower()
            try:
                alarm = FloodAlarmLevel(level_str)
            except ValueError:
                alarm = FloodAlarmLevel.UNKNOWN

            advisories.append(
                FloodAdvisory(
                    advisory_id=str(item.get("id", f"mmda-{time.time():.0f}")),
                    area=area,
                    alarm_level=alarm,
                    water_level_m=item.get("water_level"),
                    issued_at=self._parse_datetime(item.get("timestamp", item.get("issued_at", ""))),
                    description=description[:500],
                    station_id=item.get("station_id"),
                    affects_paranaque=_advisory_affects_paranaque(combined),
                    confidence=0.8,
                )
            )

        return advisories

    def _fetch_advisories_rss(self) -> List[FloodAdvisory]:
        """Fallback: parse MMDA RSS feed."""
        response = mmda_flood_breaker.call(
            requests.get,
            MMDA_RSS_URL,
            headers=self._headers,
            timeout=MMDA_TIMEOUT,
        )
        response.raise_for_status()

        advisories: List[FloodAdvisory] = []
        try:
            root = ElementTree.fromstring(response.content)  # nosec B314
            for item in root.findall(".//item"):
                title = (item.findtext("title") or "").strip()
                desc = (item.findtext("description") or "").strip()
                pub_date = (item.findtext("pubDate") or "").strip()
                combined = f"{title} {desc}"

                level = self._infer_alarm_level(combined)
                water = self._extract_water_level(combined)

                advisories.append(
                    FloodAdvisory(
                        advisory_id=item.findtext("link") or f"mmda-rss-{len(advisories)}",
                        area=title,
                        alarm_level=level,
                        water_level_m=water,
                        issued_at=self._parse_datetime(pub_date),
                        description=desc[:500],
                        affects_paranaque=_advisory_affects_paranaque(combined),
                        confidence=0.5,  # RSS = lower confidence than structured API
                    )
                )
        except ElementTree.ParseError:
            logger.error("Failed to parse MMDA RSS XML")

        return advisories

    @retry_with_backoff(max_retries=2, base_delay=2.0, exceptions=(requests.RequestException,))
    def _fetch_station_readings(self) -> List[FloodStationReading]:
        """Fetch water-level readings for Parañaque stations."""
        readings: List[FloodStationReading] = []

        # Try fetching from MMDA API for each station
        for station_id, station_info in PARANAQUE_FLOOD_STATIONS.items():
            try:
                reading = self._fetch_single_station(station_id, station_info)
                if reading:
                    readings.append(reading)
            except Exception as exc:
                logger.warning(f"Failed to fetch station {station_id}: {exc}")
                # Generate a synthetic "unknown" reading so the station still appears
                readings.append(
                    FloodStationReading(
                        station_id=station_id,
                        station_name=station_info["name"],
                        lat=station_info["lat"],
                        lon=station_info["lon"],
                        water_level_m=0.0,
                        alarm_level=FloodAlarmLevel.UNKNOWN,
                        timestamp=datetime.now(timezone.utc),
                        confidence=0.0,
                    )
                )

        return readings

    def _fetch_single_station(self, station_id: str, station_info: Dict[str, Any]) -> Optional[FloodStationReading]:
        """Fetch a single station reading from MMDA API."""
        try:
            response = mmda_flood_breaker.call(
                requests.get,
                f"{MMDA_FLOODMON_URL}/stations/{station_id}",
                headers=self._headers,
                timeout=MMDA_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

            water_level = float(data.get("water_level", data.get("level", 0)))
            alarm = _classify_alarm(water_level, station_id)

            return FloodStationReading(
                station_id=station_id,
                station_name=station_info["name"],
                lat=station_info["lat"],
                lon=station_info["lon"],
                water_level_m=water_level,
                alarm_level=alarm,
                timestamp=self._parse_datetime(data.get("timestamp", "")),
                trend=data.get("trend", "stable"),
                confidence=0.85,
            )
        except Exception as exc:
            logger.debug(f"Station API call failed for {station_id}: {exc}")
            return None

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _parse_datetime(s: str) -> datetime:
        if not s:
            return datetime.now(timezone.utc)
        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%a, %d %b %Y %H:%M:%S %z",
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

    @staticmethod
    def _infer_alarm_level(text: str) -> FloodAlarmLevel:
        t = text.lower()
        if "overflow" in t or "impassable" in t or "waist" in t or "chest" in t:
            return FloodAlarmLevel.OVERFLOW
        if "critical" in t or "knee" in t:
            return FloodAlarmLevel.CRITICAL
        if "alert" in t or "rising" in t or "ankle" in t:
            return FloodAlarmLevel.ALERT
        if "normal" in t or "passable" in t:
            return FloodAlarmLevel.NORMAL
        return FloodAlarmLevel.UNKNOWN

    @staticmethod
    def _extract_water_level(text: str) -> Optional[float]:
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:m|meters?|metre)", text, re.IGNORECASE)
        return float(match.group(1)) if match else None


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------


def get_mmda_flood_service() -> MMDAFloodService:
    """Get the singleton MMDA flood service instance."""
    return MMDAFloodService.get_instance()
