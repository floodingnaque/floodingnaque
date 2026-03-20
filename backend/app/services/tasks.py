"""
Celery Background Tasks.

Defines background tasks for async processing.
"""

import os
import smtplib
import time
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from app.models.db import get_db_session
from app.services.celery_app import celery_app
from app.utils.observability.logging import get_logger
from app.utils.secrets import get_secret
from sqlalchemy import text

logger = get_logger(__name__)


@celery_app.task(bind=True, name="app.services.tasks.model_retraining")
def model_retraining(self, model_id=None):
    """
    Retrain the flood prediction model with latest data.

    Uses the UnifiedTrainer pipeline from scripts.train_unified to run a
    full training cycle: data loading, preprocessing, training, validation,
    and model serialisation.

    Args:
        model_id: Optional model ID / version to retrain

    Returns:
        dict: Real training results including metrics
    """
    import sys

    task_id = self.request.id
    logger.info(f"Starting model retraining task {task_id}")
    train_start = time.time()

    try:
        # Ensure scripts package is importable
        backend_path = Path(__file__).resolve().parent.parent.parent
        if str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))

        from scripts.train_unified import TrainingMode, UnifiedTrainer

        # Step 1 - Initialise trainer
        self.update_state(state="PROGRESS", meta={"status": "Initialising trainer...", "progress": 10})
        mode = TrainingMode.PRODUCTION
        trainer = UnifiedTrainer(mode=mode)
        logger.info(f"Trainer initialised in {mode.value} mode")

        # Step 2 - Run training pipeline
        self.update_state(state="PROGRESS", meta={"status": "Training model...", "progress": 30})
        train_results = trainer.train()

        # Step 3 - Extract real metrics from training output
        self.update_state(state="PROGRESS", meta={"status": "Collecting metrics...", "progress": 80})
        metrics = train_results.get("metrics", {})
        model_path = train_results.get("model_path", "")

        # Step 4 - Reload the newly trained model into the inference cache
        self.update_state(state="PROGRESS", meta={"status": "Reloading model...", "progress": 90})
        try:
            from app.services.predict import _load_model

            _load_model(model_path=model_path if model_path else None, force_reload=True)
            logger.info("Inference model hot-reloaded")
        except Exception as reload_err:
            logger.warning(f"Model reload skipped (will load on next request): {reload_err}")

        elapsed = round(time.time() - train_start, 1)

        result = {
            "task_id": task_id,
            "model_id": model_id,
            "status": "completed",
            "training_mode": mode.value,
            "training_time_seconds": elapsed,
            "model_path": str(model_path),
            "accuracy": metrics.get("accuracy"),
            "precision": metrics.get("precision"),
            "recall": metrics.get("recall"),
            "f1_score": metrics.get("f1_score"),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"Model retraining completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Model retraining failed: {str(e)}")
        self.update_state(state="FAILURE", meta={"error": str(e), "status": "Training failed"})
        raise


@celery_app.task(bind=True, name="app.services.tasks.auto_retrain_pipeline")
def auto_retrain_pipeline(self, force=False, include_deep_learning=False):
    """
    Automated retraining pipeline with drift detection & performance gating.

    Checks triggers (schedule, data freshness, drift) and conditionally
    retrains the model, including optional ENSO/spatial feature enrichment
    and deep learning model training.

    Args:
        force: Skip trigger checks and retrain unconditionally.
        include_deep_learning: Also train LSTM/Transformer alongside RF.

    Returns:
        dict: Pipeline results with metrics and promotion status.
    """
    task_id = self.request.id
    logger.info(f"Starting auto-retrain pipeline task {task_id}")

    try:
        from app.services.auto_retrain import RetrainingConfig, run_auto_retrain

        config = RetrainingConfig(include_deep_learning=include_deep_learning)

        def progress_cb(msg, pct):
            self.update_state(state="PROGRESS", meta={"status": msg, "progress": pct})

        result = run_auto_retrain(
            force=force,
            config=config,
            progress_callback=progress_cb,
        )
        result["task_id"] = task_id
        logger.info(f"Auto-retrain pipeline completed: status={result.get('status')}")
        return result

    except Exception as e:
        logger.error(f"Auto-retrain pipeline failed: {str(e)}")
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise


@celery_app.task(bind=True, name="app.services.tasks.data_processing")
def process_weather_data(self, data_batch):
    """
    Process a batch of weather data asynchronously.

    Args:
        data_batch: List of weather data records

    Returns:
        dict: Processing results
    """
    task_id = self.request.id
    logger.info(f"Processing weather data batch {task_id} with {len(data_batch)} records")

    try:
        processed_count = 0
        failed_count = 0

        for i, record in enumerate(data_batch):
            try:
                # Process individual weather record
                # In real implementation: validate, transform, save to database
                processed_count += 1

                # Update progress
                if i % 10 == 0:  # Update every 10 records
                    progress = int((i / len(data_batch)) * 100)
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "status": f"Processed {processed_count} records",
                            "progress": progress,
                            "processed": processed_count,
                            "failed": failed_count,
                        },
                    )

            except Exception as e:
                logger.warning(f"Failed to process record {i}: {str(e)}")
                failed_count += 1

        result = {
            "task_id": task_id,
            "status": "completed",
            "total_records": len(data_batch),
            "processed": processed_count,
            "failed": failed_count,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"Data processing completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Data processing failed: {str(e)}")
        self.update_state(state="FAILURE", meta={"error": str(e), "status": "Processing failed"})
        raise


