"""System Monitoring Service.

Provides aggregated metrics for:
- Uptime & health checks (per-service probes with scheduler)
- API response time tracking
- ML model prediction drift detection
- Alert delivery confirmation tracking
"""

import logging
import math
import os
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from threading import Lock, Thread
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Uptime tracker (in-memory, resets on restart)
# ---------------------------------------------------------------------------

_start_time: float = time.time()
_health_checks: deque = deque(maxlen=1000)  # Recent health checks
_health_lock = Lock()

# Per-service health state ──────────────────────────────────────────────────
_service_checks: Dict[str, deque] = {}  # service_name → deque of check results
_service_lock = Lock()
_HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL_SECONDS", "30"))
_health_thread: Optional[Thread] = None
_health_thread_running = False

# Service definitions ──────────────────────────────────────────────────────
MONITORED_SERVICES = [
    "api_server",
    "database",
    "ml_model",
    "redis",
    "scheduler",
    "sentry",
]


def get_uptime_seconds() -> float:
    """Return seconds since process start."""
    return time.time() - _start_time


def record_health_check(healthy: bool, response_ms: float) -> None:
    """Record an aggregate health-check result for uptime calculation."""
    with _health_lock:
        _health_checks.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "healthy": healthy,
                "response_ms": round(response_ms, 2),
            }
        )


def _record_service_check(
    service: str,
    status: str,
    latency_ms: float,
    detail: str = "",
) -> None:
    """Record a per-service health probe result."""
    with _service_lock:
        if service not in _service_checks:
            _service_checks[service] = deque(maxlen=500)
        _service_checks[service].append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": status,  # "healthy" | "degraded" | "offline"
                "latency_ms": round(latency_ms, 2),
                "detail": detail,
            }
        )


# ── Individual service probes ──────────────────────────────────────────────


def _probe_api_server() -> None:
    """Probe the API server by checking if we're inside a live process."""
    start = time.perf_counter()
    try:
        # Simply verify the Flask app is importable and has been initialised
        from flask import current_app  # noqa: F401

        latency = (time.perf_counter() - start) * 1000
        _record_service_check("api_server", "healthy", latency, "Process alive")
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        _record_service_check("api_server", "offline", latency, str(exc)[:120])


def _probe_database() -> None:
    """Probe the database with a ping query."""
    start = time.perf_counter()
    try:
        from app.models.db import get_db_session
        from sqlalchemy import text

        with get_db_session() as session:
            session.execute(text("SELECT 1"))
        latency = (time.perf_counter() - start) * 1000
        status = "healthy" if latency < 500 else "degraded"
        _record_service_check("database", status, latency)
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        _record_service_check("database", "offline", latency, str(exc)[:120])


def _probe_ml_model() -> None:
    """Probe the ML model by checking if it's loaded."""
    start = time.perf_counter()
    try:
        from app.services.predict import get_current_model_info

        info = get_current_model_info()
        latency = (time.perf_counter() - start) * 1000
        if info and info.get("loaded"):
            _record_service_check("ml_model", "healthy", latency, f"v{info.get('version', '?')}")
        else:
            _record_service_check("ml_model", "degraded", latency, "Model not loaded")
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        _record_service_check("ml_model", "offline", latency, str(exc)[:120])


def _probe_redis() -> None:
    """Probe Redis if configured."""
    start = time.perf_counter()
    storage_url = os.getenv("RATE_LIMIT_STORAGE_URL", "memory://")
    if "redis" not in storage_url.lower():
        _record_service_check("redis", "healthy", 0, "Not configured (memory://)")
        return
    try:
        from urllib.parse import urlparse

        import redis as _redis

        parsed = urlparse(storage_url)
        r = _redis.Redis(
            host=parsed.hostname or "localhost",
            port=parsed.port or 6379,
            password=parsed.password,
            socket_timeout=3,
            socket_connect_timeout=3,
        )
        r.ping()
        latency = (time.perf_counter() - start) * 1000
        _record_service_check("redis", "healthy", latency)
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        _record_service_check("redis", "offline", latency, str(exc)[:120])


def _probe_scheduler() -> None:
    """Check scheduler status."""
    start = time.perf_counter()
    try:
        from app.services.scheduler import scheduler

        latency = (time.perf_counter() - start) * 1000
        if scheduler and getattr(scheduler, "running", False):
            _record_service_check("scheduler", "healthy", latency, "Running")
        else:
            _record_service_check("scheduler", "degraded", latency, "Not running")
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        _record_service_check("scheduler", "offline", latency, str(exc)[:120])


