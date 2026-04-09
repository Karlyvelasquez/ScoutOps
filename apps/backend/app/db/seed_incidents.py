"""Seed Neon/PostgreSQL ticket history with realistic incident samples."""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.db.database import get_db, init_db

PLUGINS = [
    "api-plugin-payments-stripe",
    "catalog-service",
    "auth-gateway",
    "deploy-pipeline",
]

INCIDENT_TYPES = [
    "checkout_failure",
    "catalog_issue",
    "login_error",
    "deployment_incident",
]

TEAMS = [
    "payments-team",
    "catalog-team",
    "accounts-team",
    "orders-team",
]

SEVERITIES = ["P1", "P2", "P3"]

DESCRIPTIONS = [
    "Intermittent checkout errors with pending charges visible in user banks.",
    "Catalog endpoint returning stale products and delayed search indexing.",
    "Authentication gateway rejects valid tokens after idle period.",
    "Deployment pipeline rollback failed and service remained degraded.",
]


def _weighted_hour() -> int:
    # Cluster most incidents between 2pm and 4pm for a meaningful heatmap.
    weighted = random.choices(
        population=list(range(24)),
        weights=[1, 1, 1, 1, 1, 1, 1, 2, 2, 3, 4, 6, 7, 9, 12, 11, 7, 5, 3, 2, 2, 1, 1, 1],
        k=1,
    )
    return int(weighted[0])


async def seed(total: int = 50) -> None:
    await init_db()
    connection = await get_db()

    try:
        now = datetime.now(timezone.utc)
        for idx in range(total):
            day_offset = random.randint(0, 29)
            hour = _weighted_hour()
            minute = random.randint(0, 59)

            opened_at = now - timedelta(days=day_offset)
            opened_at = opened_at.replace(hour=hour, minute=minute, second=0, microsecond=0)

            severity = random.choices(SEVERITIES, weights=[4, 6, 8], k=1)[0]
            incident_type = random.choice(INCIDENT_TYPES)
            plugin = random.choice(PLUGINS)
            team = random.choice(TEAMS)

            resolved_at = None
            status = "open"
            if random.random() < 0.78:
                duration_hours = random.uniform(0.5, 8.0)
                resolved_at = opened_at + timedelta(hours=duration_hours)
                status = "resolved"

            github_ticket_number = 1000 + idx
            github_ticket_url = f"https://github.com/example/sre-incidents/issues/{github_ticket_number}"

            await connection.execute(
                """
                INSERT INTO tickets (
                    id,
                    incident_type,
                    severity,
                    affected_plugin,
                    summary,
                    original_description,
                    status,
                    github_ticket_url,
                    github_ticket_number,
                    jira_ticket_url,
                    jira_ticket_key,
                    created_at,
                    resolved_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                ON CONFLICT (id)
                DO NOTHING
                """,
                f"inc_seed_{uuid4().hex[:12]}",
                incident_type,
                severity,
                plugin,
                f"{incident_type} impacting {plugin}",
                f"{random.choice(DESCRIPTIONS)} Team: {team}.",
                status,
                github_ticket_url,
                github_ticket_number,
                None,
                None,
                opened_at.isoformat(),
                resolved_at.isoformat() if resolved_at else None,
            )
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(seed(total=50))
    print("Seed complete: 50 incidents inserted into tickets table.")
