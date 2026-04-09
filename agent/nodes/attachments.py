import time
import mimetypes
from pathlib import Path
from agent.state import AgentState
from agent.utils.logger import logger
from agent.utils.prompts import load_prompt
from agent.utils.llm_client import generate_with_vision, generate_structured_output
from observability.tracing import trace_node

IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}
MAX_LOG_CHARS = 4000


def _detect_mime(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    return mime or "application/octet-stream"


def _analyze_image(prompt: str, path: str) -> str:
    mime_type = _detect_mime(path)
    image_bytes = Path(path).read_bytes()
    return generate_with_vision(prompt=prompt, image_bytes=image_bytes, mime_type=mime_type)


def _analyze_log(prompt_template: str, description: str, log_text: str) -> str:
    truncated = log_text[:MAX_LOG_CHARS]
    prompt = prompt_template.format(
        attachment_type="log",
        description=description,
        attachment_content=truncated,
    )
    schema = {
        "type": "object",
        "properties": {
            "error_codes": {"type": "array", "items": {"type": "string"}},
            "stack_trace_summary": {"type": "string"},
            "severity_indicators": {"type": "array", "items": {"type": "string"}},
            "affected_components": {"type": "array", "items": {"type": "string"}},
            "technical_context": {"type": "string"},
        },
        "required": ["error_codes", "severity_indicators", "affected_components", "technical_context"],
    }
    result = generate_structured_output(prompt=prompt, response_schema=schema, temperature=0.2)
    if isinstance(result, dict):
        parts = [result.get("technical_context", "")]
        if result.get("error_codes"):
            parts.append("Error codes: " + ", ".join(result["error_codes"]))
        if result.get("severity_indicators"):
            parts.append("Severity indicators: " + ", ".join(result["severity_indicators"]))
        if result.get("affected_components"):
            parts.append("Components: " + ", ".join(result["affected_components"]))
        return " | ".join(p for p in parts if p)
    return str(result)


@trace_node("attachments_node")
def attachments_node(state: AgentState) -> AgentState:
    logger.info("attachments_node_started")
    start_time = time.time()

    attachment_path = state["incident_report"].attachment_path
    attachment_type = state["incident_report"].attachment_type

    if not attachment_path or not Path(attachment_path).exists():
        state["attachment_analysis"] = None
        state["node_timings"]["attachments"] = 0
        logger.info("attachments_node_skipped", reason="no_attachment")
        return state

    try:
        prompt_template = load_prompt("attachments_prompt")
        description = state["incident_report"].description

        if attachment_type == "image":
            vision_prompt = prompt_template.format(
                attachment_type="image",
                description=description,
                attachment_content="[Image provided inline]",
            )
            analysis = _analyze_image(vision_prompt, attachment_path)
        else:
            log_text = Path(attachment_path).read_text(encoding="utf-8", errors="replace")
            analysis = _analyze_log(prompt_template, description, log_text)

        state["attachment_analysis"] = analysis

        elapsed_ms = int((time.time() - start_time) * 1000)
        state["node_timings"]["attachments"] = elapsed_ms

        logger.info(
            "attachments_node_completed",
            attachment_type=attachment_type,
            analysis_length=len(analysis),
            elapsed_ms=elapsed_ms,
        )

    except Exception as e:
        logger.error("attachments_node_failed", error=str(e))
        state["errors"].append(f"Attachment analysis failed: {str(e)}")
        state["attachment_analysis"] = None
        state["node_timings"]["attachments"] = int((time.time() - start_time) * 1000)

    return state
