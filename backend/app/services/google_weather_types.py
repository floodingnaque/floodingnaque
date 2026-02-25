"""Shared data types for Google Weather / Earth Engine services.

Used by both GoogleWeatherService (sync) and AsyncGoogleWeatherService.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SatellitePrecipitation:
    """Satellite precipitation observation data structure."""

    timestamp: datetime
    latitude: float
    longitude: float
    precipitation_rate: float  # mm/hour
    accumulation_1h: Optional[float] = None  # mm
    accumulation_3h: Optional[float] = None  # mm
    accumulation_24h: Optional[float] = None  # mm
    data_quality: Optional[float] = None  # 0-1 quality score
    dataset: str = "GPM"  # GPM, CHIRPS, ERA5
    source: str = "earth_engine"


@dataclass
class WeatherReanalysis:
    """ERA5 reanalysis data structure."""

    timestamp: datetime
    latitude: float
    longitude: float
    temperature: float  # Celsius
    humidity: float  # Percentage
    precipitation: float  # mm
    wind_speed: Optional[float] = None  # m/s
    pressure: Optional[float] = None  # hPa
    source: str = "era5"


__all__ = ["SatellitePrecipitation", "WeatherReanalysis"]
