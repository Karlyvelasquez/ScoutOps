"""SQL schema definitions for public ticket dashboard history."""

from __future__ import annotations

TICKETS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tickets (
    id TEXT PRIMARY KEY,
    incident_type TEXT,
    severity TEXT,
    affected_plugin TEXT,
    summary TEXT,
    original_description TEXT,
    status TEXT DEFAULT 'open',
    github_ticket_url TEXT,
    github_ticket_number INTEGER,
    jira_ticket_url TEXT,
    jira_ticket_key TEXT,
    created_at TEXT NOT NULL,
    resolved_at TEXT
);
"""

IDX_STATUS_SQL = """
CREATE INDEX IF NOT EXISTS idx_status ON tickets(status);
"""

IDX_CREATED_AT_SQL = """
CREATE INDEX IF NOT EXISTS idx_created_at ON tickets(created_at);
"""

SCHEMA_SQL: tuple[str, ...] = (
    TICKETS_TABLE_SQL,
    IDX_STATUS_SQL,
    IDX_CREATED_AT_SQL,
)
