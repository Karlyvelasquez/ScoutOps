from pathlib import Path
import json
from typing import Optional
from datetime import datetime
from agent.graph import run_triage_agent
from agent.schemas.input_schema import IncidentReport
from agent.schemas.output_schema import TriageResult


class AgentService:
    def __init__(self, results_dir: str = "./data/incidents"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def process_incident(self, description: str, source: str) -> TriageResult:
        incident_report = IncidentReport(
            description=description,
            source=source
        )
        
        result = run_triage_agent(incident_report)
        
        self._save_result(result)
        
        return result
    
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
            data.pop("saved_at", None)
            return TriageResult(**data)
    
    def list_incidents(self, limit: int = 50) -> list[dict]:
        incidents = []
        
        for file_path in sorted(self.results_dir.glob("*.json"), reverse=True)[:limit]:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                incidents.append({
                    "incident_id": data["incident_id"],
                    "incident_type": data["incident_type"],
                    "severity": data["severity"],
                    "assigned_team": data["assigned_team"],
                    "saved_at": data.get("saved_at")
                })
        
        return incidents