def _probe_sentry() -> None:
    """Check Sentry configuration."""
    start = time.perf_counter()
    try:
        from app.utils.observability.sentry import is_sentry_enabled

        latency = (time.perf_counter() - start) * 1000
        if is_sentry_enabled():
            _record_service_check("sentry", "healthy", latency, "Enabled")
        else:
            _record_service_check("sentry", "degraded", latency, "Not configured")
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        _record_service_check("sentry", "offline", latency, str(exc)[:120])


_SERVICE_PROBES = {
    "api_server": _probe_api_server,
    "database": _probe_database,
    "ml_model": _probe_ml_model,
    "redis": _probe_redis,
    "scheduler": _probe_scheduler,
    "sentry": _probe_sentry,
}


def run_all_health_checks() -> None:
    """Execute all service health probes and record an aggregate result."""
    start = time.perf_counter()
    any_offline = False
    for name, probe in _SERVICE_PROBES.items():
        try:
            probe()
        except Exception:
            _record_service_check(name, "offline", 0, "Probe exception")
            any_offline = True

    total_ms = (time.perf_counter() - start) * 1000
    record_health_check(healthy=not any_offline, response_ms=total_ms)


def _health_check_loop() -> None:
    """Background loop that runs health checks at a fixed interval."""
    global _health_thread_running
    while _health_thread_running:
        try:
            run_all_health_checks()
        except Exception:
            logger.exception("Health check loop error")
        time.sleep(_HEALTH_CHECK_INTERVAL)


def start_health_checker() -> None:
    """Start the background health-check thread (call once at app startup)."""
    global _health_thread, _health_thread_running
    if _health_thread_running:
        return
    _health_thread_running = True
    _health_thread = Thread(target=_health_check_loop, daemon=True, name="health-checker")
    _health_thread.start()
    logger.info("Health-check scheduler started (interval=%ds)", _HEALTH_CHECK_INTERVAL)


def stop_health_checker() -> None:
    """Stop the background health-check thread."""
    global _health_thread_running
    _health_thread_running = False


def get_service_statuses() -> List[Dict[str, Any]]:
    """Return latest status for each monitored service."""
    result = []
    with _service_lock:
        for svc in MONITORED_SERVICES:
            checks = list(_service_checks.get(svc, []))
            if not checks:
                result.append(
                    {
                        "service": svc,
                        "status": "unknown",
                        "latency_ms": 0,
                        "last_checked": None,
                        "detail": "No checks yet",
                        "uptime_pct_24h": None,
                    }
                )
                continue
            latest = checks[-1]
            # Calculate uptime % over last 24h
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            recent = [c for c in checks if c["timestamp"] >= cutoff]
            healthy_count = sum(1 for c in recent if c["status"] == "healthy")
            uptime_pct = round((healthy_count / len(recent)) * 100, 2) if recent else None
            result.append(
                {
                    "service": svc,
                    "status": latest["status"],
                    "latency_ms": latest["latency_ms"],
                    "last_checked": latest["timestamp"],
                    "detail": latest.get("detail", ""),
                    "uptime_pct_24h": uptime_pct,
                }
            )
    return result


def get_uptime_stats() -> Dict[str, Any]:
    """Return uptime statistics from recent health checks."""
    with _health_lock:
        checks = list(_health_checks)

    total = len(checks)
    healthy = sum(1 for c in checks if c["healthy"])
    avg_ms = sum(c["response_ms"] for c in checks) / total if total else 0

    return {
        "uptime_seconds": round(get_uptime_seconds(), 1),
        "uptime_formatted": _format_uptime(get_uptime_seconds()),
        "health_check_count": total,
        "healthy_count": healthy,
        "uptime_percentage": round((healthy / total) * 100, 2) if total else 100.0,
        "avg_response_ms": round(avg_ms, 2),
        "last_check": checks[-1] if checks else None,
        "services": get_service_statuses(),
    }


