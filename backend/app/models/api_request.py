"""API request logging ORM models."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String, Text

from app.models.db import Base


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
        Index("idx_api_request_response_time", "response_time_ms"),
        Index("idx_api_request_endpoint_time", "endpoint", "created_at"),
        Index("idx_api_request_active_created", "is_deleted", "created_at"),
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
