"""
WebSocket endpoint for real-time voice interaction.

Protocol (messages sent by the client):
  {"type": "transcript", "text": "...", "lang": "es"|"en"}
      – Final transcript from Web Speech API.

  {"type": "poll"}
      – Ask the server to check the last incident status.

  {"type": "end_session"}
      – Graceful close.

Messages sent by the server:
  {"type": "transcript",    "text": "..."}      – Echo of transcript received
  {"type": "response_text", "text": "..."}      – Text being synthesised
  {"type": "audio_end"}                         – All audio chunks sent
  {"type": "incident_created", "incident_id": "..."}
  {"type": "incident_result",  "text": "...", "data": {...}}
  {"type": "error",            "message": "..."}

  <binary frame>  – MP3 audio chunk from edge-tts
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.agent_service import AgentService
from voice.intent_handler import VoiceIntentHandler
from voice.session import VoiceSession
from voice.synthesizer import StreamingSynthesizer

router = APIRouter()

# Shared singletons (one per backend process)
_agent_service = AgentService()
_synthesizer = StreamingSynthesizer()
_intent_handler = VoiceIntentHandler(_agent_service)

# Active sessions
_sessions: Dict[str, VoiceSession] = {}

# Max seconds to wait for pipeline completion while connection is open
_POLL_MAX_SECONDS = 90
_POLL_INTERVAL = 2.0


async def _speak(websocket: WebSocket, text: str, lang: str) -> None:
    """Send response_text frame then stream MP3 chunks, then audio_end."""
    await websocket.send_json({"type": "response_text", "text": text})
    async for chunk in _synthesizer.synthesize_stream(text, lang):
        await websocket.send_bytes(chunk)
    await websocket.send_json({"type": "audio_end"})


async def _wait_for_result(
    websocket: WebSocket,
    session: VoiceSession,
    incident_id: str,
) -> None:
    """
    Background task: polls the incident until it reaches a terminal state,
    then speaks the result over the same WebSocket.
    """
    elapsed = 0.0
    while elapsed < _POLL_MAX_SECONDS:
        await asyncio.sleep(_POLL_INTERVAL)
        elapsed += _POLL_INTERVAL

        result_text = _intent_handler.poll_result(incident_id, session.lang)
        if result_text is None:
            continue  # Still processing

        # Send structured data for the UI to consume
        raw = _agent_service.get_incident_status(incident_id)
        await websocket.send_json({
            "type": "incident_result",
            "text": result_text,
            "data": raw,
        })
        await _speak(websocket, result_text, session.lang)
        return

    # Timeout
    timeout_msg = (
        "El análisis está tardando más de lo esperado. Puedes consultar el resultado en el dashboard."
        if session.lang == "es"
        else "Analysis is taking longer than expected. You can check the result in the dashboard."
    )
    await _speak(websocket, timeout_msg, session.lang)


@router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket) -> None:
    await websocket.accept()

    session_id = str(uuid.uuid4())
    session = VoiceSession(session_id=session_id)
    _sessions[session_id] = session

    # Active background result-waiting tasks keyed by incident_id
    pending_tasks: Dict[str, asyncio.Task] = {}

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "invalid JSON"})
                continue

            msg_type = msg.get("type")

            # ----------------------------------------------------------------
            # New transcript from the browser's Web Speech API
            # ----------------------------------------------------------------
            if msg_type == "transcript":
                transcript: str = msg.get("text", "").strip()
                lang: str = msg.get("lang", "es")
                if not transcript:
                    continue

                # Update session language from client hint
                session.lang = lang

                # Echo back so the UI can show it
                await websocket.send_json({"type": "transcript", "text": transcript})

                # Classify intent and get immediate response
                response_text = await _intent_handler.handle(transcript, session)

                # If a new incident was just created, schedule result polling
                if session.last_incident_id and session.last_incident_id not in pending_tasks:
                    inc_id = session.last_incident_id
                    await websocket.send_json({
                        "type": "incident_created",
                        "incident_id": inc_id,
                    })
                    task = asyncio.create_task(
                        _wait_for_result(websocket, session, inc_id)
                    )
                    pending_tasks[inc_id] = task

                # Speak the immediate acknowledgement
                await _speak(websocket, response_text, session.lang)

            # ----------------------------------------------------------------
            # Manual poll request (UI button or follow-up question)
            # ----------------------------------------------------------------
            elif msg_type == "poll":
                if not session.last_incident_id:
                    msg_text = (
                        "No hay ningún incidente activo en esta sesión."
                        if session.lang == "es"
                        else "No active incident in this session."
                    )
                    await _speak(websocket, msg_text, session.lang)
                else:
                    result_text = _intent_handler.poll_result(
                        session.last_incident_id, session.lang
                    )
                    if result_text:
                        raw_data = _agent_service.get_incident_status(session.last_incident_id)
                        await websocket.send_json({
                            "type": "incident_result",
                            "text": result_text,
                            "data": raw_data,
                        })
                        await _speak(websocket, result_text, session.lang)
                    else:
                        still_msg = (
                            "El incidente todavía está siendo procesado."
                            if session.lang == "es"
                            else "The incident is still being processed."
                        )
                        await _speak(websocket, still_msg, session.lang)

            # ----------------------------------------------------------------
            # Graceful close
            # ----------------------------------------------------------------
            elif msg_type == "end_session":
                break

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        # Cancel any in-flight result watchers
        for task in pending_tasks.values():
            task.cancel()
        _sessions.pop(session_id, None)
