"""
Data Aggregation Service Layer.

Central orchestrator that unifies all multi-source data feeds into a single,
consistent interface for the flood prediction engine.  Implements:

- **Source prioritisation & fallback**: each data category has a ranked list
  of providers; if the primary fails the next is tried automatically.
- **Data reliability scoring**: every data point carries a 0–1 confidence
  score computed from source quality, freshness, and consistency checks.
- **Concurrent fetching**: independent sources are queried in parallel via
  ``concurrent.futures`` to minimise latency.
- **Caching & deduplication**: prevents redundant external calls within the
  configured TTL windows.

Architecture
------------
The aggregation layer does NOT replace individual services - it *composes*
them.  Each underlying service (PAGASA, MMDA, WorldTides, river, etc.)
retains its own caching and circuit-breaker logic.  This layer adds:

1. A unified ``get_aggregated_data()`` call for the prediction pipeline.
2. A per-source health check (``get_source_health()``).
3. Reliability metadata attached to every response.

Usage::

    from app.services.data_aggregation_service import get_aggregation_service

    svc = get_aggregation_service()
    data = svc.get_aggregated_data()
    print(data["reliability_score"])      # 0.82
    print(data["sources"]["rainfall"])    # best-available rainfall data
"""

import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

AGG_CACHE_TTL = int(os.getenv("DATA_AGGREGATION_CACHE_TTL", "120"))  # 2 min
MAX_FETCH_WORKERS = int(os.getenv("DATA_AGGREGATION_WORKERS", "6"))
FETCH_TIMEOUT = int(os.getenv("DATA_AGGREGATION_TIMEOUT", "30"))


# ---------------------------------------------------------------------------
# Data Reliability Scoring
# ---------------------------------------------------------------------------


class SourceQuality(str, Enum):
    """Quality tier for a data source."""

    AUTHORITATIVE = "authoritative"  # Official gov API, telemetry
    PRIMARY = "primary"  # Well-known API with SLA
    SECONDARY = "secondary"  # RSS, scraped, community
    FALLBACK = "fallback"  # Computed/estimated locally
    UNAVAILABLE = "unavailable"  # Source is down / circuit open


# Base confidence weights per quality tier
_QUALITY_WEIGHTS: Dict[SourceQuality, float] = {
    SourceQuality.AUTHORITATIVE: 1.0,
    SourceQuality.PRIMARY: 0.85,
    SourceQuality.SECONDARY: 0.60,
    SourceQuality.FALLBACK: 0.40,
    SourceQuality.UNAVAILABLE: 0.0,
}


@dataclass
class SourceResult:
    """Result from a single data source with reliability metadata."""

    source_name: str
    category: str  # e.g. "rainfall", "tide", "river", "advisory"
    quality: SourceQuality
    data: Any  # The actual payload
    confidence: float  # 0-1 composite confidence
    freshness_seconds: float  # Age of data in seconds
    latency_ms: float  # How long the fetch took
    error: Optional[str] = None
    is_fallback: bool = False
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["quality"] = self.quality.value
        return d


@dataclass
class AggregatedData:
    """Unified multi-source data envelope for flood prediction."""

    sources: Dict[str, Any]
    reliability_score: float  # Global composite 0-1
    source_count: int
    sources_available: int
    sources_failed: int
    fetch_latency_ms: float
    timestamp: str
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Reliability Scoring Functions
# ---------------------------------------------------------------------------


