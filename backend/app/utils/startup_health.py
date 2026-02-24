"""
Startup Health Validation for Floodingnaque.

Performs comprehensive health checks during application startup to verify:
- ML model loads successfully and version matches expected
- All required environment variables are set
- Database connection works
- Redis connection works (if configured)
- ML stack versions match training environment

Usage:
    from app.utils.startup_health import validate_startup_health, StartupHealthReport

    # At startup (in create_app)
    report = validate_startup_health(
        check_model=True,
        check_database=True,
        check_redis=True,
        raise_on_failure=True  # Fail fast in production
    )

    if not report.is_healthy:
        logger.error(f"Startup validation failed: {report.summary}")
"""

import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.utils.secrets import get_secret

logger = logging.getLogger(__name__)


class HealthCheckStatus(str, Enum):
    """Status of a health check."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"  # Functional but with warnings
    UNHEALTHY = "unhealthy"
    SKIPPED = "skipped"


class HealthCheckSeverity(str, Enum):
    """Severity of a health check failure."""

    CRITICAL = "critical"  # Prevents startup
    WARNING = "warning"  # Startup continues with warning
    INFO = "info"  # Informational only


@dataclass
class HealthCheckResult:
    """Result of a single health check."""

    name: str
    status: HealthCheckStatus
    message: str
    severity: HealthCheckSeverity = HealthCheckSeverity.INFO
    details: Dict[str, Any] = field(default_factory=dict)
    latency_ms: Optional[float] = None

    @property
    def is_healthy(self) -> bool:
        return self.status in (HealthCheckStatus.HEALTHY, HealthCheckStatus.SKIPPED)

    @property
    def is_critical_failure(self) -> bool:
        return self.status == HealthCheckStatus.UNHEALTHY and self.severity == HealthCheckSeverity.CRITICAL


@dataclass
class StartupHealthReport:
    """Aggregate report of all startup health checks."""

    checks: List[HealthCheckResult] = field(default_factory=list)
    timestamp: str = ""
    total_latency_ms: float = 0.0

    @property
    def is_healthy(self) -> bool:
        """True if no critical failures."""
        return not any(c.is_critical_failure for c in self.checks)

    @property
    def has_warnings(self) -> bool:
        """True if any warnings."""
        return any(
            c.status in (HealthCheckStatus.DEGRADED, HealthCheckStatus.UNHEALTHY)
            and c.severity == HealthCheckSeverity.WARNING
            for c in self.checks
        )

    @property
    def summary(self) -> str:
        """Get summary of health check results."""
        healthy = sum(1 for c in self.checks if c.is_healthy)
        total = len(self.checks)
        critical = sum(1 for c in self.checks if c.is_critical_failure)
        warnings = sum(1 for c in self.checks if c.status == HealthCheckStatus.DEGRADED)

        return f"{healthy}/{total} healthy, {critical} critical failures, {warnings} warnings"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "is_healthy": self.is_healthy,
            "has_warnings": self.has_warnings,
            "summary": self.summary,
            "timestamp": self.timestamp,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "checks": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "severity": c.severity.value,
                    "details": c.details,
                    "latency_ms": c.latency_ms,
                }
                for c in self.checks
            ],
        }


# =============================================================================
# REQUIRED ENVIRONMENT VARIABLES
# =============================================================================

REQUIRED_ENV_VARS = {
    # Required in production only
    "production": [
        "SECRET_KEY",
        "JWT_SECRET_KEY",
        "DATABASE_URL",
    ],
    # Required in all environments
    "all": [
        # None strictly required for development
    ],
    # Optional but recommended
    "recommended": [
        "SENTRY_DSN",
        "RATE_LIMIT_STORAGE_URL",
        "OPENWEATHERMAP_API_KEY",
    ],
}

# Default values that indicate unconfigured state
UNSAFE_DEFAULTS = {
    "SECRET_KEY": ["change-me-in-production", "change_this_to_a_random_secret_key_in_production"],
    "JWT_SECRET_KEY": ["change_this_to_another_random_secret_key"],
}


# =============================================================================
# HEALTH CHECK IMPLEMENTATIONS
# =============================================================================


def check_environment_variables() -> HealthCheckResult:
    """
    Verify all required environment variables are set.

    Checks:
    - Required variables for current environment (production/development)
    - Ensures secrets aren't using unsafe default values
    - Warns about recommended but missing variables
    """
    start = time.time()
    app_env = os.getenv("APP_ENV", "development").lower()
    is_production = app_env in ("production", "prod", "staging", "stage")

    missing_required = []
    using_unsafe_defaults = []
    missing_recommended = []

    # Check required variables
    required = REQUIRED_ENV_VARS.get("all", []).copy()
    if is_production:
        required.extend(REQUIRED_ENV_VARS.get("production", []))

    for var in required:
        value = os.getenv(var)
        if not value:
            missing_required.append(var)
        elif var in UNSAFE_DEFAULTS and value in UNSAFE_DEFAULTS[var]:
            using_unsafe_defaults.append(var)

    # Check recommended variables
    for var in REQUIRED_ENV_VARS.get("recommended", []):
        if not os.getenv(var):
            missing_recommended.append(var)

    latency_ms = (time.time() - start) * 1000

    # Determine status
    if missing_required or (is_production and using_unsafe_defaults):
        return HealthCheckResult(
            name="environment_variables",
            status=HealthCheckStatus.UNHEALTHY,
            message="Missing or unsafe environment variables",
            severity=HealthCheckSeverity.CRITICAL if is_production else HealthCheckSeverity.WARNING,
            details={
                "missing_required": missing_required,
                "using_unsafe_defaults": using_unsafe_defaults,
                "missing_recommended": missing_recommended,
                "environment": app_env,
            },
            latency_ms=latency_ms,
        )
    elif missing_recommended:
        return HealthCheckResult(
            name="environment_variables",
            status=HealthCheckStatus.DEGRADED,
            message=f"Some recommended variables not set: {', '.join(missing_recommended)}",
            severity=HealthCheckSeverity.WARNING,
            details={
                "missing_recommended": missing_recommended,
                "environment": app_env,
            },
            latency_ms=latency_ms,
        )
    else:
        return HealthCheckResult(
            name="environment_variables",
            status=HealthCheckStatus.HEALTHY,
            message="All environment variables configured",
            details={"environment": app_env},
            latency_ms=latency_ms,
        )


def check_ml_model() -> HealthCheckResult:
    """
    Verify ML model loads successfully.

    Checks:
    - Model file exists
    - Model loads without errors
    - Model version matches expected (if version tracking enabled)
    - ML stack versions compatible with training versions
    """
    start = time.time()

    try:
        from app.services.predict import get_current_model_info
        from app.utils.ml_version_check import check_model_training_versions, validate_ml_versions

        # Check ML stack versions first
        version_results = validate_ml_versions()
        version_issues = [r for r in version_results if r.status != "ok"]
        critical_version_issues = [r for r in version_results if r.severity == "error"]

        if critical_version_issues:
            latency_ms = (time.time() - start) * 1000
            return HealthCheckResult(
                name="ml_model",
                status=HealthCheckStatus.UNHEALTHY,
                message=f"ML stack version mismatch: {len(critical_version_issues)} critical issues",
                severity=HealthCheckSeverity.CRITICAL,
                details={
                    "version_issues": [
                        {"package": r.package, "expected": r.expected, "actual": r.actual, "message": r.message}
                        for r in critical_version_issues
                    ]
                },
                latency_ms=latency_ms,
            )

        # Try to load the model (get_current_model_info handles loading internally)
        try:
            model_info = get_current_model_info()
            if model_info is None:
                raise ValueError("Model could not be loaded")
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            return HealthCheckResult(
                name="ml_model",
                status=HealthCheckStatus.UNHEALTHY,
                message=f"Failed to load ML model: {str(e)}",
                severity=HealthCheckSeverity.CRITICAL,
                details={"error": str(e), "error_type": type(e).__name__},
                latency_ms=latency_ms,
            )

        # Check model training versions if available
        training_warnings = []
        if model_info and model_info.get("metadata") and "training_versions" in model_info.get("metadata", {}):
            training_warnings = check_model_training_versions(model_info.get("metadata", {}))

        latency_ms = (time.time() - start) * 1000

        # Get version from metadata
        version = "unknown"
        if model_info and model_info.get("metadata"):
            version = model_info["metadata"].get("version", "unknown")

        if version_issues or training_warnings:
            return HealthCheckResult(
                name="ml_model",
                status=HealthCheckStatus.DEGRADED,
                message=f"Model loaded with {len(version_issues)} version warnings",
                severity=HealthCheckSeverity.WARNING,
                details={
                    "model_info": model_info,
                    "version_warnings": [r.message for r in version_issues],
                    "training_warnings": training_warnings,
                },
                latency_ms=latency_ms,
            )
        else:
            return HealthCheckResult(
                name="ml_model",
                status=HealthCheckStatus.HEALTHY,
                message=f"Model loaded successfully: {version}",
                details={"model_info": model_info},
                latency_ms=latency_ms,
            )

    except ImportError as e:
        latency_ms = (time.time() - start) * 1000
        return HealthCheckResult(
            name="ml_model",
            status=HealthCheckStatus.UNHEALTHY,
            message=f"ML module import error: {str(e)}",
            severity=HealthCheckSeverity.CRITICAL,
            details={"import_error": str(e)},
            latency_ms=latency_ms,
        )
    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        return HealthCheckResult(
            name="ml_model",
            status=HealthCheckStatus.UNHEALTHY,
            message=f"Unexpected error during model check: {str(e)}",
            severity=HealthCheckSeverity.CRITICAL,
            details={"error": str(e), "error_type": type(e).__name__},
            latency_ms=latency_ms,
        )


def check_database() -> HealthCheckResult:
    """
    Verify database connection works.

    Checks:
    - Database URL is configured
    - Connection can be established
    - Basic query executes successfully
    """
    start = time.time()

    try:
        from app.models.db import get_db_session
        from sqlalchemy import text

        database_url = get_secret("DATABASE_URL", default="")
        is_sqlite = database_url.startswith("sqlite") or not database_url

        with get_db_session() as session:
            # Execute a simple query to test connection
            result = session.execute(text("SELECT 1"))
            result.fetchone()

        latency_ms = (time.time() - start) * 1000

        return HealthCheckResult(
            name="database",
            status=HealthCheckStatus.HEALTHY,
            message="Database connection successful",
            details={
                "type": "sqlite" if is_sqlite else "postgresql",
                "latency_ms": round(latency_ms, 2),
            },
            latency_ms=latency_ms,
        )

    except ImportError as e:
        latency_ms = (time.time() - start) * 1000
        return HealthCheckResult(
            name="database",
            status=HealthCheckStatus.UNHEALTHY,
            message=f"Database module import error: {str(e)}",
            severity=HealthCheckSeverity.CRITICAL,
            details={"import_error": str(e)},
            latency_ms=latency_ms,
        )
    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        return HealthCheckResult(
            name="database",
            status=HealthCheckStatus.UNHEALTHY,
            message=f"Database connection failed: {str(e)}",
            severity=HealthCheckSeverity.CRITICAL,
            details={"error": str(e), "error_type": type(e).__name__},
            latency_ms=latency_ms,
        )


def check_redis() -> HealthCheckResult:
    """
    Verify Redis connection works (if configured).

    Checks:
    - Redis URL is configured
    - Connection can be established
    - PING command succeeds
    """
    start = time.time()

    storage_url = os.getenv("RATE_LIMIT_STORAGE_URL", "memory://")

    if "redis" not in storage_url.lower():
        return HealthCheckResult(
            name="redis",
            status=HealthCheckStatus.SKIPPED,
            message="Redis not configured (using memory storage)",
            severity=HealthCheckSeverity.INFO,
            latency_ms=0,
        )

    try:
        from urllib.parse import urlparse

        import redis

        parsed = urlparse(storage_url)
        r = redis.Redis(
            host=parsed.hostname or "localhost",
            port=parsed.port or 6379,
            password=parsed.password,
            socket_timeout=5,
            socket_connect_timeout=5,
        )

        if r.ping():
            latency_ms = (time.time() - start) * 1000
            return HealthCheckResult(
                name="redis",
                status=HealthCheckStatus.HEALTHY,
                message="Redis connection successful",
                details={"host": parsed.hostname, "port": parsed.port},
                latency_ms=latency_ms,
            )
        else:
            latency_ms = (time.time() - start) * 1000
            return HealthCheckResult(
                name="redis",
                status=HealthCheckStatus.UNHEALTHY,
                message="Redis PING failed",
                severity=HealthCheckSeverity.WARNING,
                latency_ms=latency_ms,
            )

    except ImportError:
        latency_ms = (time.time() - start) * 1000
        return HealthCheckResult(
            name="redis",
            status=HealthCheckStatus.DEGRADED,
            message="Redis package not installed",
            severity=HealthCheckSeverity.WARNING,
            details={"suggestion": "pip install redis"},
            latency_ms=latency_ms,
        )
    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        return HealthCheckResult(
            name="redis",
            status=HealthCheckStatus.UNHEALTHY,
            message=f"Redis connection failed: {str(e)}",
            severity=HealthCheckSeverity.WARNING,  # Not critical - can fall back to memory
            details={"error": str(e), "error_type": type(e).__name__},
            latency_ms=latency_ms,
        )


def check_model_directory() -> HealthCheckResult:
    """
    Verify model directory exists and contains expected files.
    """
    start = time.time()

    models_dir = Path(os.getenv("MODELS_DIR", "models"))

    if not models_dir.exists():
        latency_ms = (time.time() - start) * 1000
        return HealthCheckResult(
            name="model_directory",
            status=HealthCheckStatus.UNHEALTHY,
            message=f"Models directory not found: {models_dir}",
            severity=HealthCheckSeverity.CRITICAL,
            details={"path": str(models_dir)},
            latency_ms=latency_ms,
        )

    # Find model files
    joblib_files = list(models_dir.glob("*.joblib"))
    json_files = list(models_dir.glob("*.json"))

    if not joblib_files:
        latency_ms = (time.time() - start) * 1000
        return HealthCheckResult(
            name="model_directory",
            status=HealthCheckStatus.UNHEALTHY,
            message="No .joblib model files found",
            severity=HealthCheckSeverity.CRITICAL,
            details={
                "path": str(models_dir),
                "files_found": [f.name for f in models_dir.iterdir()],
            },
            latency_ms=latency_ms,
        )

    latency_ms = (time.time() - start) * 1000
    return HealthCheckResult(
        name="model_directory",
        status=HealthCheckStatus.HEALTHY,
        message=f"Found {len(joblib_files)} model file(s)",
        details={
            "path": str(models_dir),
            "model_files": [f.name for f in joblib_files],
            "metadata_files": [f.name for f in json_files],
        },
        latency_ms=latency_ms,
    )


# =============================================================================
# MAIN VALIDATION FUNCTION
# =============================================================================


def validate_startup_health(
    check_env: bool = True,
    check_model: bool = True,
    check_database_conn: bool = True,
    check_redis_conn: bool = True,
    raise_on_failure: bool = False,
    log_results: bool = True,
) -> StartupHealthReport:
    """
    Perform comprehensive startup health validation.

    Args:
        check_env: Verify environment variables
        check_model: Verify ML model loads
        check_database_conn: Verify database connection
        check_redis_conn: Verify Redis connection (if configured)
        raise_on_failure: Raise RuntimeError if critical failures
        log_results: Log results to logger

    Returns:
        StartupHealthReport with all check results

    Raises:
        RuntimeError: If raise_on_failure is True and critical failures found
    """
    from datetime import datetime

    start_time = time.time()
    report = StartupHealthReport(
        timestamp=datetime.utcnow().isoformat(),
    )

    # Run checks
    if check_env:
        report.checks.append(check_environment_variables())

    if check_model:
        report.checks.append(check_model_directory())
        report.checks.append(check_ml_model())

    if check_database_conn:
        report.checks.append(check_database())

    if check_redis_conn:
        report.checks.append(check_redis())

    report.total_latency_ms = (time.time() - start_time) * 1000

    # Log results
    if log_results:
        log_startup_health_report(report)

    # Raise on critical failures if requested
    if raise_on_failure and not report.is_healthy:
        critical_failures = [c for c in report.checks if c.is_critical_failure]
        error_messages = [f"{c.name}: {c.message}" for c in critical_failures]
        raise RuntimeError(
            f"Startup health validation failed with {len(critical_failures)} critical issues:\n"
            + "\n".join(f"  - {msg}" for msg in error_messages)
        )

    return report


def log_startup_health_report(report: StartupHealthReport) -> None:
    """Log startup health report."""
    logger.info("=" * 60)
    logger.info("STARTUP HEALTH VALIDATION")
    logger.info("=" * 60)

    for check in report.checks:
        if check.status == HealthCheckStatus.HEALTHY:
            logger.info(f"  [OK] {check.name}: {check.message}")
        elif check.status == HealthCheckStatus.SKIPPED:
            logger.info(f"  [SKIP] {check.name}: {check.message}")
        elif check.status == HealthCheckStatus.DEGRADED:
            logger.warning(f"  [WARN] {check.name}: {check.message}")
        else:
            if check.severity == HealthCheckSeverity.CRITICAL:
                logger.error(f"  [FAIL] {check.name}: {check.message}")
            else:
                logger.warning(f"  [WARN] {check.name}: {check.message}")

    logger.info("-" * 60)
    logger.info(f"Summary: {report.summary}")
    logger.info(f"Total validation time: {report.total_latency_ms:.0f}ms")
    logger.info("=" * 60)

    if not report.is_healthy:
        logger.error("STARTUP VALIDATION FAILED - Application may not function correctly")
    elif report.has_warnings:
        logger.warning("Startup completed with warnings - review configuration")
    else:
        logger.info("Startup validation passed - all systems healthy")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def quick_health_check() -> Tuple[bool, str]:
    """
    Quick health check for readiness probes.

    Returns:
        Tuple of (is_healthy, message)
    """
    try:
        report = validate_startup_health(
            check_env=False,
            check_model=True,
            check_database_conn=True,
            check_redis_conn=False,
            raise_on_failure=False,
            log_results=False,
        )
        return report.is_healthy, report.summary
    except Exception as e:
        return False, f"Health check error: {str(e)}"


def get_startup_health_endpoint_data() -> Dict[str, Any]:
    """
    Get startup health data for API endpoint.

    Returns:
        Dictionary suitable for JSON response
    """
    report = validate_startup_health(
        raise_on_failure=False,
        log_results=False,
    )
    return report.to_dict()
