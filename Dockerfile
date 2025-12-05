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

echo "[Docker] Starting gunicorn..."
exec gunicorn -b 0.0.0.0:7860 --timeout 1800 --graceful-timeout 1800 --worker-class sync hue_portal.hue_portal.wsgi:application
EOF

RUN chmod +x /entrypoint.sh

EXPOSE 7860
CMD ["/entrypoint.sh"]
