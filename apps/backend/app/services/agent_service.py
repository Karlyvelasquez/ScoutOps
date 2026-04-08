from pathlib import Path
import json
from typing import Optional
from datetime import datetime, timezone
from uuid import uuid4
from agent.graph import run_triage_agent
from agent.schemas.input_schema import IncidentReport
from agent.schemas.output_schema import TriageResult
from app.security.guardrails import assert_safe_text, sanitize_text
from app.schemas.incident_model import (
    Incident,
    IncidentError,
    IncidentInput,
    IncidentMetadata,
    IncidentState,
    IncidentTicket,
    RAGResponse,
)


class AgentService:
    def __init__(self, results_dir: str = "./data/incidents"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def create_incident(self, description: str, source: str) -> str:
        cleaned_description = sanitize_text(description)
        assert_safe_text(cleaned_description)

        incident_id = f"inc_{uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        incident = Incident(
            incident_id=incident_id,
            state=IncidentState.EN_PROCESO,
            input=IncidentInput(description=cleaned_description, source=source),
            metadata=IncidentMetadata(
                created_at=now,
                updated_at=now,
                started_processing_at=None,
                completed_at=None,
            ),
        )
        self._save_incident(incident)
        return incident_id

    def process_incident_async(self, incident_id: str, description: str, source: str) -> None:
        incident = self._load_incident(incident_id)
        if incident is None:
            return

        try:
            cleaned_description = sanitize_text(description)
            assert_safe_text(cleaned_description)

            incident_report = IncidentReport(description=cleaned_description, source=source)
            start_time = datetime.now(timezone.utc)
            result = run_triage_agent(incident_report)
            end_time = datetime.now(timezone.utc)

            rag_response = RAGResponse.from_triage_result(result.model_dump())
            incident.state = IncidentState.COMPLETADO
            incident.rag_response = rag_response
            incident.metadata.started_processing_at = start_time
            incident.metadata.completed_at = end_time
            incident.metadata.updated_at = end_time
            self._save_incident(incident)
        except Exception as exc:
            now = datetime.now(timezone.utc)
            incident.state = IncidentState.ERROR
            incident.error = IncidentError(
                message=str(exc),
                error_type=type(exc).__name__,
                timestamp=now,
            )
            incident.metadata.updated_at = now
            self._save_incident(incident)
    
    def process_incident(self, description: str, source: str) -> TriageResult:
        incident_report = IncidentReport(
            description=description,
            source=source
        )
        
        result = run_triage_agent(incident_report)
        
        self._save_result(result)
        
        return result

    def get_incident_status(self, incident_id: str) -> Optional[dict]:
        incident = self._load_incident(incident_id)
        if incident is None:
            return None
        return incident.model_dump_for_storage()

    def update_ticket_status(
        self,
        incident_id: str,
        ticket_id: str,
        ticket_status: str,
        resolution_notes: Optional[str] = None,
    ) -> Optional[dict]:
        incident = self._load_incident(incident_id)
        if incident is None:
            return None

        now = datetime.now(timezone.utc)
        incident.ticket = IncidentTicket(
            ticket_id=ticket_id,
            status=ticket_status,
            resolution_notes=resolution_notes,
            updated_at=now,
        )
        incident.metadata.updated_at = now
        self._save_incident(incident)
        return incident.model_dump_for_storage()

    def _save_incident(self, incident: Incident) -> None:
        file_path = self.results_dir / f"{incident.incident_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(incident.model_dump_for_storage(), f, indent=2, default=str)

    def _load_incident(self, incident_id: str) -> Optional[Incident]:
        file_path = self.results_dir / f"{incident_id}.json"
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return Incident.from_dict(data)
        except Exception:
            return None
    
    def _save_result(self, result: TriageResult):
        file_path = self.results_dir / f"{result.incident_id}.json"
        
        result_dict = result.model_dump()
        result_dict["saved_at"] = datetime.now().isoformat()
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, indent=2, default=str)
    
    def get_incident(self, incident_id: str) -> Optional[TriageResult]:
        file_path = self.results_dir / f"{incident_id}.json"
        
        if not file_path.exists():
            return None
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Backward compatibility with records that include lifecycle fields.
            if "result" in data and data["result"]:
                data = data["result"]
            data.pop("saved_at", None)
            return TriageResult(**data)
    
    def list_incidents(self, limit: int = 50) -> list[dict]:
        incidents = []
        
        for file_path in sorted(self.results_dir.glob("*.json"), reverse=True)[:limit]:
            incident = self._load_incident(file_path.stem)
            if incident is None or incident.rag_response is None:
                continue
            incidents.append({
                "incident_id": incident.incident_id,
                "incident_type": incident.rag_response.incident_type,
                "severity": incident.rag_response.severity,
                "assigned_team": incident.rag_response.assigned_team,
                "state": incident.state.value,
                "created_at": incident.metadata.created_at.isoformat(),
            })
        
        return incidents
