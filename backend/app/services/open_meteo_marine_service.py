"""
Open-Meteo Marine Service — Free Fallback for Tide Data.

Provides estimated tidal data using a simple harmonic model calibrated
for Manila Bay when WorldTides API credits are exhausted.  Also fetches
real-time wave/swell data from the Open-Meteo Marine API.

Manila Bay tidal characteristics (NAMRIA reference):
- Predominantly mixed, mainly diurnal
- Mean tidal range ≈ 0.6–1.2 m
- Principal constituents: K1, O1 (diurnal) + M2, S2 (semi-diurnal)
"""

import logging
import math
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests
from app.core.constants import DEFAULT_LATITUDE, DEFAULT_LONGITUDE
from app.services.worldtides_types import TideData, TideExtreme

logger = logging.getLogger(__name__)

# ── Harmonic model constants (Manila Bay / Parañaque) ────────────────────
# Two-constituent approximation: K1 (diurnal) + M2 (semi-diurnal)
_K1_PERIOD_H = 23.9345  # hours
_M2_PERIOD_H = 12.4206  # hours
_K1_AMPLITUDE = 0.35  # metres (dominant diurnal component)
_M2_AMPLITUDE = 0.15  # metres (secondary semi-diurnal)
_K1_PHASE_H = 6.0  # hours offset from UTC midnight (approximate)
_M2_PHASE_H = 0.0

# Open-Meteo marine API (no key required)
_MARINE_API_URL = "https://marine-api.open-meteo.com/v1/marine"


