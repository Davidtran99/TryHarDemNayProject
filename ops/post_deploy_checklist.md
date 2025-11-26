# Post-Deployment Checklist (Legal Upload Stack)

Use this list after each release or infrastructure change affecting ingestion, OCR, or retrieval.

## 1. OCR Smoke Test
- Upload a known scanned PDF (image-only) via `/legal-upload`.
- Confirm ingestion job finishes (`GET /api/legal-ingestion-jobs/<id>/` → `completed`).
- In Django admin, open the new `LegalDocument`; `raw_text_ocr` should contain text and at least one `LegalSection` must have `is_ocr=true`.

## 2. Queue & Worker Health
- Run `docker compose ps celery` (or `systemctl status celery`) – worker must be `Up`.
- Monitor Redis queue length: `redis-cli -u $REDIS_URL LLEN celery`.
- Check Celery heartbeat logs for warnings/errors.
- If jobs are stuck in `pending/running` longer than expected, inspect `docker compose logs celery`.

## 3. Embedding & FAISS Refresh
- After running `scripts/refresh_legal_data.sh`, verify:
  - `backend/hue_portal/artifacts/faiss_indexes/` contains updated timestamps.
  - `scripts/generate_embeddings.py` log ends with `Completed model=legal`.
- Restart backend (or reload model cache) if FAISS is loaded in memory.

## 4. Chatbot Regression
- Ask the chatbot about the freshly ingested document (e.g. “Trích Điều 3 của TT-02”).
- Response should include snippet + `download_url` reference to the new document.

## 5. Monitoring Notes
- Dashboard metrics to watch:
  - Average ingestion latency (upload → completed).
  - Celery queue size / worker heartbeat.
  - FAISS rebuild duration (emit logs every run).
- Set alerts if queue length > 10 for more than 5 minutes or if worker heartbeat is missing for >2 minutes.

Document any anomalies in `ops/dashboard_queries.md` or incident tracker.

