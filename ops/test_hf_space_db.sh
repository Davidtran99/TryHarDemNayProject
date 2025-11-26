#!/bin/bash
# Gửi request tới HF Space để đảm bảo API + dữ liệu hoạt động.

set -euo pipefail

SPACE_BASE_URL="${HF_SPACE_URL:-https://davidtran999-hue-portal-backend.hf.space}"
API_BASE="${SPACE_BASE_URL%/}/api"

curl_json() {
  local method="$1"
  local url="$2"
  local data="${3:-}"
  echo ""
  echo "--------------------------------------------"
  echo "$method $url"
  if [[ -n "$data" ]]; then
    echo "Payload: $data"
  fi
  echo "--------------------------------------------"
  local response
  if [[ "$method" == "GET" ]]; then
    response=$(curl -sSL -w "\nHTTP:%{http_code}" "$url" 2>&1)
  else
    response=$(curl -sSL -w "\nHTTP:%{http_code}" -X "$method" \
      -H "Content-Type: application/json" \
      -d "$data" \
      "$url" 2>&1)
  fi
  local http_code=$(echo "$response" | grep "HTTP:" | cut -d: -f2)
  local body=$(echo "$response" | grep -v "HTTP:")
  echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
  echo "HTTP Status: $http_code"
  if [[ "$http_code" -ge 200 && "$http_code" -lt 300 ]]; then
    echo "✅ Success"
  else
    echo "❌ Failed"
  fi
}

echo "Testing SPACE_BASE_URL=$SPACE_BASE_URL"
echo ""

echo "1️⃣ Testing Health Endpoint..."
curl_json GET "$API_BASE/chatbot/health/"

echo ""
echo "2️⃣ Testing Model Status..."
curl_json GET "$API_BASE/chatbot/model-status/"

echo ""
echo "3️⃣ Testing Chat (General Query)..."
curl_json POST "$API_BASE/chatbot/chat/" '{"message": "Xin chào"}'

echo ""
echo "4️⃣ Testing Chat (Data Query)..."
curl_json POST "$API_BASE/chatbot/chat/" '{"message": "Mức phạt vượt đèn đỏ là bao nhiêu?"}'

echo ""
echo "✅ Đã gọi xong các endpoint. Kiểm tra log HF Space để chắc chắn truy vấn SQL thành công."

