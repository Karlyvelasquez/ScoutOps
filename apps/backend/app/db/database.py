"""Async PostgreSQL connection helpers for backend persistence."""

from __future__ import annotations

import logging
import os

import asyncpg

from app.db.models import SCHEMA_SQL

logger = logging.getLogger(__name__)


def _database_url() -> str | None:
    """Resolve Neon/Postgres connection string from environment. Returns None if not configured."""
    raw_url = os.getenv("NEON_DATABASE_URL", os.getenv("DATABASE_URL", "")).strip()
    return raw_url or None


async def get_db() -> asyncpg.Connection:
    """Return an async PostgreSQL connection for ad-hoc database access."""
    url = _database_url()
    if not url:
        raise RuntimeError("Missing NEON_DATABASE_URL (or DATABASE_URL) environment variable")
    return await asyncpg.connect(url)


async def init_db() -> None:
    """Initialize PostgreSQL schema. Skips gracefully if no DB URL is configured."""
    url = _database_url()
    if not url:
        logger.warning(
            "NEON_DATABASE_URL not set — ticket history dashboard disabled. "
            "Set NEON_DATABASE_URL in .env to enable it."
        )
        return
    connection = await asyncpg.connect(url)
    try:
        for statement in SCHEMA_SQL:
            await connection.execute(statement)
    finally:
        await connection.close()
