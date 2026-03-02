"""
Manila Bay Tide Level Service.

Provides enhanced tidal data specifically for Manila Bay and its influence
on Parañaque City's flood risk.  Wraps the existing WorldTides service
with Manila-Bay-specific logic and adds fallback data sources.

Key Features:
- Manila Bay astronomical tide predictions
- Storm surge estimation overlay
- Tidal influence scoring for flood risk
- Fallback to NAMRIA / PAGASA tide tables when WorldTides is unavailable

Physics Context:
- Manila Bay has a semi-diurnal tide (~2 cycles / day).
- Mean tidal range ≈ 0.9 m; spring tides up to 1.4 m.
- Storm surge during typhoons can add 1–3 m.
- High tide + heavy rain = severely reduced drainage for Parañaque.
"""

import logging
import math
import os
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
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

# Manila Bay reference point (just off Parañaque/Tambo coast)
MANILA_BAY_LAT = float(os.getenv("MANILA_BAY_LAT", "14.518"))
MANILA_BAY_LON = float(os.getenv("MANILA_BAY_LON", "120.945"))

# NAMRIA (Philippine hydrographic office) tide table fallback
NAMRIA_TIDE_URL = os.getenv(
    "NAMRIA_TIDE_URL",
    "https://www.namria.gov.ph/api/tides",
)

TIDE_CACHE_TTL = int(os.getenv("MANILA_TIDE_CACHE_TTL", "900"))  # 15 min
TIDE_TIMEOUT = int(os.getenv("MANILA_TIDE_TIMEOUT", "20"))

manila_tide_breaker = CircuitBreaker(
    failure_threshold=4,
    recovery_timeout=120,
    name="manila_bay_tide",
)

# ---------------------------------------------------------------------------
# Manila Bay Tidal Constants (astronomical harmonics)
# ---------------------------------------------------------------------------

# Mean Sea Level at Manila Bay (above chart datum), metres
MSL_MANILA_BAY = 0.65

# Principal harmonic constituents for Manila Bay tide approximation
# Source: Published tidal harmonics for Manila South Harbour
_HARMONICS = [
    # (name, amplitude_m, period_hours, phase_deg)
    ("M2", 0.35, 12.4206, 120.0),   # Principal lunar semidiurnal
    ("S2", 0.14, 12.0000, 145.0),   # Principal solar semidiurnal
    ("K1", 0.22, 23.9345, 210.0),   # Luni-solar diurnal
    ("O1", 0.18, 25.8193, 190.0),   # Lunar diurnal
    ("N2", 0.07, 12.6584, 100.0),   # Larger lunar elliptic
    ("P1", 0.07, 24.0659, 205.0),   # Solar diurnal
]

# Reference epoch for phase calculation (2026-01-01T00:00 UTC)
_EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class ManilaBayTide:
    """Tide data point for Manila Bay."""
    height_m: float                 # Height above chart datum
    height_above_msl_m: float      # Height above MSL
    timestamp: datetime
    datum: str = "MSL"
    tide_phase: str = "unknown"     # rising, falling, high, low
    source: str = "manila_bay_tide"
    is_spring_tide: bool = False
    storm_surge_m: float = 0.0
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d


@dataclass
class TideInfluence:
    """Computed tidal influence on Parañaque flood risk."""
    current_height_m: float
    tide_phase: str
    drainage_reduction_pct: float   # 0-100% how much tide reduces drainage
    flood_risk_multiplier: float    # 1.0 = no effect, >1 = increased risk
    next_high_tide: Optional[datetime]
    next_low_tide: Optional[datetime]
    is_king_tide: bool
    storm_surge_m: float
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["next_high_tide"] = self.next_high_tide.isoformat() if self.next_high_tide else None
        d["next_low_tide"] = self.next_low_tide.isoformat() if self.next_low_tide else None
        return d


# ---------------------------------------------------------------------------
# Astronomical Tide Computation (harmonic prediction)
# ---------------------------------------------------------------------------


def _compute_astronomical_tide(dt: datetime) -> float:
    """
    Predict the astronomical tide height at Manila Bay for a given datetime
    using harmonic constituents.

    Returns height in metres above chart datum.
    """
    hours_since_epoch = (dt - _EPOCH).total_seconds() / 3600.0
    height = MSL_MANILA_BAY

    for _name, amplitude, period_hrs, phase_deg in _HARMONICS:
        omega = 2.0 * math.pi / period_hrs  # angular frequency
        phase_rad = math.radians(phase_deg)
        height += amplitude * math.cos(omega * hours_since_epoch - phase_rad)

    return round(height, 4)


