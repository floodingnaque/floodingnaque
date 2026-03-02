"""Routes package for Weather Data Collector Service."""

from app.routes.data import data_bp
from app.routes.ingest import ingest_bp
from app.routes.tides import tides_bp
from app.routes.weather import weather_bp

__all__ = ["weather_bp", "ingest_bp", "tides_bp", "data_bp"]
