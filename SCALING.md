# SCALING — ScoutOps Incident Triage Agent

## Overview

This document describes the current capacity of the single-instance deployment, the known bottlenecks in each subsystem, and the concrete path to scale each component independently. It also documents the technical assumptions and trade-off decisions made during the hackathon.

---

## Current Architecture (Single Instance)

```
  ┌──────────────────────────────────────────────────────────┐
  │  Docker Compose — single host                            │
  │                                                          │
  │  [Next.js Frontend] ──► [FastAPI Backend]                │
  │                              │                           │
  │                    ┌─────────┴──────────┐                │
  │                    │   LangGraph Agent  │                │
  │                    │ (6-node pipeline)  │                │
  │                    └─────────┬──────────┘                │
  │                              │                           │
  │              ┌───────────────┼───────────────┐           │
  │              ▼               ▼               ▼           │
  │        [Chroma DB]   [Gemini API]   [GitHub/Jira/Slack]  │
  │        (local vol)  (external)      (external APIs)      │
  │                                                          │
  │  [Resolution Watcher] — polls GitHub every 30 s          │
  └──────────────────────────────────────────────────────────┘
```

**All components run in a single Docker Compose stack.** Processing is synchronous per incident: the FastAPI request waits for the full 6-node LangGraph pipeline to complete before returning.

---

## Bottleneck Analysis

| Component | Current implementation | Bottleneck | Impact |
|-----------|----------------------|------------|--------|
| **LangGraph pipeline** | Synchronous, sequential 6 nodes | 2–4 s per LLM call × 4 nodes = 8–15 s total | Primary latency driver |
| **Gemini API** | 1 call per node (classify, extract, summarize, route) | External rate limit: 15 RPM (free tier) | Hard ceiling on concurrent incidents |
| **Chroma vector DB** | Single-node, local filesystem | No horizontal scaling; all reads hit one process | Limits RAG throughput under concurrent load |
| **GitHub API** | 1–2 calls per incident (search + create or comment) | 5,000 req/hr per token | ~83 incidents/min max (create only) |
| **Jira API** | 1 call per incident (create ticket) | Rate limit varies by plan | Additional latency ~300–800 ms |
| **Resolution watcher** | Polls GitHub every 30 s | Redundant API calls; O(n) per poll cycle | Rate limit waste; delayed close detection |
| **FastAPI** | Single uvicorn worker (default) | Blocks on background tasks | Limits true concurrency |
| **Deduplication** | `search_similar_issues()` before every ticket | 1 extra GitHub API call per incident | +200–400 ms, but reduces total ticket volume |

---

## Current Capacity

Single instance with default configuration:

- **End-to-end latency per incident:** 8–15 s (LLM-bound)
- **Effective throughput:** ~4–7 incidents/min (limited by Gemini free-tier RPM)
- **Paid Gemini tier:** ~60–120 incidents/min (latency-bound, not rate-bound)
- **Daily capacity (8 h window):** ~2,880–57,600 incidents depending on Gemini quota
- **Resolution notification delay:** up to 30 s after ticket close (polling interval)

> **Assumption:** Incident volume for a mid-size e-commerce platform is bursty, not continuous. Peak load is 10–50 incidents/hour during deployments or incidents, not sustained thousands/min.

---

## Scaling Path

### 1. API Layer — Decouple Ingestion from Processing

**Current:** `POST /incident` is synchronous — it waits for the full triage pipeline.

**Target:** Accept-and-queue pattern.

```
POST /incident  →  push to queue  →  return { incident_id, status: "en_proceso" }
                                              │
                                    Worker pool picks up task
                                    and runs LangGraph pipeline
```

**Implementation:** Redis + Celery or RabbitMQ + Celery.
- API layer becomes stateless and horizontally scalable.
- Worker replicas can scale independently based on queue depth.
- Priority queues: P1 incidents can be routed to a high-priority queue.

**Estimated gain:** 10× throughput increase with 4 worker replicas.

---

### 2. LangGraph Agent — Parallelise Independent Nodes

**Current:** Linear sequential pipeline — each node waits for the previous.

**Potential optimisation:** Nodes 3 and 4 (`retrieve` and `attachments`) are independent and can run in parallel after `extract`.

```
classify → extract → ┌─ retrieve    ─┐
                     └─ attachments ─┘  → summarize → route
```

**Implementation:** LangGraph supports `add_conditional_edges` with parallel branches.

**Estimated gain:** Reduce pipeline latency by ~20–30% (saves one full LLM-call slot).

---

### 3. Gemini API — Reduce Per-Node Calls

**Current:** 4 LLM calls per incident (classify, extract, summarize, route).

