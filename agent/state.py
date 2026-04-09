from typing import TypedDict, Optional, Dict, Any, List
from agent.schemas.input_schema import IncidentReport
from agent.schemas.output_schema import TriageResult


class AgentState(TypedDict):
    incident_report: IncidentReport
    
    incident_type: Optional[str]
    entities: Optional[Dict[str, Any]]
    rag_context: Optional[List[Dict[str, Any]]]
    attachment_analysis: Optional[str]
    technical_summary: Optional[str]
    
    triage_result: Optional[TriageResult]
    escalated: bool
    
    errors: List[str]
    node_timings: Dict[str, int]
