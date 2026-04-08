from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class TriageResult(BaseModel):
    incident_id: str = Field(..., description="ID único del incidente")
    incident_type: str = Field(..., description="Tipo de incidente clasificado")
    severity: Literal["P1", "P2", "P3"] = Field(..., description="Nivel de severidad")
    affected_plugin: str = Field(..., description="Plugin de Reaction Commerce afectado")
    layer: str = Field(..., description="Capa donde ocurre el problema")
    affected_file: Optional[str] = Field(None, description="Archivo específico afectado")
    assigned_team: str = Field(..., description="Equipo asignado para resolver")
    summary: str = Field(..., description="Resumen técnico del incidente")
    suggested_actions: List[str] = Field(..., description="Acciones sugeridas para resolver")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confianza del análisis")
    processing_time_ms: int = Field(..., description="Tiempo de procesamiento en ms")
    
    class Config:
        json_schema_extra = {
            "example": {
                "incident_id": "inc_123456",
                "incident_type": "checkout_failure",
                "severity": "P1",
                "affected_plugin": "api-plugin-payments-stripe",
                "layer": "GraphQL resolver → placeOrder",
                "affected_file": "resolvers/Mutation/placeOrder.js",
                "assigned_team": "payments-team",
                "summary": "Users cannot complete checkout due to Stripe payment timeout.",
                "suggested_actions": [
                    "Check Stripe API status at status.stripe.com",
                    "Inspect resolver logs in api-plugin-payments-stripe/resolvers/",
                    "Verify STRIPE_SECRET_KEY env variable in production"
                ],
                "confidence_score": 0.85,
                "processing_time_ms": 3500
            }
        }
