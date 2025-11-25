#!/bin/bash
# Orchestrates local development stack: Postgres/Redis (Docker), Django backend, Vite frontend.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
  printf "%b%s%b\n" "$BLUE" "$1" "$NC"
}

success() {
  printf "%b%s%b\n" "$GREEN" "$1" "$NC"
}

warn() {
  printf "%b%s%b\n" "$YELLOW" "$1" "$NC"
}

log "🔧 Starting Docker services (db, redis)..."
if docker compose up -d db redis >/dev/null; then
  success "Docker services are up."
else
  warn "Docker compose failed—please ensure Docker Desktop is running."
  exit 1
fi

log "🚀 Starting backend..."
if ! pgrep -f "manage.py runserver 0.0.0.0:8000" >/dev/null; then
  (
    cd backend/hue_portal
    source ../venv/bin/activate
    python3 manage.py runserver 0.0.0.0:8000 > ../../backend.log 2>&1 &
  )
  success "Backend listening on http://localhost:8000 (logs: backend.log)"
else
  warn "Backend already running."
fi

log "🖥️  Starting frontend (Vite)..."
if ! pgrep -f "vite" >/dev/null; then
  (
    cd frontend
    VITE_API_BASE="https://davidtran999-hue-portal-backend.hf.space/api" npm run dev -- --host 0.0.0.0 > ../frontend.log 2>&1 &
  )
  success "Frontend listening on http://127.0.0.1:3000 (logs: frontend.log)"
else
  warn "Frontend already running."
fi

cat <<'EOF'

========================
✅ Services started
------------------------
Backend:  http://localhost:8000
Frontend: http://127.0.0.1:3000

To stop:
  pkill -f "manage.py runserver"
  pkill -f "vite"
  docker compose down

Logs:
  tail -f backend.log
  tail -f frontend.log
========================
EOF


