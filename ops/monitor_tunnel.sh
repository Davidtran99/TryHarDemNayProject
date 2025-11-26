#!/bin/bash
# Quick status script để xem tunnel PostgreSQL đang hoạt động ra sao.
# Usage: ./ops/monitor_tunnel.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/ops/.env.tunnel"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "⚠️  Chưa tìm thấy $ENV_FILE. Copy ops/env.tunnel.example rồi chạy lại." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

print_section() {
  echo "----------------------------------------"
  echo "$1"
  echo "----------------------------------------"
}

print_section "1) Thông tin tunnel hiện tại"
echo "HF Space      : ${HF_SPACE_ID:-davidtran999/hue-portal-backend}"
echo "Local port    : ${PG_TUNNEL_LOCAL_PORT:-${POSTGRES_PORT:-5543}}"
echo "Remote host   : ${PG_TUNNEL_HOST:-<chưa có>}"
echo "Remote port   : ${PG_TUNNEL_PORT:-<chưa có>}"
echo "Database      : ${PG_TUNNEL_DB:-${POSTGRES_DB:-hue_portal}}"
echo "User          : ${PG_TUNNEL_USER:-${POSTGRES_USER:-hue}}"
echo "Last updated  : ${PG_TUNNEL_LAST_UPDATED:-<unknown>}"
echo ""

print_section "2) Tiến trình ngrok"
if pgrep -f "ngrok tcp" >/dev/null; then
  echo "✅ Ngrok process đang chạy."
else
  echo "❌ Không tìm thấy process ngrok."
fi
echo ""

print_section "3) Kiểm tra pg_isready"
if [[ -z "${PG_TUNNEL_HOST:-}" || -z "${PG_TUNNEL_PORT:-}" ]]; then
  echo "⚠️  Chưa có thông tin host/port. Chạy start_ngrok_and_set_db.py trước."
else
  if command -v pg_isready >/dev/null; then
    PGPASSWORD="${PG_TUNNEL_PASSWORD:-${POSTGRES_PASSWORD:-}}" \
      pg_isready \
      -h "${PG_TUNNEL_HOST}" \
      -p "${PG_TUNNEL_PORT}" \
      -d "${PG_TUNNEL_DB:-${POSTGRES_DB:-hue_portal}}" \
      -U "${PG_TUNNEL_USER:-${POSTGRES_USER:-hue}}" \
      || true
  else
    echo "⚠️  pg_isready không có trong PATH."
  fi
fi
echo ""

print_section "4) Gợi ý next steps"
echo "- Chạy ./ops/pg_tunnel_watchdog.py --once để test watchdog."
echo "- Dùng ./hue-portal-backend/start_ngrok_and_set_db.py nếu cần tạo tunnel mới."
echo "- Kiểm tra log: $ROOT_DIR/ops/logs/tunnel_watchdog.log"
#!/bin/bash
# Quick status script cho tunnel PostgreSQL (ngrok + pg_isready)
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"
TUNNEL_ENV_FILE="$ROOT_DIR/ops/.env.tunnel"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

if [[ -f "$TUNNEL_ENV_FILE" ]]; then
  set -a
  source "$TUNNEL_ENV_FILE"
  set +a
fi

HOST="${PG_TUNNEL_HOST:-}"
PORT="${PG_TUNNEL_PORT:-}"
USER="${PG_TUNNEL_USER:-${POSTGRES_USER:-hue}}"
PASSWORD="${PG_TUNNEL_PASSWORD:-${POSTGRES_PASSWORD:-}}"
DB_NAME="${PG_TUNNEL_DB:-${POSTGRES_DB:-hue_portal}}"
LOCAL_PORT="${PG_TUNNEL_LOCAL_PORT:-${POSTGRES_PORT:-5543}}"

printf "=== Tunnel status (%s) ===\n" "$(date)"

if pgrep -f "ngrok tcp ${LOCAL_PORT}" >/dev/null 2>&1; then
  echo "Ngrok process: RUNNING"
else
  echo "Ngrok process: NOT FOUND"
fi

if command -v curl >/dev/null 2>&1; then
  if curl -sf "http://127.0.0.1:4040/api/tunnels" >/dev/null 2>&1; then
    url=$(curl -sf "http://127.0.0.1:4040/api/tunnels" | python3 -c "import json,sys;data=json.load(sys.stdin);print(next((t['public_url'] for t in data.get('tunnels',[]) if t.get('proto')=='tcp'), ''))")
    if [[ -n "$url" ]]; then
      echo "Ngrok public URL: $url"
    else
      echo "Ngrok public URL: (không thấy tunnel TCP trong API)"
    fi
  else
    echo "Không thể truy vấn API 4040 của ngrok."
  fi
else
  echo "curl không khả dụng; bỏ qua bước kiểm tra API ngrok."
fi

if [[ -z "$HOST" || -z "$PORT" ]]; then
  echo "Thiếu PG_TUNNEL_HOST/PORT trong ops/.env.tunnel – chạy lại start_ngrok_and_set_db.py."
  exit 1
fi

if ! command -v pg_isready >/dev/null 2>&1; then
  echo "pg_isready không khả dụng; cài đặt postgresql client để kiểm tra kết nối."
  exit 1
fi

echo "Testing PostgreSQL via tunnel ($HOST:$PORT/$DB_NAME)..."
if [[ -n "$PASSWORD" ]]; then
  PGPASSWORD="$PASSWORD" pg_isready -h "$HOST" -p "$PORT" -U "$USER"
else
  pg_isready -h "$HOST" -p "$PORT" -U "$USER"
fi

echo "Done."


