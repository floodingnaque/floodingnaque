"""
Dashboard API Routes.

Provides aggregated statistics and summary endpoints for frontend dashboard.
"""

import logging
from datetime import datetime, timedelta, timezone

from app.api.middleware.rate_limit import limiter
from app.models.db import (
    AlertHistory,
    Prediction,
    WeatherData,
    get_db_session,
)
from app.utils.api_constants import HTTP_BAD_REQUEST, HTTP_INTERNAL_ERROR, HTTP_OK
from app.utils.api_responses import api_error
from app.utils.resilience.cache import cached
from flask import Blueprint, g, jsonify, request
from sqlalchemy import case, desc, func

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/summary", methods=["GET"])
@dashboard_bp.route("/stats", methods=["GET"])  # Alias for frontend compatibility
@limiter.limit("60 per minute")
def get_dashboard_summary():
    """
    Get aggregated dashboard summary statistics.

    Returns comprehensive stats for:
    - Total predictions made
    - Total alerts sent
    - Weather data points
    - Risk distribution
    - Recent activity

    Returns:
        200: Dashboard summary data
    ---
    tags:
      - Dashboard
    responses:
      200:
        description: Dashboard summary statistics
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        summary = _fetch_dashboard_summary()

        return (
            jsonify(
                {
                    "success": True,
                    "summary": summary,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Error fetching dashboard summary [{request_id}]: {str(e)}", exc_info=True)
        return api_error("FetchFailed", "Failed to fetch dashboard summary", HTTP_INTERNAL_ERROR, request_id)


@cached("dashboard:summary", ttl=300)
def _fetch_dashboard_summary() -> dict:
    """Fetch and return dashboard summary data (cached for 60s)."""
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    with get_db_session() as session:
        # --- Single aggregation query for WeatherData + Prediction counts ---
        weather_row = (
            session.query(
                func.count(WeatherData.id).label("total"),
                func.count(case((WeatherData.created_at >= today, 1))).label("today"),
            )
            .filter(WeatherData.is_deleted.is_(False))
            .one()
        )

        pred_row = (
            session.query(
                func.count(Prediction.id).label("total"),
                func.count(case((Prediction.created_at >= today, 1))).label("today"),
                func.count(case((Prediction.created_at >= week_ago, 1))).label("week"),
            )
            .filter(Prediction.is_deleted.is_(False))
            .one()
        )

        alert_row = (
            session.query(
                func.count(AlertHistory.id).label("total"),
                func.count(case((AlertHistory.created_at >= today, 1))).label("today"),
                func.count(
                    case(
                        (
                            (AlertHistory.risk_level == 2) & (AlertHistory.created_at >= now - timedelta(hours=24)),
                            1,
                        )
                    )
                ).label("critical_24h"),
            )
            .filter(AlertHistory.is_deleted.is_(False))
            .one()
        )

        # Risk level distribution (last 30 days) — kept as GROUP BY
        risk_distribution = (
            session.query(Prediction.risk_level, func.count(Prediction.id))
            .filter(Prediction.is_deleted.is_(False), Prediction.created_at >= month_ago)
            .group_by(Prediction.risk_level)
            .all()
        )

        risk_stats = {"safe": 0, "alert": 0, "critical": 0}
        for level, count in risk_distribution:
            if level == 0:
                risk_stats["safe"] = count
            elif level == 1:
                risk_stats["alert"] = count
            elif level == 2:
                risk_stats["critical"] = count

        # Latest weather data
        latest_weather = (
            session.query(WeatherData)
            .filter(WeatherData.is_deleted.is_(False))
            .order_by(desc(WeatherData.timestamp))
            .limit(1)
            .first()
        )

        latest_weather_data = None
        if latest_weather:
            latest_weather_data = {
                "temperature": latest_weather.temperature,
                "humidity": latest_weather.humidity,
                "precipitation": latest_weather.precipitation,
                "timestamp": latest_weather.timestamp.isoformat() if latest_weather.timestamp else None,
            }

        # Latest prediction
        latest_prediction = (
            session.query(Prediction)
            .filter(Prediction.is_deleted.is_(False))
            .order_by(desc(Prediction.created_at))
            .limit(1)
            .first()
        )

        latest_prediction_data = None
        if latest_prediction:
            latest_prediction_data = {
                "prediction": latest_prediction.prediction,
                "risk_level": latest_prediction.risk_level,
                "risk_label": latest_prediction.risk_label,
                "confidence": latest_prediction.confidence,
                "created_at": latest_prediction.created_at.isoformat() if latest_prediction.created_at else None,
            }

    return {
        "weather_data": {
            "total": weather_row.total,
            "today": weather_row.today,
            "latest": latest_weather_data,
        },
        "predictions": {
            "total": pred_row.total,
            "today": pred_row.today,
            "this_week": pred_row.week,
            "latest": latest_prediction_data,
        },
        "alerts": {
            "total": alert_row.total,
            "today": alert_row.today,
            "critical_24h": alert_row.critical_24h,
        },
        "risk_distribution_30d": risk_stats,
    }


@dashboard_bp.route("/statistics", methods=["GET"])
@limiter.limit("30 per minute")
def get_statistics():
    """
    Get detailed statistics for charts and graphs.

    Query Parameters:
        period (str): Time period - 'day', 'week', 'month' (default: 'week')
        metric (str): Metric type - 'predictions', 'alerts', 'weather' (default: all)

    Returns:
        200: Time-series statistics data
    ---
    tags:
      - Dashboard
    parameters:
      - in: query
        name: period
        type: string
        enum: [day, week, month]
        default: week
      - in: query
        name: metric
        type: string
        enum: [predictions, alerts, weather]
    responses:
      200:
        description: Statistics data for charts
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        period = request.args.get("period", "week")
        metric = request.args.get("metric")

        valid_periods = ["day", "week", "month"]
        if period not in valid_periods:
            return api_error("ValidationError", f"Period must be one of: {valid_periods}", HTTP_BAD_REQUEST, request_id)

        result = _fetch_statistics(period, metric)
        result["success"] = True
        result["request_id"] = request_id

        return jsonify(result), HTTP_OK

    except Exception as e:
        logger.error(f"Error fetching statistics [{request_id}]: {str(e)}", exc_info=True)
        return api_error("FetchFailed", "Failed to fetch statistics", HTTP_INTERNAL_ERROR, request_id)


