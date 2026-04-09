"""
Classifies user intent from a transcript and produces a voice response.

Supported intents:
  REPORT_INCIDENT  – user describes a technical problem
  ASK_STATUS       – user asks about a prior incident
  ASK_QUESTION     – user asks a general question about the system
  CHITCHAT         – greeting / small talk
  CONFIRM          – confirms a pending action
  CANCEL           – cancels a pending action
"""
from __future__ import annotations

import asyncio
from typing import Optional, TYPE_CHECKING

from agent.utils.llm_client import generate_structured_output
from voice.session import VoiceSession

if TYPE_CHECKING:
    from app.services.agent_service import AgentService


# ---------------------------------------------------------------------------
# Prompts (bilingual — the LLM handles both ES and EN naturally)
# ---------------------------------------------------------------------------

_INTENT_PROMPT = """\
You are an intent classifier for an SRE incident-reporting voice assistant.
The assistant supports BOTH Spanish and English.

Conversation history:
{context}

User message: "{transcript}"

Classify the intent and detect the language.

Intents:
- REPORT_INCIDENT : user describes a technical error, failure, degradation, or bug
- ASK_STATUS      : user asks about the status/result of a previous incident
- ASK_QUESTION    : user asks a general question about the system or procedures
- CHITCHAT        : greeting, farewell, or off-topic small talk
- CONFIRM         : user confirms a pending action (sí / yes / confirm / ok)
- CANCEL          : user cancels a pending action (no / cancel / nevermind)

Rules:
- If REPORT_INCIDENT, extract a clean description in `extracted_description`
  (remove filler words, keep the technical content).
- `lang` must be "es" if the message is in Spanish, "en" if in English.
- `confidence` is your certainty in the intent (0.0–1.0).
"""

_INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": ["REPORT_INCIDENT", "ASK_STATUS", "ASK_QUESTION", "CHITCHAT", "CONFIRM", "CANCEL"],
        },
        "confidence": {"type": "number"},
        "lang": {"type": "string", "enum": ["es", "en"]},
        "extracted_description": {"type": "string"},
    },
    "required": ["intent", "confidence", "lang"],
}

# ---------------------------------------------------------------------------
# Canned responses (bilingual)
# ---------------------------------------------------------------------------

_GREETING = {
    "es": "Hola, soy el asistente de incidentes de ScoutOps. ¿Qué problema técnico tienes?",
    "en": "Hi, I'm the ScoutOps incident assistant. What technical issue can I help you with?",
}
_ACK_PROCESSING = {
    "es": "Recibido. Estoy analizando el incidente, dame unos segundos.",
    "en": "Got it. Analyzing the incident, give me a few seconds.",
}
_NO_INCIDENT = {
    "es": "No tengo ningún incidente activo en esta sesión. Puedes describirme el problema.",
    "en": "I don't have an active incident in this session. You can describe the issue.",
}
_GENERAL_HELP = {
    "es": "Puedo ayudarte a reportar incidentes técnicos, consultar su estado y explicar las acciones tomadas.",
    "en": "I can help you report technical incidents, check their status, and explain the actions taken.",
}
_CONFIRM_NEEDED = {
    "es": "Esto parece un incidente crítico. ¿Confirmas que debo crear un ticket P1 y notificar al equipo ahora? Di 'sí' para continuar.",
    "en": "This looks like a critical incident. Should I create a P1 ticket and notify the team now? Say 'yes' to confirm.",
}
_CANCELLED = {
    "es": "Acción cancelada. ¿Hay algo más en lo que pueda ayudarte?",
    "en": "Action cancelled. Is there anything else I can help you with?",
}


# ---------------------------------------------------------------------------
# State-to-response builders
# ---------------------------------------------------------------------------

def _status_response(data: dict, lang: str) -> str:
    state = data.get("state", "unknown")
    inc_id = data.get("incident_id", "")[-6:].upper()
    state_map_es = {
        "EN_PROCESO": f"El incidente {inc_id} aún está siendo procesado.",
        "COMPLETADO": f"El incidente {inc_id} fue completado. Se creó un ticket y se notificó al equipo.",
        "ESCALADO_HUMANO": f"El incidente {inc_id} fue escalado a revisión humana por baja confianza del agente.",
        "ERROR": f"El incidente {inc_id} encontró un error durante el análisis.",
    }
    state_map_en = {
        "EN_PROCESO": f"Incident {inc_id} is still being processed.",
        "COMPLETADO": f"Incident {inc_id} was completed. A ticket was created and the team was notified.",
        "ESCALADO_HUMANO": f"Incident {inc_id} was escalated for human review due to low agent confidence.",
        "ERROR": f"Incident {inc_id} encountered an error during analysis.",
    }
    mapping = state_map_en if lang == "en" else state_map_es
    return mapping.get(state, f"Estado: {state}")


