"""Shared data types for Meteostat services.

Used by both MeteostatService (sync) and AsyncMeteostatService.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class WeatherObservation:
    """Weather observation data structure.

    Fields use Optional with defaults to gracefully handle missing
    data from weather stations without raising errors.
    """

    timestamp: datetime
    temperature: Optional[float] = None  # Celsius
    humidity: Optional[float] = None  # Percentage (0-100)
    precipitation: Optional[float] = None  # mm
    wind_speed: Optional[float] = None  # m/s
    pressure: Optional[float] = None  # hPa
    station_id: Optional[str] = None
    source: str = "meteostat"


__all__ = ["WeatherObservation"]