@cached(
    "dashboard:statistics",
    ttl=300,
    key_builder=lambda period, metric: f"dashboard:statistics:{period}:{metric or 'all'}",
)
def _fetch_statistics(period: str, metric: str | None) -> dict:
    """Fetch statistics using SQL aggregation (cached for 5 minutes)."""
    now = datetime.now(timezone.utc)

    if period == "day":
        start_date = now - timedelta(hours=24)
        date_fmt = "YYYY-MM-DD HH24:00"
    elif period == "week":
        start_date = now - timedelta(days=7)
        date_fmt = "YYYY-MM-DD"
    else:  # month
        start_date = now - timedelta(days=30)
        date_fmt = "YYYY-MM-DD"

    result = {
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": now.isoformat(),
    }

    with get_db_session() as session:
        # Prediction statistics — SQL GROUP BY
        if not metric or metric == "predictions":
            pred_groups = (
                session.query(
                    func.to_char(Prediction.created_at, date_fmt).label("date_key"),
                    func.count(Prediction.id).label("count"),
                    func.count(case((Prediction.prediction == 1, 1))).label("flood"),
                    func.count(case((Prediction.risk_level == 0, 1))).label("safe"),
                    func.count(case((Prediction.risk_level == 1, 1))).label("alert"),
                    func.count(case((Prediction.risk_level == 2, 1))).label("critical"),
                )
                .filter(Prediction.is_deleted.is_(False), Prediction.created_at >= start_date)
                .group_by(func.to_char(Prediction.created_at, date_fmt))
                .order_by(func.to_char(Prediction.created_at, date_fmt))
                .all()
            )

            pred_by_date = {}
            total = 0
            flood_count = 0
            for row in pred_groups:
                pred_by_date[row.date_key] = {
                    "count": row.count,
                    "flood": row.flood,
                    "safe": row.safe,
                    "alert": row.alert,
                    "critical": row.critical,
                }
                total += row.count
                flood_count += row.flood

            # Risk timeline — last 50 data points only
            risk_over_time_rows = (
                session.query(
                    Prediction.created_at,
                    Prediction.risk_level,
                    Prediction.confidence,
                )
                .filter(Prediction.is_deleted.is_(False), Prediction.created_at >= start_date)
                .order_by(desc(Prediction.created_at))
                .limit(50)
                .all()
            )

            risk_over_time = [
                {
                    "timestamp": row.created_at.isoformat(),
                    "risk_level": row.risk_level,
                    "confidence": row.confidence,
                }
                for row in reversed(risk_over_time_rows)
            ]

            result["predictions"] = {
                "by_date": pred_by_date,
                "total": total,
                "flood_count": flood_count,
                "risk_timeline": risk_over_time,
            }

        # Alert statistics — SQL GROUP BY
        if not metric or metric == "alerts":
            alert_groups = (
                session.query(
                    func.to_char(AlertHistory.created_at, date_fmt).label("date_key"),
                    func.count(AlertHistory.id).label("count"),
                    func.count(case((AlertHistory.risk_level == 2, 1))).label("critical"),
                    func.count(case((AlertHistory.delivery_status == "delivered", 1))).label("delivered"),
                )
                .filter(AlertHistory.is_deleted.is_(False), AlertHistory.created_at >= start_date)
                .group_by(func.to_char(AlertHistory.created_at, date_fmt))
                .order_by(func.to_char(AlertHistory.created_at, date_fmt))
                .all()
            )

            alerts_by_date = {}
            alert_total = 0
            critical_count = 0
            for row in alert_groups:
                alerts_by_date[row.date_key] = {
                    "count": row.count,
                    "critical": row.critical,
                    "delivered": row.delivered,
                }
                alert_total += row.count
                critical_count += row.critical

            result["alerts"] = {
                "by_date": alerts_by_date,
                "total": alert_total,
                "critical_count": critical_count,
            }

        # Weather statistics — SQL aggregation + limited timeline query
        if not metric or metric == "weather":
            weather_agg = (
                session.query(
                    func.count(WeatherData.id).label("total"),
                    func.avg(WeatherData.temperature).label("avg_temp"),
                    func.avg(WeatherData.humidity).label("avg_humidity"),
                    func.coalesce(func.sum(WeatherData.precipitation), 0).label("total_precip"),
                )
                .filter(WeatherData.is_deleted.is_(False), WeatherData.timestamp >= start_date)
                .one()
            )

            weather_rows = (
                session.query(
                    WeatherData.timestamp,
                    WeatherData.temperature,
                    WeatherData.humidity,
                    WeatherData.precipitation,
                )
                .filter(WeatherData.is_deleted.is_(False), WeatherData.timestamp >= start_date)
                .order_by(desc(WeatherData.timestamp))
                .limit(100)
                .all()
            )

            weather_timeline = [
                {
                    "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                    "temperature": row.temperature,
                    "humidity": row.humidity,
                    "precipitation": row.precipitation,
                }
                for row in reversed(weather_rows)
            ]

            result["weather"] = {
                "total_data_points": weather_agg.total,
                "timeline": weather_timeline,
                "avg_temperature": float(weather_agg.avg_temp) if weather_agg.avg_temp else None,
                "avg_humidity": float(weather_agg.avg_humidity) if weather_agg.avg_humidity else None,
                "total_precipitation": float(weather_agg.total_precip),
            }

    return result


