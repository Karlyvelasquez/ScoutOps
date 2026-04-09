"""Jira Cloud integration for creating incident tickets from triage output."""

from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv

from observability.logs import get_logger

logger = get_logger(__name__)


def _priority_from_severity(severity: str) -> str:
    mapping = {
        "P1": "Highest",
        "P2": "High",
        "P3": "Medium",
    }
    return mapping.get(str(severity).upper(), "Medium")


def _adf_heading(text: str) -> dict[str, Any]:
    return {
        "type": "heading",
        "attrs": {"level": 3},
        "content": [{"type": "text", "text": text}],
    }


def _adf_paragraph(text: str) -> dict[str, Any]:
    return {
        "type": "paragraph",
        "content": [{"type": "text", "text": text}],
    }


def _adf_bullet_list(items: list[str]) -> dict[str, Any]:
    bullet_items: list[dict[str, Any]] = []
    for item in items:
        bullet_items.append(
            {
                "type": "listItem",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": str(item)}],
                    }
                ],
            }
        )

    return {
        "type": "bulletList",
        "content": bullet_items,
    }


def _build_adf_description(incident: dict[str, Any]) -> dict[str, Any]:
    suggested_actions_raw = incident.get("suggested_actions") or []
    suggested_actions = [str(action) for action in suggested_actions_raw]

    content: list[dict[str, Any]] = [
        _adf_heading("Summary"),
        _adf_paragraph(str(incident.get("summary", "No summary provided"))),
        _adf_heading("Affected Layer"),
        _adf_paragraph(str(incident.get("layer", "unknown"))),
        _adf_heading("Assigned Team"),
        _adf_paragraph(str(incident.get("assigned_team", "unknown"))),
        _adf_heading("Suggested Actions"),
    ]

    if suggested_actions:
        content.append(_adf_bullet_list(suggested_actions))
    else:
        content.append(_adf_paragraph("No suggested actions provided"))

    content.extend(
        [
            _adf_heading("Original Description"),
            _adf_paragraph(str(incident.get("original_description", ""))),
        ]
    )

    return {
        "type": "doc",
        "version": 1,
        "content": content,
    }


async def create_ticket(incident: dict[str, Any]) -> dict[str, Any]:
    """Create a Jira issue and return basic ticket metadata."""
    load_dotenv()

    jira_base_url = os.getenv("JIRA_BASE_URL", "").strip().rstrip("/")
    jira_email = os.getenv("JIRA_EMAIL", "").strip()
    jira_api_token = os.getenv("JIRA_API_TOKEN", "").strip()
    jira_project_key = os.getenv("JIRA_PROJECT_KEY", "").strip()

    if not jira_base_url or not jira_email or not jira_api_token or not jira_project_key:
        logger.error(
            "jira_ticket_config_invalid",
            extra={"service": "integrations", "node_name": "jira.create_ticket"},
        )
        return {"ticket_id": None, "ticket_url": None, "ticket_key": None}

    severity = str(incident.get("severity", "P3")).upper()
    incident_type = str(incident.get("incident_type", "unknown"))
    affected_plugin = str(incident.get("affected_plugin", "unknown"))
    assigned_team = str(incident.get("assigned_team", "unassigned")).strip().lower().replace(" ", "-")

    issue_summary = f"[{severity}] {incident_type} — {affected_plugin}"
    issue_url = f"{jira_base_url}/rest/api/3/issue"

    payload: dict[str, Any] = {
        "fields": {
            "project": {"key": jira_project_key},
            "summary": issue_summary,
            "description": _build_adf_description(incident),
            "issuetype": {"name": "Bug"},
            "priority": {"name": _priority_from_severity(severity)},
            "labels": [assigned_team, "sre-agent"],
        }
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                issue_url,
                auth=(jira_email, jira_api_token),
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        ticket_key = str(data.get("key", ""))
        result = {
            "ticket_id": data.get("id"),
            "ticket_url": f"{jira_base_url}/browse/{ticket_key}" if ticket_key else None,
            "ticket_key": ticket_key or None,
        }

        logger.info(
            "jira_ticket_created",
            extra={
                "service": "integrations",
                "node_name": "jira.create_ticket",
                "incident_id": incident.get("incident_id"),
                "ticket_key": result.get("ticket_key"),
            },
        )
        return result
    except httpx.HTTPStatusError as exc:
        response_text = ""
        status_code = None
        if exc.response is not None:
            status_code = exc.response.status_code
            response_text = exc.response.text

        logger.exception(
            "jira_ticket_create_http_failed",
            extra={
                "service": "integrations",
                "node_name": "jira.create_ticket",
                "incident_id": incident.get("incident_id"),
                "status_code": status_code,
                "response_text": response_text,
            },
        )
        return {"ticket_id": None, "ticket_url": None, "ticket_key": None}
    except Exception:
        logger.exception(
            "jira_ticket_create_failed",
            extra={
                "service": "integrations",
                "node_name": "jira.create_ticket",
                "incident_id": incident.get("incident_id"),
            },
        )
        return {"ticket_id": None, "ticket_url": None, "ticket_key": None}
