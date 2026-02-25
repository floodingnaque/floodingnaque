"""Cache ORM models for satellite weather and tide data."""

from datetime import datetime, timezone

from app.models.db import Base
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Float, Index, Integer, String


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
