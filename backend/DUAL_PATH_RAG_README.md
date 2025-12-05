# Dual-Path RAG Architecture

## Overview

Dual-Path RAG là kiến trúc tối ưu cho chatbot legal, tách biệt 2 đường xử lý:

- **Fast Path**: Golden dataset (200 câu phổ biến) → <200ms, 100% accuracy
- **Slow Path**: Full RAG pipeline → 4-8s, 99.99% accuracy

## Architecture

```
User Query
    ↓
Intent Classification
    ↓
Dual-Path Router
    ├─ Keyword Router (exact/fuzzy match)
    ├─ Semantic Similarity Search (threshold 0.85)
    └─ LLM Router (optional, for edge cases)
    ↓
┌─────────────────┬─────────────────┐
│   Fast Path     │   Slow Path      │
│   (<200ms)      │   (4-8s)         │
│                 │                  │
│ Golden Dataset  │ Full RAG:        │
│ - Exact match   │ - Hybrid Search  │
│ - Fuzzy match   │ - Top 20 docs    │
│ - Similarity    │ - LLM Generation │
│                 │ - Guardrails     │
│ 100% accuracy   │ 99.99% accuracy  │
└─────────────────┴─────────────────┘
    ↓
Response + Routing Log
```

## Components

### 1. Database Models

**GoldenQuery**: Stores verified queries and responses
- `query`, `query_normalized`, `query_embedding`
- `intent`, `response_message`, `response_data`
- `verified_by`, `usage_count`, `accuracy_score`

**QueryRoutingLog**: Logs routing decisions for monitoring
- `route` (fast_path/slow_path)
- `router_method` (keyword/similarity/llm/default)
- `response_time_ms`, `similarity_score`

### 2. Router Components

**KeywordRouter**: Fast keyword-based matching
- Exact match (normalized query)
- Fuzzy match (70% word overlap)
- ~1-5ms latency

**DualPathRouter**: Main router with hybrid logic
- Step 1: Keyword routing (fastest)
- Step 2: Semantic similarity (threshold 0.85)
- Step 3: LLM router fallback (optional)
- Default: Slow Path

### 3. Path Handlers

**FastPathHandler**: Returns cached responses from golden dataset
- Increments usage count
- Returns verified response instantly

**SlowPathHandler**: Full RAG pipeline
- Hybrid search (BM25 + vector)
- Top 20 documents
- LLM generation with structured output
- Auto-save high-quality responses to golden dataset

## Setup

### 1. Run Migration

```bash
cd backend/hue_portal
python manage.py migrate core
```

### 2. Import Initial Golden Dataset

```bash
# Import from JSON file
python manage.py manage_golden_dataset import --file golden_queries.json --format json

# Or import from CSV
python manage.py manage_golden_dataset import --file golden_queries.csv --format csv
```

### 3. Generate Embeddings (for semantic search)

```bash
# Generate embeddings for all queries
python manage.py manage_golden_dataset update_embeddings

# Or for specific query
python manage.py manage_golden_dataset update_embeddings --query-id 123
```

## Management Commands

### Import Queries

```bash
python manage.py manage_golden_dataset import \
    --file golden_queries.json \
    --format json \
    --verify-by legal_expert \
    --skip-embeddings  # Skip if embeddings will be generated later
```

### Verify Query

```bash
python manage.py manage_golden_dataset verify \
    --query-id 123 \
    --verify-by gpt4 \
    --accuracy 1.0
```

### Update Embeddings

```bash
python manage.py manage_golden_dataset update_embeddings \
    --batch-size 10
```

### View Statistics

```bash
python manage.py manage_golden_dataset stats
```

### Export Dataset

```bash
python manage.py manage_golden_dataset export \
    --file exported_queries.json \
    --active-only
```

### Delete Query

```bash
# Soft delete (deactivate)
python manage.py manage_golden_dataset delete --query-id 123 --soft

# Hard delete
python manage.py manage_golden_dataset delete --query-id 123
```

## API Endpoints

### Chat Endpoint (unchanged)

```
POST /api/chatbot/chat/
{
  "message": "Mức phạt vượt đèn đỏ là bao nhiêu?",
  "session_id": "optional-uuid",
  "reset_session": false
}
```

