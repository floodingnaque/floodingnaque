"""A/B Test persistence ORM model.

Stores running A/B test state (config, metrics, user assignments) so that
a process restart does not lose test progress.
"""

from datetime import datetime, timezone

from app.models.db import Base
from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON


class ABTestRecord(Base):
    """Persisted A/B test state."""

    __tablename__ = "ab_tests"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Identity
    test_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Configuration (JSON blobs)
    variants_json = Column(JSON, nullable=False, comment="List of ModelVariant dicts")
    strategy = Column(String(50), nullable=False, default="random")
    target_sample_size = Column(Integer, nullable=False, default=1000)

    # Lifecycle
    status = Column(String(50), nullable=False, default="created", index=True)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)

    # State (JSON blobs)
    metrics_json = Column(JSON, nullable=True, comment="Dict[variant_name, ABTestMetrics]")
    user_assignments_json = Column(JSON, nullable=True, comment="Dict[user_id, variant_name]")
    round_robin_index = Column(Integer, nullable=False, default=0)
    canary_percentage = Column(Float, nullable=False, default=0.0)
    canary_increment = Column(Float, nullable=False, default=10.0)

    # Result
    winner = Column(String(100), nullable=True)
    statistical_significance = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<ABTestRecord(test_id={self.test_id!r}, status={self.status!r})>"
