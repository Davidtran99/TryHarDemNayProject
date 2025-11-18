# API Stress & Latency Test Plan (Draft)

## Objective
Prepare repeatable scenarios to benchmark chatbot API performance once staging load testing is requested.

## Preconditions
- Django server running with `DEBUG=0` if possible.
- Embeddings + FAISS indexes built.
- Database seeded (procedures, advisories, fines, offices).
- `API_BASE_URL` exported to match target environment.

## Test Scenarios
1. **Warm-up Smoke Test**
   - Run `scripts/test_api_endpoint.py` twice.
   - Record first-run vs second-run latency deltas (captures model warm-up).

2. **Sequential Latency Sweep**
   - Script: `python scripts/tests/seq_latency.py` (todo).
   - Send 100 sequential mixed-intent queries.
   - Metrics: p50/p90/p99 latency, mean RAG confidence.

3. **Concurrent Load (Low)**
   - Tool: `hey` or `wrk` against `/api/chat/` with 2 concurrent workers.
   - Duration: 60s.
   - Payloads: rotating JSON body list (procedure, advisory, fine, office, greeting).

4. **Concurrent Load (Moderate)**
   - 5–10 concurrent workers, 120s duration.
   - Monitor DB CPU + memory (Docker stats or `pg_stat_activity`).

5. **Timeout/Error Handling**
   - Intentionally kill Postgres mid-run to confirm API returns 500 with graceful message.
   - Restart and ensure recovery without manual intervention.

6. **Large Payload Edge Case**
   - Send message ~2,000 characters containing mixed language and emojis to confirm request validation + latency.

## Metrics to Capture
- Request count, success/error ratio.
- Latency (avg, p95, max).
- Intent accuracy sample (compare expected vs actual for 10% of requests).
- Resource usage: CPU, memory, DB connections.

## Reporting Template
- Date, environment, git commit.
- Table of scenarios vs metrics.
- Notable observations / regressions.
- Next actions.
