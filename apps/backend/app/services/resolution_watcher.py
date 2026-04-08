"""Async background watcher that emails reporters when labeled GitHub issues are closed."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

from integrations.email import notify_reporter
from observability.logs import get_logger

logger = get_logger(__name__)
POLL_SECONDS = 30


def _data_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data"


def _reporter_map_path() -> Path:
    return _data_dir() / "issue_reporters.json"


def _notified_path() -> Path:
    return _data_dir() / "notified_issues.json"


def _load_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception(
            "resolution_watcher_json_load_failed",
            extra={"service": "backend", "node_name": "resolution_watcher"},
        )
        return default


def _save_json(path: Path, data: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        logger.exception(
            "resolution_watcher_json_save_failed",
            extra={"service": "backend", "node_name": "resolution_watcher"},
        )


async def _fetch_closed_labeled_issues(github_repo: str, github_token: str) -> list[dict[str, Any]]:
    url = f"https://api.github.com/repos/{github_repo}/issues"
    params = {
        "state": "closed",
        "labels": "sre-agent",
        "per_page": 100,
        "sort": "updated",
        "direction": "desc",
    }
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        issues = response.json()

    # GitHub issues API can include PRs; filter those out.
    return [item for item in issues if "pull_request" not in item]


async def start_resolution_watcher() -> None:
    """Continuously watch closed SRE-agent issues and notify original reporters once."""
    load_dotenv()

    github_repo = os.getenv("GITHUB_REPO", "").strip()
    github_token = os.getenv("GITHUB_TOKEN", "").strip()

    if not github_repo or not github_token:
        logger.error(
            "resolution_watcher_missing_github_config",
            extra={"service": "backend", "node_name": "resolution_watcher"},
        )
        return

    logger.info(
        "resolution_watcher_started",
        extra={"service": "backend", "node_name": "resolution_watcher"},
    )

    while True:
        try:
            reporter_map = _load_json(_reporter_map_path(), default={})
            notified_issues = set(_load_json(_notified_path(), default=[]))
            closed_issues = await _fetch_closed_labeled_issues(github_repo, github_token)

            for issue in closed_issues:
                issue_number = issue.get("number")
                issue_key = str(issue_number)
                if issue_key in notified_issues:
                    continue

                reporter_email = reporter_map.get(issue_key)
                if not reporter_email:
                    logger.warning(
                        "resolution_watcher_reporter_missing",
                        extra={
                            "service": "backend",
                            "node_name": "resolution_watcher",
                            "incident_id": issue_key,
                        },
                    )
                    notified_issues.add(issue_key)
                    continue

                resolved_ok = await notify_reporter(
                    reporter_email=reporter_email,
                    ticket_url=issue.get("html_url", ""),
                    resolution_summary=issue.get("body", "Issue resolved by engineering team."),
                )

                if resolved_ok:
                    notified_issues.add(issue_key)
                    logger.info(
                        "resolution_watcher_reporter_notified",
                        extra={
                            "service": "backend",
                            "node_name": "resolution_watcher",
                            "incident_id": issue_key,
                        },
                    )

            _save_json(_notified_path(), sorted(notified_issues))
        except Exception:
            logger.exception(
                "resolution_watcher_poll_failed",
                extra={"service": "backend", "node_name": "resolution_watcher"},
            )

        await asyncio.sleep(POLL_SECONDS)