@dashboard_bp.route("/activity", methods=["GET"])
@limiter.limit("60 per minute")
def get_recent_activity():
    """
    Get recent system activity for activity feed.

    Query Parameters:
        limit (int): Maximum items to return (default: 20, max: 100)

    Returns:
        200: Recent activity items
    ---
    tags:
      - Dashboard
    parameters:
      - in: query
        name: limit
        type: integer
        default: 20
    responses:
      200:
        description: Recent activity feed
    """
    request_id = getattr(g, "request_id", "unknown")

    try:
        limit = min(request.args.get("limit", 20, type=int), 100)

        with get_db_session() as session:
            # Get recent predictions
            predictions = (
                session.query(Prediction)
                .filter(Prediction.is_deleted.is_(False))
                .order_by(desc(Prediction.created_at))
                .limit(limit // 2)
                .all()
            )

            # Get recent alerts
            alerts = (
                session.query(AlertHistory)
                .filter(AlertHistory.is_deleted.is_(False))
                .order_by(desc(AlertHistory.created_at))
                .limit(limit // 2)
                .all()
            )

            # Combine and sort by timestamp
            activity = []

            for pred in predictions:
                activity.append(
                    {
                        "type": "prediction",
                        "timestamp": pred.created_at.isoformat() if pred.created_at else None,
                        "data": {
                            "id": pred.id,
                            "prediction": pred.prediction,
                            "risk_level": pred.risk_level,
                            "risk_label": pred.risk_label,
                        },
                    }
                )

            for alert in alerts:
                activity.append(
                    {
                        "type": "alert",
                        "timestamp": alert.created_at.isoformat() if alert.created_at else None,
                        "data": {
                            "id": alert.id,
                            "risk_level": alert.risk_level,
                            "risk_label": alert.risk_label,
                            "location": alert.location,
                            "delivery_status": alert.delivery_status,
                        },
                    }
                )

            # Sort by timestamp
            activity.sort(key=lambda x: x["timestamp"] or "", reverse=True)
            activity = activity[:limit]

        return (
            jsonify({"success": True, "activity": activity, "count": len(activity), "request_id": request_id}),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Error fetching activity [{request_id}]: {str(e)}", exc_info=True)
        return api_error("FetchFailed", "Failed to fetch activity", HTTP_INTERNAL_ERROR, request_id)
