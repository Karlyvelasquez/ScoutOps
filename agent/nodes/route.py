import time
from agent.state import AgentState
from agent.utils.logger import logger
from agent.utils.prompts import load_prompt
from agent.utils.llm_client import generate_structured_output
from observability.tracing import trace_node


PLUGIN_TO_TEAM = {
    "api-plugin-payments": "payments-team",
    "api-plugin-payments-stripe": "payments-team",
    "api-plugin-orders": "orders-team",
    "api-plugin-catalog": "catalog-team",
    "api-plugin-carts": "catalog-team",
    "api-plugin-accounts": "accounts-team",
    "api-plugin-inventory": "catalog-team",
    "api-plugin-shipments": "orders-team",
}


@trace_node("route_node")
def route_node(state: AgentState) -> AgentState:
    logger.info("route_node_started")
    start_time = time.time()
    
    try:
        entities = state.get("entities", {})
        
        prompt_template = load_prompt("route_prompt")
        prompt = prompt_template.format(
            incident_type=state.get("incident_type", "unknown"),
            summary=state.get("technical_summary", "No summary available"),
            affected_service=entities.get("affected_service", "unknown")
        )
        
        schema = {
            "type": "object",
            "properties": {
                "severity": {
                    "type": "string",
                    "enum": ["P1", "P2", "P3"]
                },
                "assigned_team": {"type": "string"},
                "affected_plugin": {"type": "string"},
                "layer": {"type": "string"},
                "suggested_actions": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["severity", "assigned_team", "affected_plugin", "layer", "suggested_actions"]
        }
        
        response = generate_structured_output(
            prompt=prompt,
            response_schema=schema,
            temperature=0.3
        )
        
        plugin = response.get("affected_plugin", "api-plugin-unknown")
        team = PLUGIN_TO_TEAM.get(plugin, response.get("assigned_team", "platform-team"))
        
        routing_info = {
            "severity": response.get("severity", "P3"),
            "assigned_team": team,
            "affected_plugin": plugin,
            "layer": response.get("layer", "Unknown layer"),
            "suggested_actions": response.get("suggested_actions", [])
        }
        
        if state["entities"] is None:
            state["entities"] = {}
        state["entities"].update(routing_info)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        state["node_timings"]["route"] = elapsed_ms
        
        logger.info(
            "route_node_completed",
            severity=routing_info["severity"],
            team=routing_info["assigned_team"],
            elapsed_ms=elapsed_ms
        )
        
        return state
        
    except Exception as e:
        logger.error("route_node_failed", error=str(e))
        state["errors"].append(f"Routing failed: {str(e)}")
        
        if state["entities"] is None:
            state["entities"] = {}
        
        state["entities"].update({
            "severity": "P3",
            "assigned_team": "platform-team",
            "affected_plugin": "unknown",
            "layer": "Unknown",
            "suggested_actions": ["Manual triage required"]
        })
        
        state["node_timings"]["route"] = int((time.time() - start_time) * 1000)
        return state
