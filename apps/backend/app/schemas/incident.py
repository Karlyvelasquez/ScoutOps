from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.security.guardrails import GuardrailViolationError, assert_safe_text, sanitize_text


class IncidentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(..., min_length=10)
    source: Literal["QA", "soporte", "monitoring"]

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        cleaned = sanitize_text(value)
        if len(cleaned) < 10:
            raise ValueError("description must have at least 10 characters after sanitization")
        try:
            assert_safe_text(cleaned)
        except GuardrailViolationError as exc:
            raise ValueError(str(exc)) from exc
        return cleaned


class IncidentCreateResponse(BaseModel):
    incident_id: str
    status: Literal["en_proceso", "completado", "escalado_humano", "error"]


class TicketInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket_id: str
    status: str
    resolution_notes: Optional[str] = None
    duplicate_of: Optional[int] = None
    updated_at: datetime


class IncidentStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: str
    status: Literal["en_proceso", "completado", "escalado_humano", "error"]
    description: str
    source: Literal["QA", "soporte", "monitoring"]
    created_at: datetime
    updated_at: datetime
    result: Optional[dict] = None
    error: Optional[str] = None
    ticket: Optional[TicketInfo] = None


class TicketUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: str = Field(..., pattern=r"^inc_[a-f0-9]{12}$")
    ticket_id: str = Field(..., min_length=3, max_length=64)
    ticket_status: Literal["open", "in_progress", "resolved", "closed"]
    resolution_notes: Optional[str] = None

    @field_validator("resolution_notes")
    @classmethod
    def validate_resolution_notes(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = sanitize_text(value)
        if cleaned:
            try:
                assert_safe_text(cleaned)
            except GuardrailViolationError as exc:
                raise ValueError(str(exc)) from exc
        return cleaned
