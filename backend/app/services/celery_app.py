"""
Celery Application Configuration.

Sets up Celery for background task processing.
"""

import os

from app.utils.logging import get_logger
from app.utils.secrets import get_secret
from celery import Celery

logger = get_logger(__name__)

# Create Celery instance
celery_app = Celery("floodingnaque")

# Configure Celery
celery_app.conf.update(
    # Broker settings
    broker_url=get_secret("CELERY_BROKER_URL", default="redis://localhost:6379/1"),
    result_backend=get_secret("CELERY_RESULT_BACKEND", default="redis://localhost:6379/2"),
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task routing
    task_routes={
        "app.services.tasks.model_retraining": {"queue": "ml_tasks"},
        "app.services.tasks.data_processing": {"queue": "data_tasks"},
        "app.services.tasks.notifications": {"queue": "notification_tasks"},
    },
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    # Result settings
    result_expires=3600,  # 1 hour
    result_compression="gzip",
    # Error handling
    task_reject_on_worker_lost=True,
    task_ignore_result=False,
    # Beat schedule (for periodic tasks)
    beat_schedule={
        "cleanup-old-results": {
            "task": "app.services.tasks.cleanup_old_results",
            "schedule": 3600.0,  # Every hour
        },
        "health-check": {
            "task": "app.services.tasks.health_check",
            "schedule": 300.0,  # Every 5 minutes
        },
    },
)

# Optional: Import tasks to register them
try:
    from app.services import tasks  # noqa: F401

    logger.info("Celery tasks module loaded")
except ImportError as e:
    logger.warning(f"Could not import Celery tasks: {e}")

if __name__ == "__main__":
    celery_app.start()
