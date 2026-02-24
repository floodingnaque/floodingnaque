import logging
import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.orm import declarative_base, relationship, scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool

logger = logging.getLogger(__name__)

# Pool connection metrics
pool_metrics = {
    "checkouts": 0,
    "checkins": 0,
    "invalidated": 0,
    "last_checkout_time": None,
    "connection_errors": 0,
    "pool_exhausted_count": 0,
    "avg_checkout_time_ms": 0.0,
    "total_checkout_time_ms": 0.0,
}


# SQLAlchemy 1.4/2.0 compatible declarative base
Base = declarative_base()

# Enhanced database configuration with Supabase support
# Note: The actual DATABASE_URL is validated in app.core.config._get_database_url()
# Development allows SQLite fallback; Production/Staging require Supabase PostgreSQL
DB_URL = os.getenv("DATABASE_URL")

if not DB_URL:
    # Only for initial module load before config is loaded - will be overridden
    app_env = os.getenv("APP_ENV", "development").lower()
    if app_env in ("production", "prod", "staging", "stage"):
        raise ValueError(
            f"DATABASE_URL must be set for {app_env}! " "Configure a Supabase PostgreSQL connection string."
        )
    DB_URL = "sqlite:///data/floodingnaque.db"
    logger.warning("DATABASE_URL not set - using SQLite for development only")


# Supabase-specific: Handle connection string format
# Auto-select the best PostgreSQL driver based on platform:
# - Linux/Docker: Use psycopg2 (faster C-based driver)
# - Windows: Use pg8000 (pure Python, no compilation needed)
def _get_pg_driver():
    """Determine the best PostgreSQL driver for the current platform."""
    if sys.platform == "win32":
        return "pg8000"
    # On Linux/Docker, prefer psycopg2 if available
    try:
        pass

        return "psycopg2"
    except ImportError:
        return "pg8000"


pg_driver = _get_pg_driver()
logger.info(f"Using PostgreSQL driver: {pg_driver}")

# Handle SSL mode for pg8000 (doesn't accept sslmode in URL like psycopg2)
# Extract sslmode from URL and configure via connect_args for pg8000
# Also support environment-based SSL configuration via DB_SSL_MODE and DB_SSL_CA_CERT
ssl_context = None

# Get SSL configuration from environment
db_ssl_mode = os.getenv("DB_SSL_MODE", "").lower()
db_ssl_ca_cert = os.getenv("DB_SSL_CA_CERT", "")

# Determine app environment for default SSL mode
app_env = os.getenv("APP_ENV", "development").lower()
if not db_ssl_mode:
    # Default: verify-full for production/staging, require for development
    if app_env in ("production", "prod", "staging", "stage"):
        db_ssl_mode = "verify-full"
    else:
        db_ssl_mode = "require"

