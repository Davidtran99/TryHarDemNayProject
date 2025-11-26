#!/bin/bash
# Kiểm thử nhanh kết nối PostgreSQL thông qua tunnel local.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/ops/.env.tunnel"
PYTHON_BIN="${PYTHON:-python3}"
MANAGE_PY="$ROOT_DIR/backend/hue_portal/manage.py"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "❌ Không tìm thấy $ENV_FILE. Chạy start_ngrok_and_set_db.py trước." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

if [[ -z "${PG_TUNNEL_HOST:-}" || -z "${PG_TUNNEL_PORT:-}" ]]; then
  echo "❌ Thiếu PG_TUNNEL_HOST/PORT trong $ENV_FILE." >&2
  exit 1
fi

DATABASE_URL="postgres://${PG_TUNNEL_USER:-${POSTGRES_USER:-hue}}:${PG_TUNNEL_PASSWORD:-${POSTGRES_PASSWORD:-}}@${PG_TUNNEL_HOST}:${PG_TUNNEL_PORT}/${PG_TUNNEL_DB:-${POSTGRES_DB:-hue_portal}}"
export DATABASE_URL

echo "============================================"
echo "🔍 Kiểm tra Django manage.py check"
echo "DATABASE_URL=$DATABASE_URL"
echo "============================================"
"$PYTHON_BIN" "$MANAGE_PY" check

if command -v pytest >/dev/null; then
  echo ""
  echo "============================================"
  echo "🧪 Chạy pytest core/tests/test_legal_ingestion.py (nếu có)."
  echo "============================================"
  (cd "$ROOT_DIR/backend/hue_portal" && pytest core/tests/test_legal_ingestion.py || true)
else
  echo "⚠️  pytest chưa được cài, bỏ qua bước test."
fi

echo ""
echo "============================================"
echo "📡 pg_isready qua tunnel"
echo "============================================"
if command -v pg_isready >/dev/null; then
  PGPASSWORD="${PG_TUNNEL_PASSWORD:-${POSTGRES_PASSWORD:-}}" \
    pg_isready \
    -h "${PG_TUNNEL_HOST}" \
    -p "${PG_TUNNEL_PORT}" \
    -d "${PG_TUNNEL_DB:-${POSTGRES_DB:-hue_portal}}" \
    -U "${PG_TUNNEL_USER:-${POSTGRES_USER:-hue}}"
else
  echo "⚠️  pg_isready không có sẵn."
fi

echo ""
echo "✅ Test local hoàn tất."

