from pathlib import Path
import json
import asyncio
from typing import Optional
from datetime import datetime, timezone
from uuid import uuid4
from agent.graph import run_triage_agent
from agent.schemas.input_schema import IncidentReport
from agent.schemas.output_schema import TriageResult
from integrations.github import create_ticket as create_github_ticket
from integrations.jira import create_ticket as create_jira_ticket
from integrations.slack import notify_team
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

    def create_incident(
        self,
        description: str,
        source: str,
        reporter_email: Optional[str] = None,
    ) -> str:
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

    def process_incident_async(
        self,
        incident_id: str,
        description: str,
        source: str,
        attachment_path: Optional[str] = None,
        attachment_type: Optional[str] = None,
        reporter_email: Optional[str] = None,
    ) -> None:
        incident = self._load_incident(incident_id)
        if incident is None:
            return

        try:
            cleaned_description = sanitize_text(description)
            assert_safe_text(cleaned_description)

            incident_report = IncidentReport(
                description=cleaned_description,
                source=source,
                attachment_path=attachment_path,
                attachment_type=attachment_type,
                reporter_email=reporter_email,
            )
            start_time = datetime.now(timezone.utc)
            result = run_triage_agent(incident_report)
            end_time = datetime.now(timezone.utc)

            rag_response = RAGResponse.from_triage_result(result.model_dump())

            effective_reporter_email = reporter_email or "unknown@example.com"
            incident_payload = {
                "incident_id": incident_id,
                "incident_type": result.incident_type,
                "severity": result.severity,
                "affected_plugin": result.affected_plugin,
                "layer": result.layer,
                "assigned_team": result.assigned_team,
                "summary": result.summary,
                "suggested_actions": result.suggested_actions,
                "reporter_email": effective_reporter_email,
                "original_description": cleaned_description,
                "confidence_score": result.confidence_score,
            }

            CONFIDENCE_THRESHOLD = 0.70

            if result.confidence_score < CONFIDENCE_THRESHOLD:
                notify_team(
                    {**incident_payload, "escalated": True},
                    "https://github.com",
                )
                incident.state = IncidentState.ESCALADO_HUMANO
                incident.rag_response = rag_response
                incident.metadata.started_processing_at = start_time
                incident.metadata.completed_at = end_time
                incident.metadata.updated_at = end_time
                self._save_incident(incident)
                return

            github_ticket = create_github_ticket(incident_payload)
            jira_ticket = self._run_async_jira_ticket(incident_payload)

            github_ticket_url = github_ticket.get("ticket_url")
            jira_ticket_url = jira_ticket.get("ticket_url")
            ticket_url = github_ticket_url or jira_ticket_url

            ticket_number = github_ticket.get("ticket_number")
            if ticket_number:
                self._save_issue_reporter_mapping(str(ticket_number), effective_reporter_email)
                incident.ticket = IncidentTicket(
                    ticket_id=str(ticket_number),
                    status="open",
                    resolution_notes=None,
                    updated_at=end_time,
                )
            elif jira_ticket.get("ticket_key"):
                incident.ticket = IncidentTicket(
                    ticket_id=str(jira_ticket.get("ticket_key")),
                    status="open",
                    resolution_notes=None,
                    updated_at=end_time,
                )

            if ticket_url:
                notify_team(incident_payload, str(ticket_url))

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

    def _run_async_jira_ticket(self, incident_payload: dict) -> dict:
        try:
            return asyncio.run(create_jira_ticket(incident_payload))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(create_jira_ticket(incident_payload))
            finally:
                loop.close()
        except Exception:
            return {"ticket_id": None, "ticket_url": None, "ticket_key": None}
    
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

    def _save_issue_reporter_mapping(self, ticket_number: str, reporter_email: str) -> None:
        mapping_file = Path(__file__).resolve().parents[2] / "data" / "issue_reporters.json"
        mapping_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            if mapping_file.exists():
                with open(mapping_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    data = {}
            else:
                data = {}
        except Exception:
            data = {}

        data[str(ticket_number)] = reporter_email

        with open(mapping_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    
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
