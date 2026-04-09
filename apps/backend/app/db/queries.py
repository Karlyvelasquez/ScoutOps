"""Async query helpers for public ticket dashboard and status tracking."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import aiosqlite


def _db_path() -> Path:
    raw_path = os.getenv("SQLITE_DB_PATH", "./data/sre_agent.db").strip() or "./data/sre_agent.db"
    return Path(raw_path)


async def insert_ticket(ticket: dict[str, Any]) -> None:
    db_path = _db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(db_path) as connection:
        await connection.execute(
            """
            INSERT OR REPLACE INTO tickets (
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(ticket.get("id", "")),
                ticket.get("incident_type"),
                ticket.get("severity"),
                ticket.get("affected_plugin"),
                ticket.get("summary"),
                ticket.get("original_description"),
                ticket.get("status", "open"),
                ticket.get("github_ticket_url"),
                ticket.get("github_ticket_number"),
                ticket.get("jira_ticket_url"),
                ticket.get("jira_ticket_key"),
                ticket.get("created_at"),
                ticket.get("resolved_at"),
            ),
        )
        await connection.commit()


async def get_all_tickets() -> list[dict[str, Any]]:
    async with aiosqlite.connect(_db_path()) as connection:
        connection.row_factory = aiosqlite.Row
        cursor = await connection.execute(
            """
            SELECT *
            FROM tickets
            ORDER BY created_at DESC
            """
        )
        rows = await cursor.fetchall()

    return [dict(row) for row in rows]


async def get_ticket_by_id(incident_id: str) -> dict[str, Any] | None:
    async with aiosqlite.connect(_db_path()) as connection:
        connection.row_factory = aiosqlite.Row
        cursor = await connection.execute(
            "SELECT * FROM tickets WHERE id = ?",
            (incident_id,),
        )
        row = await cursor.fetchone()

    return dict(row) if row is not None else None


async def update_ticket_status(incident_id: str, status: str, resolved_at: str) -> None:
    async with aiosqlite.connect(_db_path()) as connection:
        await connection.execute(
            """
            UPDATE tickets
            SET status = ?, resolved_at = ?
            WHERE id = ?
            """,
            (status, resolved_at, incident_id),
        )
        await connection.commit()


async def get_open_tickets() -> list[dict[str, Any]]:
    async with aiosqlite.connect(_db_path()) as connection:
        connection.row_factory = aiosqlite.Row
        cursor = await connection.execute(
            """
            SELECT *
            FROM tickets
            WHERE status IN ('open', 'in_progress')
            ORDER BY created_at DESC
            """
        )
        rows = await cursor.fetchall()

    return [dict(row) for row in rows]


async def get_ticket_by_github_number(github_number: int) -> dict[str, Any] | None:
    async with aiosqlite.connect(_db_path()) as connection:
        connection.row_factory = aiosqlite.Row
        cursor = await connection.execute(
            "SELECT * FROM tickets WHERE github_ticket_number = ?",
            (github_number,),
        )
        row = await cursor.fetchone()

    return dict(row) if row is not None else None


async def get_ticket_by_jira_key(jira_key: str) -> dict[str, Any] | None:
    async with aiosqlite.connect(_db_path()) as connection:
        connection.row_factory = aiosqlite.Row
        cursor = await connection.execute(
            "SELECT * FROM tickets WHERE jira_ticket_key = ?",
            (jira_key,),
        )
        row = await cursor.fetchone()

    return dict(row) if row is not None else None
