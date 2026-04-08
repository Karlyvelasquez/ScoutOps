from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class IncidentState(str, Enum):
    EN_PROCESO = "en_proceso"
    COMPLETADO = "completado"
    ERROR = "error"


class AffectedComponent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Nombre del componente")
    plugin: str = Field(..., description="Plugin de Reaction Commerce")
    layer: str = Field(..., description="Capa de arquitectura (GraphQL, Resolver, Service, etc.)")
    file: Optional[str] = Field(None, description="Archivo específico afectado")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confianza de que esté afectado")


class RAGResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_type: str = Field(...)
    severity: Literal["P1", "P2", "P3"] = Field(...)
    summary: str = Field(...)
    suggested_actions: List[str] = Field(default_factory=list)
    affected_components: List[AffectedComponent] = Field(default_factory=list)
    assigned_team: str = Field(...)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    processing_time_ms: int = Field(default=0)

    @classmethod
    def from_triage_result(cls, triage_result: dict) -> "RAGResponse":
        """Converts TriageResult from agent into RAGResponse."""
        components = [
            AffectedComponent(
                name=triage_result.get("affected_plugin", ""),
                plugin=triage_result.get("affected_plugin", ""),
                layer=triage_result.get("layer", ""),
                file=triage_result.get("affected_file"),
                confidence=triage_result.get("confidence_score", 0.8),
            )
        ]
        return cls(
            incident_type=triage_result.get("incident_type", "unknown"),
            severity=triage_result.get("severity", "P3"),
            summary=triage_result.get("summary", ""),
            suggested_actions=triage_result.get("suggested_actions", []),
            affected_components=components,
            assigned_team=triage_result.get("assigned_team", ""),
            confidence_score=triage_result.get("confidence_score", 0.0),
            processing_time_ms=triage_result.get("processing_time_ms", 0),
        )


class IncidentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(..., description="Descripción del incidente sanitizada")
    source: Literal["QA", "soporte", "monitoring"] = Field(...)


class IncidentTicket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket_id: str = Field(...)
    status: Literal["open", "in_progress", "resolved", "closed"] = Field(default="open")
    resolution_notes: Optional[str] = Field(None)
    updated_at: datetime = Field(...)


class IncidentMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    started_processing_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)


class IncidentError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(...)
    error_type: str = Field(...)
    timestamp: datetime = Field(...)


class Incident(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: str = Field(..., description="ID único")
    state: IncidentState = Field(..., description="Estado actual")
    input: IncidentInput = Field(..., description="Entrada procesada")
    metadata: IncidentMetadata = Field(..., description="Timestamps y auditoría")
    rag_response: Optional[RAGResponse] = Field(None, description="Respuesta del RAG/Agente")
    ticket: Optional[IncidentTicket] = Field(None, description="Información cruzada de ticket")
    error: Optional[IncidentError] = Field(None, description="Información de error si aplica")

    def model_dump_for_storage(self) -> dict:
        """Returns dict suitable for JSON file storage while preserving all data."""
        return self.model_dump(mode="json", exclude_none=False)

    @classmethod
    def from_dict(cls, data: dict) -> "Incident":
        """Reconstruct Incident from stored dict."""
        return cls(**data)