**Options:**
- **Prompt chaining:** Merge classify + extract into one call (single structured output with both fields). Saves one LLM round-trip.
- **Response caching:** Cache classify results for identical or near-identical descriptions (e.g., Redis with embedding similarity lookup).
- **Batch API:** Gemini batch mode for non-urgent incidents (async, higher quota).

**Estimated gain:** Merging classify+extract saves ~1–2 s and one rate-limit slot.

---

### 4. Vector DB — Distributed RAG

**Current:** Chroma single-node, local Docker volume.

**Migration path:**
1. Wrap vector client behind an adapter interface (`rag/embeddings.py`, `rag/queries.py`) — already partially done.
2. Deploy Qdrant or Weaviate as a separate service.
3. Dual-write during migration; cut read path after validation.
4. Add replication and sharding for high-availability.

**When to migrate:** When RAG retrieval latency exceeds 500 ms or when running >2 backend replicas (Chroma can't be shared across processes safely).

---

### 5. Ticketing / Event Flow — Replace Polling with Webhooks

**Current:** `resolution_watcher.py` polls GitHub every 30 s for closed issues.

**Issues:**
- O(n) GitHub API calls per poll cycle regardless of activity.
- Up to 30 s delay between ticket close and reporter email.
- Consumes GitHub rate limit quota continuously.

**Target:** GitHub webhook → FastAPI endpoint → process close event → send email.

```
GitHub closes issue  →  POST /webhooks/github  →  send SMTP notification
Jira resolves ticket →  POST /webhooks/jira    →  update incident state
```

**Additional:** Use idempotency keys per `(incident_id, ticket_id)` to prevent duplicate notifications on retries.

---

### 6. Infrastructure — Container Orchestration

**Current:** Docker Compose on a single host.

**Production target:**

| Service | Scaling unit | Notes |
|---------|-------------|-------|
| FastAPI | 2–4 replicas + load balancer (nginx/Traefik) | Stateless; scale horizontally |
| LangGraph workers | 4–10 Celery replicas | Scale based on queue depth metric |
| Chroma → Qdrant | 3-node cluster | Replication factor 2 |
| Resolution watcher | 1 instance with leader election | Avoid duplicate notifications |

**Migration:** Docker Compose → Kubernetes (Helm chart) or AWS ECS when load demands it.

---

## Throughput Estimates

| Setup | Incidents/min | Notes |
|-------|--------------|-------|
| Current (free Gemini tier) | 4–7 | Rate-limited by Gemini 15 RPM |
| Current (paid Gemini tier) | 60–80 | Latency-bound (~8–15 s/incident) |
| 4 Celery workers + paid Gemini | 120–200 | Queue absorbs burst; workers parallelise |
| 10 workers + merged classify+extract | 300–500 | Prompt optimisation reduces call count |
| Full production (webhook + distributed RAG) | 500–1,000+ | No polling overhead, RAG scales independently |

---

## Technical Assumptions

1. **Incident volume is bursty, not sustained.** Peak load occurs during deployments (~10–50 incidents/hour). Continuous high-frequency ingestion is not the primary use case.
2. **LLM is the primary cost and latency driver.** All other components (Chroma, GitHub API, Slack) are fast relative to Gemini response time.
3. **Deduplication reduces ticket volume by ~30–50%** in practice. Repeated incidents during the same outage are consolidated, reducing GitHub/Jira API pressure.
4. **≤ 0.70 escalation threshold reduces LLM load for vague inputs.** The `vague_input` short-circuit skips 4 out of 6 LLM calls for clearly invalid reports, saving quota.
5. **RAG corpus is bounded.** The Reaction Commerce plugin codebase is ~10K chunks. Chroma handles this comfortably; migration to Qdrant is only needed at 10× corpus size or multi-replica deployment.
6. **Integrations (GitHub, Jira, Slack, SMTP) are non-blocking on failure.** Each integration call has a try/except; failures are logged but don't retry or block the response. A production system would add a retry queue.

---

## Recommended Next Steps (Priority Order)

1. **Queue-backed workers** — highest impact; decouples ingestion from processing and enables horizontal scaling without changing agent logic.
2. **Webhook-based resolution events** — eliminates polling overhead and reduces GitHub rate limit consumption.
3. **Merge classify + extract nodes** — easy prompt change, saves ~1.5 s and one Gemini rate-limit slot per incident.
4. **Parallel retrieve + attachments** — LangGraph change, saves ~20% latency for incidents with attachments.
5. **Qdrant migration** — needed only when deploying >1 backend replica or RAG corpus exceeds 50K chunks.
6. **Idempotency table for notifications** — prevents duplicate emails/Slack messages on retry or watcher restart.