def compute_source_confidence(
    quality: SourceQuality,
    freshness_seconds: float,
    max_age_seconds: float = 900,  # 15 min
    consistency_score: float = 1.0,
) -> float:
    """
    Compute a 0–1 confidence score for a data source.

    Factors:
    - **Quality tier** (authoritative > primary > secondary > fallback)
    - **Freshness**: exponential decay as data ages
    - **Consistency**: cross-check score against other sources

    Args:
        quality: Source quality tier.
        freshness_seconds: Age of the data.
        max_age_seconds: Data older than this gets 0 freshness bonus.
        consistency_score: 0-1 score from cross-source consistency checks.
    """
    base = _QUALITY_WEIGHTS.get(quality, 0.0)

    # Freshness penalty: halve confidence for data older than max_age
    if freshness_seconds <= 0:
        freshness_factor = 1.0
    elif freshness_seconds >= max_age_seconds:
        freshness_factor = 0.5
    else:
        freshness_factor = 1.0 - 0.5 * (freshness_seconds / max_age_seconds)

    score = base * freshness_factor * consistency_score
    return round(max(0.0, min(1.0, score)), 3)


def compute_global_reliability(results: List[SourceResult]) -> float:
    """
    Compute global reliability score across all sources.

    Weighted average of individual source confidences, with bonuses for
    having multiple independent sources agreeing.
    """
    if not results:
        return 0.0

    # Category weights (how important each category is for flood prediction)
    category_weights = {
        "rainfall": 0.30,
        "flood_advisory": 0.20,
        "tide": 0.15,
        "river": 0.20,
        "severe_weather": 0.15,
    }

    weighted_sum = 0.0
    total_weight = 0.0

    for r in results:
        w = category_weights.get(r.category, 0.1)
        weighted_sum += r.confidence * w
        total_weight += w

    if total_weight == 0:
        return 0.0

    base_score = weighted_sum / total_weight

    # Multi-source bonus: having >3 sources boosts confidence
    available = sum(1 for r in results if r.quality != SourceQuality.UNAVAILABLE)
    multi_bonus = min(available * 0.02, 0.10)  # up to +0.10 for 5 sources

    return round(min(1.0, base_score + multi_bonus), 3)


def cross_check_consistency(
    rainfall_mm: Optional[float],
    advisory_level: Optional[str],
    river_alarm: Optional[str],
) -> float:
    """
    Simple cross-source consistency check.

    If rainfall is high but advisory says 'normal', or vice versa,
    reduce consistency score.
    """
    score = 1.0

    if rainfall_mm is not None and advisory_level:
        # High rain + no advisory → slight inconsistency
        if rainfall_mm > 15.0 and advisory_level in ("none", "normal", "yellow"):
            score -= 0.15
        # Low rain + severe advisory → might be stale data
        if rainfall_mm < 2.0 and advisory_level in ("red", "orange"):
            score -= 0.20

    if rainfall_mm is not None and river_alarm:
        if rainfall_mm > 20.0 and river_alarm == "normal":
            score -= 0.10
        if rainfall_mm < 2.0 and river_alarm in ("critical", "overflow"):
            score -= 0.15

    return max(0.0, min(1.0, round(score, 3)))


# ---------------------------------------------------------------------------
# Fallback Chain Logic
# ---------------------------------------------------------------------------