@celery_app.task(bind=True, name="app.services.tasks.send_notification")
def send_notification(self, notification_type, recipient, message):
    """
    Send notification (email, SMS, webhook) asynchronously.

    Delegates to the existing AlertSystem for email/SMS, and uses
    ``requests`` for webhook delivery.

    Args:
        notification_type: Type of notification ('email', 'sms', 'webhook')
        recipient: Recipient address/phone/webhook URL
        message: Message content

    Returns:
        dict: Notification delivery results
    """
    task_id = self.request.id
    logger.info(f"Sending {notification_type} notification to {recipient}")

    try:
        self.update_state(state="PROGRESS", meta={"status": "Sending notification...", "progress": 50})

        delivery_status: str = "unknown"

        if notification_type == "email":
            from app.services.alerts import get_alert_system

            alert_system = get_alert_system(email_enabled=True)
            delivery_status = alert_system._send_email(
                recipients=[recipient],
                subject="Floodingnaque Notification",
                message=message,
            )

        elif notification_type == "sms":
            from app.services.alerts import get_alert_system

            alert_system = get_alert_system(sms_enabled=True)
            delivery_status = alert_system._send_sms(
                recipients=[recipient],
                message=message,
            )

        elif notification_type == "webhook":
            import requests as http_requests

            webhook_url = recipient
            payload = {
                "text": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "floodingnaque",
            }
            resp = http_requests.post(webhook_url, json=payload, timeout=15)
            resp.raise_for_status()
            delivery_status = "delivered"

        else:
            raise ValueError(f"Unsupported notification type: {notification_type}")

        result = {
            "task_id": task_id,
            "notification_type": notification_type,
            "recipient": recipient,
            "status": delivery_status,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"Notification sent: {result}")
        return result

    except Exception as e:
        logger.error(f"Failed to send notification: {str(e)}")
        self.update_state(state="FAILURE", meta={"error": str(e), "status": "Notification failed"})
        raise


@celery_app.task(name="app.services.tasks.cleanup_old_results")
def cleanup_old_results():
    """
    Periodic task to clean up old Celery task results from the result backend.

    Connects to the Redis result backend, scans for celery-task-meta-* keys,
    and deletes entries whose results are older than the configured retention
    period (default: 24 hours, matching ``result_expires``).
    """
    logger.info("Starting cleanup of old task results")

    try:
        import json as _json
        from urllib.parse import urlparse

        import redis

        result_backend_url = get_secret("CELERY_RESULT_BACKEND") or "redis://localhost:6379/2"
        parsed = urlparse(result_backend_url)
        r = redis.Redis(
            host=parsed.hostname or "localhost",
            port=parsed.port or 6379,
            db=int((parsed.path or "/0").lstrip("/") or "0"),
            password=parsed.password,
            socket_timeout=10,
        )

        retention_seconds = int(os.environ.get("CELERY_RESULT_RETENTION", "86400"))  # 24 h
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=retention_seconds)
        deleted = 0
        scanned = 0

        # Scan for celery result keys
        for key in r.scan_iter(match="celery-task-meta-*", count=200):
            scanned += 1
            try:
                raw = r.get(key)
                if raw is None:
                    continue
                meta = _json.loads(raw)
                # Celery stores 'date_done' as ISO timestamp
                date_done_str = meta.get("date_done")
                if date_done_str:
                    date_done = datetime.fromisoformat(date_done_str.replace("Z", "+00:00"))
                    if date_done.tzinfo is None:
                        date_done = date_done.replace(tzinfo=timezone.utc)
                    if date_done < cutoff:
                        r.delete(key)
                        deleted += 1
            except Exception as key_err:
                logger.debug(f"Skipping key {key}: {key_err}")

        logger.info(f"Cleanup completed: scanned={scanned}, deleted={deleted}")
        return {
            "status": "completed",
            "scanned": scanned,
            "deleted": deleted,
            "retention_seconds": retention_seconds,
            "cleaned_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(name="app.services.tasks.health_check")
def health_check():
    """
    Periodic health check task.
    """
    try:
        # Check database connectivity
        with get_db_session() as session:
            session.execute(text("SELECT 1"))

        # Check Redis connectivity (if configured)
        redis_url = get_secret("CELERY_BROKER_URL") or ""
        if redis_url and "redis" in redis_url.lower():
            from urllib.parse import urlparse

            import redis

            parsed = urlparse(redis_url)
            r = redis.Redis(
                host=parsed.hostname or "localhost",
                port=parsed.port or 6379,
                password=parsed.password,
                socket_timeout=5,
            )
            r.ping()

        logger.info("Health check passed")
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {"database": "ok", "redis": "ok"},
        }

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "unhealthy", "timestamp": datetime.now(timezone.utc).isoformat(), "error": str(e)}


