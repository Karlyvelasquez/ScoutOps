# QUICKGUIDE — Run ScoutOps from Zero

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Docker Desktop (or Engine + Compose v2) | Required to run all services |
| Python 3.11+ | Required for RAG ingestion and local tests |
| Git | Required to clone the repo |
| **Gemini API key** | Required — LLM backbone |
| **GitHub token** (`issues:write` scope) | Required — ticket creation + deduplication |
| **Slack incoming webhook URL** | Required — team notifications |
| Jira API token + project key | Optional — creates Jira tickets in parallel |
| Langfuse public + secret key | Optional but recommended for tracing |

---

## Step 1 — Clone the repo

```bash
git clone https://github.com/Karlyvelasquez/ScoutOps.git
cd ScoutOps
```

---

## Step 2 — Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in the required values:

```env
# --- Required ---
GEMINI_API_KEY=...          # or set LLM_PROVIDER=openai + OPENAI_API_KEY
GITHUB_TOKEN=...            # personal access token, scope: issues:write
GITHUB_REPO=owner/repo      # e.g. Karlyvelasquez/sre-agent-tickets (or your own repo)

SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# --- Optional: Jira ---
JIRA_BASE_URL=https://your-site.atlassian.net
JIRA_EMAIL=you@example.com
JIRA_API_TOKEN=...
JIRA_PROJECT_KEY=SRE

# --- Optional: per-team Slack channel routing ---
# Maps team names to dedicated Slack incoming webhook URLs.
# If a team is not listed, falls back to SLACK_WEBHOOK_URL.
SLACK_TEAM_WEBHOOKS_JSON={
  "payments-team":    "https://hooks.slack.com/services/..."  ,
  "accounts-team":   "https://hooks.slack.com/services/...",
  "catalog-team":    "https://hooks.slack.com/services/...",
  "orders-team":     "https://hooks.slack.com/services/...",
  "inc-human-review":"https://hooks.slack.com/services/...",
  "tickets-resolved":"https://hooks.slack.com/services/..."
}
# Channel mapping:
#   payments-team    → #inc-payments
#   accounts-team    → #inc-accounts
#   catalog-team     → #inc-catalog
#   orders-team      → #inc-orders
#   inc-human-review → #inc-human-review  (escalations)
#   tickets-resolved → #tickets-resolved  (resolution notifications)

# --- Optional: Observability ---
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# --- Optional: Ticket history + SRE Reports dashboard ---
NEON_DATABASE_URL=postgresql://user:password@ep-xxx.neon.tech/neondb?sslmode=require
# Leave blank to run without persistent history (JSON-only mode)

# --- Optional: SRE Wrapped AI narration ---
OPENAI_API_KEY=sk-...  # Used only by GET /reports/summary; falls back to static phrases if absent
```

---

## Step 3 — Index the codebase (RAG ingestion)

This step populates the Chroma vector DB with Reaction Commerce plugin source code. It only needs to run once (or when the codebase changes).

```bash
pip install -r requirements.txt
python rag/ingest_repo.py
```

What it does:
- Clones or reads Reaction Commerce from `REACTION_COMMERCE_REPO_PATH`
- Indexes `packages/api-plugin-*` files (`.js`, `.graphql`, `README.md`)
- Creates the `reaction_commerce` collection in `./chroma_data/`

Expected output:
```
Indexing api-plugin-payments-stripe... 24 chunks
Indexing api-plugin-catalog... 31 chunks
...
✅ Ingestion complete. Total chunks: 312
```

---

## Step 4 — Start all services

```bash
docker compose up --build
```

Services started:

| Service | URL | Description |
|---------|-----|-------------|
| Frontend (Next.js) | http://localhost:3000 | Incident report form + history dashboard |
| Backend (FastAPI) | http://localhost:8000 | Agent API + triage pipeline |
| Vector DB (Chroma) | http://localhost:8001 | RAG retrieval |

Wait for all three services to show healthy before testing:
```
vector-db  | Chroma server online
backend    | INFO: Application startup complete
frontend   | ✓ Ready on http://localhost:3000
```

---

## Step 5 — Test the full flow

### Option A — Via UI

1. Open **http://localhost:3000**
2. Paste a valid incident description, e.g.:
   > *"Los usuarios no pueden completar el checkout. El carrito muestra error 500 cuando intentan procesar el pago con Stripe. Afecta al 15% de los usuarios desde hace 30 minutos."*
3. Click **Enviar Reporte**
4. Watch the spinner — triage runs in ~8–15 s
5. Result panel shows: severity, team, confidence score, suggested actions
6. Check GitHub — a new issue should appear with labels `P1`, `payments-team`, `checkout_failure`
7. Check Slack — Block Kit notification sent to configured webhook

### Option B — Via cURL

```bash
# Submit incident
curl -X POST http://localhost:8000/incident \
  -F "description=Users cannot complete checkout. Error 500 from Stripe API. Affects 15% of users since 14:30 UTC." \
  -F "source=QA"

# Returns: {"incident_id": "inc_abc123..."}

# Poll for result
curl http://localhost:8000/incident/inc_abc123...
```

### Option C — Validate input only (no ticket created)

```bash
curl -X POST http://localhost:8000/validate-input \
  -H "Content-Type: application/json" \
  -d '{"description": "algo está roto", "source": "QA"}'

# Returns: {"is_valid": false, "reason": "..."}
```

---

## Step 6 — Test escalation (low-confidence)

Submit a vague input that should escalate instead of creating a ticket:

```bash
curl -X POST http://localhost:8000/incident \
  -F "description=Algo no funciona. Los usuarios se quejan." \
  -F "source=soporte"
```

