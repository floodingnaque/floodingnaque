"""
PAGASA Radar-Based Precipitation Service.

Integrates with PAGASA (Philippine Atmospheric, Geophysical and Astronomical
Services Administration) radar data for localized rainfall detection within
individual barangays of Parañaque City.

Data Sources:
- PAGASA Doppler Radar Mosaic (Tagaytay / Subic stations covering Metro Manila)
- PAGASA AWS (Automated Weather Stations) for ground-truth calibration
- PAGASA Rainfall Advisory bulletins via RSS/XML

The service fetches radar-estimated precipitation and calibrates it against
nearby AWS observations for improved accuracy at barangay resolution.
"""

import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from app.core.constants import (
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
    STUDY_AREA_BOUNDS,
    STUDY_AREA_STATIONS,
)
from app.utils.circuit_breaker import retry_with_backoff
from app.utils.correlation import inject_correlation_headers

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PAGASA Radar configuration
# ---------------------------------------------------------------------------

# PAGASA public endpoints for weather data
PAGASA_BASE_URL = os.getenv(
    "PAGASA_BASE_URL", "https://pubfiles.pagasa.dost.gov.ph"
)
PAGASA_API_URL = os.getenv(
    "PAGASA_API_URL", "https://api.pagasa.dost.gov.ph"
)

# Radar mosaic tile resolution (~1 km per pixel at Metro Manila latitudes)
RADAR_RESOLUTION_KM = 1.0

# Cache TTL for radar data (5 minutes - matches radar sweep interval)
RADAR_CACHE_TTL_SECONDS = int(os.getenv("PAGASA_RADAR_CACHE_TTL", "300"))

# Request timeout for PAGASA endpoints
PAGASA_TIMEOUT = int(os.getenv("PAGASA_TIMEOUT", "15"))

# ---------------------------------------------------------------------------
# Barangay centroids for per-barangay radar look-ups
# ---------------------------------------------------------------------------

