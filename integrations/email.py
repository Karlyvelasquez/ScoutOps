"""Async email integration used to notify incident reporters after resolution."""

from __future__ import annotations

import os
import importlib
from email.message import EmailMessage

from dotenv import load_dotenv

from observability.logs import get_logger

logger = get_logger(__name__)


def _smtp_is_configured(host: str, port: int, user: str, password: str) -> bool:
    return bool(host and port and user and password)


async def notify_reporter(reporter_email: str, ticket_url: str, resolution_summary: str) -> bool:
    """Notify the incident reporter that their ticket has been resolved."""
    load_dotenv()

    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "0") or "0")
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_password = os.getenv("SMTP_PASSWORD", "").strip()

    if not _smtp_is_configured(smtp_host, smtp_port, smtp_user, smtp_password):
        logger.info(
            "email_mock_mode_notification",
            extra={
                "service": "integrations",
                "node_name": "email.notify_reporter",
                "incident_id": None,
                "reporter_email": reporter_email,
                "ticket_url": ticket_url,
            },
        )
        return True

    message = EmailMessage()
    message["From"] = smtp_user
    message["To"] = reporter_email
    message["Subject"] = "Your incident report has been resolved"
    message.set_content(
        "Hello,\n\n"
        "Your reported incident has been resolved by the engineering team.\n\n"
        f"Ticket: {ticket_url}\n"
        f"Resolution summary: {resolution_summary}\n\n"
        "Thank you for helping us improve reliability.\n"
    )

    try:
        aiosmtplib = importlib.import_module("aiosmtplib")

        await aiosmtplib.send(
            message,
            hostname=smtp_host,
            port=smtp_port,
            username=smtp_user,
            password=smtp_password,
            start_tls=True,
            timeout=20.0,
        )
        logger.info(
            "email_notification_sent",
            extra={
                "service": "integrations",
                "node_name": "email.notify_reporter",
                "incident_id": None,
                "reporter_email": reporter_email,
            },
        )
        return True
    except Exception:
        logger.exception(
            "email_notification_failed",
            extra={
                "service": "integrations",
                "node_name": "email.notify_reporter",
                "incident_id": None,
                "reporter_email": reporter_email,
            },
        )
        return False
