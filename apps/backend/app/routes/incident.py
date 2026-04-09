"""Reporter ticket history endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.db.queries import get_all_tickets, get_ticket_by_id

router = APIRouter()


@router.get("/tickets")
async def tickets_list() -> list[dict[str, Any]]:
    tickets = await get_all_tickets()
    tickets.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return tickets


@router.get("/tickets/{incident_id}")
async def ticket_detail(incident_id: str) -> dict[str, Any]:
    ticket = await get_ticket_by_id(incident_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket
