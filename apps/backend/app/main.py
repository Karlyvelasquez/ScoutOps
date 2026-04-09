import asyncio
import json
import shutil
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel as PydanticBaseModel
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from app.services.agent_service import AgentService
from app.services.resolution_watcher import start_resolution_watcher
from app.schemas.incident import (
    IncidentCreateResponse,
    IncidentStatusResponse,
    TicketUpdateRequest,
)
from app.security.guardrails import GuardrailViolationError, assert_safe_text, sanitize_text

UPLOAD_DIR = Path("./data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    watcher_task = asyncio.create_task(start_resolution_watcher())
    try:
        yield
    finally:
        watcher_task.cancel()
        try:
            await watcher_task
        except asyncio.CancelledError:
            pass

app = FastAPI(
    title="SRE Agent API",
    description="API for SRE incident triage agent",
    version="1.0.0",
    lifespan=lifespan,
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


class ValidateInputRequest(PydanticBaseModel):
    description: str
    source: str = "QA"


@app.post("/validate-input")
def validate_input(request: ValidateInputRequest):
    from agent.nodes.classify import classify_node
    from agent.schemas.input_schema import IncidentReport

    try:
        cleaned = sanitize_text(request.description)
    except Exception:
        return {"is_valid": False, "classification_confidence": 0.0, "reason": "Input could not be sanitized."}

    incident_report = IncidentReport(description=cleaned, source=request.source)
    state = {
        "incident_report": incident_report,
        "incident_type": None,
        "entities": None,
        "rag_context": None,
        "attachment_analysis": None,
        "technical_summary": None,
        "triage_result": None,
        "escalated": False,
        "vague_input": False,
        "errors": [],
        "node_timings": {},
    }
    try:
        result = classify_node(state)
    except Exception:
        return {"is_valid": True, "classification_confidence": 1.0, "reason": "Validation unavailable, proceeding."}

    is_vague = result.get("vague_input", False)
    if is_vague:
        confidence = 0.15
        reason = "The input does not appear to be a valid incident report. Please describe a specific technical issue."
    else:
        confidence = 0.85
        reason = "Input looks like a valid incident report."

    return {
        "is_valid": not is_vague,
        "classification_confidence": confidence,
        "incident_type": result.get("incident_type", "unknown"),
        "reason": reason,
    }


@app.post("/incident", response_model=IncidentCreateResponse)
async def create_incident(
    request: Request,
    background_tasks: BackgroundTasks,
    description: str | None = Form(default=None),
    source: str | None = Form(default=None),
    reporter_email: str | None = Form(default=""),
    attachment: UploadFile = File(default=None),
):
    if not description or not source:
        content_type = request.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            try:
                body = await request.json()
            except json.JSONDecodeError as exc:
                raise HTTPException(status_code=422, detail=f"invalid JSON body: {exc.msg}")
            description = description or body.get("description")
            source = source or body.get("source")
            if not reporter_email:
                reporter_email = body.get("reporter_email", "")

    if not description:
        raise HTTPException(status_code=422, detail="description is required")
    if not source:
        raise HTTPException(status_code=422, detail="source is required")
    if len(description) < 10:
        raise HTTPException(status_code=422, detail="description must be at least 10 characters")

    try:
        cleaned_description = sanitize_text(description)
        assert_safe_text(cleaned_description)
    except GuardrailViolationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if source not in ("QA", "soporte", "monitoring"):
        raise HTTPException(status_code=422, detail="source must be QA, soporte, or monitoring")

    attachment_path: str | None = None
    attachment_type: str | None = None

    if attachment and attachment.filename:
        incident_uid = uuid.uuid4().hex[:12]
        safe_name = f"{incident_uid}_{Path(attachment.filename).name}"
        dest = UPLOAD_DIR / safe_name
        with open(dest, "wb") as f:
            shutil.copyfileobj(attachment.file, f)
        attachment_path = str(dest)
        mime = attachment.content_type or ""
        attachment_type = "image" if mime.startswith("image/") else "log"

    incident_id = agent_service.create_incident(
        description=cleaned_description,
        source=source,
        reporter_email=reporter_email or None,
    )
    background_tasks.add_task(
        agent_service.process_incident_async,
        incident_id,
        cleaned_description,
        source,
        attachment_path,
        attachment_type,
        reporter_email or None,
    )
    return IncidentCreateResponse(incident_id=incident_id, status="en_proceso")


def map_incident_response(incident_data: dict) -> dict:
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
    
    return mapped_data

@app.get("/incident/{incident_id}", response_model=IncidentStatusResponse)
def get_incident(incident_id: str):
    incident_data = agent_service.get_incident_status(incident_id)

    if incident_data is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    return IncidentStatusResponse(**map_incident_response(incident_data))


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
        return IncidentStatusResponse(**map_incident_response(incident_data))
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
