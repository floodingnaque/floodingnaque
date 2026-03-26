"""
Celery Application Configuration.

Sets up Celery for background task processing with dead letter queue
support for permanently failed tasks.
"""

import json
import os
import time

from app.utils.observability.logging import get_logger
from app.utils.secrets import get_secret
from celery import Celery
from celery.schedules import crontab
from celery.signals import task_failure, task_rejected, task_revoked

logger = get_logger(__name__)

# Create Celery instance
celery_app = Celery("floodingnaque")

# ---------------------------------------------------------------------------
# Dead Letter Queue (DLQ) - stores permanently failed tasks for inspection
# ---------------------------------------------------------------------------

# Redis key prefix for DLQ entries
DLQ_REDIS_KEY = "celery:dlq"
DLQ_MAX_ENTRIES = int(os.getenv("CELERY_DLQ_MAX_ENTRIES", "1000"))


def _get_dlq_redis():
    """Get a Redis connection for DLQ operations."""
    import redis

    broker_url = get_secret("CELERY_BROKER_URL", default="redis://localhost:6379/1")
    return redis.Redis.from_url(broker_url, decode_responses=True)


def push_to_dlq(task_name: str, task_id: str, args: tuple, kwargs: dict, exception: str, queue: str = "default"):
    """Push a failed task into the dead letter queue (Redis list)."""
    try:
        r = _get_dlq_redis()
        entry = json.dumps(
            {
                "task_name": task_name,
                "task_id": task_id,
                "args": list(args) if args else [],
                "kwargs": kwargs or {},
                "exception": str(exception)[:2000],
                "queue": queue,
                "failed_at": time.time(),
            }
        )
        r.lpush(DLQ_REDIS_KEY, entry)
        r.ltrim(DLQ_REDIS_KEY, 0, DLQ_MAX_ENTRIES - 1)
        logger.warning("Task %s (%s) moved to DLQ: %s", task_name, task_id, str(exception)[:200])
    except Exception as exc:
        logger.error("Failed to push task to DLQ: %s", exc)


def get_dlq_entries(limit: int = 50) -> list:
    """Retrieve recent DLQ entries."""
    try:
        r = _get_dlq_redis()
        raw = r.lrange(DLQ_REDIS_KEY, 0, limit - 1)
        return [json.loads(entry) for entry in raw]
    except Exception as exc:
        logger.error("Failed to read DLQ: %s", exc)
        return []


def get_dlq_count() -> int:
    """Return the number of entries in the DLQ."""
    try:
        r = _get_dlq_redis()
        return r.llen(DLQ_REDIS_KEY)
    except Exception:
        return 0


def replay_dlq_entry(index: int = -1) -> dict:
    """
    Replay a single DLQ entry by re-sending it to its original queue.

    Uses RPOP (oldest first) by default. Returns the replayed entry.
    """
    try:
        r = _get_dlq_redis()
        raw = r.rpop(DLQ_REDIS_KEY)
        if not raw:
            return {"replayed": False, "reason": "DLQ is empty"}
        entry = json.loads(raw)
        celery_app.send_task(
            entry["task_name"],
            args=entry.get("args", []),
            kwargs=entry.get("kwargs", {}),
            queue=entry.get("queue", "default"),
        )
        logger.info("Replayed DLQ task: %s (%s)", entry["task_name"], entry.get("task_id"))
        return {"replayed": True, "task": entry}
    except Exception as exc:
        logger.error("Failed to replay DLQ entry: %s", exc)
        return {"replayed": False, "reason": str(exc)}


def clear_dlq() -> int:
    """Clear all DLQ entries. Returns count of removed entries."""
    try:
        r = _get_dlq_redis()
        count = r.llen(DLQ_REDIS_KEY)
        r.delete(DLQ_REDIS_KEY)
        return count
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Celery signals - route permanently failed tasks to DLQ
# ---------------------------------------------------------------------------


@task_failure.connect
def _on_task_failure(sender=None, task_id=None, exception=None, args=None, kwargs=None, einfo=None, **kw):
    """Move tasks that have exhausted retries to the DLQ."""
    request = sender.request if sender else None
    retries = getattr(request, "retries", 0) if request else 0
    max_retries = getattr(sender, "max_retries", 3) if sender else 3

    if max_retries is None or retries >= (max_retries or 3):
        task_name = sender.name if sender else "unknown"
        queue = getattr(request, "delivery_info", {}).get("routing_key", "default") if request else "default"
        push_to_dlq(task_name, task_id, args or (), kwargs or {}, str(exception), queue=queue)


@task_rejected.connect
def _on_task_rejected(sender=None, message=None, exc=None, **kw):
    """Capture rejected (unrecoverable) tasks."""
    body = getattr(message, "body", None)
    task_name = body.get("task", "unknown") if isinstance(body, dict) else "unknown"
    task_id = body.get("id", "unknown") if isinstance(body, dict) else "unknown"
    push_to_dlq(task_name, task_id, (), {}, f"Rejected: {exc}")


# ---------------------------------------------------------------------------
# Celery configuration
# ---------------------------------------------------------------------------

# Configure Celery
celery_app.conf.update(
    # Broker settings
    broker_url=get_secret("CELERY_BROKER_URL", default="redis://localhost:6379/1"),
    result_backend=get_secret("CELERY_RESULT_BACKEND", default="redis://localhost:6379/2"),
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=os.getenv("CELERY_TIMEZONE", "Asia/Manila"),
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
        "database-backup": {
            "task": "app.services.tasks.database_backup",
            "schedule": crontab(hour=2, minute=0),  # Daily at 2:00 AM UTC
            "options": {"queue": "data_tasks"},
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