if pg_driver == "pg8000":
    import ssl

    # Remove sslmode from URL for pg8000 if present
    if "sslmode=" in DB_URL:
        import re

        sslmode_match = re.search(r"[?&]sslmode=([^&]*)", DB_URL)
        if sslmode_match:
            url_sslmode = sslmode_match.group(1).lower()
            # Use URL sslmode if DB_SSL_MODE not explicitly set
            if not os.getenv("DB_SSL_MODE"):
                db_ssl_mode = url_sslmode
            # Remove sslmode parameter from URL
            DB_URL = re.sub(r"[?&]sslmode=[^&]*", "", DB_URL)
            # Clean up URL if we left a dangling ? or &
            DB_URL = DB_URL.replace("?&", "?").rstrip("?")

    if db_ssl_mode in ("require", "verify-ca", "verify-full"):
        ssl_context = ssl.create_default_context()

        if db_ssl_mode == "require":
            # Encrypted connection, no certificate verification
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            logger.info("SSL mode 'require': Encrypted connection without certificate verification")

        elif db_ssl_mode in ("verify-ca", "verify-full"):
            # Full certificate verification
            ssl_context.verify_mode = ssl.CERT_REQUIRED

            if db_ssl_mode == "verify-full":
                ssl_context.check_hostname = True
                logger.info("SSL mode 'verify-full': Full certificate and hostname verification")
            else:
                ssl_context.check_hostname = False
                logger.info("SSL mode 'verify-ca': Certificate verification without hostname check")

            # Load CA certificate
            if db_ssl_ca_cert:
                import os.path

                if os.path.isfile(db_ssl_ca_cert):
                    ssl_context.load_verify_locations(db_ssl_ca_cert)
                    logger.info(f"Loaded CA certificate from: {db_ssl_ca_cert}")
                else:
                    error_msg = (
                        f"CRITICAL: SSL certificate file not found: {db_ssl_ca_cert}. "
                        f"SSL mode '{db_ssl_mode}' requires a valid CA certificate. "
                        "Set DB_SSL_CA_CERT to the path of your CA certificate file."
                    )
                    logger.error(error_msg)
                    # Fail fast in production/staging
                    if app_env in ("production", "prod", "staging", "stage"):
                        raise ValueError(error_msg)
                    else:
                        # Fall back to require mode in development
                        logger.warning("Falling back to SSL mode 'require' for development")
                        ssl_context.check_hostname = False
                        ssl_context.verify_mode = ssl.CERT_NONE
                        db_ssl_mode = "require"
            else:
                error_msg = (
                    f"CRITICAL: DB_SSL_CA_CERT not set but SSL mode is '{db_ssl_mode}'. "
                    "Certificate verification modes require DB_SSL_CA_CERT to be set."
                )
                logger.error(error_msg)
                # Fail fast in production/staging
                if app_env in ("production", "prod", "staging", "stage"):
                    raise ValueError(error_msg)
                else:
                    # Fall back to require mode in development
                    logger.warning("Falling back to SSL mode 'require' for development")
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                    db_ssl_mode = "require"

        logger.info(f"Configured SSL context for pg8000 (sslmode={db_ssl_mode})")

if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", f"postgresql+{pg_driver}://", 1)
elif DB_URL.startswith("postgresql://") and "+" not in DB_URL.split("://")[0]:
    DB_URL = DB_URL.replace("postgresql://", f"postgresql+{pg_driver}://", 1)

# Connection pool settings for better performance and reliability
# Get pool settings from environment (defaults match config.py)
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # 30 minutes for better connection freshness
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "True").lower() == "true"
DB_ECHO_POOL = os.getenv("DB_ECHO_POOL", "False").lower() == "true"

if DB_URL.startswith("sqlite"):
    # SQLite-specific settings
    engine = create_engine(
        DB_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # SQLite works best with StaticPool
        pool_pre_ping=True,  # Verify connections before using
    )
else:
    # PostgreSQL/Supabase settings
    # Use QueuePool for production with configurable settings
    is_supabase = "supabase" in DB_URL.lower()

    # Respect environment variables, but provide conservative defaults for Supabase free tier
    # Users can override these in .env for paid tiers
    if is_supabase and DB_POOL_SIZE == 20:  # Only use conservative defaults if user hasn't customized
        pool_size = 3  # Slightly higher for better concurrency
        max_overflow = 5  # Allow more overflow connections
        pool_recycle = 600  # 10 minutes for Supabase connections
        logger.info("Using optimized pool settings for Supabase (override with DB_POOL_SIZE in .env)")
    else:
        pool_size = DB_POOL_SIZE
        max_overflow = DB_MAX_OVERFLOW
        pool_recycle = DB_POOL_RECYCLE

    # Build engine with optimized connection pooling
    # Configure connect_args based on driver
    connect_args = {}
    if pg_driver == "pg8000" and ssl_context:
        connect_args["ssl_context"] = ssl_context

    engine = create_engine(
        DB_URL,
        echo=DB_ECHO_POOL,  # Log SQL statements when debugging
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_recycle=pool_recycle,
        pool_timeout=DB_POOL_TIMEOUT,
        pool_pre_ping=DB_POOL_PRE_PING,  # Health check before using connection
        poolclass=QueuePool,
        # Performance-oriented settings
        pool_use_lifo=True,  # LIFO reduces latency for connections
        pool_reset_on_return="rollback",  # Clean state on return
        connect_args=connect_args if connect_args else {},
    )

    logger.info(
        f"Database pool configured: size={pool_size}, overflow={max_overflow}, "
        f"recycle={pool_recycle}s, timeout={DB_POOL_TIMEOUT}s, pre_ping={DB_POOL_PRE_PING}"
    )