PARANAQUE_BARANGAYS: Dict[str, Dict[str, Any]] = {
    "baclaran": {"lat": 14.5240, "lon": 121.0010, "name": "Baclaran"},
    "don_galo": {"lat": 14.5120, "lon": 120.9920, "name": "Don Galo"},
    "la_huerta": {"lat": 14.4891, "lon": 120.9876, "name": "La Huerta"},
    "san_dionisio": {"lat": 14.5070, "lon": 121.0070, "name": "San Dionisio"},
    "tambo": {"lat": 14.5180, "lon": 120.9950, "name": "Tambo"},
    "vitalez": {"lat": 14.4950, "lon": 120.9910, "name": "Vitalez"},
    "bf_homes": {"lat": 14.4545, "lon": 121.0234, "name": "BF Homes"},
    "don_bosco": {"lat": 14.4760, "lon": 121.0240, "name": "Don Bosco"},
    "marcelo_green": {"lat": 14.4820, "lon": 121.0100, "name": "Marcelo Green Village"},
    "merville": {"lat": 14.4720, "lon": 121.0360, "name": "Merville"},
    "moonwalk": {"lat": 14.4540, "lon": 121.0100, "name": "Moonwalk"},
    "san_antonio": {"lat": 14.4680, "lon": 121.0140, "name": "San Antonio"},
    "san_isidro": {"lat": 14.4500, "lon": 121.0300, "name": "San Isidro"},
    "san_martin": {"lat": 14.4610, "lon": 121.0000, "name": "San Martin de Porres"},
    "santo_nino": {"lat": 14.4450, "lon": 121.0170, "name": "Santo Niño"},
    "sucat": {"lat": 14.4625, "lon": 121.0456, "name": "Sun Valley (Sucat)"},
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

class RadarPrecipitationEstimate:
    """Radar precipitation estimate for a single point/barangay."""

    def __init__(
        self,
        *,
        barangay_key: str,
        barangay_name: str,
        lat: float,
        lon: float,
        rainfall_mm: float,
        intensity: str,
        timestamp: datetime,
        source: str = "pagasa_radar",
        confidence: float = 0.0,
        calibrated: bool = False,
        aws_station: Optional[str] = None,
    ):
        self.barangay_key = barangay_key
        self.barangay_name = barangay_name
        self.lat = lat
        self.lon = lon
        self.rainfall_mm = rainfall_mm
        self.intensity = intensity
        self.timestamp = timestamp
        self.source = source
        self.confidence = confidence
        self.calibrated = calibrated
        self.aws_station = aws_station

    def to_dict(self) -> Dict[str, Any]:
        return {
            "barangay_key": self.barangay_key,
            "barangay_name": self.barangay_name,
            "lat": self.lat,
            "lon": self.lon,
            "rainfall_mm": round(self.rainfall_mm, 2),
            "intensity": self.intensity,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "confidence": round(self.confidence, 2),
            "calibrated": self.calibrated,
            "aws_station": self.aws_station,
        }


def _classify_rain_intensity(mm_per_hour: float) -> str:
    """
    Classify rainfall intensity per PAGASA categories.

    PAGASA uses the following thresholds:
    - No rain: 0 mm/hr
    - Light rain: 0.1 – 2.5 mm/hr
    - Moderate rain: 2.6 – 7.5 mm/hr
    - Heavy rain: 7.6 – 15.0 mm/hr
    - Intense rain: 15.1 – 30.0 mm/hr
    - Torrential rain: > 30.0 mm/hr
    """
    if mm_per_hour <= 0:
        return "no_rain"
    elif mm_per_hour <= 2.5:
        return "light"
    elif mm_per_hour <= 7.5:
        return "moderate"
    elif mm_per_hour <= 15.0:
        return "heavy"
    elif mm_per_hour <= 30.0:
        return "intense"
    else:
        return "torrential"


class PAGASARadarService:
    """
    Service for fetching radar-based precipitation estimates from PAGASA.

    Supports:
    - City-wide radar mosaic look-up for Parañaque
    - Per-barangay precipitation estimates
    - AWS ground-truth calibration
    - Rainfall advisory parsing
    - Thread-safe caching with configurable TTL
    """

    _instance: Optional["PAGASARadarService"] = None
    _init_lock = threading.Lock()

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()
        self._last_fetch: Optional[float] = None
        self._enabled = os.getenv("PAGASA_RADAR_ENABLED", "True").lower() == "true"
        self._api_key = os.getenv("PAGASA_API_KEY", "")
        self._headers = {
            "User-Agent": "Floodingnaque/2.0 (Thesis Flood Prediction – Parañaque City)",
            "Accept": "application/json",
        }
        if self._api_key:
            self._headers["Authorization"] = f"Bearer {self._api_key}"

    @classmethod
    def get_instance(cls) -> "PAGASARadarService":
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_enabled(self) -> bool:
        return self._enabled

    def get_city_precipitation(self) -> Dict[str, Any]:
        """
        Fetch the latest radar precipitation mosaic for Parañaque City.

        Returns a summary dict with per-barangay estimates and a city-wide
        average. Results are cached for ``RADAR_CACHE_TTL_SECONDS``.
        """
        if not self._enabled:
            return {"status": "disabled", "message": "PAGASA radar integration is disabled"}

        cached = self._get_cached("city_precip")
        if cached is not None:
            return cached

        try:
            estimates = self._fetch_radar_estimates()
            aws_data = self._fetch_aws_observations()

            # Calibrate radar estimates against AWS observations
            calibrated = self._calibrate_estimates(estimates, aws_data)

            result = self._build_city_summary(calibrated)
            self._set_cached("city_precip", result)
            return result
        except Exception as exc:
            logger.error(f"Failed to fetch PAGASA radar data: {exc}", exc_info=True)
            return {
                "status": "error",
                "message": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def get_barangay_precipitation(self, barangay_key: str) -> Optional[Dict[str, Any]]:
        """
        Get radar precipitation estimate for a single barangay.

        Args:
            barangay_key: Barangay identifier (e.g. 'bf_homes')

        Returns:
            Precipitation data dict or None if barangay not found
        """
        if barangay_key not in PARANAQUE_BARANGAYS:
            return None

        city_data = self.get_city_precipitation()
        if city_data.get("status") in ("disabled", "error"):
            return city_data

        barangay_estimates = city_data.get("barangays", {})
        return barangay_estimates.get(barangay_key)

    def get_rainfall_advisory(self) -> Dict[str, Any]:
        """
        Fetch the latest PAGASA rainfall advisory for Metro Manila.

        Returns parsed advisory data including warning level and affected areas.
        """
        if not self._enabled:
            return {"status": "disabled"}

        cached = self._get_cached("rainfall_advisory")
        if cached is not None:
            return cached

        try:
            result = self._fetch_rainfall_advisory()
            self._set_cached("rainfall_advisory", result, ttl=600)  # 10 min cache
            return result
        except Exception as exc:
            logger.error(f"Failed to fetch rainfall advisory: {exc}", exc_info=True)
            return {"status": "error", "message": str(exc)}

    # ------------------------------------------------------------------
    # Radar data fetching
    # ------------------------------------------------------------------

    def _fetch_radar_estimates(self) -> List[RadarPrecipitationEstimate]:
        """
        Fetch radar-estimated precipitation for each barangay centroid.

        Uses the PAGASA radar mosaic composite (Tagaytay + Subic + Baler
        Doppler coverage) to extract reflectivity-derived rainfall rates
        at each barangay centroid.
        """
        estimates: List[RadarPrecipitationEstimate] = []
        now = datetime.now(timezone.utc)

        # Build bulk request for all barangay centroids
        points = [
            {"key": k, "lat": v["lat"], "lon": v["lon"], "name": v["name"]}
            for k, v in PARANAQUE_BARANGAYS.items()
        ]

        try:
            headers = inject_correlation_headers(self._headers.copy())

            # PAGASA radar precipitation endpoint - grid point extraction
            url = f"{PAGASA_API_URL}/v1/radar/precipitation"
            payload = {
                "points": [{"lat": p["lat"], "lon": p["lon"]} for p in points],
                "product": "qpe",  # Quantitative Precipitation Estimate
                "interval_minutes": 60,
                "format": "json",
            }

            @retry_with_backoff(
                max_retries=2,
                base_delay=1.0,
                exceptions=(requests.exceptions.RequestException,),
            )
            def _do_fetch():
                resp = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=PAGASA_TIMEOUT,
                )
                resp.raise_for_status()
                return resp.json()

            data = _do_fetch()

            # Parse response - expected: { "estimates": [ { "lat", "lon", "rainfall_mm" }, ... ] }
            raw_estimates = data.get("estimates", [])
            for idx, point in enumerate(points):
                rainfall = 0.0
                if idx < len(raw_estimates):
                    rainfall = float(raw_estimates[idx].get("rainfall_mm", 0))

                est = RadarPrecipitationEstimate(
                    barangay_key=point["key"],
                    barangay_name=point["name"],
                    lat=point["lat"],
                    lon=point["lon"],
                    rainfall_mm=rainfall,
                    intensity=_classify_rain_intensity(rainfall),
                    timestamp=now,
                    source="pagasa_radar",
                    confidence=0.70,  # Radar-only baseline confidence
                )
                estimates.append(est)

            logger.info(f"Fetched PAGASA radar estimates for {len(estimates)} barangays")

        except requests.exceptions.RequestException as exc:
            logger.warning(f"PAGASA radar API unavailable, falling back to interpolation: {exc}")
            estimates = self._interpolate_from_stations(now)
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning(f"Error parsing PAGASA radar response: {exc}")
            estimates = self._interpolate_from_stations(now)

        return estimates

    def _interpolate_from_stations(self, ts: datetime) -> List[RadarPrecipitationEstimate]:
        """
        Fallback: interpolate precipitation across barangays from nearest
        PAGASA Automated Weather Station (AWS) readings when radar API
        is unavailable.

        Uses inverse-distance weighting (IDW) from the three closest
        PAGASA synoptic / AWS stations near Parañaque.
        """
        station_readings = self._fetch_aws_observations()
        estimates: List[RadarPrecipitationEstimate] = []

        for key, brgy in PARANAQUE_BARANGAYS.items():
            rainfall = self._idw_interpolate(
                brgy["lat"], brgy["lon"], station_readings
            )
            estimates.append(
                RadarPrecipitationEstimate(
                    barangay_key=key,
                    barangay_name=brgy["name"],
                    lat=brgy["lat"],
                    lon=brgy["lon"],
                    rainfall_mm=rainfall,
                    intensity=_classify_rain_intensity(rainfall),
                    timestamp=ts,
                    source="pagasa_aws_interpolated",
                    confidence=0.50,
                )
            )

        return estimates

    @staticmethod
    def _idw_interpolate(
        lat: float,
        lon: float,
        stations: List[Dict[str, Any]],
        power: float = 2.0,
    ) -> float:
        """Inverse-distance-weighted interpolation of rainfall from stations."""
        if not stations:
            return 0.0

        numerator = 0.0
        denominator = 0.0
        for st in stations:
            dist_sq = (st["lat"] - lat) ** 2 + (st["lon"] - lon) ** 2
            if dist_sq < 1e-10:
                return st.get("rainfall_mm", 0.0)
            weight = 1.0 / (dist_sq ** (power / 2))
            numerator += weight * st.get("rainfall_mm", 0.0)
            denominator += weight

        return numerator / denominator if denominator else 0.0

    # ------------------------------------------------------------------
    # AWS ground-truth observations
    # ------------------------------------------------------------------

    def _fetch_aws_observations(self) -> List[Dict[str, Any]]:
        """
        Fetch current observations from PAGASA Automated Weather Stations
        near Parañaque for radar calibration.

        Stations: Port Area (Manila), NAIA (Pasay), Science Garden (QC).
        """
        cached = self._get_cached("aws_obs")
        if cached is not None:
            return cached

        stations = [
            {"id": "port_area", "name": "Port Area", "lat": 14.5840, "lon": 120.9690},
            {"id": "naia", "name": "NAIA", "lat": 14.5086, "lon": 121.0197},
            {"id": "science_garden", "name": "Science Garden", "lat": 14.6470, "lon": 121.0440},
        ]

        results: List[Dict[str, Any]] = []

        try:
            headers = inject_correlation_headers(self._headers.copy())
            url = f"{PAGASA_API_URL}/v1/aws/observations"
            params = {
                "station_ids": ",".join(s["id"] for s in stations),
                "fields": "rainfall,temperature,humidity,wind_speed",
            }

            resp = requests.get(url, params=params, headers=headers, timeout=PAGASA_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            for obs in data.get("observations", []):
                station = next((s for s in stations if s["id"] == obs.get("station_id")), None)
                if station:
                    results.append({
                        "station_id": station["id"],
                        "name": station["name"],
                        "lat": station["lat"],
                        "lon": station["lon"],
                        "rainfall_mm": float(obs.get("rainfall", 0)),
                        "temperature": obs.get("temperature"),
                        "humidity": obs.get("humidity"),
                        "wind_speed": obs.get("wind_speed"),
                        "timestamp": obs.get("timestamp"),
                    })

            logger.info(f"Fetched AWS observations from {len(results)} stations")
        except requests.exceptions.RequestException as exc:
            logger.warning(f"AWS observations unavailable: {exc}")
            # Return station stubs with zero rainfall as graceful degradation
            results = [
                {"station_id": s["id"], "name": s["name"], "lat": s["lat"], "lon": s["lon"], "rainfall_mm": 0.0}
                for s in stations
            ]
        except (KeyError, ValueError) as exc:
            logger.warning(f"Error parsing AWS observations: {exc}")
            results = [
                {"station_id": s["id"], "name": s["name"], "lat": s["lat"], "lon": s["lon"], "rainfall_mm": 0.0}
                for s in stations
            ]

        self._set_cached("aws_obs", results, ttl=300)
        return results

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    def _calibrate_estimates(
        self,
        estimates: List[RadarPrecipitationEstimate],
        aws_data: List[Dict[str, Any]],
    ) -> List[RadarPrecipitationEstimate]:
        """
        Calibrate radar estimates using AWS ground-truth via mean-field
        bias correction.

        The calibration factor ``G`` is computed as:
            G = mean(AWS_rainfall) / mean(Radar_at_AWS_locations)

        Each radar estimate is then multiplied by ``G``.
        """
        if not aws_data or not estimates:
            return estimates

        # Compute radar values at AWS station locations
        radar_at_stations: List[float] = []
        aws_values: List[float] = []

        for aws in aws_data:
            nearest_est = min(
                estimates,
                key=lambda e: (e.lat - aws["lat"]) ** 2 + (e.lon - aws["lon"]) ** 2,
            )
            radar_at_stations.append(nearest_est.rainfall_mm)
            aws_values.append(aws.get("rainfall_mm", 0.0))

        mean_radar = sum(radar_at_stations) / len(radar_at_stations) if radar_at_stations else 0
        mean_aws = sum(aws_values) / len(aws_values) if aws_values else 0

        if mean_radar > 0.1:
            g_factor = mean_aws / mean_radar
            # Clamp to reasonable range to avoid over-correction
            g_factor = max(0.3, min(g_factor, 3.0))
        else:
            g_factor = 1.0

        calibrated: List[RadarPrecipitationEstimate] = []
        for est in estimates:
            cal_rainfall = est.rainfall_mm * g_factor
            calibrated.append(
                RadarPrecipitationEstimate(
                    barangay_key=est.barangay_key,
                    barangay_name=est.barangay_name,
                    lat=est.lat,
                    lon=est.lon,
                    rainfall_mm=cal_rainfall,
                    intensity=_classify_rain_intensity(cal_rainfall),
                    timestamp=est.timestamp,
                    source="pagasa_radar_calibrated",
                    confidence=min(est.confidence + 0.15, 0.95),
                    calibrated=True,
                    aws_station=None,
                )
            )

        logger.info(f"Calibrated {len(calibrated)} estimates with G-factor={g_factor:.3f}")
        return calibrated

    # ------------------------------------------------------------------
    # Rainfall advisory
    # ------------------------------------------------------------------

    def _fetch_rainfall_advisory(self) -> Dict[str, Any]:
        """Fetch and parse the latest PAGASA rainfall advisory."""
        headers = inject_correlation_headers(self._headers.copy())

        try:
            url = f"{PAGASA_API_URL}/v1/advisories/rainfall"
            params = {"region": "NCR", "format": "json"}
            resp = requests.get(url, params=params, headers=headers, timeout=PAGASA_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            advisory = data.get("advisory", {})
            return {
                "status": "ok",
                "warning_level": advisory.get("level", "none"),
                "title": advisory.get("title", ""),
                "description": advisory.get("description", ""),
                "affected_areas": advisory.get("affected_areas", []),
                "issued_at": advisory.get("issued_at"),
                "valid_until": advisory.get("valid_until"),
                "source": "PAGASA",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except requests.exceptions.RequestException as exc:
            logger.warning(f"Rainfall advisory fetch failed: {exc}")
            return {"status": "unavailable", "message": str(exc)}

    # ------------------------------------------------------------------
    # Summary builder
    # ------------------------------------------------------------------

    def _build_city_summary(
        self, estimates: List[RadarPrecipitationEstimate]
    ) -> Dict[str, Any]:
        """Build a city-wide summary from per-barangay estimates."""
        barangays: Dict[str, Any] = {}
        total_rain = 0.0
        max_rain = 0.0
        max_brgy = ""

        for est in estimates:
            barangays[est.barangay_key] = est.to_dict()
            total_rain += est.rainfall_mm
            if est.rainfall_mm > max_rain:
                max_rain = est.rainfall_mm
                max_brgy = est.barangay_name

        avg_rain = total_rain / len(estimates) if estimates else 0.0

        return {
            "status": "ok",
            "city": "Parañaque City",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "average_rainfall_mm": round(avg_rain, 2),
                "max_rainfall_mm": round(max_rain, 2),
                "max_rainfall_barangay": max_brgy,
                "overall_intensity": _classify_rain_intensity(avg_rain),
                "barangay_count": len(estimates),
                "source": estimates[0].source if estimates else "unknown",
                "calibrated": any(e.calibrated for e in estimates),
            },
            "barangays": barangays,
        }

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _get_cached(self, key: str) -> Optional[Any]:
        with self._cache_lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if time.time() - entry["ts"] > entry.get("ttl", RADAR_CACHE_TTL_SECONDS):
                del self._cache[key]
                return None
            return entry["data"]

    def _set_cached(self, key: str, data: Any, ttl: int = RADAR_CACHE_TTL_SECONDS) -> None:
        with self._cache_lock:
            self._cache[key] = {"data": data, "ts": time.time(), "ttl": ttl}


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

def get_pagasa_radar_service() -> PAGASARadarService:
    """Get singleton PAGASARadarService instance."""
    return PAGASARadarService.get_instance()
