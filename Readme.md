# ScoutOps — SRE Incident Triage Agent

ScoutOps is an end-to-end incident triage system for e-commerce operations that converts raw reports (text, logs, screenshots) into actionable engineering work: it performs retrieval-augmented diagnosis over the Reaction Commerce monorepo, generates structured triage output, opens a GitHub Issue and a Jira ticket, alerts the team in Slack, deduplicates repeat incidents, and notifies the original reporter when the issue is resolved.

## Architecture

```mermaid
flowchart LR
    A[Incident Report\nText + Attachments] --> B[Backend API\nFastAPI]
    V[Voice Interface\nWebSocket + Web Speech] --> B
    B --> C[Agent Orchestrator\nLangGraph]
    C --> D[RAG Query Layer\nChroma + MiniLM]
    D --> E[Reaction Commerce KB\napi-plugin-* chunks]
    C --> F[GitHub Integration\nDedup + Create Issue]
    C --> G[Slack Integration\nTeam Notification]
    C --> L[Jira Integration\nCreate Ticket]
    H[Resolution Watcher\nPoll Closed Issues] --> F
    H --> S2[Slack #tickets-resolved\nResolution Alert]
    C --> K[Langfuse Tracing + JSON Logs]
    B --> N[Neon/Postgres\nTicket History]
    N --> R[SRE Reports\nWrapped Analytics]
```

## Agent Pipeline

The triage pipeline runs as a LangGraph `StateGraph` with 6 sequential nodes. Each node is independently traced via `@trace_node` (Langfuse) and logs structured JSON on completion.

```
Input: { description, source, attachment? }  ← also accepted via voice WebSocket
  │
  ▼
[1] classify_node        → incident_type: checkout_failure | login_error | catalog_issue | ...
  │                        classification_confidence < 0.35 → vague_input=True (short-circuits to escalation)
  │                        NOTE: attachment present → vague_input always False (file is the report)
  ▼
[2] extract_node         → entities: affected_service, feature, error_patterns, user_impact
  │
  ▼
[3] retrieve_node        → rag_context: top-5 Reaction Commerce code chunks by cosine similarity (1 - d²/2)
  │                        side-effect: sets entities.affected_file from best RAG hit
  ▼
[4] attachments_node     → attachment_analysis: Gemini Vision (images) or structured LLM (logs)
  │                        skipped if no attachment provided
  ▼
[5] summarize_node       → technical_summary: synthesizes description + RAG context + attachment
  │
  ▼
[6] route_node           → severity (P1/P2/P3) + assigned_team + affected_plugin + layer
                           hybrid_confidence = (llm × 0.7) + (rag_relevance × 0.3)  [if RAG results]
                           hybrid_confidence = llm_confidence                         [if no RAG results]
                           if confidence ≤ 0.70 → escalated_human (no ticket created)
                           if confidence > 0.70 → local dedup → GitHub dedup → create Issue + Jira ticket

Output: TriageResult JSON  ← spoken aloud via edge-tts if submitted via voice
```

> **Design note — Severity assignment:** Severity is determined inside `route_node` alongside team routing. This avoids a redundant LLM invocation and reduces latency by ~1–2 s. Both decisions share context and are produced atomically.

## Input Explainability

When multiple signals are present, the agent prioritizes them in this order:

1. **Attachment (log/image)** — highest fidelity. Error codes and stack traces extracted by `attachments_node` and injected verbatim into the summarize prompt.
2. **RAG codebase context** — `retrieve_node` maps the incident to exact plugin files via semantic search. Top relevance score contributes 30% of the hybrid confidence.
3. **Free-text description** — used by `classify_node` and `extract_node` for incident type and entity extraction.

The `confidence_score` field in the output reflects how well all signals agree. If signals conflict (e.g., attachment says `CPU 100%` but description mentions `Timeout`), both are injected into the summarize prompt and the LLM reconciles them explicitly.

## Governance Controls

| Control | Implementation |
|---|---|
| Vague input filter | `classify_node` sets `vague_input=True` when `classification_confidence < 0.35`; `route_node` short-circuits to escalation without further LLM calls |
| Attachment bypass | If an attachment is present, `vague_input` is never set to `True` — the file itself is treated as the incident report |
| Confidence threshold | `route_node` hybrid confidence ≤ 0.70 → no ticket created, Slack escalation alert sent |
| Human-in-the-loop | Frontend shows escalation card; Slack sends `⚠️ HUMAN REVIEW REQUIRED` Block Kit message |
| Local deduplication | `_find_local_duplicate()` scans the last 100 local incident files for an open ticket with the same `incident_type` before calling GitHub API, saving rate-limit quota |
| GitHub deduplication | `search_similar_issues()` checks open GitHub issues with matching `incident_type` + `affected_plugin`; if found, adds a comment instead of opening a new issue |
| Prompt injection guard | `guardrails.py` blocks 9 pattern classes before any LLM call; raises `GuardrailViolationError` → HTTP 400 |
| Input sanitization | Control chars stripped, whitespace collapsed in `sanitize_text()` before any LLM call |
| Notification deduplication | Resolution watcher marks tickets `resolved` in Postgres; `notify_resolution()` is called once per ticket close event |
| Frontend guard | Submit button disabled when `POST /validate-input` returns `is_valid: false` |

