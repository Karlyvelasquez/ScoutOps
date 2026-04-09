import time
import json
from agent.state import AgentState
from agent.utils.logger import logger
from agent.utils.prompts import load_prompt
from agent.utils.llm_client import generate_structured_output
from observability.tracing import trace_node


def _normalize_summary(value: object, _depth: int = 0) -> str:
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("{") and text.endswith("}"):
            try:
                parsed = json.loads(text)
                return _normalize_summary(parsed, _depth)
            except json.JSONDecodeError:
                return text
        return text
    if isinstance(value, dict):
        # Priority: well-known top-level string keys.
        for key in ("summary", "problem", "description", "text", "message", "technical_context"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
        # Structured shape: technical_summary dict with problem/component/impact sub-keys.
        technical_summary = value.get("technical_summary") or value.get("incident_summary")
        if isinstance(technical_summary, dict):
            problem = technical_summary.get("problem") or technical_summary.get("broken_component")
            component = technical_summary.get("affected_component") or technical_summary.get("error_signals")
            impact = technical_summary.get("user_impact") or technical_summary.get("user_business_impact")
            parts = [p for p in (problem, component, impact) if isinstance(p, str) and p.strip() and p.strip() != "unknown"]
            if parts:
                return " ".join(parts)
        # Recursive fallback: depth-limited walk of all values looking for longest useful string.
        if _depth < 3:
            candidates: list[str] = []
            for v in value.values():
                result = _normalize_summary(v, _depth + 1)
                if result and result != "Unable to generate summary" and len(result) > 20:
                    candidates.append(result)
            if candidates:
                return max(candidates, key=len)
        return ""
    if value is None:
        return "Unable to generate summary"
    return str(value)


def _build_fallback_summary(state: AgentState, entities: dict) -> str:
    incident_type = state.get("incident_type", "unknown")
    affected_service = entities.get("affected_service", "unknown service")
    feature = entities.get("feature", "core flow")
    user_impact = entities.get("user_impact", "users are impacted")
    description = state["incident_report"].description

    return (
        f"Incident type {incident_type} is affecting {affected_service} in feature {feature}. "
        f"{user_impact}. Reported behavior: {description}"
    )


@trace_node("summarize_node")
def summarize_node(state: AgentState) -> AgentState:
    logger.info("summarize_node_started")
    start_time = time.time()
    
    try:
        entities = state.get("entities", {})
        
        rag_context = state.get("rag_context") or []
        if rag_context:
            rag_lines = []
            for item in rag_context[:3]:
                rag_lines.append(
                    f"Plugin: {item.get('plugin_name', 'unknown')} | "
                    f"File: {item.get('file_path', 'unknown')} | "
                    f"Relevance: {item.get('relevance_score', 0):.2f}\n"
                    f"{item.get('content', '')[:300]}"
                )
            rag_context_str = "\n---\n".join(rag_lines)
        else:
            rag_context_str = "No codebase context available."

        attachment_analysis = state.get("attachment_analysis") or "No attachment provided."

        prompt_template = load_prompt("summarize_prompt")
        prompt = prompt_template.format(
            description=state["incident_report"].description,
            incident_type=state.get("incident_type", "unknown"),
            affected_service=entities.get("affected_service", "unknown"),
            feature=entities.get("feature", "unknown"),
            error_patterns=", ".join(entities.get("error_patterns", [])),
            user_impact=entities.get("user_impact", "Unknown impact"),
            rag_context=rag_context_str,
            attachment_analysis=attachment_analysis,
        )
        
        schema = {
            "type": "object",
            "properties": {
                "broken_component": {"type": "string"},
                "error_signals": {"type": "string"},
                "user_business_impact": {"type": "string"},
            },
            "required": ["broken_component", "error_signals", "user_business_impact"]
        }
        
        response = generate_structured_output(
            prompt=prompt,
            response_schema=schema,
            temperature=0.4
        )
        
        if isinstance(response, dict):
            broken = response.get("broken_component", "").strip()
            signals = response.get("error_signals", "").strip()
            impact = response.get("user_business_impact", "").strip()
            
            parts = [p for p in (broken, signals, impact) if p and p.lower() != "unknown"]
            if parts:
                summary = " ".join(parts)
            else:
                summary = ""
        else:
            summary = _normalize_summary(response)
        
        if not summary or summary == "Unable to generate summary" or summary.startswith("{"):
            summary = _build_fallback_summary(state, entities)
            logger.warning("summarize_node_used_fallback_summary")
        
        state["technical_summary"] = summary
        elapsed_ms = int((time.time() - start_time) * 1000)
        state["node_timings"]["summarize"] = elapsed_ms
        
        logger.info(
            "summarize_node_completed",
            summary_length=len(summary),
            elapsed_ms=elapsed_ms
        )
        
        return state
        
    except Exception as e:
        logger.error("summarize_node_failed", error=str(e))
        state["errors"].append(f"Summary generation failed: {str(e)}")
        state["technical_summary"] = f"Error generating summary: {str(e)}"
        state["node_timings"]["summarize"] = int((time.time() - start_time) * 1000)
        return state
