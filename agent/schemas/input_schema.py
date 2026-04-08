from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class IncidentReport(BaseModel):
    description: str = Field(..., min_length=10, description="Descripción del incidente")
    source: Literal["QA", "soporte", "monitoring"] = Field(..., description="Fuente del reporte")
    attachment: Optional[str] = Field(None, description="Path al archivo adjunto (para futuro)")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp del reporte")
    
    class Config:
        json_schema_extra = {
            "example": {
                "description": "Users getting 500 error when trying to pay with credit card",
                "source": "QA",
                "attachment": None
            }
        }
