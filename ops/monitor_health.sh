#!/bin/bash
# Script giám sát health endpoint + pg_isready để dùng với cron.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/ops/.env.tunnel"
SPACE_BASE_URL="${HF_SPACE_URL:-https://davidtran999-hue-portal-backend.hf.space}"
API_HEALTH="${SPACE_BASE_URL%/}/api/chatbot/health/"
LOG_PATH="$ROOT_DIR/ops/logs/monitor_health.log"

timestamp() {
  date "+%Y-%m-%d %H:%M:%S"
}

log() {
  local level="$1"
  shift
  local msg="$*"
  printf "%s [%s] %s\n" "$(timestamp)" "$level" "$msg" | tee -a "$LOG_PATH"
}

check_health() {
  local response
  response=$(curl -s -w "\nHTTP:%{http_code}\n" "$API_HEALTH" || true)
  local status
  status=$(echo "$response" | grep "HTTP:" | cut -d: -f2)
  if [[ "$status" == "200" ]]; then
    log "INFO" "Health OK"
  else
    log "ERROR" "Health FAILED (status=$status)"
    echo "$response" | grep -v "HTTP:" >>"$LOG_PATH"
  fi
}

check_pg() {
  if [[ ! -f "$ENV_FILE" ]]; then
    log "WARN" "Bỏ qua pg_isready: chưa có $ENV_FILE"
    return
  fi
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  if [[ -z "${PG_TUNNEL_HOST:-}" || -z "${PG_TUNNEL_PORT:-}" ]]; then
    log "WARN" "Bỏ qua pg_isready: thiếu thông tin tunnel trong $ENV_FILE"
    return
  fi
  if ! command -v pg_isready >/dev/null; then
    log "WARN" "pg_isready không có trong PATH."
    return
  fi
  if PGPASSWORD="${PG_TUNNEL_PASSWORD:-${POSTGRES_PASSWORD:-}}" \
    pg_isready \
      -h "${PG_TUNNEL_HOST}" \
      -p "${PG_TUNNEL_PORT}" \
      -d "${PG_TUNNEL_DB:-${POSTGRES_DB:-hue_portal}}" \
      -U "${PG_TUNNEL_USER:-${POSTGRES_USER:-hue}}"; then
    log "INFO" "pg_isready OK"
  else
    log "ERROR" "pg_isready FAILED"
  fi
}

check_health
check_pg

