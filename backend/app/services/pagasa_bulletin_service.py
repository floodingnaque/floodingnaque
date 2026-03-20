"""
PAGASA Rainfall Bulletin Service.

Fetches and parses PAGASA rainfall bulletins (advisories) for Metro Manila,
focusing on Parañaque City and nearby areas.  This complements the radar
service by providing official advisory-level data.

Data Sources:
- PAGASA Rainfall Advisory RSS Feed
- PAGASA Severe Weather Bulletin API
- PAGASA AWS (Automated Weather Stations) hourly summaries

The service normalises advisory text into structured records and maps
affected areas to Parañaque barangays.
"""

import logging
import os
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree  # nosec B405 - parsing PAGASA public RSS feeds

import requests
from app.core.constants import (
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
    STUDY_AREA_BOUNDS,
)
from app.utils.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    retry_with_backoff,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PAGASA_BULLETIN_BASE = os.getenv(
    "PAGASA_BULLETIN_BASE_URL",
    "https://pubfiles.pagasa.dost.gov.ph",
)
PAGASA_BULLETIN_RSS = os.getenv(
    "PAGASA_BULLETIN_RSS_URL",
    f"{PAGASA_BULLETIN_BASE}/pagasaweb/files/rainfall_advisory.xml",
)
PAGASA_SEVERE_WEATHER_URL = os.getenv(
    "PAGASA_SEVERE_WEATHER_URL",
    f"{PAGASA_BULLETIN_BASE}/pagasaweb/files/severe_weather.xml",
)

BULLETIN_CACHE_TTL = int(os.getenv("PAGASA_BULLETIN_CACHE_TTL", "600"))  # 10 min
BULLETIN_CONNECT_TIMEOUT = int(os.getenv("PAGASA_BULLETIN_CONNECT_TIMEOUT", "5"))
BULLETIN_READ_TIMEOUT = int(os.getenv("PAGASA_BULLETIN_READ_TIMEOUT", "15"))
BULLETIN_TIMEOUT = (BULLETIN_CONNECT_TIMEOUT, BULLETIN_READ_TIMEOUT)

# Circuit breaker for PAGASA bulletin endpoint
pagasa_bulletin_breaker = CircuitBreaker(
    failure_threshold=4,
    recovery_timeout=120,
    name="pagasa_bulletin",
)


# ---------------------------------------------------------------------------
# Enums & Data Classes
# ---------------------------------------------------------------------------


class RainfallAdvisoryLevel(str, Enum):
    """PAGASA rainfall advisory colour codes."""

    YELLOW = "yellow"  # 7.5–15 mm in 1 hr  or  light–moderate rain
    ORANGE = "orange"  # 15–30 mm in 1 hr   or  heavy rain
    RED = "red"  # >30 mm in 1 hr     or  intense–torrential rain
    UNKNOWN = "unknown"


@dataclass
class RainfallBulletin:
    """Single parsed PAGASA rainfall bulletin."""

    bulletin_id: str
    title: str
    advisory_level: RainfallAdvisoryLevel
    issued_at: datetime
    valid_until: Optional[datetime]
    affected_areas: List[str]
    rainfall_mm_hr: Optional[float]
    description: str
    source: str = "pagasa_bulletin"
    raw_text: str = ""
    affects_paranaque: bool = False
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["advisory_level"] = self.advisory_level.value
        d["issued_at"] = self.issued_at.isoformat()
        d["valid_until"] = self.valid_until.isoformat() if self.valid_until else None
        return d


@dataclass
class SevereWeatherBulletin:
    """Parsed severe-weather/typhoon bulletin from PAGASA."""

    bulletin_no: str
    storm_name: Optional[str]
    signal_no: Optional[int]
    issued_at: datetime
    affected_areas: List[str]
    max_winds_kph: Optional[float]
    rainfall_description: str
    affects_paranaque: bool = False
    source: str = "pagasa_severe_weather"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["issued_at"] = self.issued_at.isoformat()
        return d


# ---------------------------------------------------------------------------
# Area Matching Helpers
# ---------------------------------------------------------------------------

