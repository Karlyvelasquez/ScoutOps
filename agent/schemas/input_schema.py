from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class IncidentReport(BaseModel):
    description: str = Field(..., min_length=10, description="Descripción del incidente")
    source: Literal["QA", "soporte", "monitoring"] = Field(..., description="Fuente del reporte")
    attachment_path: Optional[str] = Field(None, description="Ruta al archivo adjunto guardado en el servidor")
    attachment_type: Optional[Literal["image", "log"]] = Field(None, description="Tipo del adjunto: imagen o log")
    reporter_email: Optional[str] = Field(None, description="Email del reportero para notificación de resolución")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp del reporte")
    
    class Config:
        json_schema_extra = {
            "example": {
                "description": "Users getting 500 error when trying to pay with credit card",
                "source": "QA",
                "attachment_path": None,
                "attachment_type": None,
                "reporter_email": "engineer@company.com"
            }
        }
