"""Conversational state per WebSocket session (short-term memory)."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Turn:
    role: str   # "user" | "assistant"
    text: str


@dataclass
class VoiceSession:
    session_id: str
    # Language detected from the last user utterance: "es" | "en"
    lang: str = "es"
    # Last incident managed in this session
    last_incident_id: Optional[str] = None
    last_incident_type: Optional[str] = None
    last_severity: Optional[str] = None
    # Pending confirmation flow
    awaiting_confirmation: bool = False
    pending_description: Optional[str] = None
    # Rolling conversation window (last 6 turns = 3 exchanges)
    history: deque = field(default_factory=lambda: deque(maxlen=6))

    def add_turn(self, role: str, text: str) -> None:
        self.history.append(Turn(role=role, text=text))

    def context_for_prompt(self) -> str:
        if not self.history:
            return "(no prior context)"
        return "\n".join(f"{t.role}: {t.text}" for t in self.history)
