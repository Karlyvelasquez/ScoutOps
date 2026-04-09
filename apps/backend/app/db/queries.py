"""Async query helpers for public ticket dashboard and status tracking."""

from __future__ import annotations

import asyncio
from typing import Any

import asyncpg

from app.db.database import _database_url, init_db


async def _connect() -> asyncpg.Connection:
    return await asyncpg.connect(_database_url())


_schema_ready = False
_schema_lock = asyncio.Lock()


async def _ensure_schema() -> None:
    """Lazily initialize schema for fresh Neon databases."""
    global _schema_ready
    if _schema_ready:
        return

    async with _schema_lock:
        if _schema_ready:
            return
        await init_db()
        _schema_ready = True


async def insert_ticket(ticket: dict[str, Any]) -> None:
    await _ensure_schema()
    connection = await _connect()
    try:
        github_ticket_number = ticket.get("github_ticket_number")
        if github_ticket_number is not None:
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
                ON CONFLICT DO NOTHING
                """,
                str(ticket.get("id", "")),
                ticket.get("incident_type"),
                ticket.get("severity"),
                ticket.get("affected_plugin"),
                ticket.get("summary"),
                ticket.get("original_description"),
                ticket.get("status", "open"),
                ticket.get("github_ticket_url"),
                github_ticket_number,
                ticket.get("jira_ticket_url"),
                ticket.get("jira_ticket_key"),
                ticket.get("created_at"),
                ticket.get("resolved_at"),
            )
            return

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
            DO UPDATE SET
                incident_type = EXCLUDED.incident_type,
                severity = EXCLUDED.severity,
                affected_plugin = EXCLUDED.affected_plugin,
                summary = EXCLUDED.summary,
                original_description = EXCLUDED.original_description,
                status = EXCLUDED.status,
                github_ticket_url = EXCLUDED.github_ticket_url,
                github_ticket_number = EXCLUDED.github_ticket_number,
                jira_ticket_url = EXCLUDED.jira_ticket_url,
                jira_ticket_key = EXCLUDED.jira_ticket_key,
                created_at = EXCLUDED.created_at,
                resolved_at = EXCLUDED.resolved_at
            """,
            str(ticket.get("id", "")),
            ticket.get("incident_type"),
            ticket.get("severity"),
            ticket.get("affected_plugin"),
            ticket.get("summary"),
            ticket.get("original_description"),
            ticket.get("status", "open"),
            ticket.get("github_ticket_url"),
            github_ticket_number,
            ticket.get("jira_ticket_url"),
            ticket.get("jira_ticket_key"),
            ticket.get("created_at"),
            ticket.get("resolved_at"),
        )
    finally:
        await connection.close()


async def get_all_tickets() -> list[dict[str, Any]]:
    await _ensure_schema()
    connection = await _connect()
    try:
        rows = await connection.fetch(
            """
            SELECT *
            FROM tickets
            ORDER BY created_at DESC
            """
        )
        return [dict(row) for row in rows]
    finally:
        await connection.close()


async def get_ticket_by_id(incident_id: str) -> dict[str, Any] | None:
    await _ensure_schema()
    connection = await _connect()
    try:
        row = await connection.fetchrow("SELECT * FROM tickets WHERE id = $1", incident_id)
        return dict(row) if row is not None else None
    finally:
        await connection.close()


async def update_ticket_status(incident_id: str, status: str, resolved_at: str) -> None:
    await _ensure_schema()
    connection = await _connect()
    try:
        await connection.execute(
            """
            UPDATE tickets
            SET status = $1, resolved_at = $2
            WHERE id = $3
            """,
            status,
            resolved_at,
            incident_id,
        )
    finally:
        await connection.close()


async def get_open_tickets() -> list[dict[str, Any]]:
    await _ensure_schema()
    connection = await _connect()
    try:
        rows = await connection.fetch(
            """
            SELECT *
            FROM tickets
            WHERE status IN ('open', 'in_progress')
            ORDER BY created_at DESC
            """
        )
        return [dict(row) for row in rows]
    finally:
        await connection.close()


async def get_ticket_by_github_number(github_number: int) -> dict[str, Any] | None:
    await _ensure_schema()
    connection = await _connect()
    try:
        row = await connection.fetchrow("SELECT * FROM tickets WHERE github_ticket_number = $1", github_number)
        return dict(row) if row is not None else None
    finally:
        await connection.close()


async def get_ticket_by_jira_key(jira_key: str) -> dict[str, Any] | None:
    await _ensure_schema()
    connection = await _connect()
    try:
        row = await connection.fetchrow("SELECT * FROM tickets WHERE jira_ticket_key = $1", jira_key)
        return dict(row) if row is not None else None
    finally:
        await connection.close()
