#test_incident_model.py ejecutar pruebas unitrarias para validar el modelo Incident.
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "../.."))

from app.schemas.incident_model import (
    Incident,
    IncidentError,
    IncidentInput,
    IncidentMetadata,
    IncidentState,
    IncidentTicket,
    RAGResponse,
    AffectedComponent,
)


def test_incident_model_complete_lifecycle():
    """Valida que el modelo Incident capture todo el ciclo de vida sin pérdida de datos."""
    
    print("\n" + "=" * 80)
    print("TEST: Incident Model Complete Lifecycle")
    print("=" * 80)
    
    # 1. Crear incidente en estado EN_PROCESO
    now = datetime.now(timezone.utc)
    incident_id = "inc_test123456"
    
    incident = Incident(
        incident_id=incident_id,
        state=IncidentState.EN_PROCESO,
        input=IncidentInput(
            description="Users getting 500 error when trying to pay with credit card",
            source="QA"
        ),
        metadata=IncidentMetadata(
            created_at=now,
            updated_at=now,
            started_processing_at=None,
            completed_at=None,
        ),
    )
    
    print(f"\n✅ Incident created:")
    print(f"   ID: {incident.incident_id}")
    print(f"   State: {incident.state.value}")
    print(f"   Description: {incident.input.description}")
    
    # 2. Serializar a JSON (simular almacenamiento)
    incident_json = incident.model_dump_for_storage()
    json_str = json.dumps(incident_json, default=str, indent=2)
    print(f"\n✅ Serialized to JSON ({len(json_str)} bytes)")
    
    # 3. Deserializar desde JSON (simular recuperación)
    incident_restored = Incident.from_dict(json.loads(json_str))
    assert incident_restored.incident_id == incident_id
    assert incident_restored.state == IncidentState.EN_PROCESO
    print(f"✅ Deserialized from JSON: state={incident_restored.state.value}")
    
    # 4. Simular respuesta del RAG
    rag_data = {
        "incident_type": "checkout_failure",
        "severity": "P1",
        "summary": "Users cannot complete checkout due to Stripe payment timeout.",
        "suggested_actions": [
            "Check Stripe API status",
            "Verify STRIPE_SECRET_KEY in production",
        ],
        "affected_plugin": "api-plugin-payments-stripe",
        "layer": "GraphQL resolver → placeOrder",
        "affected_file": "resolvers/Mutation/placeOrder.js",
        "assigned_team": "payments-team",
        "confidence_score": 0.92,
        "processing_time_ms": 3200,
    }
    
    rag_response = RAGResponse.from_triage_result(rag_data)
    print(f"\n✅ RAG Response created:")
    print(f"   Type: {rag_response.incident_type}")
    print(f"   Severity: {rag_response.severity}")
    print(f"   Team: {rag_response.assigned_team}")
    print(f"   Components: {len(rag_response.affected_components)}")
    
    # 5. Actualizar incidente con RAG response
    incident_restored.state = IncidentState.COMPLETADO
    incident_restored.rag_response = rag_response
    incident_restored.metadata.started_processing_at = now
    incident_restored.metadata.completed_at = datetime.now(timezone.utc)
    
    # 6. Re-serializar y re-deserializar
    completed_json = incident_restored.model_dump_for_storage()
    json_str2 = json.dumps(completed_json, default=str, indent=2)
    incident_final = Incident.from_dict(json.loads(json_str2))
    
    print(f"\n✅ Incident updated after processing:")
    print(f"   State: {incident_final.state.value}")
    print(f"   RAG Type: {incident_final.rag_response.incident_type}")
    print(f"   RAG Severity: {incident_final.rag_response.severity}")
    
    # 7. Agregar ticket
    ticket_now = datetime.now(timezone.utc)
    incident_final.ticket = IncidentTicket(
        ticket_id="TCK-456",
        status="in_progress",
        resolution_notes="Monitoring Stripe API status",
        updated_at=ticket_now,
    )
    incident_final.metadata.updated_at = ticket_now
    
    # 8. Re-serializar con ticket
    ticket_json = incident_final.model_dump_for_storage()
    json_str3 = json.dumps(ticket_json, default=str, indent=2)
    incident_with_ticket = Incident.from_dict(json.loads(json_str3))
    
    print(f"\n✅ Incident with ticket attached:")
    print(f"   Ticket ID: {incident_with_ticket.ticket.ticket_id}")
    print(f"   Ticket Status: {incident_with_ticket.ticket.status}")
    
    # 9. Agregar error y validar
    incident_error = Incident(
        incident_id="inc_error_test",
        state=IncidentState.ERROR,
        input=IncidentInput(
            description="Test error handling",
            source="monitoring",
        ),
        metadata=IncidentMetadata(
            created_at=now,
            updated_at=datetime.now(timezone.utc),
            started_processing_at=now,
            completed_at=None,
        ),
        error=IncidentError(
            message="LLM API timeout",
            error_type="TimeoutError",
            timestamp=datetime.now(timezone.utc),
        ),
    )
    
    error_json = incident_error.model_dump_for_storage()
    json_str4 = json.dumps(error_json, default=str, indent=2)
    incident_error_restored = Incident.from_dict(json.loads(json_str4))
    
    print(f"\n✅ Incident with error captured:")
    print(f"   State: {incident_error_restored.state.value}")
    print(f"   Error Type: {incident_error_restored.error.error_type}")
    print(f"   Error Message: {incident_error_restored.error.message}")
    
    # 10. Validar que todos los datos están preservados
    assert incident_with_ticket.incident_id == incident_id
    assert incident_with_ticket.state == IncidentState.COMPLETADO
    assert incident_with_ticket.input.description is not None
    assert incident_with_ticket.rag_response is not None
    assert incident_with_ticket.ticket is not None
    assert incident_with_ticket.metadata.created_at is not None
    assert incident_with_ticket.metadata.completed_at is not None
    
    print(f"\n" + "=" * 80)
    print("✅ ALL TESTS PASSED - Data integrity preserved through full lifecycle")
    print("=" * 80)


if __name__ == "__main__":
    try:
        test_incident_model_complete_lifecycle()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
