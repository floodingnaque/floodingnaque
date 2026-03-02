"""
Base class for notification channels.

All channel implementations inherit from ``NotificationChannel`` and
override the ``send`` method.  The base class provides common
functionality for sandbox mode, logging, and status tracking.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class NotificationChannel(ABC):
    """
    Abstract base for notification channels.

    Sub-classes must implement :meth:`send`.  Common behaviour
    (sandbox gating, dry-run logging) lives here so individual
    channels stay lean.
    """

    channel_id: str = "base"
    display_name: str = "Base Channel"

    def __init__(self, sandbox: bool = False):
        self.sandbox = sandbox or os.getenv(
            f"{self.channel_id.upper()}_SANDBOX_MODE", "False"
        ).lower() == "true"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def dispatch(
        self,
        message: str,
        risk_label: str,
        location: str,
        recipients: Optional[List[str]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Dispatch an alert via this channel.

        Args:
            message: Formatted alert text.
            risk_label: Risk level label (Safe / Alert / Critical).
            location: Location name.
            recipients: Optional list of recipients (phone, email, chat id …).
            extra: Arbitrary channel-specific payload data.

        Returns:
            Delivery status string:
            ``delivered``, ``partial``, ``failed``, ``sandbox``, ``not_configured``.
        """
        if self.sandbox:
            logger.info(
                "[SANDBOX] %s alert would be sent — risk=%s, location=%s, recipients=%s",
                self.display_name,
                risk_label,
                location,
                recipients,
            )
            return "sandbox"

        if not self.is_configured():
            logger.warning(
                "%s channel not configured — skipping dispatch", self.display_name
            )
            return "not_configured"

        try:
            return self.send(
                message=message,
                risk_label=risk_label,
                location=location,
                recipients=recipients,
                extra=extra,
            )
        except Exception as exc:
            logger.error(
                "%s dispatch failed: %s", self.display_name, exc, exc_info=True
            )
            return "failed"

    # ------------------------------------------------------------------
    # Template methods
    # ------------------------------------------------------------------

    @abstractmethod
    def send(
        self,
        message: str,
        risk_label: str,
        location: str,
        recipients: Optional[List[str]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Perform the actual delivery.  Override in sub-classes.

        Returns delivery status string.
        """

    @abstractmethod
    def is_configured(self) -> bool:
        """Return *True* when all required credentials / env vars are present."""

    def get_info(self) -> Dict[str, Any]:
        """Return a JSON-serialisable description of this channel."""
        return {
            "id": self.channel_id,
            "name": self.display_name,
            "configured": self.is_configured(),
            "sandbox": self.sandbox,
        }
