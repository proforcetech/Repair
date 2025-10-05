# backend/app/core/notifier.py

## This file handles email notifications for the application.
# It uses the aiosmtplib library to send emails asynchronously.
# It constructs an email message with the specified recipient, subject, and body.
# Make sure to set the SMTP configuration in your environment variables.
from __future__ import annotations

import asyncio
import functools
import logging
import os
from email.message import EmailMessage
from importlib import util as importlib_util
from typing import Any, Protocol

import aiosmtplib
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

__all__ = [
    "send_email",
    "send_sms",
    "notify_slack",
    "notify_user",
    "get_sms_provider",
    "set_sms_provider",
    "TwilioSMSProvider",
]
load_dotenv()


# This module handles email notifications for the application.
async def send_email(to_email: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = os.getenv("EMAIL_FROM", "noreply@repairshop.com")
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    await aiosmtplib.send(
        msg,
        hostname=os.getenv("SMTP_HOST"),
        port=int(os.getenv("SMTP_PORT", 587)),
        username=os.getenv("SMTP_USER"),
        password=os.getenv("SMTP_PASS"),
        start_tls=True,
    )


class SMSProvider(Protocol):
    """Protocol describing an async-capable SMS provider."""

    async def send(self, phone: str, body: str) -> None:  # pragma: no cover - protocol
        """Deliver ``body`` to ``phone``."""


class ConsoleSMSProvider:
    """Fallback provider that logs SMS payloads for debugging."""

    async def send(self, phone: str, body: str) -> None:
        logger.info("SMS to %s: %s", phone, body)


_twilio_package_spec = importlib_util.find_spec("twilio")
_twilio_rest_spec = importlib_util.find_spec("twilio.rest") if _twilio_package_spec else None
if _twilio_package_spec and _twilio_rest_spec:
    from twilio.rest import Client as TwilioClient  # type: ignore[conditional-import]
else:  # pragma: no cover - exercised when twilio isn't installed
    TwilioClient = None  # type: ignore[assignment]


class TwilioSMSProvider:
    """Async wrapper around the synchronous Twilio REST client."""

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        *,
        client: Any | None = None,
    ) -> None:
        if client is None:
            if TwilioClient is None:  # pragma: no cover - requires optional dependency
                raise RuntimeError("twilio package is not installed")
            client = TwilioClient(account_sid, auth_token)

        self._client = client
        self._from_number = from_number

    async def send(self, phone: str, body: str) -> None:
        loop = asyncio.get_running_loop()
        create_message = functools.partial(
            self._client.messages.create,
            to=phone,
            from_=self._from_number,
            body=body,
        )
        await loop.run_in_executor(None, create_message)


_sms_provider: SMSProvider | None = None


def set_sms_provider(provider: SMSProvider | None) -> None:
    """Override the global SMS provider used by :func:`send_sms`."""

    global _sms_provider
    _sms_provider = provider


def get_sms_provider() -> SMSProvider:
    """Return the configured SMS provider, initialising the default as needed."""

    global _sms_provider
    if _sms_provider is None:
        _sms_provider = _build_default_sms_provider()
    return _sms_provider


def _build_default_sms_provider() -> SMSProvider:
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")

    if account_sid and auth_token and from_number:
        if TwilioClient is None:
            logger.warning(
                "Twilio credentials provided but the twilio package is not installed; "
                "falling back to console SMS provider."
            )
        else:
            return TwilioSMSProvider(account_sid, auth_token, from_number)

    return ConsoleSMSProvider()


async def send_sms(phone: str, body: str) -> None:
    """Send an SMS notification using the configured provider."""

    provider = get_sms_provider()
    await provider.send(phone, body)


async def notify_slack(channel: str, message: str, **_: Any) -> None:
    """Send a Slack notification (stub implementation)."""

    # Production code would post to a webhook URL. Tests can monkeypatch this
    # coroutine to assert that the alert logic attempted to notify Slack.
    return None


# This function sends a notification email to the user.
# It reuses the async SMTP helper above so the same configuration applies
# everywhere we send mail from the platform.
async def notify_user(email: str, subject: str, body: str) -> None:
    """Notify a user via email using the async SMTP helper."""

    await send_email(email, subject, body)