# Pool monitoring events for PostgreSQL/Supabase connections
if not DB_URL.startswith("sqlite"):

    @event.listens_for(engine, "checkout")
    def receive_checkout(dbapi_conn, connection_record, connection_proxy):
        """Track when a connection is checked out from the pool."""
        pool_metrics["checkouts"] += 1
        pool_metrics["last_checkout_time"] = time.time()
        connection_record.info["checkout_time"] = time.time()
        logger.debug(f"Connection checked out from pool (total: {pool_metrics['checkouts']})")

    @event.listens_for(engine, "checkin")
    def receive_checkin(dbapi_conn, connection_record):
        """Track when a connection is returned to the pool."""
        pool_metrics["checkins"] += 1
        checkout_time = connection_record.info.get("checkout_time")
        if checkout_time:
            duration_ms = (time.time() - checkout_time) * 1000
            pool_metrics["total_checkout_time_ms"] += duration_ms
            total_checkouts = pool_metrics["checkins"]
            if total_checkouts > 0:
                pool_metrics["avg_checkout_time_ms"] = pool_metrics["total_checkout_time_ms"] / total_checkouts
        logger.debug(f"Connection checked in to pool (total: {pool_metrics['checkins']})")

    @event.listens_for(engine, "invalidate")
    def receive_invalidate(dbapi_conn, connection_record, exception):
        """Track when a connection is invalidated."""
        pool_metrics["invalidated"] += 1
        if exception:
            pool_metrics["connection_errors"] += 1
            logger.warning(f"Connection invalidated due to: {exception}")
        else:
            logger.debug(f"Connection invalidated (total: {pool_metrics['invalidated']})")

    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_conn, connection_record):
        """Log new database connections."""
        logger.info("New database connection established")

    @event.listens_for(engine, "close")
    def receive_close(dbapi_conn, connection_record):
        """Log when a connection is closed."""
        logger.debug("Database connection closed")

    @event.listens_for(engine, "detach")
    def receive_detach(dbapi_conn, connection_record):
        """Log when a connection is detached from pool."""
        logger.debug("Connection detached from pool")


