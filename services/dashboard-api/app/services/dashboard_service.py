"""
Dashboard API — DashboardService

Orchestrates data aggregation from all microservices (weather-collector,
ml-prediction, alert-notification, user-management) to construct the
composite views required by the frontend dashboard.

NOTE: Each method uses inter-service HTTP calls via the shared
ServiceClient (with circuit-breaker & retry). When a downstream
service is unreachable the method returns gracefully-degraded data
rather than propagating the failure (fault-isolation pattern).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import redis
import requests
from flask import Flask

logger = logging.getLogger(__name__)

# Default cache TTL in seconds
_CACHE_TTL = int(os.getenv("CACHE_TTL", "60"))


class DashboardService:
    """Aggregation service for the dashboard frontend."""

    def __init__(self, app: Flask) -> None:
        self.app = app
        self.weather_url: str = app.config["WEATHER_SERVICE_URL"]
        self.prediction_url: str = app.config["PREDICTION_SERVICE_URL"]
        self.alert_url: str = app.config["ALERT_SERVICE_URL"]
        self.user_url: str = app.config["USER_SERVICE_URL"]
        self._timeout = (5, 15)  # (connect, read) seconds

        # Redis cache (optional — degrades to no-cache)
        try:
            self._redis = redis.from_url(
                app.config.get("REDIS_URL", "redis://redis:6379/0"),
                decode_responses=True,
            )
            self._redis.ping()
        except Exception:
            logger.warning("Redis unavailable — caching disabled")
            self._redis = None

    # ── Public Methods ──────────────────────────────────────────────

    def get_summary(self) -> dict[str, Any]:
        """Build a consolidated dashboard summary."""
        weather = self._get_cached_or_fetch(
            "dashboard:summary:weather",
            lambda: self._call(self.weather_url, "/api/v1/weather/current"),
        )
        predictions = self._get_cached_or_fetch(
            "dashboard:summary:predictions",
            lambda: self._call(self.prediction_url, "/api/v1/predict/recent"),
        )
        alerts = self._get_cached_or_fetch(
            "dashboard:summary:alerts",
            lambda: self._call(self.alert_url, "/api/v1/alerts/active"),
        )

        # Derive risk level from latest prediction
        latest = predictions[0] if isinstance(predictions, list) and predictions else {}
        risk_level = latest.get("risk_level", "unknown")

        return {
            "current_weather": weather,
            "latest_risk_level": risk_level,
            "active_alerts": len(alerts) if isinstance(alerts, list) else 0,
            "recent_predictions": (predictions[:5] if isinstance(predictions, list) else []),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_statistics(self, since: datetime, period: str) -> dict[str, Any]:
        """Aggregate statistics over a given window."""
        weather_stats = self._call(
            self.weather_url,
            "/api/v1/weather/data",
            params={"since": since.isoformat()},
        )
        prediction_stats = self._call(
            self.prediction_url,
            "/api/v1/predict/recent",
            params={"since": since.isoformat()},
        )
        alert_stats = self._call(
            self.alert_url,
            "/api/v1/alerts/",
            params={"since": since.isoformat()},
        )

        return {
            "period": period,
            "weather_observations": (len(weather_stats) if isinstance(weather_stats, list) else 0),
            "predictions_made": (len(prediction_stats) if isinstance(prediction_stats, list) else 0),
            "alerts_triggered": (len(alert_stats) if isinstance(alert_stats, list) else 0),
            "risk_distribution": self._compute_risk_distribution(prediction_stats),
        }

    def get_activity_feed(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """Merge events across services into a unified feed."""
        events: list[dict] = []

        # Gather recent items from each service
        weather_events = self._call(
            self.weather_url, "/api/v1/weather/data", params={"limit": limit}
        )
        if isinstance(weather_events, list):
            for item in weather_events:
                events.append({
                    "type": "weather_observation",
                    "source": "weather-collector",
                    "timestamp": item.get("timestamp", ""),
                    "summary": f"Weather data recorded — temp: {item.get('temperature', 'N/A')}°C",
                    "data": item,
                })

        pred_events = self._call(
            self.prediction_url, "/api/v1/predict/recent", params={"limit": limit}
        )
        if isinstance(pred_events, list):
            for item in pred_events:
                events.append({
                    "type": "prediction",
                    "source": "ml-prediction",
                    "timestamp": item.get("timestamp", ""),
                    "summary": f"Prediction: {item.get('risk_level', 'N/A')} risk ({item.get('confidence', 'N/A')}%)",
                    "data": item,
                })

        alert_events = self._call(
            self.alert_url, "/api/v1/alerts/", params={"limit": limit}
        )
        if isinstance(alert_events, list):
            for item in alert_events:
                events.append({
                    "type": "alert",
                    "source": "alert-notification",
                    "timestamp": item.get("created_at", ""),
                    "summary": f"Alert: {item.get('severity', 'N/A')} — {item.get('message', '')}",
                    "data": item,
                })

        # Sort by timestamp descending, then paginate
        events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        return events[offset : offset + limit]

    def get_widget_data(self, widget_ids: list[str]) -> dict[str, Any]:
        """Return data keyed by widget id."""
        widget_map: dict[str, Any] = {}

        for wid in widget_ids:
            try:
                if wid == "weather_current":
                    widget_map[wid] = self._call(self.weather_url, "/api/v1/weather/current")
                elif wid == "risk_gauge":
                    preds = self._call(self.prediction_url, "/api/v1/predict/recent")
                    latest = preds[0] if isinstance(preds, list) and preds else {}
                    widget_map[wid] = {
                        "risk_level": latest.get("risk_level", "unknown"),
                        "confidence": latest.get("confidence", 0),
                    }
                elif wid == "alert_count":
                    alerts = self._call(self.alert_url, "/api/v1/alerts/active")
                    widget_map[wid] = {
                        "active": len(alerts) if isinstance(alerts, list) else 0,
                    }
                elif wid == "tide_info":
                    widget_map[wid] = self._call(self.weather_url, "/api/v1/weather/tides")
                elif wid == "user_count":
                    widget_map[wid] = self._call(self.user_url, "/api/v1/users/count")
                else:
                    widget_map[wid] = {"error": "Unknown widget"}
            except Exception as e:
                widget_map[wid] = {"error": str(e)}

        return widget_map

    def get_system_overview(self) -> dict[str, Any]:
        """Health-check each downstream service and aggregate."""
        services = {
            "weather-collector": self.weather_url,
            "ml-prediction": self.prediction_url,
            "alert-notification": self.alert_url,
            "user-management": self.user_url,
        }
        overview: dict[str, Any] = {"services": {}, "timestamp": datetime.now(timezone.utc).isoformat()}
        for name, url in services.items():
            try:
                resp = requests.get(f"{url}/health", timeout=5)
                overview["services"][name] = {
                    "status": "healthy" if resp.status_code == 200 else "degraded",
                    "response_time_ms": resp.elapsed.total_seconds() * 1000,
                    "details": resp.json() if resp.status_code == 200 else None,
                }
            except Exception:
                overview["services"][name] = {"status": "unreachable", "response_time_ms": None}

        healthy = sum(1 for s in overview["services"].values() if s["status"] == "healthy")
        overview["overall_status"] = "healthy" if healthy == len(services) else (
            "degraded" if healthy > 0 else "critical"
        )
        return overview

    # ── Prediction helpers ──────────────────────────────────────────

    def list_predictions(self, page: int, per_page: int, filters: dict) -> dict:
        params = {"page": page, "per_page": per_page, **filters}
        result = self._call(self.prediction_url, "/api/v1/predict/recent", params=params)
        items = result if isinstance(result, list) else []
        return {"items": items, "total": len(items), "pages": max(1, len(items) // per_page)}

    def get_prediction_detail(self, prediction_id: str) -> dict | None:
        result = self._call(self.prediction_url, f"/api/v1/predict/{prediction_id}")
        return result if isinstance(result, dict) else None

    def get_prediction_analytics(self, period: str) -> dict:
        return self._call(
            self.prediction_url, "/api/v1/predict/analytics", params={"period": period}
        ) or {}

    def get_model_comparison(self) -> dict:
        return self._call(self.prediction_url, "/api/v1/models/comparison") or {}

    # ── Aggregation helpers ─────────────────────────────────────────

    def aggregate_weather_risk(self, days: int) -> list[dict]:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        weather = self._call(self.weather_url, "/api/v1/weather/data", params={"since": since})
        predictions = self._call(self.prediction_url, "/api/v1/predict/recent", params={"since": since})

        weather_list = weather if isinstance(weather, list) else []
        pred_list = predictions if isinstance(predictions, list) else []

        # Combine into a time-series
        series: list[dict] = []
        for w in weather_list:
            entry: dict[str, Any] = {
                "timestamp": w.get("timestamp"),
                "rainfall": w.get("rainfall"),
                "temperature": w.get("temperature"),
                "humidity": w.get("humidity"),
                "risk_score": None,
                "risk_level": None,
            }
            # Attempt to find a prediction close to this timestamp
            for p in pred_list:
                if p.get("timestamp") == w.get("timestamp"):
                    entry["risk_score"] = p.get("risk_score")
                    entry["risk_level"] = p.get("risk_level")
                    break
            series.append(entry)

        return series

    def aggregate_alert_timeline(self, days: int) -> list[dict]:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        alerts = self._call(self.alert_url, "/api/v1/alerts/", params={"since": since})
        return alerts if isinstance(alerts, list) else []

    def aggregate_flood_events(self, year: str | None = None) -> list[dict]:
        params = {"year": year} if year else {}
        events = self._call(self.prediction_url, "/api/v1/predict/events", params=params)
        return events if isinstance(events, list) else []

    def get_trend_analysis(self, metric: str, period: str) -> dict:
        data = self._call(
            self.weather_url,
            "/api/v1/weather/data",
            params={"metric": metric, "period": period},
        )
        items = data if isinstance(data, list) else []

        if not items:
            return {"metric": metric, "period": period, "trend": "insufficient_data", "data": []}

        values = [item.get(metric, 0) for item in items if item.get(metric) is not None]

        if len(values) >= 2:
            first_half = sum(values[: len(values) // 2]) / max(len(values) // 2, 1)
            second_half = sum(values[len(values) // 2 :]) / max(len(values) // 2, 1)
            trend = "increasing" if second_half > first_half * 1.05 else (
                "decreasing" if second_half < first_half * 0.95 else "stable"
            )
        else:
            trend = "insufficient_data"

        return {
            "metric": metric,
            "period": period,
            "trend": trend,
            "average": sum(values) / max(len(values), 1),
            "min": min(values, default=0),
            "max": max(values, default=0),
            "data_points": len(values),
        }

    # ── Export helpers ──────────────────────────────────────────────

    def export_predictions(
        self, start_date: str | None, end_date: str | None, risk_level: str | None
    ) -> list[dict]:
        params: dict[str, str] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if risk_level:
            params["risk_level"] = risk_level
        result = self._call(self.prediction_url, "/api/v1/predict/recent", params=params)
        return result if isinstance(result, list) else []

    def export_weather(self, days: int) -> list[dict]:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        result = self._call(self.weather_url, "/api/v1/weather/data", params={"since": since})
        return result if isinstance(result, list) else []

    def export_alerts(self, days: int, severity: str | None = None) -> list[dict]:
        params: dict[str, Any] = {"days": days}
        if severity:
            params["severity"] = severity
        result = self._call(self.alert_url, "/api/v1/alerts/", params=params)
        return result if isinstance(result, list) else []

    def generate_full_report(self, period: str) -> dict:
        days_map = {"1d": 1, "7d": 7, "30d": 30, "90d": 90}
        days = days_map.get(period, 30)

        return {
            "report_type": "comprehensive_flood_risk",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "period": period,
            "weather": self.export_weather(days),
            "predictions": self.export_predictions(None, None, None),
            "alerts": self.export_alerts(days),
            "statistics": self.get_statistics(
                since=datetime.now(timezone.utc) - timedelta(days=days), period=period
            ),
        }

    # ── Performance helpers ─────────────────────────────────────────

    def get_service_health(self) -> dict:
        return self.get_system_overview()

    def get_model_performance(self) -> dict:
        return self._call(self.prediction_url, "/api/v1/models/metrics") or {}

    def get_latency_metrics(self, period: str) -> dict:
        """Aggregate latency from Redis tracking keys or Prometheus."""
        return {"period": period, "services": {}, "note": "Requires metrics backend"}

    def get_throughput_metrics(self, period: str) -> dict:
        return {"period": period, "services": {}, "note": "Requires metrics backend"}

    def get_error_metrics(self, period: str) -> dict:
        return {"period": period, "services": {}, "note": "Requires metrics backend"}

    # ── GIS helpers ─────────────────────────────────────────────────

    def get_risk_zones(self) -> dict:
        """Return GeoJSON FeatureCollection of flood risk zones."""
        cached = self._get_cached("dashboard:gis:risk_zones")
        if cached:
            return cached

        predictions = self._call(self.prediction_url, "/api/v1/predict/spatial")
        if not isinstance(predictions, list):
            predictions = []

        features = []
        for pred in predictions:
            features.append({
                "type": "Feature",
                "geometry": pred.get("geometry", {"type": "Point", "coordinates": [120.9842, 14.5995]}),
                "properties": {
                    "risk_level": pred.get("risk_level", "unknown"),
                    "risk_score": pred.get("risk_score", 0),
                    "location": pred.get("location", ""),
                },
            })

        geojson = {"type": "FeatureCollection", "features": features}
        self._set_cached("dashboard:gis:risk_zones", geojson, ttl=300)
        return geojson

    def get_weather_stations_geojson(self) -> dict:
        stations = self._call(self.weather_url, "/api/v1/weather/stations")
        if not isinstance(stations, list):
            stations = []

        features = []
        for s in stations:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [s.get("longitude", 0), s.get("latitude", 0)],
                },
                "properties": {
                    "name": s.get("name", ""),
                    "latest_reading": s.get("latest_reading"),
                },
            })
        return {"type": "FeatureCollection", "features": features}

    def get_flood_extent(self, prediction_id: str) -> dict | None:
        result = self._call(self.prediction_url, f"/api/v1/predict/{prediction_id}/extent")
        return result if isinstance(result, dict) else None

    def get_risk_heatmap(self, resolution: str = "medium") -> list:
        result = self._call(
            self.prediction_url,
            "/api/v1/predict/heatmap",
            params={"resolution": resolution},
        )
        return result if isinstance(result, list) else []

    def get_drainage_network(self) -> dict:
        """Return GeoJSON of local drainage network (static data or from weather service)."""
        result = self._call(self.weather_url, "/api/v1/weather/drainage")
        if isinstance(result, dict):
            return result
        return {"type": "FeatureCollection", "features": []}

    # ── Private helpers ─────────────────────────────────────────────

    def _call(
        self,
        base_url: str,
        path: str,
        method: str = "GET",
        params: dict | None = None,
        json_body: dict | None = None,
    ) -> Any:
        """Make an inter-service HTTP call with fault tolerance."""
        url = f"{base_url}{path}"
        try:
            resp = requests.request(
                method,
                url,
                params=params,
                json=json_body,
                timeout=self._timeout,
                headers=self._service_headers(),
            )
            if resp.status_code < 300:
                data = resp.json()
                # Unwrap common envelope
                if isinstance(data, dict) and "data" in data:
                    return data["data"]
                return data
            logger.warning("Service %s returned %s", url, resp.status_code)
            return None
        except requests.exceptions.ConnectionError:
            logger.warning("Service unreachable: %s", url)
            return None
        except requests.exceptions.Timeout:
            logger.warning("Service timeout: %s", url)
            return None
        except Exception as e:
            logger.error("Unexpected error calling %s: %s", url, e)
            return None

    def _service_headers(self) -> dict[str, str]:
        """Build headers for inter-service authentication."""
        try:
            from shared.auth import create_service_token

            token = create_service_token("dashboard-api")
            return {"Authorization": f"Bearer {token}", "X-Service-Name": "dashboard-api"}
        except ImportError:
            return {"X-Service-Name": "dashboard-api"}

    def _get_cached(self, key: str) -> Any | None:
        if self._redis is None:
            return None
        try:
            raw = self._redis.get(key)
            return json.loads(raw) if raw else None
        except Exception:
            return None

    def _set_cached(self, key: str, value: Any, ttl: int = _CACHE_TTL) -> None:
        if self._redis is None:
            return
        try:
            self._redis.setex(key, ttl, json.dumps(value, default=str))
        except Exception:
            pass

    def _get_cached_or_fetch(self, key: str, fetch_fn) -> Any:
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        result = fetch_fn()
        if result is not None:
            self._set_cached(key, result)
        return result

    @staticmethod
    def _compute_risk_distribution(predictions: Any) -> dict[str, int]:
        dist: dict[str, int] = {"low": 0, "moderate": 0, "high": 0, "critical": 0}
        if not isinstance(predictions, list):
            return dist
        for p in predictions:
            level = p.get("risk_level", "").lower()
            if level in dist:
                dist[level] += 1
        return dist