def _format_uptime(seconds: float) -> str:
    days, rem = divmod(int(seconds), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# API response tracking (in-memory rolling window)
# ---------------------------------------------------------------------------

_api_metrics: deque = deque(maxlen=5000)
_api_lock = Lock()


def record_api_response(
    endpoint: str,
    method: str,
    status_code: int,
    response_ms: float,
) -> None:
    """Record an API response for metrics tracking."""
    with _api_lock:
        _api_metrics.append(
            {
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "response_ms": round(response_ms, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )


def get_api_response_stats(minutes: int = 60) -> Dict[str, Any]:
    """Aggregate API response stats over the last N minutes.

    ``error_rate`` is returned as a **decimal ratio** (0–1), e.g. 0.1687 for 16.87%.
    The frontend is responsible for formatting (× 100 + "%").
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    cutoff_iso = cutoff.isoformat()

    with _api_lock:
        recent = [m for m in _api_metrics if m["timestamp"] >= cutoff_iso]

    total = len(recent)
    if total == 0:
        return {
            "period_minutes": minutes,
            "total_requests": 0,
            "avg_response_ms": 0,
            "p95_response_ms": 0,
            "p99_response_ms": 0,
            "error_rate": 0,
            "status_breakdown": {},
            "slowest_endpoints": [],
        }

    times = sorted(m["response_ms"] for m in recent)
    errors = sum(1 for m in recent if m["status_code"] >= 400)

    # Status breakdown
    status_buckets: Dict[str, int] = {}
    for m in recent:
        bucket = f"{m['status_code'] // 100}xx"
        status_buckets[bucket] = status_buckets.get(bucket, 0) + 1

    # Slowest endpoints (with per-endpoint p95, p99, error count)
    from collections import defaultdict

    ep_data: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"times": [], "errors": 0})
    for m in recent:
        ep_data[m["endpoint"]]["times"].append(m["response_ms"])
        if m["status_code"] >= 400:
            ep_data[m["endpoint"]]["errors"] += 1

    slowest = []
    for ep, data in ep_data.items():
        t = sorted(data["times"])
        n = len(t)
        slowest.append(
            {
                "endpoint": ep,
                "avg_ms": round(sum(t) / n, 2),
                "p95_ms": round(t[int(n * 0.95)] if n > 1 else t[0], 2),
                "p99_ms": round(t[int(n * 0.99)] if n > 1 else t[0], 2),
                "count": n,
                "error_count": data["errors"],
                "sla_exceeded": (sum(t) / n) > 1000,
            }
        )

    slowest.sort(key=lambda x: x["avg_ms"], reverse=True)
    slowest = slowest[:10]

    return {
        "period_minutes": minutes,
        "total_requests": total,
        "avg_response_ms": round(sum(times) / total, 2),
        "p95_response_ms": round(times[int(total * 0.95)] if total > 1 else times[0], 2),
        "p99_response_ms": round(times[int(total * 0.99)] if total > 1 else times[0], 2),
        "error_rate": round(errors / total, 4),  # decimal ratio 0–1
        "status_breakdown": status_buckets,
        "slowest_endpoints": slowest,
    }


# ---------------------------------------------------------------------------
# Model prediction drift monitoring
# ---------------------------------------------------------------------------

_prediction_window: deque = deque(maxlen=2000)
_prediction_lock = Lock()

# Baseline distribution (set after first training / model load)
_baseline_distribution: Optional[Dict[str, float]] = None


def set_baseline_distribution(distribution: Dict[str, float]) -> None:
    """Set baseline prediction distribution for drift detection.

    Args:
        distribution: e.g. {"Safe": 0.70, "Alert": 0.20, "Critical": 0.10}
    """
    global _baseline_distribution
    _baseline_distribution = distribution
    logger.info("Prediction drift baseline set: %s", distribution)


def record_prediction_result(risk_label: str, confidence: float) -> None:
    """Record a single prediction for drift monitoring."""
    with _prediction_lock:
        _prediction_window.append(
            {
                "risk_label": risk_label,
                "confidence": confidence,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )


def get_prediction_drift_stats(window_minutes: int = 60) -> Dict[str, Any]:
    """Compute prediction drift over the rolling window.

    Returns distribution comparison, PSI (Population Stability Index),
    and confidence statistics.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=window_minutes)).isoformat()

    with _prediction_lock:
        recent = [p for p in _prediction_window if p["timestamp"] >= cutoff]

    total = len(recent)
    if total == 0:
        return {
            "window_minutes": window_minutes,
            "total_predictions": 0,
            "current_distribution": {},
            "baseline_distribution": _baseline_distribution,
            "psi": None,
            "drift_detected": False,
            "avg_confidence": 0,
            "confidence_stats": {},
        }

    # Current distribution
    counts: Dict[str, int] = {}
    confidences: List[float] = []
    for p in recent:
        label = p["risk_label"]
        counts[label] = counts.get(label, 0) + 1
        confidences.append(p["confidence"])

    current_dist = {k: round(v / total, 4) for k, v in counts.items()}

    # PSI calculation (Population Stability Index)
    psi = None
    drift_detected = False
    psi_threshold = float(os.getenv("DRIFT_PSI_THRESHOLD", "0.2"))

    if _baseline_distribution:
        psi = 0.0
        all_labels = set(list(_baseline_distribution.keys()) + list(current_dist.keys()))
        for label in all_labels:
            expected = max(_baseline_distribution.get(label, 0.001), 0.001)
            actual = max(current_dist.get(label, 0.001), 0.001)
            psi += (actual - expected) * math.log(actual / expected)

        psi = round(psi, 4)
        drift_detected = psi > psi_threshold

    # Confidence stats
    sorted_conf = sorted(confidences)
    avg_conf = sum(confidences) / len(confidences)

    return {
        "window_minutes": window_minutes,
        "total_predictions": total,
        "current_distribution": current_dist,
        "baseline_distribution": _baseline_distribution,
        "psi": psi,
        "psi_threshold": psi_threshold,
        "drift_detected": drift_detected,
        "avg_confidence": round(avg_conf, 4),
        "confidence_stats": {
            "min": round(sorted_conf[0], 4),
            "max": round(sorted_conf[-1], 4),
            "p50": round(sorted_conf[len(sorted_conf) // 2], 4),
            "p95": (
                round(sorted_conf[int(len(sorted_conf) * 0.95)], 4)
                if len(sorted_conf) > 1
                else round(sorted_conf[0], 4)
            ),
        },
    }


# ---------------------------------------------------------------------------
# Alert delivery tracking
# ---------------------------------------------------------------------------


def get_alert_delivery_stats(hours: int = 24) -> Dict[str, Any]:
    """Query alert delivery statistics from the database.

    Returns totals by status, channel, success rate, and recent failures.
    """
    try:
        from app.models.alert import AlertHistory
        from app.models.db import get_db_session
        from sqlalchemy import func

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        with get_db_session() as session:
            base_q = session.query(AlertHistory).filter(
                AlertHistory.created_at >= cutoff,
                AlertHistory.is_deleted == False,  # noqa: E712
            )

            total = base_q.count()

            # By status
            status_counts = dict(
                session.query(AlertHistory.delivery_status, func.count())
                .filter(AlertHistory.created_at >= cutoff, AlertHistory.is_deleted == False)  # noqa: E712
                .group_by(AlertHistory.delivery_status)
                .all()
            )

            # By channel
            channel_counts = dict(
                session.query(AlertHistory.delivery_channel, func.count())
                .filter(AlertHistory.created_at >= cutoff, AlertHistory.is_deleted == False)  # noqa: E712
                .group_by(AlertHistory.delivery_channel)
                .all()
            )

            # Success rate (decimal ratio 0–1)
            delivered = status_counts.get("delivered", 0)
            success_rate = round(delivered / total, 4) if total else 0

            # Recent failures
            failures = (
                session.query(AlertHistory)
                .filter(
                    AlertHistory.created_at >= cutoff,
                    AlertHistory.delivery_status == "failed",
                    AlertHistory.is_deleted == False,  # noqa: E712
                )
                .order_by(AlertHistory.created_at.desc())
                .limit(10)
                .all()
            )

            recent_failures = [
                {
                    "id": f.id,
                    "risk_label": f.risk_label,
                    "channel": f.delivery_channel,
                    "error": f.error_message,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in failures
            ]

        return {
            "period_hours": hours,
            "total_alerts": total,
            "status_breakdown": status_counts,
            "channel_breakdown": channel_counts,
            "success_rate": success_rate,
            "recent_failures": recent_failures,
        }
    except Exception as exc:
        logger.warning("Failed to fetch alert delivery stats: %s", exc)
        return {
            "period_hours": hours,
            "total_alerts": 0,
            "status_breakdown": {},
            "channel_breakdown": {},
            "success_rate": 0,
            "recent_failures": [],
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Combined monitoring summary
# ---------------------------------------------------------------------------


def get_monitoring_summary() -> Dict[str, Any]:
    """Return a combined monitoring dashboard payload."""
    return {
        "uptime": get_uptime_stats(),
        "api_responses": get_api_response_stats(minutes=60),
        "prediction_drift": get_prediction_drift_stats(window_minutes=60),
        "alert_delivery": get_alert_delivery_stats(hours=24),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
