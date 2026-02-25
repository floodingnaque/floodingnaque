"""Shared data types for WorldTides services.

Used by both WorldTidesService (sync) and AsyncWorldTidesService.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TideData:
    """Tide observation data structure."""

    timestamp: datetime
    height: float  # meters relative to datum
    type: Optional[str] = None  # 'high', 'low', or None for regular height
    datum: str = "MSL"  # Mean Sea Level
    source: str = "worldtides"


@dataclass
class TideExtreme:
    """Tide extreme (high/low) data structure."""

    timestamp: datetime
    height: float  # meters
    type: str  # 'High' or 'Low'
    datum: str = "MSL"


__all__ = ["TideData", "TideExtreme"]
