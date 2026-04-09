"""Async PostgreSQL connection helpers for backend persistence."""

from __future__ import annotations

import os

import asyncpg

from app.db.models import SCHEMA_SQL


def _database_url() -> str:
    """Resolve Neon/Postgres connection string from environment."""
    raw_url = os.getenv("NEON_DATABASE_URL", os.getenv("DATABASE_URL", "")).strip()
    if not raw_url:
        raise RuntimeError("Missing NEON_DATABASE_URL (or DATABASE_URL) environment variable")
    return raw_url


async def get_db() -> asyncpg.Connection:
    """Return an async PostgreSQL connection for ad-hoc database access."""
    connection = await asyncpg.connect(_database_url())
    return connection


async def init_db() -> None:
    """Initialize PostgreSQL schema and ensure all required tables/indexes exist."""
    connection = await asyncpg.connect(_database_url())
    try:
        for statement in SCHEMA_SQL:
            await connection.execute(statement)
    finally:
        await connection.close()
