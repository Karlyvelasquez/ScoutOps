import time
from agent.state import AgentState
from agent.utils.logger import logger
from agent.utils.prompts import load_prompt
from agent.utils.llm_client import generate_structured_output


def extract_node(state: AgentState) -> AgentState:
    logger.info("extract_node_started", incident_type=state.get("incident_type"))
    start_time = time.time()
    
    try:
        prompt_template = load_prompt("extract_prompt")
        prompt = prompt_template.format(
            description=state["incident_report"].description,
            incident_type=state.get("incident_type", "unknown")
        )
        
        schema = {
            "type": "object",
            "properties": {
                "affected_service": {"type": "string"},
                "feature": {"type": "string"},
                "error_patterns": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "user_impact": {"type": "string"}
            },
            "required": ["affected_service", "feature", "error_patterns", "user_impact"]
        }
        
        response = generate_structured_output(
            prompt=prompt,
            response_schema=schema,
            temperature=0.3
        )
        
        state["entities"] = response
        elapsed_ms = int((time.time() - start_time) * 1000)
        state["node_timings"]["extract"] = elapsed_ms
        
        logger.info(
            "extract_node_completed",
            affected_service=response.get("affected_service"),
            elapsed_ms=elapsed_ms
        )
        
        return state
        
    except Exception as e:
        logger.error("extract_node_failed", error=str(e))
        state["errors"].append(f"Entity extraction failed: {str(e)}")
        state["entities"] = {
            "affected_service": "unknown",
            "feature": "unknown",
            "error_patterns": [],
            "user_impact": "Unknown impact"
        }
        state["node_timings"]["extract"] = int((time.time() - start_time) * 1000)
        return state
