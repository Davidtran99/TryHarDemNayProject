#!/usr/bin/env bash
set -euo pipefail

show_help() {
  cat <<'EOF'
Usage: refresh_legal_data.sh --file PATH --code CODE [options]

Steps:
  1. python manage.py load_legal_document --file <PATH> --code <CODE>
  2. python scripts/generate_embeddings.py --model legal
  3. python scripts/build_faiss_index.py --model legal

Options:
  --file PATH          PDF/DOCX file to ingest (required unless --skip-ingest)
  --code CODE          Document code (required unless --skip-ingest)
  --skip-ingest        Skip step 1 and only regenerate embeddings/indexes
  --python BIN         Python command to use (default: python3)
  --help               Show this message
EOF
}

PYTHON_BIN="python3"
FILE_PATH=""
DOC_CODE=""
SKIP_INGEST=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --file)
      FILE_PATH="$2"
      shift 2
      ;;
    --code)
      DOC_CODE="$2"
      shift 2
      ;;
    --skip-ingest)
      SKIP_INGEST=true
      shift
      ;;
    --python)
      PYTHON_BIN="$2"
      shift 2
      ;;
    --help|-h)
      show_help
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      show_help
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."
DJANGO_DIR="$PROJECT_ROOT/hue_portal"

if [[ "$SKIP_INGEST" = false ]]; then
  if [[ -z "$FILE_PATH" || -z "$DOC_CODE" ]]; then
    echo "--file and --code are required unless --skip-ingest is set" >&2
    exit 1
  fi
  if [[ ! -f "$FILE_PATH" ]]; then
    echo "File not found: $FILE_PATH" >&2
    exit 1
  fi
  echo "[1/3] Ingesting document ${DOC_CODE} ..."
  pushd "$DJANGO_DIR" >/dev/null
  "$PYTHON_BIN" manage.py load_legal_document --file "$FILE_PATH" --code "$DOC_CODE"
  popd >/dev/null
else
  echo "Skipping ingestion step."
fi

echo "[2/3] Generating embeddings (legal) ..."
pushd "$PROJECT_ROOT" >/dev/null
"$PYTHON_BIN" scripts/generate_embeddings.py --model legal
popd >/dev/null

echo "[3/3] Building FAISS index (legal) ..."
pushd "$PROJECT_ROOT" >/dev/null
"$PYTHON_BIN" scripts/build_faiss_index.py --model legal
popd >/dev/null

echo "Done. Updated artifacts located in backend/hue_portal/artifacts/faiss_indexes."