## Tech Stack

| Component | Technology | Reason |
|---|---|---|
| API service | FastAPI | Lightweight, typed backend with async support |
| Agent pipeline | LangGraph + Gemini 2.5 Flash | Multi-node triage orchestration with structured output |
| Retrieval layer | ChromaDB | Fast local persistent vector search |
| Embeddings | sentence-transformers all-MiniLM-L6-v2 | Efficient semantic code retrieval |
| Knowledge base | Reaction Commerce monorepo | Real e-commerce architecture and plugin logic |
| Ticketing | GitHub Issues API + Jira REST API | Issue tracking + enterprise workflow integration |
| Team notifications | Slack Webhooks (Block Kit) | Low-friction incident broadcast with per-team routing |
| Resolution notifications | Slack `#tickets-resolved` | Block Kit alert when GitHub/Jira issue is closed |
| Voice interface | WebSocket + Web Speech API + edge-tts | Real-time bilingual (ES/EN) voice incident reporting |
| Text-to-speech | edge-tts (Microsoft Edge Neural) | Free neural TTS, no API key required, streaming MP3 |
| Ticket persistence | asyncpg + Neon/PostgreSQL | Persistent incident history powering the reports dashboard |
| Analytics reports | `/reports/summary` + GPT-4o-mini | SRE Wrapped: AI-narrated incident stats per period |
| Observability | Langfuse + structlog (JSON) | Per-node traces and structured logs |
| Frontend | Next.js 14 + Tailwind CSS | Incident form + real-time status polling + voice UI |
| Runtime | Docker Compose | Reproducible local deployment |

## Quick Start

See **[QUICKGUIDE.md](QUICKGUIDE.md)** for full step-by-step instructions including:
- Environment variable setup (all required and optional keys)
- RAG ingestion
- Testing the full flow, escalation, deduplication, and resolution notification via UI and cURL

Minimum steps:

```bash
cp .env.example .env        # fill in GEMINI_API_KEY, GITHUB_TOKEN, GITHUB_REPO, SLACK_WEBHOOK_URL
pip install -r requirements.txt
python rag/ingest_repo.py   # index Reaction Commerce codebase into Chroma
docker compose up --build   # frontend :3000  backend :8000  chroma :8001
```

> **Note on GitHub repo configuration:** By default, tickets are created in the repo specified by `GITHUB_REPO` in `.env`. For evaluation purposes, this project uses [sre-agent-tickets](https://github.com/Karlyvelasquez/sre-agent-tickets/issues) as the demo repository. You can configure your own repo by changing `GITHUB_REPO` — the agent is agnostic to which repository receives the tickets.

## Folder Structure

```text
ScoutOps/
├── agent/                        # LangGraph pipeline
│   ├── nodes/                    #   classify, extract, retrieve, attachments, summarize, route
│   ├── prompts/                  #   .txt prompt templates per node
│   └── graph.py                  #   StateGraph definition
├── apps/
│   ├── backend/                  # FastAPI backend
│   │   └── app/
│   │       ├── db/               #   database.py (Neon/Postgres), queries.py, models.py
│   │       ├── routes/           #   incident.py, voice_ws.py, reports.py
│   │       ├── services/         #   agent_service.py, resolution_watcher.py
│   │       ├── schemas/          #   Pydantic models
│   │       ├── security/         #   guardrails.py (prompt injection)
│   │       └── main.py           #   API endpoints
│   └── frontend/                 # Next.js 14 frontend
│       └── src/
│           ├── app/              #   page.tsx (main view)
│           └── components/       #   ReportForm, ResultView, TicketStatus, VoiceButton
├── integrations/                 # GitHub, Jira, Slack, Email
├── observability/                # Langfuse tracing, structlog
├── rag/                          # Chroma ingestion and query
├── voice/                        # Voice module: intent_handler, session, synthesizer
├── docker-compose.yml
├── .env.example
├── QUICKGUIDE.md                 # Step-by-step run & test guide
├── SCALING.md                    # Scaling analysis and bottlenecks
└── AGENTS_USE.md                 # Agent documentation (hackathon submission)
```

## Hackathon Goal

Built for **AgentX Hackathon 2026**. Optimized for fast setup, practical reliability controls (confidence threshold, deduplication, escalation), and clear upgrade paths to production-scale operations documented in `SCALING.md`.
