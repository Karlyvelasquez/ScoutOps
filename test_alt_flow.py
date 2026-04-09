from agent.graph import run_triage_agent
import asyncio
from agent.schemas.input_schema import IncidentReport
from integrations.github import create_ticket
from integrations.jira import create_ticket as create_jira_ticket
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

github_ticket = create_ticket(incident)
print("GITHUB_TICKET_RESULT:", github_ticket)

jira_ticket = asyncio.run(create_jira_ticket(incident))
print("JIRA_TICKET_RESULT:", jira_ticket)

ticket_url_for_slack = github_ticket.get("ticket_url") or jira_ticket.get("ticket_url")

if ticket_url_for_slack:
    sent = notify_team(incident, ticket_url_for_slack)
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
