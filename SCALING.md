# SCALING - ScoutOps Incident Triage Agent

## Current Single-Instance Limitations

The current hackathon implementation is optimized for delivery speed and clarity:

- Single backend process handles ingestion, triage, integrations, and watcher polling.
- In-memory model caching is process-local; each backend replica would duplicate embedding model memory.
- Resolution watcher uses polling every 30 seconds, introducing delay and redundant API calls.
- Chroma runs as a single local container with local volume storage.
- Integration calls are synchronous per incident path, creating latency coupling to external APIs.

## Horizontal Scaling for Agent Workers

### Recommended architecture

- Split ingestion and triage into worker jobs.
- Keep API layer stateless.
- Push incident processing into a task queue.

### Option A: Redis + Celery

- API accepts incident and pushes task to Redis queue.
- Celery worker pool executes triage and integrations.
- Celery beat handles periodic tasks (or dedicated watcher worker).
- Scale by increasing worker replicas.

### Option B: RabbitMQ + Celery

- Better routing controls and durability for complex queue topologies.
- Useful if incident classes require priority queues (P1 > P2 > P3).

## Vector DB Scaling Path

### Current

- Chroma single-node, filesystem persistence.

### Scale-up migration

- Move to Qdrant cluster or Weaviate for distributed ANN search.
- Add tenant/project namespaces and replication.
- Move embedding generation to asynchronous batch jobs.

### Practical plan

1. Keep current chunk schema and metadata model.
2. Create adapter layer around vector client.
3. Deploy Qdrant/Weaviate and dual-write during migration.
4. Cut read path to new store after validation.

## Ticketing/Event Flow Scaling

### Current

- GitHub Issues + polling watcher.

### Scaled design

- Replace periodic polling with GitHub webhooks (issue closed event).
- Or migrate workflow to Jira/Linear webhooks for enterprise teams.
- Use event consumers to process closure notifications and dispatch email exactly-once using idempotency keys.

## Throughput Estimates

These are rough assumptions for hackathon sizing and local container resources.

### Current setup (single instance)

- End-to-end triage throughput: ~10 to 30 incidents/minute
- Main bottlenecks: LLM latency, integration API latency, single-worker concurrency
- Resolution notifications: up to 100 closed issues per 30-second poll window

### Scaled setup (queue + workers + distributed vector DB)

- 4 worker replicas: ~60 to 120 incidents/minute
- 10 worker replicas + optimized prompts/caching: ~150 to 300 incidents/minute
- Event-driven resolution notifications: near real-time (<5 seconds typical)

## Hackathon Scope Assumptions

- Incident volume is moderate and bursty, not continuous enterprise load.
- Prioritize correctness and demonstrable full-flow automation over strict SLA guarantees.
- RAG corpus is bounded to Reaction Commerce plugins and refreshed as needed.
- Minimal infrastructure operations overhead is preferred for demo reliability.

## Recommended Next Steps

1. Introduce queue-backed worker execution for triage.
2. Replace polling with webhook-based resolution events.
3. Add persistent idempotency table for notifications.
4. Migrate vector store to a distributed engine when retrieval volume grows.
