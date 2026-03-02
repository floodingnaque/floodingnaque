"""
Background Scheduler for Floodingnaque.

Handles periodic tasks like weather data ingestion.
Designed to work correctly with Gunicorn workers using distributed locking.
"""

import logging
import os
import sys
import tempfile

from apscheduler.schedulers.background import BackgroundScheduler
from app.core.constants import DEFAULT_LATITUDE, DEFAULT_LONGITUDE

logger = logging.getLogger(__name__)

# Scheduler instance - jobs are added when start() is called
scheduler = BackgroundScheduler(
    timezone=os.getenv("SCHEDULER_TIMEZONE", "Asia/Manila"),
    job_defaults={
        "coalesce": True,  # Combine missed runs into one
        "max_instances": 1,  # Only one instance of each job
        "misfire_grace_time": 300,  # 5 minute grace period
    },
)

# Track if scheduler has been initialized
_scheduler_initialized = False
_scheduler_lock_fd = None  # File descriptor for lock file


def _get_lock_file_path() -> str:
    """
    Get the path to the scheduler lock file.
    Uses temp directory for cross-platform compatibility.
    """
    if sys.platform == "win32":
        # Windows: Use temp directory
        return os.path.join(tempfile.gettempdir(), "floodingnaque_scheduler.lock")
    else:
        # Unix-like: Use /tmp for better compatibility with containers
        return "/tmp/floodingnaque_scheduler.lock"  # nosec B108