Expected result:
- `status: "escalado_humano"`
- No GitHub issue created
- Slack alert with `:warning: HUMAN REVIEW REQUIRED`
- UI shows amber/red escalation card

---

## Step 7 — Test deduplication

Submit the same incident type twice while the first GitHub issue is still open:

```bash
# First submission — creates new issue
curl -X POST http://localhost:8000/incident \
  -F "description=Users getting 402 errors on Stripe checkout. Payment service is down." \
  -F "source=monitoring"

# Second submission — should deduplicate
curl -X POST http://localhost:8000/incident \
  -F "description=Checkout failing with payment error. Stripe returning 402 for all orders." \
  -F "source=soporte"
```

Expected result on second submission:
- No new GitHub issue created
- Comment added to existing issue
- UI shows orange **Duplicado** badge with link to original issue

---

## Step 8 — Test the voice interface

1. Open **http://localhost:3000**
2. Click the **microphone** button in the form
3. Grant browser microphone permission when prompted
4. Speak an incident in Spanish or English, e.g.:
   > *"Los usuarios no pueden hacer checkout. Hay un error 500 al procesar el pago con Stripe."*
5. Wait for the spoken acknowledgement (*"Recibido. Estoy analizando el incidente..."*)
6. Wait ~10–15 s for the pipeline to complete — the result will be read aloud

Alternatively, test the WebSocket directly:

```javascript
// Browser console test
const ws = new WebSocket('ws://localhost:8000/ws/voice');
ws.onmessage = e => console.log(JSON.parse(e.data));
ws.send(JSON.stringify({
  type: 'transcript',
  text: 'Checkout failing with 500 error from Stripe API',
  lang: 'en'
}));
```

Expected messages from the server:
1. `{type: "transcript", text: "..."}` — echo
2. `{type: "response_text", text: "..."}` — acknowledgement text
3. `<binary>` — MP3 audio chunks
4. `{type: "audio_end"}`
5. `{type: "incident_created", incident_id: "inc_..."}`
6. `{type: "incident_result", text: "...", data: {...}}` — spoken result

---

## Step 9 — Test SRE Reports (Wrapped)

```bash
# Summary for the last month (default)
curl http://localhost:8000/reports/summary

# Last week
curl "http://localhost:8000/reports/summary?period=week"

# Last day
curl "http://localhost:8000/reports/summary?period=day"
```

Expected response structure:
```json
{
  "raw": {
    "total_incidents": 42,
    "most_failing_plugin": "api-plugin-payments-stripe",
    "peak_p1_hour": 14,
    "total_hours_lost": 5.2,
    "estimated_cost_usd": 780.0,
    "avg_resolution_time_per_category": {"checkout_failure": 1.4}
  },
  "phrases": {
    "team_summary": "42 incidents...",
    "villain_phrase": "api-plugin-payments-stripe attacked the scoreboard...",
    ...
  }
}
```

> **Note:** Requires `NEON_DATABASE_URL` to be set. Without it, `get_all_tickets()` returns empty and stats will show zeros. If `OPENAI_API_KEY` is absent, the `phrases` block uses deterministic fallback text.

---

## Step 10 — Test resolution notification

1. Open the GitHub issue created in Step 5
2. Close it manually
3. Wait up to 30 seconds (resolution watcher poll interval)
4. Check Slack — the `#tickets-resolved` channel should receive a Block Kit message:
   ```
   ✅ Ticket resolved - P1 checkout_failure
   Ticket: #187  |  Affected Plugin: api-plugin-payments-stripe
   Resolved Summary: ...
   ```
5. Confirm in logs:
   ```bash
   docker compose logs backend | grep slack_resolution
   ```

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| No GitHub issue created | Verify `GITHUB_TOKEN` (scope `issues:write`) and `GITHUB_REPO` format (`owner/repo`) |
| No Slack notification | Verify `SLACK_WEBHOOK_URL` is a valid incoming webhook URL |
| No Jira ticket | Verify `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY` |
| No resolution notification in Slack | Verify `tickets-resolved` key in `SLACK_TEAM_WEBHOOKS_JSON` (or set `SLACK_RESOLVED_WEBHOOK_URL`); check logs for `slack_resolution_notification_failed` |
| Empty RAG results | Re-run `python rag/ingest_repo.py` and verify `./chroma_data/` is non-empty |
| `confidence=0.0` on valid incident | Confirm RAG ingestion ran; vague input short-circuit triggers on `classification_confidence < 0.35` (bypassed automatically if attachment is present) |
| Voice: no audio output | Verify `edge-tts` is installed (`pip install edge-tts`); check browser microphone permission |
| Voice: WebSocket disconnects immediately | Check backend logs: `docker compose logs backend \| grep ws` |
| Reports: all zeros | Set `NEON_DATABASE_URL` in `.env`; run `python apps/backend/app/db/seed_incidents.py` to populate test data |
| Reports: `phrases` look plain | Set `OPENAI_API_KEY` for AI-narrated summaries; without it, deterministic fallback phrases are used |
| Frontend shows nothing | Check backend logs: `docker compose logs backend` |
| Triage taking >30 s | Check Gemini API key quota — free tier is 15 RPM |

---

## GitHub Repository Configuration

By default, ScoutOps creates tickets in the repository specified by `GITHUB_REPO` in `.env`. 

**For evaluation:** This project demonstrates ticket creation in [sre-agent-tickets](https://github.com/Karlyvelasquez/sre-agent-tickets/issues). You can view the full incident history and triage decisions there.

**For your own use:** Simply change `GITHUB_REPO` to any repository you own (e.g., `myorg/incident-tracker`). The agent is completely agnostic — it works with any GitHub repo where your token has `issues:write` permissions. No changes to the code are needed.
