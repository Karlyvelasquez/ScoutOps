"""Slack webhook integration for engineering team incident notifications."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from dotenv import load_dotenv

from observability.logs import get_logger

logger = get_logger(__name__)


def _normalize_team(team: str) -> str:
    return team.strip().lower().replace(" ", "-")


def _load_team_webhook_map() -> dict[str, str]:
    raw = os.getenv("SLACK_TEAM_WEBHOOKS_JSON", "").strip()
    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return {}

        result: dict[str, str] = {}
        for team, webhook in parsed.items():
            if isinstance(team, str) and isinstance(webhook, str) and webhook.strip():
                result[_normalize_team(team)] = webhook.strip()
        return result
    except Exception:
        logger.exception(
            "slack_team_webhook_map_parse_failed",
            extra={"service": "integrations", "node_name": "slack.notify_team"},
        )
        return {}


def _resolve_webhook_url(assigned_team: str) -> str:
    team_map = _load_team_webhook_map()
    normalized_team = _normalize_team(assigned_team)
    if normalized_team in team_map:
        return team_map[normalized_team]
    return os.getenv("SLACK_WEBHOOK_URL", "").strip()


def _severity_emoji(severity: str) -> str:
    mapping = {"P1": ":red_circle:", "P2": ":large_orange_circle:", "P3": ":large_yellow_circle:"}
    return mapping.get(severity.upper(), ":large_blue_circle:")


def notify_team(incident: dict[str, Any], ticket_url: str) -> bool:
    """Send a formatted Slack Block Kit alert for a newly created incident ticket."""
    load_dotenv()

    assigned_team = str(incident.get("assigned_team", "unassigned"))
    webhook_url = _resolve_webhook_url(assigned_team)
    if not webhook_url:
        logger.error(
            "slack_webhook_not_configured",
            extra={"service": "integrations", "node_name": "slack.notify_team"},
        )
        return False

    severity = str(incident.get("severity", "P3"))
    incident_type = str(incident.get("incident_type", "Unknown Incident"))
    affected_plugin = str(incident.get("affected_plugin", "unknown"))
    summary = str(incident.get("summary", "No summary provided"))
    is_escalated = bool(incident.get("escalated", False))
    confidence = incident.get("confidence_score")
    confidence_str = f"{float(confidence)*100:.0f}%" if confidence is not None else "N/A"

    if is_escalated:
        header_text = f":warning: HUMAN REVIEW REQUIRED — {severity} Incident: {incident_type}"
    else:
        header_text = f"{_severity_emoji(severity)} {severity} Incident: {incident_type}"

    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": header_text},
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
    ]

    if is_escalated:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":lock: *Agent confidence: {confidence_str}* (below 70% threshold). Ticket NOT auto-created. Manual triage required.",
            },
        })
    else:
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Open Ticket"},
                    "url": ticket_url,
                    "style": "primary",
                }
            ],
        })

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