def should_run_scheduler() -> bool:
    """
    Check if this process should run the scheduler.

    Uses file locking to ensure only one Gunicorn worker runs the scheduler.
    The first worker to acquire the lock becomes the scheduler master.

    Returns:
        bool: True if this process should run the scheduler
    """
    global _scheduler_lock_fd

    lock_file = _get_lock_file_path()

    try:
        if sys.platform == "win32":
            # Windows: Use msvcrt for file locking
            import msvcrt

            _scheduler_lock_fd = open(lock_file, "w")
            msvcrt.locking(_scheduler_lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
            _scheduler_lock_fd.write(str(os.getpid()))
            _scheduler_lock_fd.flush()
            logger.info(f"Acquired scheduler lock (PID: {os.getpid()})")
            return True
        else:
            # Unix: Use fcntl for file locking
            import fcntl

            _scheduler_lock_fd = open(lock_file, "w")
            fcntl.flock(_scheduler_lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            _scheduler_lock_fd.write(str(os.getpid()))
            _scheduler_lock_fd.flush()
            logger.info(f"Acquired scheduler lock (PID: {os.getpid()})")
            return True
    except (IOError, OSError) as e:
        # Another process holds the lock
        logger.info("Scheduler lock held by another worker, skipping scheduler init")
        if _scheduler_lock_fd:
            _scheduler_lock_fd.close()
            _scheduler_lock_fd = None
        return False
    except ImportError:
        # fcntl/msvcrt not available, fall back to allowing scheduler
        logger.warning("File locking not available, scheduler will run on all workers")
        return True


def scheduled_ingest():
    """
    Scheduled task for weather data ingestion.

    Runs periodically to fetch fresh weather data from APIs.
    """
    # Import here to avoid circular imports and ensure app context
    from app.services.ingest import ingest_data

    try:
        # Get default coordinates from environment or central config
        lat = float(os.getenv("DEFAULT_LATITUDE", str(DEFAULT_LATITUDE)))
        lon = float(os.getenv("DEFAULT_LONGITUDE", str(DEFAULT_LONGITUDE)))

        ingest_data(lat=lat, lon=lon)
        logger.info("Scheduled data ingestion completed successfully.")
    except Exception as e:
        logger.error(f"Error in scheduled ingestion: {str(e)}", exc_info=True)


def scheduled_purge_expired_ips():
    """
    Scheduled task to purge login IP addresses past the retention window.

    Enforces the 90-day (configurable via IP_RETENTION_DAYS) data-retention
    policy required by GDPR / Philippine Data Privacy Act.
    """
    from app.models.db import get_db_session
    from app.models.user import User

    try:
        with get_db_session() as session:
            purged = User.purge_expired_ips(session)
        if purged:
            logger.info(f"Purged login IPs for {purged} user(s) past retention window.")
    except Exception as e:
        logger.error(f"Error purging expired IPs: {str(e)}", exc_info=True)


def scheduled_auto_retrain():
    """
    Scheduled task for automated model retraining.

    Checks triggers (data freshness, drift, schedule) and conditionally
    runs the retraining pipeline with performance gating.
    """
    try:
        from app.services.auto_retrain import check_retraining_needed, run_auto_retrain

        trigger_check = check_retraining_needed()
        if trigger_check.get("should_retrain"):
            logger.info(
                f"Auto-retrain triggered by: {trigger_check.get('triggered_by')}. "
                "Starting retraining pipeline..."
            )
            result = run_auto_retrain(force=False)
            logger.info(f"Auto-retrain completed: status={result.get('status')}")
        else:
            logger.info("Auto-retrain check: no triggers fired, skipping.")
    except Exception as e:
        logger.error(f"Error in scheduled auto-retrain: {str(e)}", exc_info=True)


def scheduled_smart_alert_check():
    """
    Scheduled task for smart alert evaluation.

    Fetches the latest weather data, runs ML prediction, and evaluates
    through the smart alert pipeline.  This enables time-based escalation
    (Alert → Critical after persistence) and de-escalation even between
    user-triggered predictions.
    """
    from app.services.predict import predict_flood
    from app.services.alerts import send_flood_alert
    from app.services.smart_alert_evaluator import evaluate_smart_alert

    try:
        # Import here to avoid circular imports
        from app.models.db import WeatherData, get_db_session
        from sqlalchemy import desc

        # Get the most recent weather observation
        with get_db_session() as session:
            latest = (
                session.query(WeatherData)
                .order_by(desc(WeatherData.created_at))
                .first()
            )
            if not latest:
                logger.info("Smart alert check: no weather data available, skipping.")
                return

            weather_input = {
                "temperature": latest.temperature,
                "humidity": latest.humidity,
                "precipitation": latest.precipitation,
                "wind_speed": latest.wind_speed or 0.0,
                "precipitation_3h": latest.precipitation_3h,
                "tide_risk_factor": latest.tide_risk_factor,
                "data_quality": latest.data_quality,
            }

        # Run prediction with smart alert evaluation
        result = predict_flood(
            input_data=weather_input,
            return_proba=True,
            return_risk_level=True,
        )

        if isinstance(result, dict):
            smart_alert = result.get("smart_alert", {})
            risk_level = result.get("risk_level", 0)
            escalation_state = smart_alert.get("escalation_state", "none")
            was_suppressed = smart_alert.get("was_suppressed", False)

            logger.info(
                "Smart alert check completed: risk_level=%d, escalation=%s, suppressed=%s",
                risk_level, escalation_state, was_suppressed,
            )

            # Only dispatch if risk is elevated and not suppressed
            if risk_level >= 1 and not was_suppressed:
                from app.services.smart_alert_evaluator import SmartAlertDecision

                decision = SmartAlertDecision(
                    risk_level=smart_alert.get("original_risk_level", risk_level),
                    risk_label=result.get("risk_label", "Alert"),
                    confidence=smart_alert.get("confidence_score", 0.5),
                    rainfall_3h=smart_alert.get("rainfall_3h", 0.0),
                    was_suppressed=was_suppressed,
                    escalation_state=escalation_state,
                    escalation_reason=smart_alert.get("escalation_reason"),
                    contributing_factors=smart_alert.get("contributing_factors", []),
                    original_risk_level=smart_alert.get("original_risk_level", risk_level),
                )
                # Use the smart-adjusted risk_level for the alert data
                risk_data = {
                    "risk_level": risk_level,
                    "risk_label": result.get("risk_label", "Alert"),
                    "confidence": result.get("confidence", 0.5),
                }
                send_flood_alert(
                    risk_data=risk_data,
                    alert_type="web",
                    smart_decision=decision,
                )

    except Exception as e:
        logger.error(f"Error in scheduled smart alert check: {str(e)}", exc_info=True)


def init_scheduler():
    """
    Initialize scheduler with jobs.

    Call this AFTER the Flask app is fully configured.
    Only initializes once to prevent duplicate jobs with Gunicorn workers.
    Uses file locking to ensure only one worker runs the scheduler.
    """
    global _scheduler_initialized

    if _scheduler_initialized:
        logger.debug("Scheduler already initialized, skipping.")
        return

    # Check if scheduler is enabled
    scheduler_enabled = os.getenv("SCHEDULER_ENABLED", "True").lower() == "true"
    if not scheduler_enabled:
        logger.info("Scheduler is disabled via SCHEDULER_ENABLED=False")
        return

    # Skip APScheduler when Celery Beat handles scheduling (production)
    celery_beat_running = os.getenv("CELERY_BEAT_RUNNING", "false").lower() == "true"
    if celery_beat_running:
        logger.info("APScheduler disabled — Celery Beat handles periodic task scheduling")
        _scheduler_initialized = True
        return

    # Check if this worker should run the scheduler (distributed lock)
    if not should_run_scheduler():
        logger.info("Scheduler will run on a different worker")
        _scheduler_initialized = True  # Mark as initialized to prevent retry
        return

    # Get ingest interval from environment.
    # DATA_INGEST_INTERVAL_MINUTES takes precedence (allows sub-hour intervals
    # down to 15 min for rapidly changing conditions).  Falls back to the
    # legacy DATA_INGEST_INTERVAL_HOURS env var (default: 60 min).
    raw_minutes = os.getenv("DATA_INGEST_INTERVAL_MINUTES")
    if raw_minutes is not None:
        ingest_interval_minutes = max(15, int(raw_minutes))
    else:
        ingest_interval_hours = int(os.getenv("DATA_INGEST_INTERVAL_HOURS", "1"))
        ingest_interval_minutes = ingest_interval_hours * 60

    # Add the ingestion job
    scheduler.add_job(
        scheduled_ingest,
        "interval",
        minutes=ingest_interval_minutes,
        id="weather_ingest",
        name="Weather Data Ingestion",
        replace_existing=True,  # Replace if exists (handles restarts)
    )

    # Add the daily IP-purge job (GDPR / Data Privacy Act retention policy)
    scheduler.add_job(
        scheduled_purge_expired_ips,
        "interval",
        hours=24,
        id="purge_expired_ips",
        name="Purge Expired Login IPs",
        replace_existing=True,
    )

    # Add smart alert evaluation job (every 5 minutes by default)
    smart_alert_interval = int(os.getenv("SMART_ALERT_CHECK_INTERVAL_MINUTES", "5"))
    smart_alert_enabled = os.getenv("SMART_ALERT_ENABLED", "True").lower() == "true"
    if smart_alert_enabled:
        scheduler.add_job(
            scheduled_smart_alert_check,
            "interval",
            minutes=smart_alert_interval,
            id="smart_alert_check",
            name="Smart Alert Evaluation",
            replace_existing=True,
        )
        logger.info(f"Smart alert check scheduled every {smart_alert_interval} minute(s)")

    # Add monthly auto-retrain check
    retrain_interval_days = int(os.getenv("AUTO_RETRAIN_INTERVAL_DAYS", "30"))
    retrain_enabled = os.getenv("AUTO_RETRAIN_ENABLED", "True").lower() == "true"
    if retrain_enabled:
        # Support cron expression via AUTO_RETRAIN_CRON (e.g. "0 2 1 * *" = 2 AM on 1st of month)
        retrain_cron = os.getenv("AUTO_RETRAIN_CRON")
        if retrain_cron:
            try:
                parts = retrain_cron.strip().split()
                if len(parts) == 5:
                    cron_kwargs = {
                        "minute": parts[0],
                        "hour": parts[1],
                        "day": parts[2],
                        "month": parts[3],
                        "day_of_week": parts[4],
                    }
                    scheduler.add_job(
                        scheduled_auto_retrain,
                        "cron",
                        id="auto_retrain",
                        name="Automated Model Retraining (cron)",
                        replace_existing=True,
                        **cron_kwargs,
                    )
                    logger.info(f"Auto-retrain scheduled via cron: {retrain_cron}")
                else:
                    raise ValueError(f"Expected 5 fields, got {len(parts)}")
            except Exception as e:
                logger.warning(
                    f"Invalid AUTO_RETRAIN_CRON '{retrain_cron}': {e}. "
                    f"Falling back to interval ({retrain_interval_days} days)."
                )
                scheduler.add_job(
                    scheduled_auto_retrain,
                    "interval",
                    days=retrain_interval_days,
                    id="auto_retrain",
                    name="Automated Model Retraining Check",
                    replace_existing=True,
                )
                logger.info(f"Auto-retrain scheduled every {retrain_interval_days} day(s)")
        else:
            scheduler.add_job(
                scheduled_auto_retrain,
                "interval",
                days=retrain_interval_days,
                id="auto_retrain",
                name="Automated Model Retraining Check",
                replace_existing=True,
            )
            logger.info(f"Auto-retrain scheduled every {retrain_interval_days} day(s)")

    logger.info(f"Scheduler initialized with ingestion interval: {ingest_interval_minutes} minute(s)")
    _scheduler_initialized = True


def start():
    """
    Start the scheduler.

    Initializes jobs if not already done, then starts the scheduler.
    Safe to call multiple times - will not start if already running.
    """
    if scheduler.running:
        logger.debug("Scheduler already running.")
        return

    try:
        # Initialize jobs first
        init_scheduler()

        # Start the scheduler
        scheduler.start()
        logger.info("Background scheduler started successfully.")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {str(e)}", exc_info=True)


def shutdown():
    """Gracefully shutdown the scheduler and release lock."""
    global _scheduler_lock_fd

    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Scheduler shut down gracefully.")

    # Release the lock file
    if _scheduler_lock_fd:
        try:
            _scheduler_lock_fd.close()
            _scheduler_lock_fd = None
            logger.info("Released scheduler lock")
        except Exception as e:
            logger.warning(f"Error releasing scheduler lock: {str(e)}")
