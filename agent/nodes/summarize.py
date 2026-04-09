import time
import json
from agent.state import AgentState
from agent.utils.logger import logger
from agent.utils.prompts import load_prompt
from agent.utils.llm_client import generate_structured_output
from observability.tracing import trace_node


def _normalize_summary(value: object) -> str:
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("{") and text.endswith("}"):
            try:
                parsed = json.loads(text)
                return _normalize_summary(parsed)
            except json.JSONDecodeError:
                return text
        return text
    if isinstance(value, dict):
        # Common OpenAI/LLM shape where the final text may be nested.
        for key in ("summary", "problem", "description", "text", "message"):
            nested = value.get(key)
            if isinstance(nested, str):
                return nested
        technical_summary = value.get("technical_summary")
        if isinstance(technical_summary, dict):
            problem = technical_summary.get("problem")
            component = technical_summary.get("affected_component")
            impact = technical_summary.get("user_impact")
            if all(isinstance(x, str) and x.strip() for x in (problem, component, impact)):
                return f"{problem} Affected component: {component}. User impact: {impact}"
        return json.dumps(value, ensure_ascii=False)
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
                "summary": {"type": "string"}
            },
            "required": ["summary"]
        }
        
        response = generate_structured_output(
            prompt=prompt,
            response_schema=schema,
            temperature=0.4
        )
        
        raw_summary_value: object
        if isinstance(response, dict):
            raw_summary_value = response.get("summary", response)
        else:
            raw_summary_value = response

        summary = _normalize_summary(raw_summary_value)
        if not summary or summary == "Unable to generate summary":
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
