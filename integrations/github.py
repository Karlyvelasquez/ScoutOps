"""GitHub Issue integration for creating incident tickets from triage output."""

from __future__ import annotations

import os
from typing import Any, Optional

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
        f"- **Assigned Team:** {incident.get('assigned_team', 'unknown')}\n\n"
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


def search_similar_issues(incident_type: str, affected_plugin: str) -> Optional[dict[str, Any]]:
    """Search open GitHub Issues with matching incident_type and affected_plugin in title.

    Returns the first match as {number, title, html_url}, or None if not found.
    """
    load_dotenv()

    github_token = os.getenv("GITHUB_TOKEN", "").strip()
    github_repo = os.getenv("GITHUB_REPO", "").strip()

    if not github_token or not github_repo or "/" not in github_repo:
        return None

    query = f"repo:{github_repo} is:issue is:open {incident_type} in:title"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                "https://api.github.com/search/issues",
                params={"q": query, "per_page": 10},
                headers=headers,
            )
            response.raise_for_status()
            items = response.json().get("items", [])

        plugin_lower = affected_plugin.lower()
        type_lower = incident_type.lower()
        for item in items:
            title_lower = item.get("title", "").lower()
            if plugin_lower in title_lower or type_lower in title_lower:
                result = {
                    "number": item["number"],
                    "title": item["title"],
                    "html_url": item["html_url"],
                }
                logger.info(
                    "github_duplicate_issue_found",
                    extra={
                        "service": "integrations",
                        "node_name": "github.search_similar_issues",
                        "matched_issue_number": result["number"],
                    },
                )
                return result

        return None

    except Exception:
        logger.exception(
            "github_search_issues_failed",
            extra={"service": "integrations", "node_name": "github.search_similar_issues"},
        )
        return None


def is_issue_open(issue_number: int) -> bool:
    """Return True if the GitHub Issue is still open, False if closed or not found."""
    load_dotenv()

    github_token = os.getenv("GITHUB_TOKEN", "").strip()
    github_repo = os.getenv("GITHUB_REPO", "").strip()

    if not github_token or not github_repo or "/" not in github_repo:
        return True

    url = f"https://api.github.com/repos/{github_repo}/issues/{issue_number}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            return response.json().get("state") == "open"
    except Exception:
        logger.exception(
            "github_get_issue_state_failed",
            extra={"service": "integrations", "node_name": "github.is_issue_open", "issue_number": issue_number},
        )
        return True


def add_comment_to_issue(issue_number: int, comment: str) -> dict[str, Any]:
    """Add a comment to an existing GitHub Issue."""
    load_dotenv()

    github_token = os.getenv("GITHUB_TOKEN", "").strip()
    github_repo = os.getenv("GITHUB_REPO", "").strip()

    if not github_token or not github_repo or "/" not in github_repo:
        return {}

    url = f"https://api.github.com/repos/{github_repo}/issues/{issue_number}/comments"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(url, headers=headers, json={"body": comment})
            response.raise_for_status()
            data = response.json()

        result = {
            "comment_id": data.get("id"),
            "comment_url": data.get("html_url"),
        }
        logger.info(
            "github_comment_added",
            extra={
                "service": "integrations",
                "node_name": "github.add_comment_to_issue",
                "issue_number": issue_number,
                "comment_id": result.get("comment_id"),
            },
        )
        return result

    except Exception:
        logger.exception(
            "github_add_comment_failed",
            extra={
                "service": "integrations",
                "node_name": "github.add_comment_to_issue",
                "issue_number": issue_number,
            },
        )
        return {}
