import time
from agent.state import AgentState
from agent.utils.logger import logger
from agent.utils.prompts import load_prompt
from agent.utils.llm_client import generate_structured_output
from observability.tracing import trace_node


VALID_INCIDENT_TYPES = [
    "checkout_failure",
    "login_error",
    "catalog_issue",
    "cart_issue",
    "inventory_issue",
    "shipping_issue",
    "performance_issue",
    "unknown"
]


@trace_node("classify_node")
def classify_node(state: AgentState) -> AgentState:
    logger.info("classify_node_started")
    start_time = time.time()
    
    try:
        prompt_template = load_prompt("classify_prompt")
        prompt = prompt_template.format(
            description=state["incident_report"].description,
            source=state["incident_report"].source
        )
        
        schema = {
            "type": "object",
            "properties": {
                "incident_type": {
                    "type": "string",
                    "enum": VALID_INCIDENT_TYPES
                },
                "classification_confidence": {
                    "type": "number",
                    "description": "Confidence that this text is a real incident report (0.0-1.0). Use <0.3 for nonsensical, spam, or completely off-topic input."
                }
            },
            "required": ["incident_type", "classification_confidence"]
        }
        
        response = generate_structured_output(
            prompt=prompt,
            response_schema=schema,
            temperature=0.2
        )
        
        incident_type = response.get("incident_type", "unknown")
        classification_confidence = float(response.get("classification_confidence", 1.0))
        
        is_vague = classification_confidence < 0.35
        
        state["incident_type"] = incident_type
        state["vague_input"] = is_vague
        elapsed_ms = int((time.time() - start_time) * 1000)
        state["node_timings"]["classify"] = elapsed_ms
        
        logger.info(
            "classify_node_completed",
            incident_type=incident_type,
            classification_confidence=classification_confidence,
            vague_input=is_vague,
            elapsed_ms=elapsed_ms
        )
        
        return state
        
    except Exception as e:
        logger.error("classify_node_failed", error=str(e))
        state["errors"].append(f"Classification failed: {str(e)}")
        state["incident_type"] = "unknown"
        state["vague_input"] = False
        state["node_timings"]["classify"] = int((time.time() - start_time) * 1000)
        return state
