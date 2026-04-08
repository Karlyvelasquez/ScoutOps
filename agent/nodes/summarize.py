import time
from agent.state import AgentState
from agent.utils.logger import logger
from agent.utils.prompts import load_prompt
from agent.utils.llm_client import generate_structured_output


def summarize_node(state: AgentState) -> AgentState:
    logger.info("summarize_node_started")
    start_time = time.time()
    
    try:
        entities = state.get("entities", {})
        
        prompt_template = load_prompt("summarize_prompt")
        prompt = prompt_template.format(
            description=state["incident_report"].description,
            incident_type=state.get("incident_type", "unknown"),
            affected_service=entities.get("affected_service", "unknown"),
            feature=entities.get("feature", "unknown"),
            error_patterns=", ".join(entities.get("error_patterns", [])),
            user_impact=entities.get("user_impact", "Unknown impact")
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
        
        summary = response.get("summary", "Unable to generate summary")
        
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