class OpenMeteoMarineService:
    """Fallback tidal / marine service using harmonic estimates + Open-Meteo waves."""

    _instance: Optional["OpenMeteoMarineService"] = None

    def __init__(self):
        self.default_lat = float(os.getenv("DEFAULT_LATITUDE", str(DEFAULT_LATITUDE)))
        self.default_lon = float(os.getenv("DEFAULT_LONGITUDE", "120.9822"))
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 1800  # 30 min
        logger.info("OpenMeteoMarineService initialized (harmonic tide model)")

    @classmethod
    def get_instance(cls) -> "OpenMeteoMarineService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    # ── Harmonic tide model ──────────────────────────────────────────────

    @staticmethod
    def _harmonic_height(dt: datetime) -> float:
        """Return estimated tide height (metres, MSL) for *dt* (UTC)."""
        # hours since Unix epoch
        h = dt.timestamp() / 3600.0
        k1 = _K1_AMPLITUDE * math.cos(2 * math.pi * (h - _K1_PHASE_H) / _K1_PERIOD_H)
        m2 = _M2_AMPLITUDE * math.cos(2 * math.pi * (h - _M2_PHASE_H) / _M2_PERIOD_H)
        return round(k1 + m2, 3)

    # ── Public API (mirrors WorldTidesService interface) ─────────────────

    def get_current_tide(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        datum: Optional[str] = None,
    ) -> Optional[TideData]:
        now = datetime.now(timezone.utc)
        return TideData(
            timestamp=now,
            height=self._harmonic_height(now),
            datum=datum or "MSL",
            source="open_meteo_estimated",
        )

    def get_tide_heights(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        days: int = 1,
        datum: Optional[str] = None,
        step: int = 1800,
    ) -> List[TideData]:
        days = min(max(days, 1), 7)
        now = datetime.now(timezone.utc)
        results: List[TideData] = []
        total_seconds = days * 86400
        t = 0
        while t <= total_seconds:
            dt = now + timedelta(seconds=t)
            results.append(
                TideData(
                    timestamp=dt,
                    height=self._harmonic_height(dt),
                    datum=datum or "MSL",
                    source="open_meteo_estimated",
                )
            )
            t += step
        return results

    def get_tide_extremes(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        days: int = 2,
        datum: Optional[str] = None,
    ) -> List[TideExtreme]:
        """Find local maxima/minima in the harmonic model."""
        days = min(max(days, 1), 7)
        now = datetime.now(timezone.utc)
        step = 600  # 10-minute resolution for extremes
        total = days * 86400
        extremes: List[TideExtreme] = []

        prev_h = self._harmonic_height(now - timedelta(seconds=step))
        curr_h = self._harmonic_height(now)

        t = step
        while t <= total:
            dt = now + timedelta(seconds=t)
            next_h = self._harmonic_height(dt)
            # Local maximum
            if curr_h > prev_h and curr_h > next_h:
                extremes.append(
                    TideExtreme(
                        timestamp=now + timedelta(seconds=t - step),
                        height=curr_h,
                        type="High",
                        datum=datum or "MSL",
                    )
                )
            # Local minimum
            elif curr_h < prev_h and curr_h < next_h:
                extremes.append(
                    TideExtreme(
                        timestamp=now + timedelta(seconds=t - step),
                        height=curr_h,
                        type="Low",
                        datum=datum or "MSL",
                    )
                )
            prev_h = curr_h
            curr_h = next_h
            t += step

        return extremes

    def get_tide_data_for_prediction(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return tide features for the flood prediction model."""
        lat = lat or self.default_lat
        lon = lon or self.default_lon

        current = self.get_current_tide(lat, lon)
        extremes = self.get_tide_extremes(lat, lon, days=2)

        if not current:
            return None

        result: Dict[str, Any] = {
            "tide_height": current.height,
            "tide_datum": current.datum,
            "tide_timestamp": current.timestamp.isoformat(),
            "source": "open_meteo_estimated",
            "latitude": lat,
            "longitude": lon,
            "estimated": True,
        }

        if extremes:
            now = datetime.now(timezone.utc)
            future = [e for e in extremes if e.timestamp > now]
            if future:
                nxt = future[0]
                result["next_extreme_type"] = nxt.type
                result["next_extreme_height"] = nxt.height
                result["next_extreme_time"] = nxt.timestamp.isoformat()
                hours_until = (nxt.timestamp - now).total_seconds() / 3600
                result["hours_until_next_extreme"] = round(hours_until, 2)
                result["tide_trend"] = "rising" if nxt.type == "High" else "falling"

                next_high = next((e for e in future if e.type == "High"), None)
                if next_high:
                    result["hours_until_high_tide"] = round((next_high.timestamp - now).total_seconds() / 3600, 2)
                    result["next_high_tide_height"] = next_high.height

        # Simple risk factor
        heights = [e.height for e in extremes] if extremes else []
        if heights:
            mn, mx = min(heights), max(heights)
            rng = mx - mn
            result["tide_risk_factor"] = round(max(0, min(1, (current.height - mn) / rng)) if rng > 0 else 0.5, 3)
        else:
            result["tide_risk_factor"] = round(max(0, min(1, (current.height + 0.5) / 1.0)), 3)

        return result

    # ── Wave data from Open-Meteo (bonus) ────────────────────────────────

    def get_wave_data(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        hours: int = 24,
    ) -> Optional[Dict[str, Any]]:
        """Fetch real-time wave/swell data from Open-Meteo Marine API."""
        lat = lat or self.default_lat
        lon = lon or self.default_lon
        try:
            resp = requests.get(
                _MARINE_API_URL,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": "wave_height,wave_direction,wave_period",
                    "forecast_hours": min(hours, 168),
                    "timezone": "Asia/Manila",
                },
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning(f"Open-Meteo marine request failed: {e}")
            return None

    def is_available(self) -> bool:
        return True  # Always available (harmonic model is local)

    def get_service_status(self) -> Dict[str, Any]:
        return {
            "enabled": True,
            "type": "harmonic_estimate",
            "api_key_configured": False,
            "default_location": {"lat": self.default_lat, "lon": self.default_lon},
            "default_datum": "MSL",
            "description": "Harmonic tide model for Manila Bay (K1+M2 constituents)",
        }


def get_open_meteo_marine_service() -> OpenMeteoMarineService:
    """Module-level convenience accessor."""
    return OpenMeteoMarineService.get_instance()
