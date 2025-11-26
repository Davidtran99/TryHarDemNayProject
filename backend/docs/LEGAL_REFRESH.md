# Legal Data Refresh Workflow

Use this sequence whenever new DOCX/PDF files are imported outside the user-facing UI (e.g. nightly ETL or bulk manifests).

## Prerequisites

- Postgres + Redis running.
- Celery worker online (for interactive uploads) or `CELERY_TASK_ALWAYS_EAGER=true` for synchronous runs.
- Tesseract OCR installed (see `OCR_SETUP.md`).

## Manual Command Sequence

```
cd backend/hue_portal
source ../.venv/bin/activate

python manage.py load_legal_document --file "/path/to/docx" --code DOC-123
python ../scripts/generate_embeddings.py --model legal
python ../scripts/build_faiss_index.py --model legal
```

Notes:

- `load_legal_document` can be substituted with the manifest loader (`scripts/load_legal_documents.py`) if multiple files need ingestion.
- The embedding script logs processed sections; expect a SHA checksum for each chunk.
- FAISS builder writes artifacts under `backend/hue_portal/artifacts/faiss_indexes`.

## Automated Helper

`backend/scripts/refresh_legal_data.sh` wraps the three steps:

```
./backend/scripts/refresh_legal_data.sh \
  --file "/path/to/THONG-TU.docx" \
  --code TT-02
```

Flags:

- `--skip-ingest` to only regenerate embeddings/index (useful after editing chunking logic).
- `--python` to point at a specific interpreter (default `python3`).

## CI / Nightly Jobs

1. Sync new files into `tài nguyên/`.
2. Run the helper script for each file (or call the manifest loader first).
3. Archive FAISS artifacts (upload to object storage) so the chatbot containers can download them at boot.
4. Record build duration and artifact checksums for auditing.

## Verification Checklist

- `generate_embeddings` log ends with `Completed model=legal`.
- FAISS directory contains fresh timestamped `.faiss` + `.mappings.pkl`.
- Sample chatbot query (“Thông tư 02 ...”) returns snippets referencing the newly ingested document.

