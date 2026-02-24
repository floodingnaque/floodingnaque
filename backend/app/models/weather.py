"""WeatherData ORM model."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.db import Base


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
        Index("idx_weather_location_time", "location_lat", "location_lon", "timestamp"),
        Index("idx_weather_created", "created_at"),
        Index("idx_weather_source", "source"),
        Index("idx_weather_active", "is_deleted"),
        Index("idx_weather_active_timestamp", "is_deleted", "timestamp"),
        Index("idx_weather_active_created", "is_deleted", "created_at"),
        Index("idx_weather_source_timestamp", "source", "timestamp"),
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