Response includes routing metadata:
```json
{
  "message": "...",
  "intent": "search_fine",
  "results": [...],
  "_source": "fast_path",  // or "slow_path"
  "_routing": {
    "path": "fast_path",
    "method": "keyword",
    "confidence": 1.0
  },
  "_golden_query_id": 123  // if fast_path
}
```

### Analytics Endpoint

```
GET /api/chatbot/analytics/?days=7&type=all
```

Returns:
- `routing`: Fast/Slow path statistics
- `golden_dataset`: Golden dataset stats
- `performance`: P50/P95/P99 response times

## Golden Dataset Format

### JSON Format

```json
[
  {
    "query": "Mức phạt vượt đèn đỏ là bao nhiêu?",
    "intent": "search_fine",
    "response_message": "Mức phạt vượt đèn đỏ là từ 200.000 - 400.000 VNĐ...",
    "response_data": {
      "message": "...",
      "intent": "search_fine",
      "results": [...],
      "count": 1
    },
    "verified_by": "legal_expert",
    "accuracy_score": 1.0
  }
]
```

### CSV Format

```csv
query,intent,response_message,response_data
"Mức phạt vượt đèn đỏ là bao nhiêu?","search_fine","Mức phạt...","{\"message\":\"...\",\"results\":[...]}"
```

## Monitoring

### Routing Statistics

```python
from hue_portal.chatbot.analytics import get_routing_stats

stats = get_routing_stats(days=7)
print(f"Fast Path: {stats['fast_path_percentage']:.1f}%")
print(f"Slow Path: {stats['slow_path_percentage']:.1f}%")
print(f"Fast Path Avg Time: {stats['fast_path_avg_time_ms']:.1f}ms")
print(f"Slow Path Avg Time: {stats['slow_path_avg_time_ms']:.1f}ms")
```

### Golden Dataset Stats

```python
from hue_portal.chatbot.analytics import get_golden_dataset_stats

stats = get_golden_dataset_stats()
print(f"Active queries: {stats['active_queries']}")
print(f"Embedding coverage: {stats['embedding_coverage']:.1f}%")
```

## Best Practices

### 1. Building Golden Dataset

- Start with 50-100 most common queries from logs
- Verify each response manually or with strong LLM (GPT-4/Claude)
- Add queries gradually based on usage patterns
- Target: 200 queries covering 80% of traffic

### 2. Verification Process

- **Weekly review**: Check top 20 most-used queries
- **Monthly audit**: Review all queries for accuracy
- **Update embeddings**: When adding new queries
- **Version control**: Track changes with `version` field

### 3. Tuning Similarity Threshold

- Default: 0.85 (conservative, high precision)
- Lower (0.75): More queries go to Fast Path, but risk false matches
- Higher (0.90): Fewer false matches, but more queries go to Slow Path

### 4. Auto-Save from Slow Path

Slow Path automatically saves high-quality responses:
- Confidence >= 0.95
- Has results
- Message length > 50 chars
- Not already in golden dataset

Review auto-saved queries weekly and verify before activating.

## Troubleshooting

### Fast Path not matching

1. Check if query is normalized correctly
2. Verify golden query exists: `GoldenQuery.objects.filter(query_normalized=...)`
3. Check similarity threshold (may be too high)
4. Ensure embeddings are generated: `update_embeddings`

### Slow performance

1. Check routing logs: `QueryRoutingLog.objects.filter(route='fast_path')`
2. Verify Fast Path percentage (should be ~80%)
3. Check embedding model loading time
4. Monitor database query performance

### Low accuracy

1. Review golden dataset verification
2. Check `accuracy_score` of golden queries
3. Monitor Slow Path responses for quality
4. Update golden queries with better responses

## Expected Performance

- **Fast Path**: <200ms (target: <100ms)
- **Slow Path**: 4-8s (full RAG pipeline)
- **Overall**: 80% queries <200ms, 20% queries 4-8s
- **Cache Hit Rate**: 75-85% (Fast Path usage)

## Next Steps

1. Import initial 200 common queries
2. Generate embeddings for all queries
3. Monitor routing statistics for 1 week
4. Tune similarity threshold based on metrics
5. Expand golden dataset based on usage patterns

