from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from app.services.agent_service import AgentService
from app.schemas.incident import (
    IncidentCreateRequest,
    IncidentCreateResponse,
    IncidentStatusResponse,
    TicketUpdateRequest,
)

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


@app.get("/")
def read_root():
    return {
        "service": "SRE Agent API",
        "status": "running",
        "version": "1.0.0"
    }


@app.post("/incident", response_model=IncidentCreateResponse)
def create_incident(request: IncidentCreateRequest, background_tasks: BackgroundTasks):
    incident_id = agent_service.create_incident(
        description=request.description,
        source=request.source,
    )
    background_tasks.add_task(
        agent_service.process_incident_async,
        incident_id,
        request.description,
        request.source,
    )
    return IncidentCreateResponse(incident_id=incident_id, status="en_proceso")


@app.get("/incident/{incident_id}", response_model=IncidentStatusResponse)
def get_incident(incident_id: str):
    incident_data = agent_service.get_incident_status(incident_id)

    if incident_data is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    mapped_data = {
        "incident_id": incident_data["incident_id"],
        "status": incident_data["state"],
        "description": incident_data["input"]["description"],
        "source": incident_data["input"]["source"],
        "created_at": incident_data["metadata"]["created_at"],
        "updated_at": incident_data["metadata"]["updated_at"],
    }
    
    if incident_data.get("error"):
        mapped_data["error"] = incident_data["error"].get("message")
        
    if incident_data.get("ticket"):
        mapped_data["ticket"] = incident_data["ticket"]

    rag_response = incident_data.get("rag_response")
    if rag_response:
        result_dict = {
            "incident_id": incident_data["incident_id"],
            "incident_type": rag_response.get("incident_type"),
            "severity": rag_response.get("severity"),
            "summary": rag_response.get("summary"),
            "suggested_actions": rag_response.get("suggested_actions", []),
            "assigned_team": rag_response.get("assigned_team"),
            "confidence_score": rag_response.get("confidence_score"),
            "processing_time_ms": rag_response.get("processing_time_ms", 0)
        }
        
        components = rag_response.get("affected_components", [])
        if components:
            result_dict["affected_plugin"] = components[0].get("plugin", "")
            result_dict["layer"] = components[0].get("layer", "")
            result_dict["affected_file"] = components[0].get("file")
            
        mapped_data["result"] = result_dict

    return IncidentStatusResponse(**mapped_data)


@app.post("/webhook/ticket-update", response_model=IncidentStatusResponse)
def ticket_update_webhook(request: TicketUpdateRequest):
    try:
        incident_data = agent_service.update_ticket_status(
            incident_id=request.incident_id,
            ticket_id=request.ticket_id,
            ticket_status=request.ticket_status,
            resolution_notes=request.resolution_notes,
        )
        if incident_data is None:
            raise HTTPException(status_code=404, detail="Incident not found")
        return IncidentStatusResponse(**incident_data)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
