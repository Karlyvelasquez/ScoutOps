"""Async SQLite connection helpers for backend persistence."""

from __future__ import annotations

import os
from pathlib import Path

import aiosqlite

from app.db.models import SCHEMA_SQL


def _db_path() -> Path:
    raw_path = os.getenv("SQLITE_DB_PATH", "./data/sre_agent.db").strip() or "./data/sre_agent.db"
    return Path(raw_path)


async def get_db() -> aiosqlite.Connection:
    """Return an async SQLite connection for ad-hoc database access."""
    db_path = _db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = await aiosqlite.connect(db_path)
    return connection


async def init_db() -> None:
    """Initialize the SQLite file and ensure all required tables/indexes exist."""
    db_path = _db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(db_path) as connection:
        for statement in SCHEMA_SQL:
            await connection.execute(statement)
        await connection.commit()
