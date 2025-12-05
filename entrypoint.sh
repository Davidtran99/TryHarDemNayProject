#!/bin/bash
set -euo pipefail

log() {
  echo "[ENTRYPOINT] $1"
}

log "Boot sequence started at $(date -u +"%Y-%m-%d %H:%M:%S UTC")"

# Debug installed transformers version to ensure modeling_layers exists
python - <<'PY'
import importlib.util, transformers
print(f"[ENTRYPOINT] transformers version: {transformers.__version__}")
spec = importlib.util.find_spec("transformers.modeling_layers")
print(f"[ENTRYPOINT] transformers.modeling_layers available: {bool(spec)}")
PY

if [[ -z "${DATABASE_URL:-}" ]]; then
  log "DATABASE_URL is empty -> Django will fallback to POSTGRES_* or SQLite"
else
  log "DATABASE_URL detected (length: ${#DATABASE_URL})"
fi

cd /app

log "Running migrations..."
python hue_portal/manage.py migrate --noinput
log "Migrations completed."

log "Ensuring cache table exists..."
python hue_portal/manage.py createcachetable
log "Cache table ready."

log "Preloading all models to avoid first-request timeout..."

python -c "
import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hue_portal.hue_portal.settings')
import django
django.setup()

print('[ENTRYPOINT] 🔄 Starting model preload...', flush=True)

# 1. Preload Embedding Model (BGE-M3)
try:
    print('[ENTRYPOINT] 📦 Preloading embedding model (BGE-M3)...', flush=True)
    from hue_portal.core.embeddings import get_embedding_model
    embedding_model = get_embedding_model()
    if embedding_model:
        print('[ENTRYPOINT] ✅ Embedding model preloaded successfully', flush=True)
    else:
        print('[ENTRYPOINT] ⚠️ Embedding model not loaded', flush=True)
except Exception as e:
    print(f'[ENTRYPOINT] ⚠️ Embedding model preload failed: {e}', flush=True)

# 2. Preload LLM Model (llama.cpp)
llm_provider = os.environ.get('DEFAULT_LLM_PROVIDER') or os.environ.get('LLM_PROVIDER', '')
if llm_provider.lower() == 'llama_cpp':
    try:
        print('[ENTRYPOINT] 📦 Preloading LLM model (llama.cpp)...', flush=True)
        from hue_portal.chatbot.llm_integration import get_llm_generator
        llm_gen = get_llm_generator()
        if llm_gen and hasattr(llm_gen, 'llama_cpp') and llm_gen.llama_cpp:
            print('[ENTRYPOINT] ✅ LLM model preloaded successfully', flush=True)
        else:
            print('[ENTRYPOINT] ⚠️ LLM model not loaded (may load on first request)', flush=True)
    except Exception as e:
        print(f'[ENTRYPOINT] ⚠️ LLM model preload failed: {e} (will load on first request)', flush=True)
else:
    print(f'[ENTRYPOINT] ⏭️ Skipping LLM preload (provider is {llm_provider or \"not set\"}, not llama_cpp)', flush=True)

# 3. Preload Reranker Model (lazy, but trigger import)
try:
    print('[ENTRYPOINT] 📦 Preloading reranker model...', flush=True)
    from hue_portal.core.reranker import get_reranker
    reranker = get_reranker()
    if reranker:
        print('[ENTRYPOINT] ✅ Reranker model preloaded successfully', flush=True)
    else:
        print('[ENTRYPOINT] ⚠️ Reranker model not loaded (may load on first request)', flush=True)
except Exception as e:
    print(f'[ENTRYPOINT] ⚠️ Reranker preload failed: {e} (will load on first request)', flush=True)

print('[ENTRYPOINT] ✅ Model preload completed', flush=True)  # v2.0-preload-all
" || log "⚠️ Model preload had errors (models will load on first request)"

log "Starting Gunicorn on port ${PORT:-7860}..."

exec gunicorn hue_portal.hue_portal.wsgi:application \
    --bind 0.0.0.0:${PORT:-7860} \
    --timeout 600 \
    --workers 1 \
    --worker-class sync
