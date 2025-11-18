# Plan 2 — Tích hợp Vector Embeddings & RAG

## Tổng quan

Plan 2 nâng cấp hệ thống tìm kiếm với:
- **Vector Embeddings**: Tìm kiếm ngữ nghĩa với sentence transformers
- **Hybrid Search**: Kết hợp BM25 (từ khóa) + Vector (ngữ nghĩa)
- **RAG Pipeline**: Tạo câu trả lời thông minh từ kết quả tìm kiếm
- **ANN Search**: FAISS index cho tìm kiếm vector nhanh

## Cài đặt

### Dependencies

```bash
pip install -r backend/requirements.txt
```

Các package mới:
- `sentence-transformers>=2.2.0`: Model embeddings
- `torch>=2.0.0`: PyTorch backend
- `faiss-cpu>=1.7.4`: FAISS index

### Model Embedding

Mặc định sử dụng: `keepitreal/vietnamese-sbert-v2`
Fallback: `intfloat/multilingual-e5-large`

## Sử dụng

### 1. Generate Embeddings

```bash
# Generate embeddings cho tất cả models
python backend/scripts/generate_embeddings.py

# Chỉ generate cho một model
python backend/scripts/generate_embeddings.py --model procedure

# Dry run (không lưu)
python backend/scripts/generate_embeddings.py --dry-run
```

### 2. Build FAISS Index

```bash
# Build index cho tất cả models
python backend/scripts/build_faiss_index.py

# Chỉ build cho một model
python backend/scripts/build_faiss_index.py --model fine

# Chọn loại index
python backend/scripts/build_faiss_index.py --index-type IVF  # hoặc HNSW, Flat
```

### 3. Migrations

```bash
cd backend/hue_portal
python manage.py migrate
```

Migration `0004_add_embeddings.py` sẽ:
- Thêm field `embedding` (BinaryField) vào Procedure, Fine, Office, Advisory
- Lưu embeddings dưới dạng pickle binary

## Cấu trúc Code

### Core Modules

- `backend/hue_portal/core/embeddings.py`: Utilities cho embedding generation
- `backend/hue_portal/core/embedding_utils.py`: Helper functions load/save embeddings
- `backend/hue_portal/core/hybrid_search.py`: Hybrid search (BM25 + Vector)
- `backend/hue_portal/core/rag.py`: RAG pipeline (retrieval + generation)
- `backend/hue_portal/core/faiss_index.py`: FAISS index management
- `backend/hue_portal/core/config/hybrid_search_config.py`: Configuration cho weights

### Scripts

- `backend/scripts/generate_embeddings.py`: Generate và lưu embeddings
- `backend/scripts/build_faiss_index.py`: Build FAISS indexes

## Hybrid Search

### Configuration

Weights mặc định:
- BM25: 40%
- Vector: 60%

Có thể điều chỉnh theo content type trong `hybrid_search_config.py`:
- Procedure: 50% BM25, 50% Vector
- Fine: 60% BM25, 40% Vector
- Office: 30% BM25, 70% Vector
- Advisory: 40% BM25, 60% Vector

### Sử dụng trong Code

```python
from hue_portal.core.hybrid_search import hybrid_search
from hue_portal.core.models import Fine

# Hybrid search
results = hybrid_search(
    Fine.objects.all(),
    query="vượt đèn đỏ",
    top_k=10,
    bm25_weight=0.4,
    vector_weight=0.6
)

# Mỗi result có:
# - result._hybrid_score: Combined score
# - result._bm25_score: BM25 score
# - result._vector_score: Vector similarity score
```

## RAG Pipeline

RAG tự động được tích hợp vào chatbot response:

```python
from hue_portal.core.rag import rag_pipeline

result = rag_pipeline(
    query="mức phạt vượt đèn đỏ",
    intent="search_fine",
    top_k=5
)

# result chứa:
# - answer: Generated answer text
# - documents: Retrieved documents
# - count: Number of results
# - confidence: Confidence score
```

## FAISS Index

### Index Types

1. **Flat**: Brute-force exact search (chậm nhưng chính xác)
2. **IVF**: Inverted file index (nhanh, approximate)
3. **HNSW**: Hierarchical Navigable Small World (rất nhanh, approximate)

### Sử dụng

```python
from hue_portal.core.faiss_index import FAISSIndex, build_faiss_index_for_model
from hue_portal.core.models import Fine

# Build index
index = build_faiss_index_for_model(Fine, "Fine", index_type="IVF")

# Load index
from pathlib import Path
index = FAISSIndex.load(Path("artifacts/faiss_indexes/fine_index.faiss"))

# Search
query_vector = generate_embedding("vượt đèn đỏ")
results = index.search(query_vector, k=10)  # [(object_id, similarity), ...]
```

## Testing

```bash
# Run embedding tests
python -m pytest backend/hue_portal/core/tests/test_embeddings.py -v
```

## Performance

### Benchmark

Chạy benchmark để so sánh:
- BM25 only
- Vector only
- Hybrid (BM25 + Vector)

```bash
python backend/scripts/benchmark_search.py --compare-hybrid
```

## Troubleshooting

### Model không load được

1. Kiểm tra internet connection (model sẽ download lần đầu)
2. Thử fallback model: `intfloat/multilingual-e5-large`
3. Kiểm tra disk space (models có thể lớn ~500MB)

### Embeddings không generate

1. Kiểm tra database connection
2. Kiểm tra model đã load thành công
3. Xem logs trong console

### FAISS không available

```bash
pip install faiss-cpu
# hoặc cho GPU:
pip install faiss-gpu
```

## Next Steps

- [ ] Tích hợp FAISS vào hybrid_search
- [ ] Benchmark performance
- [ ] A/B testing framework
- [ ] Monitoring metrics
- [ ] Documentation chi tiết hơn

