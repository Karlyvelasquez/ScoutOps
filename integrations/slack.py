"""Slack webhook integration for engineering team incident notifications."""

from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv

from observability.logs import get_logger

logger = get_logger(__name__)


def _severity_emoji(severity: str) -> str:
    mapping = {"P1": ":red_circle:", "P2": ":large_orange_circle:", "P3": ":large_yellow_circle:"}
    return mapping.get(severity.upper(), ":large_blue_circle:")


def notify_team(incident: dict[str, Any], ticket_url: str) -> bool:
    """Send a formatted Slack Block Kit alert for a newly created incident ticket."""
    load_dotenv()

    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if not webhook_url:
        logger.error(
            "slack_webhook_not_configured",
            extra={"service": "integrations", "node_name": "slack.notify_team"},
        )
        return False

    severity = str(incident.get("severity", "P3"))
    incident_type = str(incident.get("incident_type", "Unknown Incident"))
    affected_plugin = str(incident.get("affected_plugin", "unknown"))
    assigned_team = str(incident.get("assigned_team", "unassigned"))
    summary = str(incident.get("summary", "No summary provided"))

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{_severity_emoji(severity)} {severity} Incident: {incident_type}",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Affected Plugin*\n{affected_plugin}"},
                {"type": "mrkdwn", "text": f"*Assigned Team*\n{assigned_team}"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Summary*\n{summary}"},
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Open Ticket"},
                    "url": ticket_url,
                    "style": "primary",
                }
            ],
        },
    ]

    payload = {"blocks": blocks}

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(webhook_url, json=payload)
            response.raise_for_status()

        logger.info(
            "slack_notification_sent",
            extra={
                "service": "integrations",
                "node_name": "slack.notify_team",
                "incident_id": incident.get("incident_id"),
            },
        )
        return True
    except Exception:
        logger.exception(
            "slack_notification_failed",
            extra={
                "service": "integrations",
                "node_name": "slack.notify_team",
                "incident_id": incident.get("incident_id"),
            },
        )
        return False