def _compute_tide_series(
    start: datetime, hours: int = 24, step_minutes: int = 15
) -> List[Dict[str, Any]]:
    """Compute a series of tide heights."""
    series = []
    for i in range(0, hours * 60, step_minutes):
        dt = start + timedelta(minutes=i)
        h = _compute_astronomical_tide(dt)
        series.append({"timestamp": dt.isoformat(), "height_m": h})
    return series


def _find_extremes(
    start: datetime, hours: int = 48, step_minutes: int = 10
) -> Dict[str, List[Dict[str, Any]]]:
    """Find high and low tides in a time window."""
    highs: List[Dict[str, Any]] = []
    lows: List[Dict[str, Any]] = []

    prev_h = _compute_astronomical_tide(start)
    prev_prev_h = _compute_astronomical_tide(start - timedelta(minutes=step_minutes))
    direction = "rising" if prev_h > prev_prev_h else "falling"

    for i in range(step_minutes, hours * 60, step_minutes):
        dt = start + timedelta(minutes=i)
        h = _compute_astronomical_tide(dt)

        new_dir = "rising" if h > prev_h else "falling"
        if direction == "rising" and new_dir == "falling":
            highs.append({
                "timestamp": (dt - timedelta(minutes=step_minutes)).isoformat(),
                "height_m": prev_h,
                "type": "high",
            })
        elif direction == "falling" and new_dir == "rising":
            lows.append({
                "timestamp": (dt - timedelta(minutes=step_minutes)).isoformat(),
                "height_m": prev_h,
                "type": "low",
            })

        direction = new_dir
        prev_h = h

    return {"highs": highs, "lows": lows}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ManilaBayTideService:
    """
    Enhanced tide service for Manila Bay / Parañaque City.

    Priority data sources:
    1. WorldTides API (if available)
    2. NAMRIA tide tables API
    3. Local harmonic prediction (always available as fallback)
    """

    _instance: Optional["ManilaBayTideService"] = None
    _init_lock = threading.Lock()

    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()
        self._enabled = os.getenv("MANILA_TIDE_ENABLED", "True").lower() == "true"
        self._worldtides_available = False
        self._namria_available = False

        # Try loading WorldTides service
        try:
            from app.services.worldtides_service import WorldTidesService
            wt = WorldTidesService.get_instance()
            self._worldtides_available = wt.enabled
        except Exception:
            logger.debug("WorldTides service not available for Manila Bay tide")

    @classmethod
    def get_instance(cls) -> "ManilaBayTideService":
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
            if entry and time.time() - entry["ts"] < TIDE_CACHE_TTL:
                return entry["data"]
        return None

    def _set_cached(self, key: str, data: Any) -> None:
        with self._cache_lock:
            self._cache[key] = {"data": data, "ts": time.time()}

    # -- public API ----------------------------------------------------------

    def is_enabled(self) -> bool:
        return self._enabled

    def get_current_tide(self) -> Dict[str, Any]:
        """
        Get current Manila Bay tide height using best available source.

        Fallback chain: WorldTides → NAMRIA → Harmonic computation.
        """
        if not self._enabled:
            return {"status": "disabled"}

        cached = self._get_cached("current_tide")
        if cached is not None:
            return cached

        now = datetime.now(timezone.utc)
        tide = None
        source = "harmonic_prediction"
        confidence = 0.0

        # Try WorldTides first
        if self._worldtides_available:
            try:
                tide = self._fetch_worldtides_current()
                if tide:
                    source = "worldtides"
                    confidence = 0.95
            except Exception as exc:
                logger.debug(f"WorldTides failed for Manila Bay: {exc}")

        # Try NAMRIA fallback
        if tide is None:
            try:
                tide = self._fetch_namria_current()
                if tide:
                    source = "namria"
                    confidence = 0.85
            except Exception as exc:
                logger.debug(f"NAMRIA fallback failed: {exc}")

        # Always-available harmonic prediction
        if tide is None:
            height = _compute_astronomical_tide(now)
            tide = ManilaBayTide(
                height_m=height,
                height_above_msl_m=round(height - MSL_MANILA_BAY, 4),
                timestamp=now,
                source="harmonic_prediction",
                confidence=0.65,
            )
            confidence = 0.65

        # Determine tide phase from recent trend
        h_prev = _compute_astronomical_tide(now - timedelta(minutes=15))
        h_now = tide.height_m if isinstance(tide, ManilaBayTide) else _compute_astronomical_tide(now)
        phase = "rising" if h_now > h_prev else "falling"

        extremes = _find_extremes(now, hours=24)

        result = {
            "status": "ok",
            "current": tide.to_dict() if isinstance(tide, ManilaBayTide) else tide,
            "tide_phase": phase,
            "source": source,
            "confidence": confidence,
            "next_high_tides": extremes["highs"][:3],
            "next_low_tides": extremes["lows"][:3],
            "timestamp": now.isoformat(),
        }
        self._set_cached("current_tide", result)
        return result

    def get_tide_forecast(self, hours: int = 24) -> Dict[str, Any]:
        """Get tide forecast for the next N hours."""
        if not self._enabled:
            return {"status": "disabled"}

        cached = self._get_cached(f"forecast_{hours}")
        if cached is not None:
            return cached

        now = datetime.now(timezone.utc)
        series = _compute_tide_series(now, hours=hours)
        extremes = _find_extremes(now, hours=hours)

        result = {
            "status": "ok",
            "forecast_hours": hours,
            "series": series,
            "extremes": extremes,
            "reference_datum": "chart_datum",
            "msl_offset_m": MSL_MANILA_BAY,
            "source": "harmonic_prediction",
            "confidence": 0.65,
            "timestamp": now.isoformat(),
        }
        self._set_cached(f"forecast_{hours}", result)
        return result

    def get_tide_influence(self, storm_surge_m: float = 0.0) -> Dict[str, Any]:
        """
        Compute the tidal influence on Parañaque flood risk.

        Args:
            storm_surge_m: Additional storm surge height (from typhoon).

        Returns:
            TideInfluence dict with drainage reduction and risk multiplier.
        """
        if not self._enabled:
            return {"status": "disabled"}

        now = datetime.now(timezone.utc)
        height = _compute_astronomical_tide(now) + storm_surge_m
        height_above_msl = height - MSL_MANILA_BAY

        # Tide phase
        h_prev = _compute_astronomical_tide(now - timedelta(minutes=15))
        phase = "rising" if height > h_prev + storm_surge_m else "falling"

        # Drainage reduction: at high tide, drainage is significantly reduced
        # Model: linear interpolation → 0% at low tide, ~80% at highest spring tide
        max_tide_range = 1.4  # max spring tide range above MSL
        normalised = max(0.0, min(1.0, height_above_msl / max_tide_range))
        drainage_reduction = round(normalised * 80.0, 1)

        # Flood risk multiplier: 1.0 at low tide, up to 2.5 at king tide + surge
        risk_multiplier = round(1.0 + normalised * 1.5, 2)
        if storm_surge_m > 0:
            risk_multiplier += round(storm_surge_m * 0.5, 2)

        # King tide check (very high spring tide)
        is_king = height_above_msl > 0.6

        extremes = _find_extremes(now, hours=24)
        next_high = None
        next_low = None
        if extremes["highs"]:
            next_high = datetime.fromisoformat(extremes["highs"][0]["timestamp"])
        if extremes["lows"]:
            next_low = datetime.fromisoformat(extremes["lows"][0]["timestamp"])

        influence = TideInfluence(
            current_height_m=round(height, 3),
            tide_phase=phase,
            drainage_reduction_pct=drainage_reduction,
            flood_risk_multiplier=risk_multiplier,
            next_high_tide=next_high,
            next_low_tide=next_low,
            is_king_tide=is_king,
            storm_surge_m=storm_surge_m,
            confidence=0.7 if storm_surge_m == 0 else 0.5,
        )

        return {
            "status": "ok",
            "influence": influence.to_dict(),
            "timestamp": now.isoformat(),
        }

    # -- internal fetchers ---------------------------------------------------

    def _fetch_worldtides_current(self) -> Optional[ManilaBayTide]:
        """Fetch current tide from WorldTides API."""
        from app.services.worldtides_service import WorldTidesService

        wt = WorldTidesService.get_instance()
        tide = wt.get_current_tide(MANILA_BAY_LAT, MANILA_BAY_LON)
        if tide:
            return ManilaBayTide(
                height_m=tide.height + MSL_MANILA_BAY,  # Convert MSL to chart datum
                height_above_msl_m=tide.height,
                timestamp=tide.timestamp,
                datum=tide.datum,
                source="worldtides",
                confidence=0.95,
            )
        return None

    @retry_with_backoff(max_retries=2, base_delay=2.0, exceptions=(requests.RequestException,))
    def _fetch_namria_current(self) -> Optional[ManilaBayTide]:
        """Fetch tide data from NAMRIA API."""
        try:
            response = manila_tide_breaker.call(
                requests.get,
                NAMRIA_TIDE_URL,
                params={"lat": MANILA_BAY_LAT, "lon": MANILA_BAY_LON},
                timeout=TIDE_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

            height = float(data.get("height", data.get("tide_height", 0)))
            return ManilaBayTide(
                height_m=height,
                height_above_msl_m=round(height - MSL_MANILA_BAY, 4),
                timestamp=datetime.now(timezone.utc),
                source="namria",
                confidence=0.85,
            )
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------


def get_manila_bay_tide_service() -> ManilaBayTideService:
    """Get the singleton Manila Bay tide service instance."""
    return ManilaBayTideService.get_instance()
