from app.routes.incident import router as incident_router
from app.routes.voice_ws import router as voice_router
from app.routes.reports import router as reports_router

__all__ = ["incident_router", "voice_router", "reports_router"]
