"""Async background watcher that syncs ticket status from GitHub/Jira into SQLite."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any

import httpx
from dotenv import load_dotenv

from app.db.queries import (
    get_open_tickets,
    get_ticket_by_github_number,
    get_ticket_by_jira_key,
    update_ticket_status,
)
from observability.logs import get_logger

logger = get_logger(__name__)


def _poll_seconds() -> int:
    raw = os.getenv("RESOLUTION_WATCHER_POLL_SECONDS", "30").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 30
    return max(5, value)


async def _fetch_github_issue(
    *, github_repo: str, github_token: str, issue_number: int
) -> dict[str, Any] | None:
    url = f"https://api.github.com/repos/{github_repo}/issues/{issue_number}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
    except Exception:
        logger.exception(
            "resolution_watcher_github_fetch_failed",
            extra={"service": "backend", "node_name": "resolution_watcher", "incident_id": str(issue_number)},
        )
        return None


async def _fetch_jira_issue(
    *, jira_base_url: str, jira_email: str, jira_api_token: str, jira_key: str
) -> dict[str, Any] | None:
    url = f"{jira_base_url.rstrip('/')}/rest/api/3/issue/{jira_key}"
    headers = {"Accept": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, auth=(jira_email, jira_api_token), headers=headers)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
    except Exception:
        logger.exception(
            "resolution_watcher_jira_fetch_failed",
            extra={"service": "backend", "node_name": "resolution_watcher", "incident_id": jira_key},
        )
        return None


def _jira_done(status_name: str) -> bool:
    return status_name.strip().lower() == "done"


async def _sync_one_ticket(
    ticket: dict[str, Any],
    *,
    github_repo: str,
    github_token: str,
    jira_base_url: str,
    jira_email: str,
    jira_api_token: str,
) -> None:
    incident_id = str(ticket.get("id", ""))
    if not incident_id:
        return

    now_iso = datetime.now(timezone.utc).isoformat()
    status_updated = False

    github_ticket_number = ticket.get("github_ticket_number")
    if github_ticket_number is not None:
        github_issue = await _fetch_github_issue(
            github_repo=github_repo,
            github_token=github_token,
            issue_number=int(github_ticket_number),
        )
        if github_issue is not None and str(github_issue.get("state", "")).lower() == "closed":
            ticket_row = await get_ticket_by_github_number(int(github_ticket_number))
            if ticket_row is not None:
                incident_id = str(ticket_row.get("id", incident_id))
                await update_ticket_status(incident_id=incident_id, status="resolved", resolved_at=now_iso)
                status_updated = True

    if not status_updated:
        jira_ticket_key = str(ticket.get("jira_ticket_key") or "").strip()
        if jira_ticket_key:
            jira_issue = await _fetch_jira_issue(
                jira_base_url=jira_base_url,
                jira_email=jira_email,
                jira_api_token=jira_api_token,
                jira_key=jira_ticket_key,
            )
            if jira_issue is not None:
                status_name = str(
                    ((jira_issue.get("fields") or {}).get("status") or {}).get("name", "")
                )
                if _jira_done(status_name):
                    ticket_row = await get_ticket_by_jira_key(jira_ticket_key)
                    if ticket_row is not None:
                        incident_id = str(ticket_row.get("id", incident_id))
                        await update_ticket_status(incident_id=incident_id, status="resolved", resolved_at=now_iso)
                        status_updated = True


async def start_resolution_watcher() -> None:
    """Continuously sync open tickets to resolved state based on GitHub/Jira status."""
    load_dotenv()

    github_repo = os.getenv("GITHUB_REPO", "").strip()
    github_token = os.getenv("GITHUB_TOKEN", "").strip()

    jira_base_url = os.getenv("JIRA_BASE_URL", "").strip()
    jira_email = os.getenv("JIRA_EMAIL", "").strip()
    jira_api_token = os.getenv("JIRA_API_TOKEN", "").strip()

    logger.info(
        "resolution_watcher_started",
        extra={"service": "backend", "node_name": "resolution_watcher", "incident_id": None},
    )

    while True:
        try:
            open_tickets = await get_open_tickets()
            for ticket in open_tickets:
                await _sync_one_ticket(
                    ticket,
                    github_repo=github_repo,
                    github_token=github_token,
                    jira_base_url=jira_base_url,
                    jira_email=jira_email,
                    jira_api_token=jira_api_token,
                )
        except Exception:
            logger.exception(
                "resolution_watcher_poll_failed",
                extra={"service": "backend", "node_name": "resolution_watcher", "incident_id": None},
            )

        await asyncio.sleep(_poll_seconds())
