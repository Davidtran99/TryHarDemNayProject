# API Testing Update — 2025-11-14

## Context
- Verified `/api/chatbot/health/` and `/api/chat/` after URL trailing slash + serialization fixes.
- All tests executed against Django dev server on port `8090` using the project virtualenv.

## Commands
```bash
# Terminal 1
cd backend/hue_portal
DJANGO_DEBUG=1 POSTGRES_HOST=localhost POSTGRES_PORT=5433 \
  ../../.venv/bin/python manage.py runserver 0.0.0.0:8090

# Terminal 2
cd backend
API_BASE_URL=http://localhost:8090 \
POSTGRES_HOST=localhost POSTGRES_PORT=5433 \
python scripts/test_api_endpoint.py
```

## Results Summary
| Metric | Value |
|--------|-------|
| Health check | 200 OK (`classifier_loaded=True`) |
| Chat queries | 6 / 6 succeeded |
| Intent accuracy | 100 % |
| Avg latency | 3.67 s (first call warms embedding model) |
| Max latency | ~17.3 s (initial model load) |
| Min latency | ~0.22 s |

## Notable Fixes Validated
1. **Trailing slash routing**: `/api/chatbot/health/` now resolves (was 404 before).
2. **Safe serialization**: `_serialize_document` prevents JSON encoding errors when returning RAG documents.
3. **RAG intent coverage**: All intents (`procedure`, `advisory`, `fine`, `office`) returned results with correct confidence scores.

## Follow-up
- Keep `API_BASE_URL` synced with whichever port `runserver` uses.
- Capture latency metrics again after deploying to staging to compare with local baseline above.
