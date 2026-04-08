from agent.graph import run_triage_agent
from agent.schemas.input_schema import IncidentReport
from integrations.github import create_ticket
from integrations.slack import notify_team
from rag.queries import query_codebase

description = "Users cannot log in after password reset and receive invalid token errors"
reporter_email = "qa+auth@test.com"

triage = run_triage_agent(
    IncidentReport(
        description=description,
        source="QA",
    )
)

incident = {
    "incident_type": triage.incident_type,
    "severity": triage.severity,
    "affected_plugin": triage.affected_plugin,
    "layer": triage.layer,
    "assigned_team": triage.assigned_team,
    "summary": triage.summary,
    "suggested_actions": triage.suggested_actions,
    "reporter_email": reporter_email,
    "original_description": description,
}

print("INFERRED_TRIAGE:", triage.model_dump())

ticket = create_ticket(incident)
print("TICKET_RESULT:", ticket)

if ticket.get("ticket_url"):
    sent = notify_team(incident, ticket["ticket_url"])
    print("SLACK_RESULT:", sent)
else:
    print("SLACK_RESULT: skipped (no ticket_url)")

results = query_codebase(
    triage.incident_type,
    description,
    n_results=3,
)
print("RAG_TOP_RESULTS:")
for r in results:
    print(" -", r["plugin_name"], "->", r["file_path"])
