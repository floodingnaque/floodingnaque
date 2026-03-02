"""Business logic services (weather, prediction, alerts, scheduling).

This module provides comprehensive service layer functionality:
- Weather data ingestion and processing
- Flood prediction and risk classification
- Alert generation and delivery
- Background task scheduling
- External API integrations (Meteostat, WorldTides, Google Earth Engine)
- Async versions of external API services with connection pooling and retry logic
- Multi-source data aggregation with fallback logic and reliability scoring
- PAGASA rainfall bulletins and severe weather advisories
- MMDA flood advisory and station monitoring
- Manila Bay tide level analysis with harmonic prediction
- River water-level monitoring (Parañaque River system)
"""

# Scheduler for periodic tasks
from app.services import scheduler

# Alert system
from app.services.alerts import AlertSystem, get_alert_system, send_flood_alert

# Celery background tasks
from app.services.celery_app import celery_app

# Data Aggregation Service (multi-source orchestrator)
from app.services.data_aggregation_service import (
    DataAggregationService,
    get_aggregation_service,
)

# System evaluation for thesis validation
from app.services.evaluation import SystemEvaluator

# Google Weather/Earth Engine service (synchronous)
from app.services.google_weather_service import GoogleWeatherService

# Google Weather/Earth Engine service (async with retry logic)
from app.services.google_weather_service_async import (
    AsyncGoogleWeatherService,
    get_async_google_weather_service,
    get_google_weather_for_ingest_async,
    get_satellite_precipitation_async,
)

# Google Weather/Earth Engine data types (shared)
from app.services.google_weather_types import SatellitePrecipitation, WeatherReanalysis

# Core prediction and ingestion services
from app.services.ingest import ingest_data

# Manila Bay Tide Service (harmonic prediction + multi-source)
from app.services.manila_bay_tide_service import (
    ManilaBayTideService,
    get_manila_bay_tide_service,
)

# Meteostat weather service (synchronous)
from app.services.meteostat_service import (
    MeteostatService,
    get_historical_weather,
    get_meteostat_service,
    get_meteostat_weather_for_ingest,
    save_meteostat_data_to_db,
)

# Meteostat weather service (async with retry logic)
from app.services.meteostat_service_async import (
    AsyncMeteostatService,
    get_async_meteostat_service,
    get_historical_weather_async,
    get_meteostat_weather_for_ingest_async,
    save_meteostat_data_to_db_async,
)

# Meteostat data types (shared)
from app.services.meteostat_types import WeatherObservation

# MMDA Flood Advisory Service
from app.services.mmda_flood_service import (
    MMDAFloodService,
    get_mmda_flood_service,
)

# PAGASA Rainfall Bulletin Service
from app.services.pagasa_bulletin_service import (
    PAGASARainfallBulletinService,
    get_pagasa_bulletin_service,
)

from app.services.predict import ModelLoader, get_current_model_info, predict_flood

# Risk classification
from app.services.risk_classifier import (
    RISK_LEVEL_COLORS,
    RISK_LEVEL_DESCRIPTIONS,
    RISK_LEVELS,
    classify_risk_level,
    format_alert_message,
    get_risk_thresholds,
)

# River Water-Level Monitoring Service
from app.services.river_water_level_service import (
    RiverWaterLevelService,
    get_river_water_level_service,
)

# Smart Alert Evaluator
from app.services.smart_alert_evaluator import (
    SmartAlertDecision,
    SmartAlertEvaluator,
    evaluate_smart_alert,
    get_smart_evaluator,
)

# WorldTides service for coastal flood prediction (synchronous)
from app.services.worldtides_service import WorldTidesService

# WorldTides service (async with aiohttp, connection pooling, and retry logic)
from app.services.worldtides_service_async import (
    AsyncWorldTidesService,
    get_async_worldtides_service,
    get_current_tide_async,
    get_tide_extremes_async,
    get_tide_for_prediction_async,
)

# WorldTides data types (shared)
from app.services.worldtides_types import TideData, TideExtreme

__all__ = [
    # Core services
    "ingest_data",
    "predict_flood",
    "get_current_model_info",
    "ModelLoader",
    # Alert system
    "AlertSystem",
    "get_alert_system",
    "send_flood_alert",
    # Data Aggregation Service
    "DataAggregationService",
    "get_aggregation_service",
    # PAGASA Rainfall Bulletin Service
    "PAGASARainfallBulletinService",
    "get_pagasa_bulletin_service",
    # MMDA Flood Advisory Service
    "MMDAFloodService",
    "get_mmda_flood_service",
    # Manila Bay Tide Service
    "ManilaBayTideService",
    "get_manila_bay_tide_service",
    # River Water-Level Service
    "RiverWaterLevelService",
    "get_river_water_level_service",
    # Meteostat service
    "MeteostatService",
    "WeatherObservation",
    "get_meteostat_service",
    "get_historical_weather",
    "get_meteostat_weather_for_ingest",
    "save_meteostat_data_to_db",
    # Meteostat service (async)
    "AsyncMeteostatService",
    "get_async_meteostat_service",
    "get_historical_weather_async",
    "get_meteostat_weather_for_ingest_async",
    "save_meteostat_data_to_db_async",
    # WorldTides service
    "WorldTidesService",
    "TideData",
    "TideExtreme",
    # WorldTides service (async)
    "AsyncWorldTidesService",
    "get_async_worldtides_service",
    "get_current_tide_async",
    "get_tide_for_prediction_async",
    "get_tide_extremes_async",
    # Google Weather service
    "GoogleWeatherService",
    "SatellitePrecipitation",
    "WeatherReanalysis",
    # Google Weather service (async)
    "AsyncGoogleWeatherService",
    "get_async_google_weather_service",
    "get_satellite_precipitation_async",
    "get_google_weather_for_ingest_async",
    # Celery
    "celery_app",
    # Scheduler
    "scheduler",
    # Evaluation
    "SystemEvaluator",
    # Risk classification
    "classify_risk_level",
    "get_risk_thresholds",
    "format_alert_message",
    "RISK_LEVELS",
    "RISK_LEVEL_COLORS",
    "RISK_LEVEL_DESCRIPTIONS",
    # Smart Alert Evaluator
    "SmartAlertEvaluator",
    "SmartAlertDecision",
    "evaluate_smart_alert",
    "get_smart_evaluator",
]
