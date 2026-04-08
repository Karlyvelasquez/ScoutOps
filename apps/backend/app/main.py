from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal
from app.services.agent_service import AgentService

app = FastAPI(
    title="SRE Agent API",
    description="API for SRE incident triage agent",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent_service = AgentService()


class IncidentRequest(BaseModel):
    description: str
    source: Literal["QA", "soporte", "monitoring"]
    
    class Config:
        json_schema_extra = {
            "example": {
                "description": "Users getting 500 error when trying to pay with credit card",
                "source": "QA"
            }
        }


@app.get("/")
def read_root():
    return {
        "service": "SRE Agent API",
        "status": "running",
        "version": "1.0.0"
    }


@app.post("/incident")
def create_incident(request: IncidentRequest):
    try:
        result = agent_service.process_incident(
            description=request.description,
            source=request.source
        )
        
        return result.model_dump()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/incident/{incident_id}")
def get_incident(incident_id: str):
    result = agent_service.get_incident(incident_id)
    
    if result is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    return result.model_dump()


@app.get("/incidents")
def list_incidents(limit: int = 50):
    incidents = agent_service.list_incidents(limit=limit)
    return {"incidents": incidents, "count": len(incidents)}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
