"""Submission models for incident intake payloads."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.security.guardrails import GuardrailViolationError, assert_safe_text, sanitize_text


class IncidentSubmission(BaseModel):
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

