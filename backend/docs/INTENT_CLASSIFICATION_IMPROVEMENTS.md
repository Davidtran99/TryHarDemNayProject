# Intent Classification Improvements

## Overview

This document describes the improvements made to intent classification in Plan 5.

## Problem Identified

Query "Cảnh báo lừa đảo giả danh công an" was being classified as `search_office` instead of `search_advisory`.

### Root Cause

1. **Keyword Conflict**: The keyword "công an" appears in both `search_office` and queries about `search_advisory`
2. **Order of Checks**: The code checked `has_office_keywords` before `has_advisory_keywords`, causing office keywords to match first
3. **Limited Training Data**: The `search_advisory` intent had only 7 examples, compared to more examples in other intents

## Solutions Implemented

### 1. Improved Keyword Matching Logic

**File**: `backend/hue_portal/chatbot/chatbot.py`

- Changed order: Check `has_advisory_keywords` **before** `has_office_keywords`
- Added more keywords for advisory: "mạo danh", "thủ đoạn", "cảnh giác"
- This ensures advisory queries are matched first when they contain both advisory and office keywords

### 2. Enhanced Training Data

**File**: `backend/hue_portal/chatbot/training/intent_dataset.json`

- Expanded `search_advisory` examples from 7 to 23 examples
- Added specific examples:
  - "cảnh báo lừa đảo giả danh công an"
  - "mạo danh cán bộ công an"
  - "lừa đảo mạo danh"
  - And 15 more variations

### 3. Retrained Model

- Retrained intent classification model with improved training data
- Model accuracy improved
- Better handling of edge cases

## Results

### Before Improvements

- Query "Cảnh báo lừa đảo giả danh công an" → `search_office` (incorrect)
- Limited training examples for `search_advisory`

### After Improvements

- Query "Cảnh báo lừa đảo giả danh công an" → `search_advisory` (correct)
- More balanced training data across all intents
- Better keyword matching logic

## Testing

Test queries that now work correctly:

- "Cảnh báo lừa đảo giả danh công an" → `search_advisory`
- "Lừa đảo mạo danh cán bộ" → `search_advisory`
- "Mạo danh cán bộ công an" → `search_advisory`

## 2025-11-14 Update — Serialization & API Regression

- Added `_serialize_document` in `backend/hue_portal/chatbot/chatbot.py` so RAG responses return JSON-safe payloads (no more `TypeError: Object of type type is not JSON serializable` when embeddings include model instances).
- Re-tested intents end-to-end via `scripts/test_api_endpoint.py` (6 queries spanning all intents):
  - **Result:** 6/6 passed, 100 % intent accuracy.
  - **Latency:** avg ~3.7 s (note: first call warms up `keepitreal/vietnamese-sbert-v2`, subsequent calls ≤1.8 s).
- Health checklist before testing:
  1. `POSTGRES_HOST=localhost POSTGRES_PORT=5433 ../../.venv/bin/python manage.py runserver 0.0.0.0:8090`
  2. `API_BASE_URL=http://localhost:8090 python scripts/test_api_endpoint.py`
  3. Watch server logs for any serialization warnings (none observed after fix).

## Files Modified

1. `backend/hue_portal/chatbot/training/intent_dataset.json` - Enhanced training data
2. `backend/hue_portal/chatbot/chatbot.py` - Improved keyword matching logic
3. `backend/hue_portal/chatbot/training/artifacts/intent_model.joblib` - Retrained model

## Future Improvements

- Continue to add more training examples as edge cases are discovered
- Consider using more sophisticated ML models (e.g., transformer-based)
- Implement active learning to automatically improve from user feedback

