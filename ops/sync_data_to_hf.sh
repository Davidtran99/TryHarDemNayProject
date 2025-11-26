#!/bin/bash
# Đồng bộ dữ liệu + embeddings + FAISS index cho chatbot.
# Usage: ./ops/sync_data_to_hf.sh [--skip-etl] [--skip-embeddings] [--skip-faiss]

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPS_DIR="$ROOT_DIR/ops"
PYTHON_BIN="${PYTHON:-python3}"

# Load environment variables from .env files
load_env_file() {
  local env_file="$1"
  if [[ -f "$env_file" ]]; then
    echo "📝 Loading environment from $(basename "$env_file")..."
    # shellcheck disable=SC1090
    set -a
    source "$env_file"
    set +a
  fi
}

# Load environment variables (priority: .env.tunnel > .env)
if [[ -f "$OPS_DIR/.env.tunnel" ]]; then
  load_env_file "$OPS_DIR/.env.tunnel"
fi
if [[ -f "$ROOT_DIR/.env" ]]; then
  load_env_file "$ROOT_DIR/.env"
fi

# Ưu tiên .venv ở root, sau đó mới đến backend/venv
if [[ -d "$ROOT_DIR/.venv" ]]; then
  VENV_PATH="$ROOT_DIR/.venv"
elif [[ -d "$ROOT_DIR/backend/venv" ]]; then
  VENV_PATH="$ROOT_DIR/backend/venv"
else
  VENV_PATH=""
fi

RUN_ETL=1
RUN_EMBEDDINGS=1
RUN_FAISS=1

for arg in "$@"; do
  case "$arg" in
    --skip-etl) RUN_ETL=0 ;;
    --skip-embeddings) RUN_EMBEDDINGS=0 ;;
    --skip-faiss) RUN_FAISS=0 ;;
    *)
      echo "Unknown flag: $arg"
      exit 1
      ;;
  esac
done

if [[ -n "$VENV_PATH" && -d "$VENV_PATH" ]]; then
  # shellcheck disable=SC1090
  source "$VENV_PATH/bin/activate"
  echo "✅ Đã kích hoạt venv: $VENV_PATH"
fi

run_step() {
  local name="$1"
  shift
  echo "============================================"
  echo "▶️  $name"
  echo "============================================"
  echo "Command: $*"
  "$@"
  echo ""
}

cd "$ROOT_DIR/backend"

# Set PYTHONPATH for Django (backend directory must be in path)
export PYTHONPATH="$ROOT_DIR/backend:$ROOT_DIR:$PYTHONPATH"

if [[ $RUN_ETL -eq 1 ]]; then
  # Ensure DATABASE_URL is set for ETL
  if [[ -z "${DATABASE_URL:-}" ]]; then
    # Try to construct from POSTGRES_* variables
    if [[ -n "${POSTGRES_HOST:-}" && -n "${POSTGRES_PORT:-}" && -n "${POSTGRES_USER:-}" && -n "${POSTGRES_PASSWORD:-}" && -n "${POSTGRES_DB:-}" ]]; then
      export DATABASE_URL="postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
      echo "📝 Đã set DATABASE_URL từ POSTGRES_* variables"
    else
      echo "⚠️  Cảnh báo: DATABASE_URL chưa được set. ETL có thể fail."
    fi
  else
    echo "✅ DATABASE_URL đã được set"
  fi
  
  run_step "ETL dữ liệu" \
    "$PYTHON_BIN" scripts/etl_load.py \
    --datasets fines procedures advisories offices
else
  echo "⏭️  Bỏ qua bước ETL."
fi

if [[ $RUN_EMBEDDINGS -eq 1 ]]; then
  run_step "Generate embeddings" \
    "$PYTHON_BIN" scripts/generate_embeddings.py
else
  echo "⏭️  Bỏ qua bước tạo embeddings."
fi

if [[ $RUN_FAISS -eq 1 ]]; then
  run_step "Build FAISS index" \
    "$PYTHON_BIN" scripts/build_faiss_index.py
else
  echo "⏭️  Bỏ qua bước build FAISS."
fi

echo "✅ Hoàn tất các bước đồng bộ. Nhớ commit & push artifacts trong backend/hue_portal/artifacts/ nếu có thay đổi."


