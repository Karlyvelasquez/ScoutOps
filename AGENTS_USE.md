# AGENTS_USE.md

## 1. Agent overview

- Agent name: ScoutOps SRE Incident Triage Agent
- Purpose: triage e-commerce incidents end-to-end from raw report to actionable issue and stakeholder notifications
- Primary stack:
  - FastAPI backend
  - LangGraph orchestration + Gemini model
  - RAG over Reaction Commerce plugin code via Chroma + sentence-transformers
  - GitHub Issues, Slack webhook, SMTP email integrations
  - Langfuse tracing + JSON structured logs

## 2. Inputs and outputs

### Inputs

- Incident description text
- Optional logs/screenshots (handled upstream)
- Reporter metadata (email/source)

### Outputs

- Structured triage payload (incident type, severity, affected plugin, team, actions)
- GitHub issue ticket metadata
- Slack incident alert message
- Resolution email notification to reporter

## 3. Tools and external systems

- LLM provider: Gemini API
- Retrieval store: Chroma persistent collection `reaction_commerce`
- Knowledge source: Reaction Commerce monorepo plugin files
- Ticketing: GitHub Issues REST API
- Notifications: Slack Webhook, SMTP
- Tracing/telemetry: Langfuse

## 4. Workflow summary

1. Receive incident report.
2. Run triage pipeline and enrich with RAG context.
3. Create GitHub issue with severity/team labels.
4. Send Slack Block Kit notification to engineering.
5. Watch closed issues labeled `sre-agent`.
6. Notify original reporter by email exactly once per issue.

## 5. Reliability and failure behavior

- Integrations are failure-safe and return safe values (`False` or empty metadata) instead of crashing.
- Resolution watcher catches and logs poll-cycle exceptions, then continues.
- Email supports mock mode when SMTP is not configured.
- Chroma query path returns empty list on failure to preserve backend availability.

## 6. Observability

### Structured log format

All components emit JSON logs with these standard fields:

- `timestamp`
- `level`
- `service`
- `node_name`
- `incident_id`

Example:

```json
{
  "timestamp": "2026-04-08T18:22:10.412Z",
  "level": "INFO",
  "service": "integrations",
  "node_name": "github.create_ticket",
  "incident_id": "inc_9d42aa3b1d22",
  "message": "github_ticket_created",
  "ticket_number": 142
}
```

### Langfuse trace structure

Each traced async node creates a span with:

- `name`: node/function name
- `input`: function args/kwargs snapshot
- `output`: return payload or error object
- `metadata.latency_ms`: measured runtime in milliseconds
- `metadata.status`: `success` or `error`

Example trace metadata:

```json
{
  "name": "route_incident",
  "input": {"args": "(...)", "kwargs": {"incident_id": "inc_9d42aa3b1d22"}},
  "output": {"severity": "P1", "assigned_team": "payments"},
  "metadata": {"latency_ms": 824.33, "status": "success"}
}
```

## 7. Security

- Input sanitization:
  - User incident text is sanitized and validated before agent processing.
  - Unsafe patterns are rejected by guardrails layer.
- Prompt injection protection:
  - RAG retrieval is constrained to indexed code chunks and metadata.
  - Agent prompts should treat retrieved code as untrusted context, not instructions.
- Secrets handling:
  - Credentials are loaded from environment variables only.
  - `.env.example` contains placeholders, never production values.
- Safe tool usage:
  - Integrations are explicitly scoped (GitHub, Slack, SMTP).
  - Exceptions are caught and logged without exposing secrets in outputs.
  - Notification deduplication prevents repeated email sends for the same closed issue.

## 8. Scalability summary

Current implementation is single-instance and polling-based for simplicity, suitable for hackathon workloads. Horizontal scaling should introduce queue-based workers (Redis/Celery or RabbitMQ), event-driven closure notifications (webhooks), and a distributed vector backend (Qdrant/Weaviate). See `SCALING.md` for detailed architecture and throughput estimates.
