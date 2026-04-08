"""GitHub Issue integration for creating incident tickets from triage output."""

from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv

from observability.logs import get_logger

logger = get_logger(__name__)


def _severity_label(severity: str) -> str:
    return severity.strip().lower()


def _build_issue_body(incident: dict[str, Any]) -> str:
    suggested = incident.get("suggested_actions") or []
    actions_block = "\n".join(f"- {item}" for item in suggested) if suggested else "- No suggestions provided"

    return (
        "## Incident Triage Report\n\n"
        f"- **Incident Type:** {incident.get('incident_type', 'unknown')}\n"
        f"- **Severity:** {incident.get('severity', 'unknown')}\n"
        f"- **Affected Plugin:** {incident.get('affected_plugin', 'unknown')}\n"
        f"- **Layer:** {incident.get('layer', 'unknown')}\n"
        f"- **Assigned Team:** {incident.get('assigned_team', 'unknown')}\n"
        f"- **Reporter Email:** {incident.get('reporter_email', 'unknown')}\n\n"
        "### Summary\n"
        f"{incident.get('summary', '')}\n\n"
        "### Suggested Actions\n"
        f"{actions_block}\n\n"
        "### Original Description\n"
        f"{incident.get('original_description', '')}\n"
    )


def create_ticket(incident: dict[str, Any]) -> dict[str, Any]:
    """Create a GitHub Issue and return basic ticket metadata."""
    load_dotenv()

    github_token = os.getenv("GITHUB_TOKEN", "").strip()
    github_repo = os.getenv("GITHUB_REPO", "").strip()

    if not github_token or not github_repo or "/" not in github_repo:
        logger.error(
            "github_ticket_config_invalid",
            extra={"service": "integrations", "node_name": "github.create_ticket"},
        )
        return {"ticket_id": None, "ticket_url": None, "ticket_number": None}

    severity = str(incident.get("severity", "P3"))
    incident_type = str(incident.get("incident_type", "Unknown Incident"))
    affected_plugin = str(incident.get("affected_plugin", "unknown"))
    assigned_team = str(incident.get("assigned_team", "unassigned")).strip().lower().replace(" ", "-")

    title = f"[{severity}] {incident_type} — {affected_plugin}"
    labels = [_severity_label(severity), assigned_team, "sre-agent"]

    payload = {
        "title": title,
        "body": _build_issue_body(incident),
        "labels": labels,
    }

    url = f"https://api.github.com/repos/{github_repo}/issues"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        result = {
            "ticket_id": data.get("id"),
            "ticket_url": data.get("html_url"),
            "ticket_number": data.get("number"),
        }

        logger.info(
            "github_ticket_created",
            extra={
                "service": "integrations",
                "node_name": "github.create_ticket",
                "incident_id": incident.get("incident_id"),
                "ticket_number": result.get("ticket_number"),
            },
        )
        return result
    except Exception:
        logger.exception(
            "github_ticket_create_failed",
            extra={
                "service": "integrations",
                "node_name": "github.create_ticket",
                "incident_id": incident.get("incident_id"),
            },
        )
        return {"ticket_id": None, "ticket_url": None, "ticket_number": None}
