"""
LGU Siren Trigger Integration Channel.

Provides an interface for triggering community flood warning sirens
in Parañaque City barangays.  Designed for future hardware integration
with LGU (Local Government Unit) infrastructure.

Current implementation:
    - HTTP API trigger to LGU siren control server (when available)
    - Fallback logging for testing / pre-deployment phase

Required environment variables:
    SIREN_API_URL   — LGU siren control API endpoint
    SIREN_API_KEY   — Authentication key for siren API

Optional:
    SIREN_SANDBOX_MODE        — "True" to skip real triggers
    SIREN_CRITICAL_ONLY       — "True" to only trigger for Critical risk
    SIREN_ACTIVATION_DURATION — Duration in seconds (default: 60)
    SIREN_ZONES               — Comma-separated default zone IDs
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from app.services.channels.base import NotificationChannel

logger = logging.getLogger(__name__)


class SirenTriggerChannel(NotificationChannel):
    """Activate LGU flood warning sirens via control API."""

    channel_id = "siren"
    display_name = "LGU Siren Trigger"

    def __init__(self, sandbox: bool = False):
        super().__init__(sandbox=sandbox)
        self._api_url = os.getenv("SIREN_API_URL", "")
        self._api_key = os.getenv("SIREN_API_KEY", "")
        self._critical_only = (
            os.getenv("SIREN_CRITICAL_ONLY", "True").lower() == "true"
        )
        self._default_duration = int(
            os.getenv("SIREN_ACTIVATION_DURATION", "60")
        )
        self._default_zones = [
            z.strip()
            for z in os.getenv("SIREN_ZONES", "").split(",")
            if z.strip()
        ]

    def is_configured(self) -> bool:
        return bool(self._api_url and self._api_key)

    # ------------------------------------------------------------------
    # Siren pattern mapping
    # ------------------------------------------------------------------

    _SIREN_PATTERNS: Dict[str, Dict[str, Any]] = {
        "Safe": {
            "pattern": "steady",
            "duration_sec": 10,
            "repeat": 1,
            "description": "Short acknowledgement tone",
        },
        "Alert": {
            "pattern": "wail",
            "duration_sec": 30,
            "repeat": 3,
            "description": "Rising-and-falling wail — evacuation advisory",
        },
        "Critical": {
            "pattern": "fast_pulse",
            "duration_sec": 60,
            "repeat": 5,
            "description": "Rapid pulsing — immediate evacuation required",
        },
    }

    # ------------------------------------------------------------------
    # Core send
    # ------------------------------------------------------------------

    def send(
        self,
        message: str,
        risk_label: str,
        location: str,
        recipients: Optional[List[str]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Trigger sirens at specified zones.

        ``recipients`` may contain zone IDs.  If empty, uses
        ``SIREN_ZONES`` default zones.

        Only triggers for ``Critical`` risk by default
        (configurable via ``SIREN_CRITICAL_ONLY``).
        """
        # Guard: skip non-critical if configured
        if self._critical_only and risk_label != "Critical":
            logger.info(
                "Siren trigger skipped — risk_label=%s (critical only mode)",
                risk_label,
            )
            return "skipped"

        zones = list(recipients) if recipients else self._default_zones
        if not zones:
            logger.warning("SirenTriggerChannel — no zones configured")
            return "not_configured"

        pattern = self._SIREN_PATTERNS.get(
            risk_label, self._SIREN_PATTERNS["Alert"]
        )

        payload = {
            "command": "activate",
            "zones": zones,
            "pattern": pattern["pattern"],
            "duration_sec": (extra or {}).get(
                "duration_sec", pattern["duration_sec"]
            ),
            "repeat": pattern["repeat"],
            "risk_label": risk_label,
            "location": location,
            "message": message[:500],
            "triggered_by": "floodingnaque_ews",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(
                f"{self._api_url}/api/v1/sirens/activate",
                json=payload,
                headers=headers,
                timeout=30,
            )

            if resp.status_code in (200, 201, 202):
                result = resp.json()
                activated = result.get("zones_activated", zones)
                logger.info(
                    "Siren activated — zones=%s, pattern=%s, duration=%ds",
                    activated,
                    pattern["pattern"],
                    pattern["duration_sec"],
                )
                return "delivered"
            else:
                logger.error(
                    "Siren API error: %s — %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return "failed"

        except requests.ConnectionError:
            logger.error(
                "Siren API unreachable at %s — "
                "logging trigger for manual follow-up",
                self._api_url,
            )
            self._log_offline_trigger(payload, zones)
            return "failed"

        except requests.RequestException as exc:
            logger.error("Siren trigger request error: %s", exc)
            return "failed"

    # ------------------------------------------------------------------
    # Offline fallback
    # ------------------------------------------------------------------

    def _log_offline_trigger(
        self, payload: Dict[str, Any], zones: List[str]
    ) -> None:
        """
        Log a trigger event when the siren API is unreachable.

        This ensures LGU operators can review missed activations
        and manually trigger sirens if needed.
        """
        logger.critical(
            "OFFLINE SIREN TRIGGER — Risk: %s | Zones: %s | "
            "Pattern: %s | Duration: %ds | "
            "MANUAL ACTIVATION REQUIRED",
            payload.get("risk_label"),
            zones,
            payload.get("pattern"),
            payload.get("duration_sec"),
        )

    # ------------------------------------------------------------------
    # Status / info
    # ------------------------------------------------------------------

    def get_info(self) -> Dict[str, Any]:
        info = super().get_info()
        info.update(
            {
                "critical_only": self._critical_only,
                "default_zones": self._default_zones,
                "default_duration_sec": self._default_duration,
                "siren_patterns": {
                    k: v["description"]
                    for k, v in self._SIREN_PATTERNS.items()
                },
            }
        )
        return info

    def get_siren_status(self) -> Dict[str, Any]:
        """Query the siren API for current hardware status."""
        if not self.is_configured():
            return {"status": "not_configured"}

        try:
            resp = requests.get(
                f"{self._api_url}/api/v1/sirens/status",
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json()
            return {"status": "error", "code": resp.status_code}
        except requests.RequestException as exc:
            return {"status": "offline", "error": str(exc)}
