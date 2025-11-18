# Database Setup - Hoàn thành ✅

## Tổng quan

Database đã được setup thành công với tất cả migrations từ Plan 1 và Plan 2.

## Đã hoàn thành

### A. Database Environment
- ✅ File `.env.example` đã tạo (copy thành `.env` để sử dụng)
- ✅ Docker và docker-compose đã có sẵn
- ✅ PostgreSQL container đang chạy trên port **5433** (vì 5432 đã bị chiếm)
- ✅ Database connection verified

### B. PostgreSQL Extensions
- ✅ `pg_trgm` extension (version 1.6) - cho BM25 search
- ✅ `unaccent` extension (version 1.1) - cho Vietnamese text

### C. Migrations
- ✅ `0000_initial`: Tạo base models (Procedure, Fine, Office, Advisory, Synonym, AuditLog)
- ✅ `0001_enable_bm25`: BM25 fields (tsv_body) và triggers
- ✅ `0002_auditlog_metrics`: AuditLog mở rộng (intent, confidence, latency_ms)
- ✅ `0003_mlmetrics`: MLMetrics model
- ✅ `0004_add_embeddings`: Embedding fields (BinaryField)

### D. Data
- ✅ Synonyms: 18 records đã được seed
- ✅ Fine: 20 records
- ✅ Office: 12 records
- ✅ AuditLog: 198 records

### E. Verification
- ✅ Tất cả tables đã được tạo
- ✅ Tất cả fields (tsv_body, embedding) đã có
- ✅ GIN indexes đã được tạo cho tsv_body
- ✅ BM25 search hoạt động (tested với query "vượt đèn đỏ")

## Database Connection Info

**Local Development:**
- Host: `localhost`
- Port: `5433` (mapped from container port 5432)
- Database: `hue_portal`
- User: `hue`
- Password: `huepass`

**Docker Container:**
- Container name: `tryhardemnayproject-db-1`
- Internal port: `5432`
- External port: `5433`

## Cấu hình .env

Tạo file `.env` trong project root với nội dung:

```env
POSTGRES_DB=hue_portal
POSTGRES_USER=hue
POSTGRES_PASSWORD=huepass
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
```

## Scripts hữu ích

### Verify Setup
```bash
python backend/scripts/verify_database_setup.py
```

### Seed Synonyms
```bash
python backend/scripts/seed_synonyms.py --include-default
```

### Generate Embeddings
```bash
python backend/scripts/generate_embeddings.py
```

### Build FAISS Index
```bash
python backend/scripts/build_faiss_index.py
```

## Next Steps

1. **Generate Embeddings**: Chạy `generate_embeddings.py` để tạo embeddings cho dữ liệu hiện có
2. **Build FAISS Index**: Chạy `build_faiss_index.py` để tạo indexes cho vector search
3. **Test Hybrid Search**: Test hybrid search với dữ liệu thực
4. **Load More Data**: Load thêm dữ liệu từ CSV files nếu cần

## Troubleshooting

### Port 5432 đã bị chiếm
- Database đang chạy trên port **5433** thay vì 5432
- Update `.env` với `POSTGRES_PORT=5433`

### Container không start
```bash
docker compose up -d db
# hoặc
docker-compose up -d db
```

### Reset database (cẩn thận - sẽ mất dữ liệu)
```bash
docker compose down -v
docker compose up -d db
python manage.py migrate
```

