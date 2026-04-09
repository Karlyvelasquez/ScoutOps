from langgraph.graph import StateGraph, END
import uuid
from agent.state import AgentState
from agent.nodes import classify, extract, summarize, route
from agent.nodes import retrieve, attachments
from agent.schemas.input_schema import IncidentReport
from agent.schemas.output_schema import TriageResult
from agent.utils.logger import logger


def create_agent_graph():
    logger.info("creating_agent_graph")
    
    workflow = StateGraph(AgentState)
    
    workflow.add_node("classify", classify.classify_node)
    workflow.add_node("extract", extract.extract_node)
    workflow.add_node("retrieve", retrieve.retrieve_node)
    workflow.add_node("attachments", attachments.attachments_node)
    workflow.add_node("summarize", summarize.summarize_node)
    workflow.add_node("route", route.route_node)
    
    workflow.set_entry_point("classify")
    workflow.add_edge("classify", "extract")
    workflow.add_edge("extract", "retrieve")
    workflow.add_edge("retrieve", "attachments")
    workflow.add_edge("attachments", "summarize")
    workflow.add_edge("summarize", "route")
    workflow.add_edge("route", END)
    
    logger.info("agent_graph_created")
    return workflow.compile()


def run_triage_agent(incident_report: IncidentReport) -> TriageResult:
    logger.info(
        "triage_agent_started",
        source=incident_report.source,
        description_length=len(incident_report.description)
    )
    
    initial_state: AgentState = {
        "incident_report": incident_report,
        "incident_type": None,
        "entities": None,
        "rag_context": None,
        "attachment_analysis": None,
        "technical_summary": None,
        "triage_result": None,
        "escalated": False,
        "vague_input": False,
        "errors": [],
        "node_timings": {}
    }
    
    graph = create_agent_graph()
    
    try:
        final_state = graph.invoke(initial_state)
        
        if final_state["errors"]:
            logger.warning(
                "triage_completed_with_errors",
                errors=final_state["errors"]
            )
        
        result = build_triage_result(final_state)
        
        logger.info(
            "triage_agent_completed",
            incident_id=result.incident_id,
            incident_type=result.incident_type,
            severity=result.severity,
            total_time_ms=result.processing_time_ms
        )
        
        return result
        
    except Exception as e:
        logger.error("triage_agent_failed", error=str(e))
        raise


def build_triage_result(state: AgentState) -> TriageResult:
    entities = state.get("entities") or {}
    total_time = sum(state["node_timings"].values())

    confidence_score = float(entities.get("confidence_score", 0.5 if state["errors"] else 0.75))

    affected_file = entities.get("affected_file")
    if not affected_file:
        rag_context = state.get("rag_context") or []
        if rag_context:
            best = max(rag_context, key=lambda r: r.get("relevance_score", 0.0))
            fp = best.get("file_path")
            if fp and fp != "unknown":
                affected_file = fp

    return TriageResult(
        incident_id=str(uuid.uuid4()),
        incident_type=state.get("incident_type", "unknown"),
        severity=entities.get("severity", "P3"),
        affected_plugin=entities.get("affected_plugin") or "unknown",
        layer=entities.get("layer", "Unknown"),
        affected_file=affected_file,
        assigned_team=entities.get("assigned_team", "platform-team"),
        summary=state.get("technical_summary", "Unable to generate summary"),
        suggested_actions=entities.get("suggested_actions", ["Manual triage required"]),
        confidence_score=confidence_score,
        processing_time_ms=total_time,
        attachment_analysis=state.get("attachment_analysis"),
    )