@celery_app.task(bind=True, name="app.services.tasks.database_backup", max_retries=2)
def database_backup(self):
    """
    Automated daily database backup task.

    Creates a compressed backup of the PostgreSQL database and
    cleans up old backups beyond the retention limit.
    """
    import sys
    from pathlib import Path

    logger.info("Starting scheduled database backup")

    try:
        self.update_state(
            state="PROGRESS",
            meta={"status": "Starting backup...", "progress": 0},
        )

        # Import backup utility
        backend_path = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(backend_path))
        from scripts.backup_database import run_backup

        # Run the backup
        backup_path = run_backup(
            backup_type="postgresql",
            compress=True,
            cleanup=True,
            keep_count=int(os.environ.get("BACKUP_RETENTION_COUNT", "30")),
        )

        result = {
            "status": "completed",
            "backup_path": str(backup_path),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(f"Database backup completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Database backup failed: {str(e)}")
        # Retry with exponential backoff (60s, then 120s)
        raise self.retry(exc=e, countdown=60 * (2**self.request.retries))


# ── Community Engagement tasks ────────────────────────────────────────────


@celery_app.task(name="app.services.tasks.score_community_report")
def score_community_report(report_id):
    """Score a community report's credibility and check auto-verify."""
    logger.info(f"Scoring community report {report_id}")
    try:
        from app.services.credibility_service import check_auto_verify, score_report

        score = score_report(report_id)
        auto_verified = check_auto_verify(report_id)
        return {
            "report_id": report_id,
            "credibility_score": score,
            "auto_verified": auto_verified,
        }
    except Exception as e:
        logger.error(f"Failed to score report {report_id}: {e}")
        raise


@celery_app.task(name="app.services.tasks.dispatch_sms_alert")
def dispatch_sms_alert(barangay, risk_label):
    """Dispatch evacuation SMS alerts for a barangay."""
    logger.info(f"Dispatching SMS alert for {barangay} ({risk_label})")
    try:
        from app.services.sms_service import dispatch_evacuation_sms

        dispatched = dispatch_evacuation_sms(barangay, risk_label)
        return {
            "barangay": barangay,
            "risk_label": risk_label,
            "dispatched_count": dispatched,
        }
    except Exception as e:
        logger.error(f"Failed to dispatch SMS alert: {e}")
        raise


# Example usage functions
def trigger_model_retraining(model_id=None):
    """Trigger model retraining task.

    Attempts async execution via Celery. Falls back to synchronous
    execution when no broker is available (e.g. development without Redis).
    """
    try:
        task = model_retraining.delay(model_id)
        return {"task_id": task.id, "status": "queued", "message": "Model retraining task queued successfully"}
    except Exception as e:
        logger.warning(f"Celery broker unavailable, executing model_retraining synchronously: {e}")
        result = model_retraining(model_id)
        return {
            "task_id": None,
            "status": "completed_sync",
            "message": "Model retraining executed synchronously",
            "result": result,
        }


def trigger_auto_retrain(force=False, include_deep_learning=False):
    """Trigger the automated retraining pipeline.

    Includes drift detection, performance gating, and optional
    deep learning model training alongside Random Forest.
    """
    try:
        task = auto_retrain_pipeline.delay(force=force, include_deep_learning=include_deep_learning)
        return {"task_id": task.id, "status": "queued", "message": "Auto-retrain pipeline queued"}
    except Exception as e:
        logger.warning(f"Celery broker unavailable, running auto_retrain_pipeline synchronously: {e}")
        result = auto_retrain_pipeline(force=force, include_deep_learning=include_deep_learning)
        return {"task_id": None, "status": "completed_sync", "result": result}


def trigger_data_processing(data_batch):
    """Trigger data processing task.

    Attempts async execution via Celery. Falls back to synchronous
    execution when no broker is available (e.g. development without Redis).
    """
    try:
        task = process_weather_data.delay(data_batch)
        return {"task_id": task.id, "status": "queued", "message": "Data processing task queued successfully"}
    except Exception as e:
        logger.warning(f"Celery broker unavailable, executing process_weather_data synchronously: {e}")
        result = process_weather_data(data_batch)
        return {
            "task_id": None,
            "status": "completed_sync",
            "message": "Data processing executed synchronously",
            "result": result,
        }


def get_task_status(task_id):
    """Get status of a Celery task."""
    from celery.result import AsyncResult

    result = AsyncResult(task_id, app=celery_app)

    return {
        "task_id": task_id,
        "status": result.state,
        "result": result.result if result.ready() else None,
        "progress": result.info.get("progress", 0) if result.state == "PROGRESS" else None,
    }
