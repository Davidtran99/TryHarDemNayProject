# Chatbot API Endpoints

## Overview

This document describes the chatbot API endpoints available in the system.

## Base URL

- Default: `http://localhost:8000`
- Override via env when running test scripts:
  ```bash
  export API_BASE_URL=http://localhost:8090  # e.g. when runserver uses port 8090
  ```

## Endpoints

### 1. Health Check

**Endpoint**: `GET /api/chatbot/health/`

**Description**: Check the health status of the chatbot service.

**Response**:
```json
{
  "status": "healthy",
  "service": "chatbot",
  "classifier_loaded": true
}
```

**Example**:
```bash
curl http://localhost:8000/api/chatbot/health/
```

### 2. Chat

**Endpoint**: `POST /api/chat/`

**Description**: Send a message to the chatbot and get a response.

**Request Body**:
```json
{
  "message": "Làm thủ tục cư trú cần gì?"
}
```

**Response**:
```json
{
  "message": "Tôi tìm thấy 5 thủ tục liên quan đến 'Làm thủ tục cư trú cần gì?':\n\n1. Đăng ký thường trú\n   ...",
  "intent": "search_procedure",
  "confidence": 0.95,
  "results": [
    {
      "type": "procedure",
      "data": {
        "id": 1,
        "title": "Đăng ký thường trú",
        "domain": "Cư trú",
        ...
      }
    }
  ],
  "count": 5
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Làm thủ tục cư trú cần gì?"}'
```

## Intent Types

The chatbot can classify queries into the following intents:

- `search_fine`: Search for traffic fines
- `search_procedure`: Search for administrative procedures
- `search_office`: Search for office/unit information
- `search_advisory`: Search for security advisories
- `general_query`: General queries
- `greeting`: Greetings

## Response Fields

- `message`: The response message to display to the user
- `intent`: The classified intent
- `confidence`: Confidence score (0.0 to 1.0)
- `results`: Array of search results
- `count`: Number of results found

## Error Handling

### 400 Bad Request

```json
{
  "error": "message is required"
}
```

### 500 Internal Server Error

```json
{
  "message": "Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.",
  "intent": "error",
  "error": "Error details",
  "results": [],
  "count": 0
}
```

## Testing

Use the provided test script:

```bash
cd backend
API_BASE_URL=http://localhost:8090 \\
POSTGRES_HOST=localhost POSTGRES_PORT=5433 \\
python scripts/test_api_endpoint.py
```

The script automatically:
- Hits `GET /api/chatbot/health/` to confirm classifier loading.
- Sends six representative queries and reports status, intent, confidence, latency, and first result title.

## API Endpoint Testing & Fixes — 2025-11-14

- Added trailing slashes to `backend/hue_portal/chatbot/urls.py` and `backend/hue_portal/core/urls.py` so `/api/chatbot/health/` and `/api/chat/` resolve correctly.
- Hardened chatbot serialization via `_serialize_document` to avoid `TypeError: Object of type type is not JSON serializable`.
- Latest test run:
  - Command: `API_BASE_URL=http://localhost:8090 POSTGRES_HOST=localhost POSTGRES_PORT=5433 python scripts/test_api_endpoint.py`
  - Result: **6/6** successful queries, **100 % intent accuracy**, avg latency **~3.7 s** (first call includes SentenceTransformer warm-up).
- Checklist before running tests:
  1. `POSTGRES_HOST=localhost POSTGRES_PORT=5433 ../../.venv/bin/python manage.py runserver 0.0.0.0:8090`
  2. Ensure `API_BASE_URL` matches runserver port.
  3. (Optional) export `DJANGO_DEBUG=1` for verbose stack traces during local debugging.

## Notes

- The API uses RAG (Retrieval-Augmented Generation) pipeline for generating responses
- Hybrid search (BM25 + Vector similarity) is used for retrieval
- Intent classification uses ML model with keyword-based fallback
- Response latency typically ranges from 200-1000ms depending on query complexity