class FallbackChain:
    """
    Executes a ranked list of fetcher functions, returning the first
    successful result.  Records which source was used and the fallback
    path taken.
    """

    def __init__(self, category: str, fetchers: List[Tuple[str, SourceQuality, Callable]]):
        """
        Args:
            category: Data category name (e.g. "rainfall").
            fetchers: List of (source_name, quality, callable) tuples
                      in priority order.
        """
        self.category = category
        self.fetchers = fetchers

    def execute(self) -> SourceResult:
        """
        Run through the fallback chain until one succeeds.

        Returns:
            SourceResult with the best available data or an error result.
        """
        errors: List[str] = []

        for source_name, quality, fetcher in self.fetchers:
            start = time.perf_counter()
            try:
                data = fetcher()
                latency_ms = (time.perf_counter() - start) * 1000

                # Check for error status in returned data
                if isinstance(data, dict) and data.get("status") in ("disabled", "error", "circuit_open"):
                    errors.append(f"{source_name}: {data.get('message', data.get('status'))}")
                    continue

                # Compute freshness
                freshness = self._compute_freshness(data)
                confidence = compute_source_confidence(quality, freshness)

                is_fallback = len(errors) > 0  # We already tried higher-priority sources

                return SourceResult(
                    source_name=source_name,
                    category=self.category,
                    quality=quality,
                    data=data,
                    confidence=confidence,
                    freshness_seconds=freshness,
                    latency_ms=round(latency_ms, 1),
                    is_fallback=is_fallback,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

            except Exception as exc:
                latency_ms = (time.perf_counter() - start) * 1000
                msg = f"{source_name}: {type(exc).__name__}: {str(exc)[:200]}"
                errors.append(msg)
                logger.warning(f"Fallback chain [{self.category}] {msg}")

        # All sources failed
        return SourceResult(
            source_name="none",
            category=self.category,
            quality=SourceQuality.UNAVAILABLE,
            data=None,
            confidence=0.0,
            freshness_seconds=0,
            latency_ms=0,
            error="; ".join(errors),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _compute_freshness(data: Any) -> float:
        """Estimate data age in seconds from timestamp fields."""
        if not isinstance(data, dict):
            return 0.0

        ts_str = data.get("fetched_at") or data.get("timestamp") or ""
        if not ts_str:
            return 60.0  # assume 1 min if unknown

        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - ts).total_seconds()
            return max(0.0, age)
        except (ValueError, TypeError):
            return 60.0


# ---------------------------------------------------------------------------
# Aggregation Service
# ---------------------------------------------------------------------------


class DataAggregationService:
    """
    Central data aggregation service.

    Orchestrates all multi-source data providers, applies fallback chains,
    and returns a unified, reliability-scored data envelope.
    """

    _instance: Optional["DataAggregationService"] = None
    _init_lock = threading.Lock()

    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()
        self._enabled = os.getenv("DATA_AGGREGATION_ENABLED", "True").lower() == "true"

    @classmethod
    def get_instance(cls) -> "DataAggregationService":
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
            if entry and time.time() - entry["ts"] < AGG_CACHE_TTL:
                return entry["data"]
        return None

    def _set_cached(self, key: str, data: Any) -> None:
        with self._cache_lock:
            self._cache[key] = {"data": data, "ts": time.time()}

    # -- public API ----------------------------------------------------------

    def is_enabled(self) -> bool:
        return self._enabled

    def get_aggregated_data(self) -> Dict[str, Any]:
        """
        Fetch data from all sources with fallback logic and return
        a unified envelope with reliability scoring.

        The call parallelises independent source categories.
        """
        if not self._enabled:
            return {"status": "disabled"}

        cached = self._get_cached("aggregated")
        if cached is not None:
            return cached

        start = time.perf_counter()

        chains = self._build_fallback_chains()
        results: List[SourceResult] = []

        # Execute chains in parallel (each chain itself is sequential fallback)
        with ThreadPoolExecutor(max_workers=MAX_FETCH_WORKERS) as executor:
            futures = {executor.submit(chain.execute): chain.category for chain in chains}
            for future in as_completed(futures, timeout=FETCH_TIMEOUT):
                category = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as exc:
                    logger.error(f"Aggregation chain [{category}] raised: {exc}")
                    results.append(
                        SourceResult(
                            source_name="none",
                            category=category,
                            quality=SourceQuality.UNAVAILABLE,
                            data=None,
                            confidence=0.0,
                            freshness_seconds=0,
                            latency_ms=0,
                            error=str(exc),
                            timestamp=datetime.now(timezone.utc).isoformat(),
                        )
                    )

        # --- Cross-source consistency ---
        rainfall_mm = self._extract_rainfall(results)
        advisory_level = self._extract_advisory_level(results)
        river_alarm = self._extract_river_alarm(results)
        consistency = cross_check_consistency(rainfall_mm, advisory_level, river_alarm)

        # Adjust confidences by consistency
        for r in results:
            r.confidence = round(r.confidence * consistency, 3)

        # --- Global reliability ---
        reliability = compute_global_reliability(results)

        total_ms = (time.perf_counter() - start) * 1000
        available = sum(1 for r in results if r.quality != SourceQuality.UNAVAILABLE)
        failed = sum(1 for r in results if r.quality == SourceQuality.UNAVAILABLE)

        warnings = []
        if reliability < 0.4:
            warnings.append("LOW_RELIABILITY: Multiple data sources unavailable")
        if consistency < 0.7:
            warnings.append("INCONSISTENT_DATA: Cross-source data does not agree")
        for r in results:
            if r.is_fallback:
                warnings.append(f"FALLBACK_USED: {r.category} using {r.source_name} (fallback)")

        sources_dict: Dict[str, Any] = {}
        for r in results:
            sources_dict[r.category] = r.to_dict()

        aggregated = AggregatedData(
            sources=sources_dict,
            reliability_score=reliability,
            source_count=len(results),
            sources_available=available,
            sources_failed=failed,
            fetch_latency_ms=round(total_ms, 1),
            timestamp=datetime.now(timezone.utc).isoformat(),
            warnings=warnings,
        )

        result_dict = aggregated.to_dict()
        self._set_cached("aggregated", result_dict)
        return result_dict

    def get_source_health(self) -> Dict[str, Any]:
        """
        Check health / availability of each data source without
        fetching full data.  Useful for monitoring dashboards.
        """
        health: Dict[str, Dict[str, Any]] = {}

        checks: List[Tuple[str, str, Callable]] = [
            ("pagasa_radar", "rainfall", self._check_pagasa_radar),
            ("pagasa_bulletin", "rainfall", self._check_pagasa_bulletin),
            ("mmda_flood", "flood_advisory", self._check_mmda),
            ("worldtides", "tide", self._check_worldtides),
            ("manila_bay_tide", "tide", self._check_manila_bay),
            ("river_monitoring", "river", self._check_river),
            ("meteostat", "weather", self._check_meteostat),
        ]

        for name, category, checker in checks:
            try:
                status = checker()
                health[name] = {
                    "status": status,
                    "category": category,
                    "healthy": status == "ok",
                }
            except Exception:
                health[name] = {"status": "error", "category": category, "healthy": False}

        total = len(health)
        healthy = sum(1 for v in health.values() if v["healthy"])

        return {
            "overall": "healthy" if healthy >= total * 0.6 else "degraded",
            "sources": health,
            "healthy_count": healthy,
            "total_count": total,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_category_data(self, category: str) -> Dict[str, Any]:
        """
        Fetch data for a single category with its fallback chain.

        Args:
            category: One of 'rainfall', 'flood_advisory', 'tide',
                      'river', 'severe_weather'.
        """
        chains = self._build_fallback_chains()
        for chain in chains:
            if chain.category == category:
                result = chain.execute()
                return result.to_dict()

        return {"error": f"Unknown category: {category}"}

    # -- fallback chain definitions ------------------------------------------

    def _build_fallback_chains(self) -> List[FallbackChain]:
        """Build the fallback chains for each data category."""
        return [
            FallbackChain(
                "rainfall",
                [
                    ("pagasa_radar", SourceQuality.AUTHORITATIVE, self._fetch_pagasa_radar),
                    ("pagasa_bulletin", SourceQuality.PRIMARY, self._fetch_pagasa_bulletin_rainfall),
                    ("meteostat", SourceQuality.SECONDARY, self._fetch_meteostat_rainfall),
                ],
            ),
            FallbackChain(
                "flood_advisory",
                [
                    ("mmda_flood", SourceQuality.AUTHORITATIVE, self._fetch_mmda_advisories),
                    ("pagasa_bulletin", SourceQuality.PRIMARY, self._fetch_pagasa_bulletin_advisories),
                ],
            ),
            FallbackChain(
                "tide",
                [
                    ("worldtides", SourceQuality.PRIMARY, self._fetch_worldtides),
                    ("manila_bay_tide", SourceQuality.SECONDARY, self._fetch_manila_bay_tide),
                ],
            ),
            FallbackChain(
                "river",
                [
                    ("efcos_dpwh", SourceQuality.AUTHORITATIVE, self._fetch_river_levels),
                    ("mmda_stations", SourceQuality.SECONDARY, self._fetch_mmda_stations),
                ],
            ),
            FallbackChain(
                "severe_weather",
                [
                    ("pagasa_severe", SourceQuality.AUTHORITATIVE, self._fetch_severe_weather),
                ],
            ),
        ]

    # -- individual source fetchers ------------------------------------------

    def _fetch_pagasa_radar(self) -> Dict[str, Any]:
        from app.services.pagasa_radar_service import get_pagasa_radar_service

        return get_pagasa_radar_service().get_city_precipitation()

    def _fetch_pagasa_bulletin_rainfall(self) -> Dict[str, Any]:
        from app.services.pagasa_bulletin_service import get_pagasa_bulletin_service

        return get_pagasa_bulletin_service().get_active_advisories(paranaque_only=True)

    def _fetch_pagasa_bulletin_advisories(self) -> Dict[str, Any]:
        from app.services.pagasa_bulletin_service import get_pagasa_bulletin_service

        return get_pagasa_bulletin_service().get_combined_status()

    def _fetch_severe_weather(self) -> Dict[str, Any]:
        from app.services.pagasa_bulletin_service import get_pagasa_bulletin_service

        return get_pagasa_bulletin_service().get_severe_weather_bulletins(paranaque_only=True)

    def _fetch_mmda_advisories(self) -> Dict[str, Any]:
        from app.services.mmda_flood_service import get_mmda_flood_service

        return get_mmda_flood_service().get_active_advisories(paranaque_only=True)

    def _fetch_mmda_stations(self) -> Dict[str, Any]:
        from app.services.mmda_flood_service import get_mmda_flood_service

        return get_mmda_flood_service().get_station_readings()

    def _fetch_worldtides(self) -> Dict[str, Any]:
        from app.services.worldtides_service import WorldTidesService

        wt = WorldTidesService.get_instance()
        if not wt.enabled:
            return {"status": "disabled"}
        tide = wt.get_current_tide()
        if not tide:
            return {"status": "error", "message": "No tide data available"}
        return {
            "status": "ok",
            "height": tide.height,
            "datum": tide.datum,
            "timestamp": tide.timestamp.isoformat(),
            "source": "worldtides",
        }

    def _fetch_manila_bay_tide(self) -> Dict[str, Any]:
        from app.services.manila_bay_tide_service import get_manila_bay_tide_service

        return get_manila_bay_tide_service().get_current_tide()

    def _fetch_river_levels(self) -> Dict[str, Any]:
        from app.services.river_water_level_service import get_river_water_level_service

        return get_river_water_level_service().get_all_readings()

    def _fetch_meteostat_rainfall(self) -> Dict[str, Any]:
        from app.services.meteostat_service import get_meteostat_service

        svc = get_meteostat_service()
        data = svc.get_current_weather()
        if data:
            return {
                "status": "ok",
                "precipitation_mm": data.get("precipitation", 0),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "meteostat",
            }
        return {"status": "error", "message": "Meteostat unavailable"}

    # -- health checks -------------------------------------------------------

    def _check_pagasa_radar(self) -> str:
        try:
            from app.services.pagasa_radar_service import get_pagasa_radar_service

            svc = get_pagasa_radar_service()
            return "ok" if svc.is_enabled() else "disabled"
        except Exception:
            return "error"

    def _check_pagasa_bulletin(self) -> str:
        try:
            from app.services.pagasa_bulletin_service import get_pagasa_bulletin_service

            svc = get_pagasa_bulletin_service()
            return "ok" if svc.is_enabled() else "disabled"
        except Exception:
            return "error"

    def _check_mmda(self) -> str:
        try:
            from app.services.mmda_flood_service import get_mmda_flood_service

            svc = get_mmda_flood_service()
            return "ok" if svc.is_enabled() else "disabled"
        except Exception:
            return "error"

    def _check_worldtides(self) -> str:
        try:
            from app.services.worldtides_service import WorldTidesService

            svc = WorldTidesService.get_instance()
            return "ok" if svc.enabled else "disabled"
        except Exception:
            return "error"

    def _check_manila_bay(self) -> str:
        try:
            from app.services.manila_bay_tide_service import get_manila_bay_tide_service

            svc = get_manila_bay_tide_service()
            return "ok" if svc.is_enabled() else "disabled"
        except Exception:
            return "error"

    def _check_river(self) -> str:
        try:
            from app.services.river_water_level_service import get_river_water_level_service

            svc = get_river_water_level_service()
            return "ok" if svc.is_enabled() else "disabled"
        except Exception:
            return "error"

    def _check_meteostat(self) -> str:
        try:
            from app.services.meteostat_service import get_meteostat_service

            svc = get_meteostat_service()
            return "ok" if svc else "disabled"
        except Exception:
            return "error"

    # -- utility extractors for cross-check ----------------------------------

    @staticmethod
    def _extract_rainfall(results: List[SourceResult]) -> Optional[float]:
        for r in results:
            if r.category == "rainfall" and r.data:
                if isinstance(r.data, dict):
                    # From pagasa radar → city_average
                    avg = r.data.get("city_average_mm")
                    if avg is not None:
                        return float(avg)
                    # From meteostat
                    prec = r.data.get("precipitation_mm")
                    if prec is not None:
                        return float(prec)
                    # From bulletins
                    bulletins = r.data.get("bulletins", [])
                    if bulletins:
                        rainfalls = [b.get("rainfall_mm_hr") for b in bulletins if b.get("rainfall_mm_hr")]
                        if rainfalls:
                            return max(rainfalls)
        return None

    @staticmethod
    def _extract_advisory_level(results: List[SourceResult]) -> Optional[str]:
        for r in results:
            if r.category in ("flood_advisory", "rainfall") and r.data:
                if isinstance(r.data, dict):
                    level = r.data.get("overall_advisory_level") or r.data.get("highest_alarm")
                    if level:
                        return str(level)
        return None

    @staticmethod
    def _extract_river_alarm(results: List[SourceResult]) -> Optional[str]:
        for r in results:
            if r.category == "river" and r.data:
                if isinstance(r.data, dict):
                    return r.data.get("overall_alarm")
        return None


# ---------------------------------------------------------------------------
# Per-Source Reliability Tracking (EMA)
# ---------------------------------------------------------------------------


@dataclass
class SourceReliability:
    """
    Track per-source reliability using an Exponential Moving Average (EMA).

    Each call to ``record_success()`` / ``record_failure()`` updates the
    running EMA score which weights recent observations more heavily than
    older ones.  This gives a smooth reliability signal that adapts to
    changing source quality without needing a sliding window.
    """

    source_name: str
    total_calls: int = 0
    success_calls: int = 0
    failure_calls: int = 0
    ema_score: float = 1.0  # Start optimistic
    last_success: Optional[str] = None
    last_failure: Optional[str] = None
    last_latency_ms: float = 0.0
    _alpha: float = 0.3  # EMA smoothing factor

    def record_success(self, latency_ms: float = 0.0) -> None:
        self.total_calls += 1
        self.success_calls += 1
        self.last_success = datetime.now(timezone.utc).isoformat()
        self.last_latency_ms = latency_ms
        self.ema_score = self._alpha * 1.0 + (1 - self._alpha) * self.ema_score

    def record_failure(self) -> None:
        self.total_calls += 1
        self.failure_calls += 1
        self.last_failure = datetime.now(timezone.utc).isoformat()
        self.ema_score = self._alpha * 0.0 + (1 - self._alpha) * self.ema_score

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 1.0
        return round(self.success_calls / self.total_calls, 3)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_name": self.source_name,
            "total_calls": self.total_calls,
            "success_calls": self.success_calls,
            "failure_calls": self.failure_calls,
            "ema_score": round(self.ema_score, 3),
            "success_rate": self.success_rate,
            "last_success": self.last_success,
            "last_failure": self.last_failure,
            "last_latency_ms": round(self.last_latency_ms, 1),
        }


# Module-level registry of per-source reliability trackers
_reliability_registry: Dict[str, SourceReliability] = {}
_reliability_lock = threading.Lock()


def _get_reliability(source_name: str) -> SourceReliability:
    """Get or create the reliability tracker for *source_name*."""
    with _reliability_lock:
        if source_name not in _reliability_registry:
            _reliability_registry[source_name] = SourceReliability(source_name=source_name)
        return _reliability_registry[source_name]


def track_reliability(source_name: str) -> Callable:
    """
    Decorator that auto-records success/failure in the EMA reliability
    tracker for the named source.

    Usage::

        @track_reliability("pagasa_radar")
        def _fetch_pagasa_radar(self):
            ...
    """

    def decorator(fn: Callable) -> Callable:
        from functools import wraps

        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracker = _get_reliability(source_name)
            start = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
                latency = (time.perf_counter() - start) * 1000
                tracker.record_success(latency_ms=latency)
                return result
            except Exception:
                tracker.record_failure()
                raise

        return wrapper

    return decorator


def reliability_snapshot() -> Dict[str, Any]:
    """
    Return a snapshot of all per-source EMA reliability scores.

    Intended for the ``/api/v1/data/reliability`` endpoint.
    """
    with _reliability_lock:
        sources = {name: tracker.to_dict() for name, tracker in _reliability_registry.items()}

    return {
        "source_count": len(sources),
        "sources": sources,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# DataBundle - typed, model-ready output
# ---------------------------------------------------------------------------

# V6 feature order - must match backend/scripts/train_progressive_v6.py
_V6_FEATURE_NAMES: List[str] = [
    "temperature",
    "humidity",
    "precipitation",
    "is_monsoon_season",
    "month",
    "temp_humidity_interaction",
    "humidity_precip_interaction",
    "monsoon_precip_interaction",
    "saturation_risk",
    "precip_3day_sum",
    "precip_7day_sum",
    "precip_14day_sum",
    "rain_streak",
    "tide_height",
]


@dataclass
class DataBundle:
    """
    Model-ready data bundle assembled from aggregated sources.

    Provides ``to_feature_vector()`` that returns values in the exact
    order expected by the v6 Random Forest model.
    """

    temperature: float = 0.0
    humidity: float = 0.0
    precipitation: float = 0.0
    is_monsoon_season: int = 0
    month: int = 1
    temp_humidity_interaction: float = 0.0
    humidity_precip_interaction: float = 0.0
    monsoon_precip_interaction: float = 0.0
    saturation_risk: float = 0.0
    precip_3day_sum: float = 0.0
    precip_7day_sum: float = 0.0
    precip_14day_sum: float = 0.0
    rain_streak: int = 0
    tide_height: float = 0.0
    reliability_score: float = 0.0
    timestamp: str = ""

    def to_feature_vector(self) -> List[float]:
        """Return feature values in V6 training order."""
        return [
            self.temperature,
            self.humidity,
            self.precipitation,
            float(self.is_monsoon_season),
            float(self.month),
            self.temp_humidity_interaction,
            self.humidity_precip_interaction,
            self.monsoon_precip_interaction,
            self.saturation_risk,
            self.precip_3day_sum,
            self.precip_7day_sum,
            self.precip_14day_sum,
            float(self.rain_streak),
            self.tide_height,
        ]

    @staticmethod
    def feature_names() -> List[str]:
        """Return feature names in V6 training order."""
        return list(_V6_FEATURE_NAMES)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------


def get_aggregation_service() -> DataAggregationService:
    """Get the singleton data aggregation service instance."""
    return DataAggregationService.get_instance()
