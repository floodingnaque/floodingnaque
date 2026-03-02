"""
Multi-Channel Alert Notification Modules.

This package provides pluggable notification channels for the
Floodingnaque flood early warning system.

Channels:
    - firebase_push : Firebase Cloud Messaging (mobile push notifications)
    - email_alerts  : SMTP-based email alert delivery
    - messenger_bot : Facebook Messenger chatbot integration
    - telegram_bot  : Telegram Bot API integration
    - siren_trigger : LGU siren activation (future hardware integration)
"""

from app.services.channels.email_alerts import EmailAlertChannel
from app.services.channels.firebase_push import FirebasePushChannel
from app.services.channels.messenger_bot import MessengerBotChannel
from app.services.channels.siren_trigger import SirenTriggerChannel
from app.services.channels.telegram_bot import TelegramBotChannel

__all__ = [
    "FirebasePushChannel",
    "EmailAlertChannel",
    "MessengerBotChannel",
    "TelegramBotChannel",
    "SirenTriggerChannel",
]