def get_pool_status():
    """Get current connection pool status and metrics."""
    if DB_URL.startswith("sqlite"):
        return {"status": "sqlite_static_pool", "metrics": None}

    pool = engine.pool

    # Calculate pool utilization percentage
    total_capacity = pool.size() + pool.overflow()
    active_connections = pool.checkedout()
    utilization_percent = (active_connections / max(total_capacity, 1)) * 100 if total_capacity > 0 else 0

    # Determine pool health status
    if utilization_percent >= 90:
        health_status = "critical"
    elif utilization_percent >= 75:
        health_status = "warning"
    else:
        health_status = "healthy"

    return {
        "pool_size": pool.size(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "checked_in": pool.checkedin(),
        "utilization_percent": round(utilization_percent, 2),
        "health_status": health_status,
        "metrics": {
            **pool_metrics,
            "avg_checkout_time_ms": round(pool_metrics.get("avg_checkout_time_ms", 0), 2),
        },
        "config": {
            "pool_size": DB_POOL_SIZE,
            "max_overflow": DB_MAX_OVERFLOW,
            "pool_recycle_seconds": DB_POOL_RECYCLE,
            "pool_timeout": DB_POOL_TIMEOUT,
            "pre_ping_enabled": DB_POOL_PRE_PING,
        },
    }


Session = sessionmaker(bind=engine)
# Use scoped_session for thread-safe session management
db_session = scoped_session(Session)


class WeatherData(Base):
    """Enhanced weather data model with validation and additional fields."""

    __tablename__ = "weather_data"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Weather measurements with validation constraints
    temperature = Column(Float, nullable=False, info={"description": "Temperature in Kelvin"})
    humidity = Column(Float, nullable=False, info={"description": "Humidity percentage (0-100)"})
    precipitation = Column(Float, nullable=False, info={"description": "Precipitation in mm"})

    # Additional weather parameters
    wind_speed = Column(Float, info={"description": "Wind speed in m/s"})
    pressure = Column(Float, info={"description": "Atmospheric pressure in hPa"})

    # Tide data (from WorldTides API)
    tide_height = Column(Float, info={"description": "Tide height in meters relative to datum"})
    tide_trend = Column(String(20), info={"description": "Tide trend: rising or falling"})
    tide_risk_factor = Column(Float, info={"description": "Tide risk factor 0-1 for flood prediction"})
    hours_until_high_tide = Column(Float, info={"description": "Hours until next high tide"})

    # Satellite precipitation data (from Google Earth Engine / GPM)
    satellite_precipitation_rate = Column(Float, info={"description": "Satellite precipitation rate in mm/hour"})
    precipitation_1h = Column(Float, info={"description": "Accumulated precipitation in last 1 hour (mm)"})
    precipitation_3h = Column(Float, info={"description": "Accumulated precipitation in last 3 hours (mm)"})
    precipitation_24h = Column(Float, info={"description": "Accumulated precipitation in last 24 hours (mm)"})
    data_quality = Column(Float, info={"description": "Data quality score 0-1"})
    dataset = Column(String(50), default="OWM", info={"description": "Dataset source: OWM, GPM, CHIRPS, ERA5"})

    # Location information
    location_lat = Column(Float, info={"description": "Latitude"})
    location_lon = Column(Float, info={"description": "Longitude"})

    # Metadata
    source = Column(
        String(50), default="OWM", info={"description": "Data source: OWM, Weatherstack, Meteostat, Manual"}
    )
    station_id = Column(String(50), nullable=True, info={"description": "Weather station ID (for Meteostat data)"})
    timestamp = Column(DateTime, nullable=False, index=True, info={"description": "Measurement timestamp"})
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        info={"description": "Record creation time"},
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        info={"description": "Last update time"},
    )

    # Relationships
    predictions = relationship("Prediction", back_populates="weather_data", cascade="all, delete-orphan")

    # Table constraints
    # Soft delete support
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("temperature >= 173.15 AND temperature <= 333.15", name="valid_temperature"),
        CheckConstraint("humidity >= 0 AND humidity <= 100", name="valid_humidity"),
        CheckConstraint("precipitation >= 0", name="valid_precipitation"),
        CheckConstraint("wind_speed IS NULL OR wind_speed >= 0", name="valid_wind_speed"),
        CheckConstraint("pressure IS NULL OR (pressure >= 870 AND pressure <= 1085)", name="valid_pressure"),
        CheckConstraint("location_lat IS NULL OR (location_lat >= -90 AND location_lat <= 90)", name="valid_latitude"),
        CheckConstraint(
            "location_lon IS NULL OR (location_lon >= -180 AND location_lon <= 180)", name="valid_longitude"
        ),
        CheckConstraint("data_quality IS NULL OR (data_quality >= 0 AND data_quality <= 1)", name="valid_data_quality"),
        Index("idx_weather_timestamp", "timestamp"),
        Index("idx_weather_location", "location_lat", "location_lon"),
        Index(
            "idx_weather_location_time", "location_lat", "location_lon", "timestamp"
        ),  # Composite index for common query patterns
        Index("idx_weather_created", "created_at"),
        Index("idx_weather_source", "source"),
        Index("idx_weather_active", "is_deleted"),  # Index for filtering active records
        # Performance optimization indexes
        Index("idx_weather_active_timestamp", "is_deleted", "timestamp"),  # Common filter: active records by time
        Index("idx_weather_active_created", "is_deleted", "created_at"),  # Common filter: active records by creation
        Index("idx_weather_source_timestamp", "source", "timestamp"),  # Filter by source and time
        {"comment": "Weather data measurements from various sources including Meteostat"},
    )

    def __repr__(self):
        return f"<WeatherData(id={self.id}, temp={self.temperature}, humidity={self.humidity}, precip={self.precipitation}, timestamp={self.timestamp})>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "precipitation": self.precipitation,
            "wind_speed": self.wind_speed,
            "pressure": self.pressure,
            "tide_height": self.tide_height,
            "tide_trend": self.tide_trend,
            "tide_risk_factor": self.tide_risk_factor,
            "hours_until_high_tide": self.hours_until_high_tide,
            "satellite_precipitation_rate": self.satellite_precipitation_rate,
            "precipitation_1h": self.precipitation_1h,
            "precipitation_3h": self.precipitation_3h,
            "precipitation_24h": self.precipitation_24h,
            "data_quality": self.data_quality,
            "dataset": self.dataset,
            "location_lat": self.location_lat,
            "location_lon": self.location_lon,
            "source": self.source,
            "station_id": self.station_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_deleted": self.is_deleted,
        }

    def soft_delete(self):
        """Mark record as deleted without removing from database."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self):
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None


class Prediction(Base):
    """Flood prediction records with audit trail."""

    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    weather_data_id = Column(Integer, ForeignKey("weather_data.id", ondelete="SET NULL"), index=True)

    # Prediction results
    prediction = Column(Integer, nullable=False, info={"description": "0=no flood, 1=flood"})
    risk_level = Column(Integer, info={"description": "0=Safe, 1=Alert, 2=Critical"})
    risk_label = Column(String(50), info={"description": "Safe/Alert/Critical"})
    confidence = Column(Float, info={"description": "Prediction confidence (0-1)"})

    # Model information
    model_version = Column(Integer, info={"description": "Model version used"})
    model_name = Column(String(100), default="flood_rf_model")

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    weather_data = relationship("WeatherData", back_populates="predictions")
    alerts = relationship("AlertHistory", back_populates="prediction", cascade="all, delete-orphan")

    # Soft delete support
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("prediction IN (0, 1)", name="valid_prediction"),
        CheckConstraint("risk_level IS NULL OR risk_level IN (0, 1, 2)", name="valid_risk_level"),
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="valid_confidence"),
        Index("idx_prediction_risk", "risk_level"),
        Index("idx_prediction_model", "model_version"),
        Index("idx_prediction_active", "is_deleted"),
        # Performance optimization indexes
        Index("idx_prediction_active_created", "is_deleted", "created_at"),  # Common filter: active by time
        Index("idx_prediction_risk_created", "risk_level", "created_at"),  # Filter by risk level and time
        Index("idx_prediction_active_risk", "is_deleted", "risk_level", "created_at"),  # Full filter combo
        {"comment": "Flood prediction history for analytics and audit"},
    )

    def __repr__(self):
        return f"<Prediction(id={self.id}, prediction={self.prediction}, risk={self.risk_label})>"

    def soft_delete(self):
        """Mark record as deleted without removing from database."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self):
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None