_PARANAQUE_PATTERNS = [
    re.compile(r"\bpara[ñn]aque\b", re.IGNORECASE),
    re.compile(r"\bmetro\s*manila\b", re.IGNORECASE),
    re.compile(r"\bncr\b", re.IGNORECASE),
    re.compile(r"\bnational\s*capital\s*region\b", re.IGNORECASE),
    re.compile(r"\bsouthern\s*metro\s*manila\b", re.IGNORECASE),
]


def _affects_paranaque(areas: List[str], text: str = "") -> bool:
    """Check whether an advisory affects Parañaque City."""
    combined = " ".join(areas) + " " + text
    return any(p.search(combined) for p in _PARANAQUE_PATTERNS)


def _parse_advisory_level(text: str) -> RainfallAdvisoryLevel:
    """Infer advisory colour level from bulletin text."""
    t = text.lower()
    if "red" in t or "torrential" in t or "intense" in t:
        return RainfallAdvisoryLevel.RED
    if "orange" in t or "heavy" in t:
        return RainfallAdvisoryLevel.ORANGE
    if "yellow" in t or "moderate" in t or "light" in t:
        return RainfallAdvisoryLevel.YELLOW
    return RainfallAdvisoryLevel.UNKNOWN


def _extract_rainfall_mm(text: str) -> Optional[float]:
    """Try to extract a numeric rainfall value from advisory text."""
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm|millimeters?)", text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class PAGASARainfallBulletinService:
    """
    Fetches and parses PAGASA rainfall advisories and severe-weather bulletins.

    Provides:
    - Current active rainfall advisories
    - Severe weather bulletins (typhoon signals)
    - Historical bulletin lookup
    - Parañaque relevance filtering
    """

    _instance: Optional["PAGASARainfallBulletinService"] = None
    _init_lock = threading.Lock()

    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()
        self._enabled = os.getenv("PAGASA_BULLETIN_ENABLED", "True").lower() == "true"
        self._headers = {
            "User-Agent": "Floodingnaque/2.0 (Thesis Flood Prediction – Parañaque City)",
            "Accept": "application/xml, text/xml, application/rss+xml",
        }

    # -- singleton -----------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "PAGASARainfallBulletinService":
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
            if entry and time.time() - entry["ts"] < BULLETIN_CACHE_TTL:
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
        Fetch current active rainfall advisories.

        Args:
            paranaque_only: If True, filter to advisories that affect Parañaque.

        Returns:
            Dict with status, list of bulletins, and metadata.
        """
        if not self._enabled:
            return {"status": "disabled", "bulletins": [], "message": "PAGASA bulletin service is disabled"}

        cache_key = f"advisories_{'pnq' if paranaque_only else 'all'}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            bulletins = self._fetch_rainfall_advisories()
            if paranaque_only:
                bulletins = [b for b in bulletins if b.affects_paranaque]

            result = {
                "status": "ok",
                "count": len(bulletins),
                "bulletins": [b.to_dict() for b in bulletins],
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "pagasa_rainfall_advisory",
            }
            self._set_cached(cache_key, result)
            return result

        except CircuitOpenError:
            logger.warning("PAGASA bulletin circuit breaker is open")
            return {"status": "circuit_open", "bulletins": [], "message": "Service temporarily unavailable"}
        except Exception as exc:
            logger.error(f"Failed to fetch PAGASA bulletins: {exc}", exc_info=True)
            return {"status": "error", "bulletins": [], "message": str(exc)}

    def get_severe_weather_bulletins(self, paranaque_only: bool = True) -> Dict[str, Any]:
        """Fetch current severe weather bulletins (e.g. typhoon signals)."""
        if not self._enabled:
            return {"status": "disabled", "bulletins": []}

        cached = self._get_cached("severe_weather")
        if cached is not None:
            return cached

        try:
            bulletins = self._fetch_severe_weather()
            if paranaque_only:
                bulletins = [b for b in bulletins if b.affects_paranaque]

            result = {
                "status": "ok",
                "count": len(bulletins),
                "bulletins": [b.to_dict() for b in bulletins],
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "pagasa_severe_weather",
            }
            self._set_cached("severe_weather", result)
            return result

        except CircuitOpenError:
            return {"status": "circuit_open", "bulletins": []}
        except Exception as exc:
            logger.error(f"Failed to fetch severe weather bulletins: {exc}", exc_info=True)
            return {"status": "error", "bulletins": [], "message": str(exc)}

    def get_combined_status(self) -> Dict[str, Any]:
        """Return rainfall advisories + severe weather in a single call."""
        advisories = self.get_active_advisories(paranaque_only=True)
        severe = self.get_severe_weather_bulletins(paranaque_only=True)

        # Determine overall alert level
        levels = []
        for b in advisories.get("bulletins", []):
            levels.append(b.get("advisory_level", "unknown"))

        if "red" in levels:
            overall = "red"
        elif "orange" in levels:
            overall = "orange"
        elif "yellow" in levels:
            overall = "yellow"
        else:
            overall = "none"

        has_typhoon = any(b.get("signal_no") and b["signal_no"] > 0 for b in severe.get("bulletins", []))

        return {
            "overall_advisory_level": overall,
            "has_active_typhoon_signal": has_typhoon,
            "rainfall_advisories": advisories,
            "severe_weather": severe,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # -- internal fetchers ---------------------------------------------------

    @retry_with_backoff(max_retries=2, base_delay=2.0, exceptions=(requests.RequestException,))
    def _fetch_rainfall_advisories(self) -> List[RainfallBulletin]:
        """Fetch and parse the PAGASA rainfall advisory RSS feed."""
        response = pagasa_bulletin_breaker.call(
            requests.get,
            PAGASA_BULLETIN_RSS,
            headers=self._headers,
            timeout=BULLETIN_TIMEOUT,
        )
        response.raise_for_status()

        bulletins: List[RainfallBulletin] = []
        try:
            root = ElementTree.fromstring(response.content)  # nosec B314
            items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")

            for item in items:
                bulletin = self._parse_rss_item(item)
                if bulletin:
                    bulletins.append(bulletin)
        except ElementTree.ParseError as exc:
            logger.error(f"Failed to parse PAGASA RSS XML: {exc}")
            # Fallback: try plain-text parsing
            bulletins = self._parse_plain_text(response.text)

        return bulletins

    @retry_with_backoff(max_retries=2, base_delay=2.0, exceptions=(requests.RequestException,))
    def _fetch_severe_weather(self) -> List[SevereWeatherBulletin]:
        """Fetch and parse PAGASA severe weather bulletins."""
        response = pagasa_bulletin_breaker.call(
            requests.get,
            PAGASA_SEVERE_WEATHER_URL,
            headers=self._headers,
            timeout=BULLETIN_TIMEOUT,
        )
        response.raise_for_status()

        bulletins: List[SevereWeatherBulletin] = []
        try:
            root = ElementTree.fromstring(response.content)  # nosec B314
            items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")

            for item in items:
                bulletin = self._parse_severe_item(item)
                if bulletin:
                    bulletins.append(bulletin)
        except ElementTree.ParseError:
            logger.error("Failed to parse PAGASA severe weather XML")

        return bulletins

    # -- XML parsers ---------------------------------------------------------

    def _parse_rss_item(self, item: ElementTree.Element) -> Optional[RainfallBulletin]:
        """Parse a single RSS <item> into a RainfallBulletin."""
        title = (item.findtext("title") or "").strip()
        description = (item.findtext("description") or "").strip()
        pub_date_str = (item.findtext("pubDate") or "").strip()
        link = (item.findtext("link") or "").strip()

        if not title and not description:
            return None

        combined = f"{title} {description}"

        # Parse publication date
        issued_at = self._parse_date(pub_date_str)
        if not issued_at:
            issued_at = datetime.now(timezone.utc)

        # Extract areas from description
        areas = self._extract_areas(combined)
        affects_pnq = _affects_paranaque(areas, combined)
        level = _parse_advisory_level(combined)
        rainfall = _extract_rainfall_mm(combined)

        # Assign confidence based on data completeness
        confidence = 0.5
        if rainfall is not None:
            confidence += 0.2
        if level != RainfallAdvisoryLevel.UNKNOWN:
            confidence += 0.2
        if affects_pnq:
            confidence += 0.1

        return RainfallBulletin(
            bulletin_id=link or f"pagasa-{issued_at.timestamp():.0f}",
            title=title,
            advisory_level=level,
            issued_at=issued_at,
            valid_until=issued_at + timedelta(hours=6) if issued_at else None,
            affected_areas=areas,
            rainfall_mm_hr=rainfall,
            description=description[:500],
            raw_text=combined[:1000],
            affects_paranaque=affects_pnq,
            confidence=min(confidence, 1.0),
        )

    def _parse_severe_item(self, item: ElementTree.Element) -> Optional[SevereWeatherBulletin]:
        """Parse a severe weather bulletin RSS item."""
        title = (item.findtext("title") or "").strip()
        description = (item.findtext("description") or "").strip()
        pub_date_str = (item.findtext("pubDate") or "").strip()

        if not title:
            return None

        combined = f"{title} {description}"
        issued_at = self._parse_date(pub_date_str) or datetime.now(timezone.utc)
        areas = self._extract_areas(combined)

        # Extract storm name
        storm_match = re.search(
            r"(?:typhoon|tropical\s+(?:storm|depression))\s+[\"']?(\w+)[\"']?",
            combined,
            re.IGNORECASE,
        )
        storm_name = storm_match.group(1) if storm_match else None

        # Extract signal number
        signal_match = re.search(r"signal\s*(?:no\.?\s*)?#?\s*(\d)", combined, re.IGNORECASE)
        signal_no = int(signal_match.group(1)) if signal_match else None

        # Extract max winds
        wind_match = re.search(r"(\d+)\s*(?:kph|km/h|kmph)", combined, re.IGNORECASE)
        max_winds = float(wind_match.group(1)) if wind_match else None

        return SevereWeatherBulletin(
            bulletin_no=f"SWB-{issued_at.strftime('%Y%m%d%H%M')}",
            storm_name=storm_name,
            signal_no=signal_no,
            issued_at=issued_at,
            affected_areas=areas,
            max_winds_kph=max_winds,
            rainfall_description=description[:300],
            affects_paranaque=_affects_paranaque(areas, combined),
        )

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime]:
        """Parse various date formats from PAGASA bulletins."""
        if not date_str:
            return None
        for fmt in (
            "%a, %d %b %Y %H:%M:%S %z",  # RFC 822
            "%Y-%m-%dT%H:%M:%S%z",  # ISO 8601
            "%Y-%m-%d %H:%M:%S",  # Simple
            "%d %B %Y %I:%M %p",  # e.g. "02 March 2026 10:00 AM"
            "%B %d, %Y %I:%M %p",  # e.g. "March 02, 2026 10:00 AM"
        ):
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))  # PHT
                return dt
            except ValueError:
                continue
        return None

    @staticmethod
    def _extract_areas(text: str) -> List[str]:
        """Extract geographic area names from advisory text."""
        areas: List[str] = []
        # Look for "affecting <area1>, <area2>, and <area3>" patterns
        match = re.search(r"(?:affecting|over|in)\s+(.+?)(?:\.|$)", text, re.IGNORECASE)
        if match:
            raw = match.group(1)
            parts = re.split(r",\s*|\s+and\s+", raw)
            areas = [p.strip() for p in parts if p.strip() and len(p.strip()) > 2]
        return areas[:20]  # cap

    @staticmethod
    def _parse_plain_text(text: str) -> List[RainfallBulletin]:
        """Fallback parser for non-XML responses."""
        bulletins: List[RainfallBulletin] = []
        # Split on double newlines which typically separate bulletins
        sections = re.split(r"\n{2,}", text.strip())
        for i, section in enumerate(sections):
            if len(section) < 20:
                continue
            level = _parse_advisory_level(section)
            rainfall = _extract_rainfall_mm(section)
            areas = PAGASARainfallBulletinService._extract_areas(section)
            bulletins.append(
                RainfallBulletin(
                    bulletin_id=f"pagasa-text-{i}",
                    title=section[:80],
                    advisory_level=level,
                    issued_at=datetime.now(timezone.utc),
                    valid_until=None,
                    affected_areas=areas,
                    rainfall_mm_hr=rainfall,
                    description=section[:500],
                    raw_text=section[:1000],
                    affects_paranaque=_affects_paranaque(areas, section),
                    confidence=0.3,
                )
            )
        return bulletins


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------


def get_pagasa_bulletin_service() -> PAGASARainfallBulletinService:
    """Get the singleton PAGASA bulletin service instance."""
    return PAGASARainfallBulletinService.get_instance()