def _completion_response(data: dict, lang: str) -> str:
    result = data.get("rag_response") or {}
    severity = result.get("severity", "P3")
    team = result.get("assigned_team", "platform-team")
    inc_type = result.get("incident_type", "unknown")
    summary = result.get("summary", "")

    # Keep TTS-friendly: no markdown, short sentences
    short_summary = summary.split(".")[0] if summary else ""

    if lang == "en":
        msg = (
            f"Analysis complete. The incident was classified as {inc_type.replace('_', ' ')}, "
            f"severity {severity}, assigned to {team}. "
        )
        if short_summary:
            msg += short_summary + "."
    else:
        msg = (
            f"Análisis completo. El incidente fue clasificado como {inc_type.replace('_', ' ')}, "
            f"severidad {severity}, asignado al equipo {team}. "
        )
        if short_summary:
            msg += short_summary + "."
    return msg


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------

class VoiceIntentHandler:
    def __init__(self, agent_service: "AgentService") -> None:
        self._svc = agent_service

    async def handle(self, transcript: str, session: VoiceSession) -> str:
        """
        Classify intent, execute the action, and return the response text for TTS.
        Updates session state in place.
        """
        classified = generate_structured_output(
            prompt=_INTENT_PROMPT.format(
                context=session.context_for_prompt(),
                transcript=transcript,
            ),
            response_schema=_INTENT_SCHEMA,
            temperature=0.1,
        )

        intent: str = classified.get("intent", "CHITCHAT")
        confidence: float = float(classified.get("confidence", 0.5))
        lang: str = classified.get("lang", "es")
        description: str = classified.get("extracted_description", transcript)

        # Update session language from this turn
        session.lang = lang
        session.add_turn("user", transcript)

        # --- Pending confirmation flow ---
        if session.awaiting_confirmation:
            if intent == "CONFIRM":
                session.awaiting_confirmation = False
                desc = session.pending_description or transcript
                session.pending_description = None
                response = await self._create_incident(desc, lang, session)
            elif intent == "CANCEL":
                session.awaiting_confirmation = False
                session.pending_description = None
                response = _CANCELLED[lang]
            else:
                # Re-ask
                response = _CONFIRM_NEEDED[lang]
            session.add_turn("assistant", response)
            return response

        # --- Normal flow ---
        if intent == "REPORT_INCIDENT" and confidence >= 0.55:
            response = await self._create_incident(description, lang, session)

        elif intent == "ASK_STATUS":
            response = self._handle_status(session, lang)

        elif intent == "CHITCHAT":
            greetings = {"hola", "buenas", "hey", "hello", "hi", "good morning", "good afternoon"}
            if any(g in transcript.lower() for g in greetings):
                response = _GREETING[lang]
            else:
                response = _GENERAL_HELP[lang]

        elif intent == "ASK_QUESTION":
            response = _GENERAL_HELP[lang]

        else:
            response = _GENERAL_HELP[lang]

        session.add_turn("assistant", response)
        return response

    async def _create_incident(self, description: str, lang: str, session: VoiceSession) -> str:
        """Create incident stub, kick off background processing, return immediate ack."""
        incident_id = self._svc.create_incident(
            description=description,
            source="soporte",
        )
        session.last_incident_id = incident_id

        # Run the synchronous pipeline in a thread so the event loop stays free
        loop = asyncio.get_event_loop()
        loop.run_in_executor(
            None,
            self._svc.process_incident_async,
            incident_id,
            description,
            "soporte",
            None,
            None,
        )

        return _ACK_PROCESSING[lang]

    def _handle_status(self, session: VoiceSession, lang: str) -> str:
        if not session.last_incident_id:
            return _NO_INCIDENT[lang]
        data = self._svc.get_incident_status(session.last_incident_id)
        if not data:
            return _NO_INCIDENT[lang]
        state = data.get("state", "")
        if state == "COMPLETADO":
            return _completion_response(data, lang)
        return _status_response(data, lang)

    def poll_result(self, incident_id: str, lang: str) -> Optional[str]:
        """
        Called by the WebSocket handler to check if an incident finished.
        Returns a TTS-ready string when done, None while still processing.
        """
        data = self._svc.get_incident_status(incident_id)
        if not data:
            return None
        state = data.get("state", "")
        if state == "COMPLETADO":
            return _completion_response(data, lang)
        if state == "ESCALADO_HUMANO":
            inc_id = incident_id[-6:].upper()
            if lang == "en":
                return f"Incident {inc_id} was escalated for human review. Confidence was below the automatic threshold."
            return f"El incidente {inc_id} fue escalado a revisión humana. La confianza del agente estuvo por debajo del umbral automático."
        if state == "ERROR":
            inc_id = incident_id[-6:].upper()
            if lang == "en":
                return f"Incident {inc_id} encountered an error during processing. Please retry or check manually."
            return f"El incidente {inc_id} encontró un error durante el análisis. Por favor reintenta o revísalo manualmente."
        return None  # Still EN_PROCESO