class AlertHistory(Base):
    """Alert delivery history and tracking."""

    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id", ondelete="CASCADE"), index=True)

    # Alert details
    risk_level = Column(Integer, nullable=False)
    risk_label = Column(String(50), nullable=False)
    location = Column(String(255), info={"description": "Location name"})
    recipients = Column(Text, info={"description": "JSON array of recipients"})
    message = Column(Text, info={"description": "Alert message content"})

    # Delivery tracking
    delivery_status = Column(String(50), info={"description": "delivered/failed/pending"})
    delivery_channel = Column(String(50), info={"description": "web/sms/email"})
    error_message = Column(Text, info={"description": "Error details if delivery failed"})

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    delivered_at = Column(DateTime, info={"description": "Actual delivery timestamp"})

    # Relationships
    prediction = relationship("Prediction", back_populates="alerts")

    # Soft delete support
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_alert_risk", "risk_level"),
        Index("idx_alert_status", "delivery_status"),
        Index("idx_alert_active", "is_deleted"),
        # Performance optimization indexes
        Index("idx_alert_active_created", "is_deleted", "created_at"),  # Active alerts by time
        Index("idx_alert_status_created", "delivery_status", "created_at"),  # Filter by status and time
        Index("idx_alert_risk_status", "risk_level", "delivery_status"),  # Filter by risk and status
        {"comment": "Alert delivery tracking and history"},
    )

    def __repr__(self):
        return f"<AlertHistory(id={self.id}, risk={self.risk_label}, status={self.delivery_status})>"

    def soft_delete(self):
        """Mark record as deleted without removing from database."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self):
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None


class ModelRegistry(Base):
    """Model version registry and metadata."""

    __tablename__ = "model_registry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(Integer, unique=True, nullable=False, index=True)

    # Model file information
    file_path = Column(String(500), nullable=False)
    algorithm = Column(String(100), default="RandomForest")

    # Performance metrics
    accuracy = Column(Float)
    precision_score = Column(Float)
    recall_score = Column(Float)
    f1_score = Column(Float)
    roc_auc = Column(Float)

    # Training information
    training_date = Column(DateTime)
    dataset_size = Column(Integer)
    dataset_path = Column(String(500))

    # Model parameters (JSON stored as text)
    parameters = Column(Text, info={"description": "JSON serialized model parameters"})
    feature_importance = Column(Text, info={"description": "JSON serialized feature importance"})

    # Status
    is_active = Column(Boolean, default=False, index=True)
    notes = Column(Text, info={"description": "Additional notes about this version"})

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_by = Column(String(100), info={"description": "User or system that created this"})

    __table_args__ = (
        CheckConstraint("accuracy IS NULL OR (accuracy >= 0 AND accuracy <= 1)", name="valid_accuracy"),
        CheckConstraint(
            "precision_score IS NULL OR (precision_score >= 0 AND precision_score <= 1)", name="valid_precision"
        ),
        CheckConstraint("recall_score IS NULL OR (recall_score >= 0 AND recall_score <= 1)", name="valid_recall"),
        CheckConstraint("f1_score IS NULL OR (f1_score >= 0 AND f1_score <= 1)", name="valid_f1"),
        {"comment": "Model version tracking and performance registry"},
    )

    def __repr__(self):
        return f"<ModelRegistry(version={self.version}, accuracy={self.accuracy}, active={self.is_active})>"


class SatelliteWeatherCache(Base):
    """
    Cache for satellite weather data from Google Earth Engine.

    Stores GPM precipitation, CHIRPS, and ERA5 reanalysis data
    to reduce API calls and improve response times.
    """

    __tablename__ = "satellite_weather_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Location
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)

    # Timestamp for the weather observation
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # GPM Precipitation data
    precipitation_rate = Column(Float, info={"description": "Current precipitation rate in mm/hour"})
    precipitation_1h = Column(Float, info={"description": "Accumulated precipitation in last 1 hour (mm)"})
    precipitation_3h = Column(Float, info={"description": "Accumulated precipitation in last 3 hours (mm)"})
    precipitation_24h = Column(Float, info={"description": "Accumulated precipitation in last 24 hours (mm)"})

    # Data quality and source
    data_quality = Column(Float, info={"description": "Quality score 0-1"})
    dataset = Column(String(50), default="GPM", info={"description": "Dataset: GPM, CHIRPS, ERA5"})
    source = Column(String(50), default="earth_engine", info={"description": "Data source"})

    # ERA5 reanalysis data
    era5_temperature = Column(Float, info={"description": "ERA5 temperature in Kelvin"})
    era5_humidity = Column(Float, info={"description": "ERA5 relative humidity percentage"})
    era5_precipitation = Column(Float, info={"description": "ERA5 precipitation in mm"})
    era5_wind_speed = Column(Float, info={"description": "ERA5 wind speed in m/s"})
    era5_pressure = Column(Float, info={"description": "ERA5 pressure in hPa"})

    # Cache metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(
        DateTime(timezone=True), nullable=False, index=True, info={"description": "Cache expiration time"}
    )
    is_valid = Column(
        Boolean, default=True, nullable=False, index=True, info={"description": "Whether cache entry is still valid"}
    )

    __table_args__ = (
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="swc_valid_latitude"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="swc_valid_longitude"),
        CheckConstraint("data_quality IS NULL OR (data_quality >= 0 AND data_quality <= 1)", name="swc_valid_quality"),
        CheckConstraint(
            "era5_humidity IS NULL OR (era5_humidity >= 0 AND era5_humidity <= 100)", name="swc_valid_humidity"
        ),
        Index("idx_swc_location", "latitude", "longitude"),
        Index("idx_swc_location_time", "latitude", "longitude", "timestamp"),
        Index("idx_swc_expires", "expires_at"),
        Index("idx_swc_valid", "is_valid"),
        {"comment": "Satellite weather data cache for Earth Engine (GPM, CHIRPS, ERA5)"},
    )

    def __repr__(self):
        return (
            f"<SatelliteWeatherCache(id={self.id}, lat={self.latitude}, lon={self.longitude}, dataset={self.dataset})>"
        )

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "precipitation_rate": self.precipitation_rate,
            "precipitation_1h": self.precipitation_1h,
            "precipitation_3h": self.precipitation_3h,
            "precipitation_24h": self.precipitation_24h,
            "data_quality": self.data_quality,
            "dataset": self.dataset,
            "source": self.source,
            "era5_temperature": self.era5_temperature,
            "era5_humidity": self.era5_humidity,
            "era5_precipitation": self.era5_precipitation,
            "era5_wind_speed": self.era5_wind_speed,
            "era5_pressure": self.era5_pressure,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_valid": self.is_valid,
        }


class TideDataCache(Base):
    """
    Cache for WorldTides API tidal data.

    Stores tide heights and extremes to minimize API credit usage
    while maintaining real-time coastal flood prediction capabilities.
    """

    __tablename__ = "tide_data_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Location
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)

    # Timestamp for the tide observation/prediction
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Tide measurements
    tide_height = Column(Float, nullable=False, info={"description": "Tide height in meters relative to datum"})
    tide_type = Column(String(20), info={"description": "Type: high, low, or None for regular height"})
    datum = Column(String(20), default="MSL", info={"description": "Vertical reference: MSL, LAT, etc."})

    # Calculated fields for prediction
    tide_trend = Column(String(20), info={"description": "rising or falling"})
    tide_risk_factor = Column(Float, info={"description": "Risk factor 0-1 for flood prediction"})
    hours_until_high_tide = Column(Float, info={"description": "Hours until next high tide"})
    next_high_tide_height = Column(Float, info={"description": "Predicted height of next high tide"})

    # Cache metadata
    source = Column(String(50), default="worldtides", info={"description": "Data source"})
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    is_valid = Column(Boolean, default=True, nullable=False, index=True)

    __table_args__ = (
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="tdc_valid_latitude"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="tdc_valid_longitude"),
        CheckConstraint(
            "tide_risk_factor IS NULL OR (tide_risk_factor >= 0 AND tide_risk_factor <= 1)",
            name="tdc_valid_risk_factor",
        ),
        CheckConstraint("tide_trend IS NULL OR tide_trend IN ('rising', 'falling')", name="tdc_valid_trend"),
        Index("idx_tdc_location", "latitude", "longitude"),
        Index("idx_tdc_location_time", "latitude", "longitude", "timestamp"),
        Index("idx_tdc_expires", "expires_at"),
        Index("idx_tdc_valid", "is_valid"),
        {"comment": "Tide data cache for WorldTides API"},
    )

    def __repr__(self):
        return f"<TideDataCache(id={self.id}, lat={self.latitude}, lon={self.longitude}, height={self.tide_height})>"

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "tide_height": self.tide_height,
            "tide_type": self.tide_type,
            "datum": self.datum,
            "tide_trend": self.tide_trend,
            "tide_risk_factor": self.tide_risk_factor,
            "hours_until_high_tide": self.hours_until_high_tide,
            "next_high_tide_height": self.next_high_tide_height,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_valid": self.is_valid,
        }


class APIRequest(Base):
    """API request logging for analytics and debugging."""

    __tablename__ = "api_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(36), unique=True, nullable=False, index=True)
    endpoint = Column(String(255), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False, index=True)
    response_time_ms = Column(Float, nullable=False)
    user_agent = Column(String(500))
    ip_address = Column(String(45), index=True)
    api_version = Column(String(10), default="v1")
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_api_request_endpoint_status", "endpoint", "status_code"),
        Index("idx_api_request_created", "created_at"),
        Index("idx_api_request_active", "is_deleted"),
        # Performance optimization indexes
        Index("idx_api_request_response_time", "response_time_ms"),  # For slow query analysis
        Index("idx_api_request_endpoint_time", "endpoint", "created_at"),  # Endpoint performance over time
        Index("idx_api_request_active_created", "is_deleted", "created_at"),  # Active requests by time
        {"comment": "API request logs for analytics and monitoring"},
    )

    def __repr__(self):
        return f"<APIRequest(id={self.id}, endpoint={self.endpoint}, status={self.status_code})>"


class EarthEngineRequest(Base):
    """
    Earth Engine API request logging.

    Tracks all requests made to Google Earth Engine for:
    - GPM satellite precipitation data
    - CHIRPS daily precipitation
    - ERA5 reanalysis data
    """

    __tablename__ = "earth_engine_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(50), unique=True, nullable=False, index=True)
    request_type = Column(String(50), nullable=False, info={"description": "Type: gpm, chirps, era5, etc."})
    dataset = Column(String(100), info={"description": "Dataset name e.g. NASA/GPM_L3/IMERG_V06"})

    # Location
    latitude = Column(Float, info={"description": "Latitude of request"})
    longitude = Column(Float, info={"description": "Longitude of request"})

    # Time range
    start_date = Column(DateTime(timezone=True), info={"description": "Start of data range"})
    end_date = Column(DateTime(timezone=True), info={"description": "End of data range"})

    # Response tracking
    status = Column(String(20), nullable=False, default="pending", info={"description": "pending/success/error"})
    response_time_ms = Column(Float, info={"description": "Response time in milliseconds"})
    error_message = Column(Text)
    data_points_returned = Column(Integer, default=0, info={"description": "Number of data points returned"})

    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    __table_args__ = (
        Index("idx_ee_request_type", "request_type"),
        Index("idx_ee_request_status", "status"),
        Index("idx_ee_request_created", "created_at"),
        {"comment": "Earth Engine API request logs for GPM, CHIRPS, ERA5 data"},
    )

    def __repr__(self):
        return f"<EarthEngineRequest(id={self.id}, type={self.request_type}, status={self.status})>"


class User(Base):
    """
    User model for authentication and authorization.

    Supports JWT-based authentication with refresh tokens.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # Profile information
    full_name = Column(String(255), info={"description": "User full name"})
    phone_number = Column(String(50), info={"description": "Phone number for SMS alerts"})

    # Role-based access control
    role = Column(String(50), default="user", nullable=False, info={"description": "user/admin/operator"})

    # Account status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_verified = Column(Boolean, default=False, nullable=False, info={"description": "Email verified"})

    # Password reset
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)

    # Refresh token management
    refresh_token_hash = Column(String(255), nullable=True)
    refresh_token_expires = Column(DateTime(timezone=True), nullable=True)

    # Login tracking
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin', 'operator')", name="valid_user_role"),
        Index("idx_user_email_active", "email", "is_active"),
        Index("idx_user_role", "role"),
        {"comment": "User accounts for authentication and authorization"},
    )

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_sensitive:
            result["phone_number"] = self.phone_number
            result["last_login_ip"] = self.last_login_ip
        return result

    def soft_delete(self):
        """Mark user as deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        self.is_active = False

    def is_locked(self) -> bool:
        """Check if user account is locked."""
        if self.locked_until is None:
            return False
        locked_until = self.locked_until
        # SQLite returns naive datetimes even for timezone=True columns.
        # Treat any naive datetime as UTC so the comparison is always valid.
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < locked_until


class Webhook(Base):
    """Webhook registrations for external system notifications."""

    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(500), nullable=False)
    events = Column(Text, nullable=False)
    secret = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_triggered_at = Column(DateTime(timezone=True))
    failure_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_webhook_active", "is_active", "is_deleted"),
        {"comment": "Webhook configurations for external notifications"},
    )

    def __repr__(self):
        return f"<Webhook(id={self.id}, url={self.url}, active={self.is_active})>"


def init_db():
    """Initialize database tables with enhanced error handling."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")

        # Log table creation
        tables = Base.metadata.tables.keys()
        logger.info(f"Created tables: {', '.join(tables)}")

        # Initialize slow query logging
        try:
            from app.utils.query_optimizer import setup_slow_query_logging

            setup_slow_query_logging(engine)
            logger.info("Slow query logging initialized")
        except ImportError:
            logger.debug("Query optimizer not available - slow query logging disabled")
        except Exception as e:
            logger.warning(f"Failed to initialize slow query logging: {e}")

        return True
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise


@contextmanager
def get_db_session():
    """Context manager for database sessions."""
    session = db_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        db_session.remove()  # Remove session from registry for scoped_session
