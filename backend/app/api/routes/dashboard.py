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
from flask import Blueprint, g, jsonify, request
from sqlalchemy import desc, func

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
        now = datetime.now(timezone.utc)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        with get_db_session() as session:
            # Weather data stats
            total_weather_data = session.query(WeatherData).filter(WeatherData.is_deleted == False).count()

            weather_today = (
                session.query(WeatherData)
                .filter(WeatherData.is_deleted == False, WeatherData.created_at >= today)
                .count()
            )

            # Prediction stats
            total_predictions = session.query(Prediction).filter(Prediction.is_deleted == False).count()

            predictions_today = (
                session.query(Prediction).filter(Prediction.is_deleted == False, Prediction.created_at >= today).count()
            )

            predictions_week = (
                session.query(Prediction)
                .filter(Prediction.is_deleted == False, Prediction.created_at >= week_ago)
                .count()
            )

            # Risk level distribution (last 30 days)
            risk_distribution = (
                session.query(Prediction.risk_level, func.count(Prediction.id))
                .filter(Prediction.is_deleted == False, Prediction.created_at >= month_ago)
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

            # Alert stats
            total_alerts = session.query(AlertHistory).filter(AlertHistory.is_deleted == False).count()

            alerts_today = (
                session.query(AlertHistory)
                .filter(AlertHistory.is_deleted == False, AlertHistory.created_at >= today)
                .count()
            )

            critical_alerts_24h = (
                session.query(AlertHistory)
                .filter(
                    AlertHistory.is_deleted == False,
                    AlertHistory.risk_level == 2,
                    AlertHistory.created_at >= now - timedelta(hours=24),
                )
                .count()
            )

            # Latest weather data
            latest_weather = (
                session.query(WeatherData)
                .filter(WeatherData.is_deleted == False)
                .order_by(desc(WeatherData.timestamp))
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
                .filter(Prediction.is_deleted == False)
                .order_by(desc(Prediction.created_at))
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

        return (
            jsonify(
                {
                    "success": True,
                    "summary": {
                        "weather_data": {
                            "total": total_weather_data,
                            "today": weather_today,
                            "latest": latest_weather_data,
                        },
                        "predictions": {
                            "total": total_predictions,
                            "today": predictions_today,
                            "this_week": predictions_week,
                            "latest": latest_prediction_data,
                        },
                        "alerts": {
                            "total": total_alerts,
                            "today": alerts_today,
                            "critical_24h": critical_alerts_24h,
                        },
                        "risk_distribution_30d": risk_stats,
                    },
                    "generated_at": now.isoformat(),
                    "request_id": request_id,
                }
            ),
            HTTP_OK,
        )

    except Exception as e:
        logger.error(f"Error fetching dashboard summary [{request_id}]: {str(e)}", exc_info=True)
        return api_error("FetchFailed", "Failed to fetch dashboard summary", HTTP_INTERNAL_ERROR, request_id)


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

        now = datetime.now(timezone.utc)

        if period == "day":
            start_date = now - timedelta(hours=24)
            interval = "hour"
        elif period == "week":
            start_date = now - timedelta(days=7)
            interval = "day"
        else:  # month
            start_date = now - timedelta(days=30)
            interval = "day"

        result = {
            "period": period,
            "start_date": start_date.isoformat(),
            "end_date": now.isoformat(),
        }

        with get_db_session() as session:
            # Prediction statistics
            if not metric or metric == "predictions":
                predictions = (
                    session.query(Prediction)
                    .filter(Prediction.is_deleted == False, Prediction.created_at >= start_date)
                    .order_by(Prediction.created_at)
                    .all()
                )

                # Group by date
                pred_by_date = {}
                risk_over_time = []
                for pred in predictions:
                    if period == "day":
                        key = pred.created_at.strftime("%Y-%m-%d %H:00")
                    else:
                        key = pred.created_at.strftime("%Y-%m-%d")

                    if key not in pred_by_date:
                        pred_by_date[key] = {"count": 0, "flood": 0, "safe": 0, "alert": 0, "critical": 0}
                    pred_by_date[key]["count"] += 1
                    if pred.prediction == 1:
                        pred_by_date[key]["flood"] += 1
                    if pred.risk_level == 0:
                        pred_by_date[key]["safe"] += 1
                    elif pred.risk_level == 1:
                        pred_by_date[key]["alert"] += 1
                    elif pred.risk_level == 2:
                        pred_by_date[key]["critical"] += 1

                    risk_over_time.append(
                        {
                            "timestamp": pred.created_at.isoformat(),
                            "risk_level": pred.risk_level,
                            "confidence": pred.confidence,
                        }
                    )

                result["predictions"] = {
                    "by_date": pred_by_date,
                    "total": len(predictions),
                    "flood_count": sum(p.prediction == 1 for p in predictions),
                    "risk_timeline": risk_over_time[-50:] if len(risk_over_time) > 50 else risk_over_time,
                }

            # Alert statistics
            if not metric or metric == "alerts":
                alerts = (
                    session.query(AlertHistory)
                    .filter(AlertHistory.is_deleted == False, AlertHistory.created_at >= start_date)
                    .order_by(AlertHistory.created_at)
                    .all()
                )

                alerts_by_date = {}
                for alert in alerts:
                    if period == "day":
                        key = alert.created_at.strftime("%Y-%m-%d %H:00")
                    else:
                        key = alert.created_at.strftime("%Y-%m-%d")

                    if key not in alerts_by_date:
                        alerts_by_date[key] = {"count": 0, "critical": 0, "delivered": 0}
                    alerts_by_date[key]["count"] += 1
                    if alert.risk_level == 2:
                        alerts_by_date[key]["critical"] += 1
                    if alert.delivery_status == "delivered":
                        alerts_by_date[key]["delivered"] += 1

                result["alerts"] = {
                    "by_date": alerts_by_date,
                    "total": len(alerts),
                    "critical_count": sum(a.risk_level == 2 for a in alerts),
                }

            # Weather statistics
            if not metric or metric == "weather":
                weather_data = (
                    session.query(WeatherData)
                    .filter(WeatherData.is_deleted == False, WeatherData.timestamp >= start_date)
                    .order_by(WeatherData.timestamp)
                    .all()
                )

                weather_timeline = []
                for w in weather_data[-100:]:  # Last 100 data points
                    weather_timeline.append(
                        {
                            "timestamp": w.timestamp.isoformat() if w.timestamp else None,
                            "temperature": w.temperature,
                            "humidity": w.humidity,
                            "precipitation": w.precipitation,
                        }
                    )

                result["weather"] = {
                    "total_data_points": len(weather_data),
                    "timeline": weather_timeline,
                    "avg_temperature": (
                        sum(w.temperature for w in weather_data) / len(weather_data) if weather_data else None
                    ),
                    "avg_humidity": sum(w.humidity for w in weather_data) / len(weather_data) if weather_data else None,
                    "total_precipitation": (
                        sum(w.precipitation for w in weather_data if w.precipitation) if weather_data else 0
                    ),
                }

        result["success"] = True
        result["request_id"] = request_id

        return jsonify(result), HTTP_OK

    except Exception as e:
        logger.error(f"Error fetching statistics [{request_id}]: {str(e)}", exc_info=True)
        return api_error("FetchFailed", "Failed to fetch statistics", HTTP_INTERNAL_ERROR, request_id)


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
                .filter(Prediction.is_deleted == False)
                .order_by(desc(Prediction.created_at))
                .limit(limit // 2)
                .all()
            )

            # Get recent alerts
            alerts = (
                session.query(AlertHistory)
                .filter(AlertHistory.is_deleted == False)
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
