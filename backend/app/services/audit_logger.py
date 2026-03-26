"""Centralized Audit Logger Service.

Records security-relevant events (logins, role changes, failed auth,
RBAC violations, password resets, etc.) for compliance and forensics.

Events are persisted to the ``audit_logs`` table and optionally emitted
to the Python logger at WARNING or higher for SIEM integration.
"""

import logging
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from flask import g, has_request_context, request

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Audit event taxonomy
# ---------------------------------------------------------------------------


class AuditAction(str, Enum):
    """Enumerated audit event types."""

    # Authentication
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"  # nosec B105 - enum label, not a password
    TOKEN_REVOKED = "token_revoked"  # nosec B105

    # Account lifecycle
    ACCOUNT_CREATED = "account_created"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    ACCOUNT_DEACTIVATED = "account_deactivated"
    ACCOUNT_REACTIVATED = "account_reactivated"
    ACCOUNT_DELETED = "account_deleted"

    # Password management
    PASSWORD_CHANGED = "password_changed"  # nosec B105 - enum label, not a password
    PASSWORD_RESET_REQUESTED = "password_reset_requested"  # nosec B105
    PASSWORD_RESET_COMPLETED = "password_reset_completed"  # nosec B105

    # Authorization
    ROLE_CHANGED = "role_changed"
    ACCESS_DENIED = "access_denied"
    RATE_LIMITED = "rate_limited"

    # Data operations
    DATA_EXPORTED = "data_exported"
    DATA_UPLOADED = "data_uploaded"
    DATA_DELETED = "data_deleted"

    # Model / system
    MODEL_RETRAINED = "model_retrained"
    MODEL_ROLLED_BACK = "model_rolled_back"
    CONFIG_CHANGED = "config_changed"
    FEATURE_FLAG_TOGGLED = "feature_flag_toggled"

    # Security incidents
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    CSRF_VIOLATION = "csrf_violation"
    INVALID_TOKEN = "invalid_token"  # nosec B105 - enum label, not a password


