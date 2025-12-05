FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# System dependencies (OCR + build essentials)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-vie \
        libpoppler-cpp-dev \
        pkg-config \
        libgl1 && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Optional check: cố gắng import CrossEncoder, nhưng KHÔNG dừng build nếu thiếu
RUN python -c "from sentence_transformers import CrossEncoder; print('[Docker] ✅ CrossEncoder available for reranking')" || \
    echo "[Docker] ❌ CrossEncoder not available! Tiếp tục build, backend sẽ tự fallback không dùng reranker."

# Copy toàn bộ backend để tránh lệch phiên bản
COPY backend /app/backend
RUN ln -sfn /app/backend/hue_portal /app/hue_portal

# Create static and media directories
RUN mkdir -p /app/hue_portal/static /app/hue_portal/media

# Create entrypoint script to run lightweight migrations before starting server
RUN cat <<'EOF' >/entrypoint.sh
#!/bin/bash
set -e

echo "[Docker] Running migrations..."
if ! python /app/hue_portal/manage.py migrate --noinput; then
    echo "[Docker] Migration failed, retrying with SQLite fallback..."
    unset DATABASE_URL
    python /app/hue_portal/manage.py migrate --noinput || echo "[Docker] SQLite migration also failed, continuing..."
fi

RUN_HEAVY_STARTUP_TASKS="${RUN_HEAVY_STARTUP_TASKS:-0}"
if [ "$RUN_HEAVY_STARTUP_TASKS" = "1" ]; then
    echo "[Docker] Running heavy startup tasks (generate QA, train intent, populate tsv)..."
    python /app/hue_portal/manage.py generate_legal_questions || echo "[Docker] generate_legal_questions failed, continuing..."
    python /app/hue_portal/chatbot/training/train_intent.py || echo "[Docker] Intent training failed, continuing..."
    python /app/hue_portal/manage.py populate_legal_tsv || echo "[Docker] populate_legal_tsv failed, continuing..."
else
    echo "[Docker] Skipping heavy startup tasks (RUN_HEAVY_STARTUP_TASKS=$RUN_HEAVY_STARTUP_TASKS)."
fi

echo "[Docker] Collecting static files..."
python /app/hue_portal/manage.py collectstatic --noinput || echo "[Docker] Collectstatic failed, continuing..."

echo "[Docker] Preloading all models to avoid first-request timeout..."
python -c "
import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hue_portal.hue_portal.settings')
import django
django.setup()

print('[Docker] 🔄 Starting model preload...', flush=True)

# 1. Preload Embedding Model (BGE-M3)
try:
    print('[Docker] 📦 Preloading embedding model (BGE-M3)...', flush=True)
    from hue_portal.core.embeddings import get_embedding_model
    embedding_model = get_embedding_model()
    if embedding_model:
        print('[Docker] ✅ Embedding model preloaded successfully', flush=True)
    else:
        print('[Docker] ⚠️ Embedding model not loaded', flush=True)
except Exception as e:
    print(f'[Docker] ⚠️ Embedding model preload failed: {e}', flush=True)

# 2. Preload LLM Model (llama.cpp)
llm_provider = os.environ.get('DEFAULT_LLM_PROVIDER') or os.environ.get('LLM_PROVIDER', '')
if llm_provider.lower() == 'llama_cpp':
    try:
        print('[Docker] 📦 Preloading LLM model (llama.cpp)...', flush=True)
        from hue_portal.chatbot.llm_integration import get_llm_generator
        llm_gen = get_llm_generator()
        if llm_gen and hasattr(llm_gen, 'llama_cpp') and llm_gen.llama_cpp:
            print('[Docker] ✅ LLM model preloaded successfully', flush=True)
        else:
            print('[Docker] ⚠️ LLM model not loaded (may load on first request)', flush=True)
    except Exception as e:
        print(f'[Docker] ⚠️ LLM model preload failed: {e} (will load on first request)', flush=True)
else:
    print(f'[Docker] ⏭️ Skipping LLM preload (provider is {llm_provider or \"not set\"}, not llama_cpp)', flush=True)

# 3. Preload Reranker Model
try:
    print('[Docker] 📦 Preloading reranker model...', flush=True)
    from hue_portal.core.reranker import get_reranker
    reranker = get_reranker()
    if reranker:
        print('[Docker] ✅ Reranker model preloaded successfully', flush=True)
    else:
        print('[Docker] ⚠️ Reranker model not loaded (may load on first request)', flush=True)
except Exception as e:
    print(f'[Docker] ⚠️ Reranker preload failed: {e} (will load on first request)', flush=True)

print('[Docker] ✅ Model preload completed', flush=True)
" || echo "[Docker] ⚠️ Model preload had errors (models will load on first request)"

echo "[Docker] Starting gunicorn..."
# Reduce tokenizers parallelism warnings and risk of fork deadlocks
export TOKENIZERS_PARALLELISM=false
# Shorter timeouts to avoid long hangs; adjust if needed
cd /app/backend && export PYTHONPATH="/app/backend:${PYTHONPATH}" && exec gunicorn -b 0.0.0.0:7860 --timeout 600 --graceful-timeout 600 --worker-class sync --config python:hue_portal.hue_portal.gunicorn_app hue_portal.hue_portal.gunicorn_app:application
EOF

RUN chmod +x /entrypoint.sh

EXPOSE 7860
CMD ["/entrypoint.sh"]

EXPOSE 7860
CMD ["/entrypoint.sh"]

EXPOSE 7860
CMD ["/entrypoint.sh"]
