import time
from agent.state import AgentState
from agent.utils.logger import logger
from observability.tracing import trace_node


@trace_node("retrieve_node")
def retrieve_node(state: AgentState) -> AgentState:
    logger.info("retrieve_node_started", incident_type=state.get("incident_type"))
    start_time = time.time()

    try:
        from rag.queries import query_codebase

        incident_type = state.get("incident_type", "unknown")
        description = state["incident_report"].description

        results = query_codebase(incident_type, description, n_results=5)

        state["rag_context"] = results

        if results:
            best = max(results, key=lambda r: r.get("relevance_score", 0.0))
            if state["entities"] is None:
                state["entities"] = {}
            if best.get("file_path") and best["file_path"] != "unknown":
                state["entities"]["affected_file"] = best["file_path"]
            if best.get("plugin_name") and best["plugin_name"] != "unknown":
                state["entities"].setdefault("rag_plugin_hint", best["plugin_name"])

        elapsed_ms = int((time.time() - start_time) * 1000)
        state["node_timings"]["retrieve"] = elapsed_ms

        logger.info(
            "retrieve_node_completed",
            results_count=len(results),
            top_score=results[0].get("relevance_score") if results else None,
            elapsed_ms=elapsed_ms,
        )

    except Exception as e:
        logger.error("retrieve_node_failed", error=str(e))
        state["errors"].append(f"RAG retrieval failed: {str(e)}")
        state["rag_context"] = []
        state["node_timings"]["retrieve"] = int((time.time() - start_time) * 1000)

    return state
