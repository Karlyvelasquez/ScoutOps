# QUICKGUIDE - Run ScoutOps from Zero

## 1. Prerequisites

- Docker Desktop (or Docker Engine + Compose v2)
- Python 3.11+
- Git
- API keys and credentials:
  - Gemini API key
  - GitHub token with issue write permissions
  - Slack incoming webhook URL
  - SMTP credentials (optional; if omitted, email runs in mock mode)
  - Langfuse keys (optional but recommended)

## 2. Clone the repo

```bash
git clone <your-repo-url>
cd ScoutOps
```

## 3. Set up environment variables

```bash
cp .env.example .env
```

Fill in `.env` with real values for required integrations.

## 4. Run ingestion

```bash
python rag/ingest_repo.py
```

What this does:
- Uses local Reaction Commerce path from `REACTION_COMMERCE_REPO_PATH` (or clones automatically)
- Indexes `packages/api-plugin-*` files (`.js`, `.graphql`, `README.md`)
- Creates/updates Chroma collection `reaction_commerce`

## 5. Start the app

```bash
docker compose up --build
```

Expected services:
- Frontend on `http://localhost:3000`
- Backend on `http://localhost:8000`
- Chroma on `http://localhost:8001`

## 6. Test the full flow

1. Submit an incident from the UI (or backend API).
2. Confirm triage runs and backend returns structured analysis.
3. Confirm a GitHub Issue is created with labels and summary.
4. Confirm Slack receives the incident Block Kit notification.
5. Close the GitHub Issue.
6. Wait up to 30 seconds for the resolution watcher poll cycle.
7. Confirm reporter receives resolution email (or mock-mode log entry).

## Troubleshooting

- No GitHub issue created: verify `GITHUB_TOKEN` and `GITHUB_REPO`.
- No Slack alert: verify `SLACK_WEBHOOK_URL`.
- No email sent: verify SMTP values or confirm mock-mode logs.
- Empty RAG retrieval: rerun ingestion and confirm Chroma path and data volume.