class AuditSeverity(str, Enum):
    """Severity classification for audit events."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# Severity mapping per action
_ACTION_SEVERITY: Dict[AuditAction, AuditSeverity] = {
    AuditAction.LOGIN_SUCCESS: AuditSeverity.INFO,
    AuditAction.LOGIN_FAILED: AuditSeverity.WARNING,
    AuditAction.LOGOUT: AuditSeverity.INFO,
    AuditAction.TOKEN_REFRESH: AuditSeverity.INFO,
    AuditAction.TOKEN_REVOKED: AuditSeverity.WARNING,
    AuditAction.ACCOUNT_CREATED: AuditSeverity.INFO,
    AuditAction.ACCOUNT_LOCKED: AuditSeverity.WARNING,
    AuditAction.ACCOUNT_UNLOCKED: AuditSeverity.INFO,
    AuditAction.ACCOUNT_DEACTIVATED: AuditSeverity.WARNING,
    AuditAction.ACCOUNT_REACTIVATED: AuditSeverity.INFO,
    AuditAction.ACCOUNT_DELETED: AuditSeverity.CRITICAL,
    AuditAction.PASSWORD_CHANGED: AuditSeverity.INFO,
    AuditAction.PASSWORD_RESET_REQUESTED: AuditSeverity.INFO,
    AuditAction.PASSWORD_RESET_COMPLETED: AuditSeverity.WARNING,
    AuditAction.ROLE_CHANGED: AuditSeverity.CRITICAL,
    AuditAction.ACCESS_DENIED: AuditSeverity.WARNING,
    AuditAction.RATE_LIMITED: AuditSeverity.WARNING,
    AuditAction.DATA_EXPORTED: AuditSeverity.INFO,
    AuditAction.DATA_UPLOADED: AuditSeverity.INFO,
    AuditAction.DATA_DELETED: AuditSeverity.CRITICAL,
    AuditAction.MODEL_RETRAINED: AuditSeverity.INFO,
    AuditAction.MODEL_ROLLED_BACK: AuditSeverity.CRITICAL,
    AuditAction.CONFIG_CHANGED: AuditSeverity.WARNING,
    AuditAction.FEATURE_FLAG_TOGGLED: AuditSeverity.WARNING,
    AuditAction.SUSPICIOUS_ACTIVITY: AuditSeverity.CRITICAL,
    AuditAction.CSRF_VIOLATION: AuditSeverity.CRITICAL,
    AuditAction.INVALID_TOKEN: AuditSeverity.WARNING,
}

# ---------------------------------------------------------------------------
# In-memory buffer for batch writes
# ---------------------------------------------------------------------------

_buffer: list = []
_buffer_lock = threading.Lock()
_BUFFER_FLUSH_SIZE = 20


def _flush_buffer() -> None:
    """Persist buffered audit events to the database."""
    with _buffer_lock:
        if not _buffer:
            return
        batch = list(_buffer)
        _buffer.clear()

    try:
        from app.models.audit_log import AuditLog
        from app.models.db import get_db_session

        with get_db_session() as session:
            for entry in batch:
                session.add(AuditLog(**entry))
    except Exception as exc:
        logger.error("Failed to flush audit log buffer: %s", exc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def log_audit_event(
    action: AuditAction,
    *,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    target_user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> None:
    """Record a single audit event.

    Parameters are best-effort extracted from the Flask request context
    when not explicitly provided.
    """
    import json

    # Auto-populate from Flask request context when available
    if has_request_context():
        if ip_address is None:
            ip_address = request.remote_addr or "unknown"
        if user_agent is None:
            user_agent = (request.headers.get("User-Agent") or "")[:500]
        if request_id is None:
            request_id = getattr(g, "request_id", None)
        if user_id is None:
            user_id = getattr(g, "current_user_id", None)
        if user_email is None:
            user_email = getattr(g, "current_user_email", None)

    severity = _ACTION_SEVERITY.get(action, AuditSeverity.INFO)

    entry = {
        "action": action.value,
        "severity": severity.value,
        "user_id": user_id,
        "user_email": user_email,
        "target_user_id": target_user_id,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "details": json.dumps(details) if details else None,
        "request_id": request_id,
        "created_at": datetime.now(timezone.utc),
    }

    # Emit to Python logger for SIEM / file-based collection
    log_level = {
        AuditSeverity.INFO: logging.INFO,
        AuditSeverity.WARNING: logging.WARNING,
        AuditSeverity.CRITICAL: logging.CRITICAL,
    }.get(severity, logging.INFO)

    logger.log(
        log_level,
        "AUDIT | %s | user=%s | ip=%s | %s",
        action.value,
        user_email or user_id or "anonymous",
        ip_address or "unknown",
        details or "",
    )

    # Buffer for batch DB write
    with _buffer_lock:
        _buffer.append(entry)
        if len(_buffer) >= _BUFFER_FLUSH_SIZE:
            _flush_buffer()


def flush() -> None:
    """Force-flush any pending audit events to the database."""
    _flush_buffer()


# Convenience helpers ----------------------------------------------------------


def audit_login_success(user_id: int, email: str) -> None:
    log_audit_event(AuditAction.LOGIN_SUCCESS, user_id=user_id, user_email=email)


def audit_login_failed(email: str, reason: str = "invalid_credentials") -> None:
    log_audit_event(AuditAction.LOGIN_FAILED, user_email=email, details={"reason": reason})


def audit_access_denied(resource: str) -> None:
    log_audit_event(AuditAction.ACCESS_DENIED, details={"resource": resource})


def audit_role_changed(target_user_id: int, old_role: str, new_role: str) -> None:
    log_audit_event(
        AuditAction.ROLE_CHANGED,
        target_user_id=target_user_id,
        details={"old_role": old_role, "new_role": new_role},
    )


def audit_rate_limited(endpoint: str) -> None:
    log_audit_event(AuditAction.RATE_LIMITED, details={"endpoint": endpoint})


def audit_data_exported(export_type: str, record_count: int) -> None:
    log_audit_event(AuditAction.DATA_EXPORTED, details={"type": export_type, "records": record_count})
