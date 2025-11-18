# Cách Query Database từ Terminal

## ✅ Có thể query database từ terminal!

Có 2 cách chính:

## Cách 1: Dùng Docker exec (Khuyến nghị - Không cần cài thêm)

### Cú pháp cơ bản:

```bash
docker exec tryhardemnayproject-db-1 psql -U admin -d hue_portal -c "SQL_QUERY"
```

### Ví dụ:

```bash
# Xem tất cả tables
docker exec tryhardemnayproject-db-1 psql -U admin -d hue_portal -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"

# Xem data trong core_fine
docker exec tryhardemnayproject-db-1 psql -U admin -d hue_portal -c "SELECT * FROM core_fine LIMIT 10;"

# Xem số lượng records
docker exec tryhardemnayproject-db-1 psql -U admin -d hue_portal -c "SELECT COUNT(*) FROM core_fine;"

# Xem data trong core_office
docker exec tryhardemnayproject-db-1 psql -U admin -d hue_portal -c "SELECT unit_name, address, phone FROM core_office LIMIT 5;"
```

### Interactive mode (nhập nhiều queries):

```bash
docker exec -it tryhardemnayproject-db-1 psql -U admin -d hue_portal
```

Sau đó bạn có thể gõ SQL trực tiếp:
```sql
SELECT * FROM core_fine LIMIT 10;
\q  -- để thoát
```

## Cách 2: Cài psql client trên máy (nếu muốn)

### Cài đặt:

**macOS:**
```bash
brew install postgresql@15
```

**Sau khi cài, kết nối:**
```bash
psql -h localhost -p 5433 -U admin -d hue_portal
# Password: admin123
```

### Hoặc dùng connection string:
```bash
PGPASSWORD=admin123 psql -h localhost -p 5433 -U admin -d hue_portal
```

## Ví dụ Queries hữu ích

### 1. Xem tất cả tables
```bash
docker exec tryhardemnayproject-db-1 psql -U admin -d hue_portal -c "\dt"
```

### 2. Xem cấu trúc table
```bash
docker exec tryhardemnayproject-db-1 psql -U admin -d hue_portal -c "\d core_fine"
```

### 3. Xem data trong table
```bash
docker exec tryhardemnayproject-db-1 psql -U admin -d hue_portal -c "SELECT * FROM core_fine LIMIT 10;"
```

### 4. Đếm số records
```bash
docker exec tryhardemnayproject-db-1 psql -U admin -d hue_portal -c "SELECT 'core_fine' as table_name, COUNT(*) as count FROM core_fine UNION ALL SELECT 'core_office', COUNT(*) FROM core_office;"
```

### 5. Tìm kiếm với BM25
```bash
docker exec tryhardemnayproject-db-1 psql -U admin -d hue_portal -c "SELECT name, rank FROM core_fine, to_tsquery('simple', 'vượt đèn đỏ') query, ts_rank(tsv_body, query) rank WHERE tsv_body @@ query ORDER BY rank DESC LIMIT 5;"
```

### 6. Xem extensions đã enable
```bash
docker exec tryhardemnayproject-db-1 psql -U admin -d hue_portal -c "\dx"
```

### 7. Xem users
```bash
docker exec tryhardemnayproject-db-1 psql -U admin -d hue_portal -c "\du"
```

## Interactive Mode (Tiện lợi nhất)

### Vào interactive mode:

```bash
docker exec -it tryhardemnayproject-db-1 psql -U admin -d hue_portal
```

### Trong interactive mode, bạn có thể:

```sql
-- Gõ SQL queries
SELECT * FROM core_fine LIMIT 10;

-- Xem tables
\dt

-- Xem cấu trúc table
\d core_fine

-- Xem databases
\l

-- Xem users
\du

-- Thoát
\q
```

## Tạo alias để dễ dùng hơn

Thêm vào `~/.zshrc` hoặc `~/.bashrc`:

```bash
# Alias cho PostgreSQL queries
alias psql-hue='docker exec -it tryhardemnayproject-db-1 psql -U admin -d hue_portal'
alias psql-hue-query='docker exec tryhardemnayproject-db-1 psql -U admin -d hue_portal -c'
```

Sau đó reload:
```bash
source ~/.zshrc
```

Sử dụng:
```bash
# Interactive mode
psql-hue

# Query nhanh
psql-hue-query "SELECT COUNT(*) FROM core_fine;"
```

## So sánh với DBeaver

| Tính năng | Terminal (psql) | DBeaver |
|-----------|----------------|---------|
| Query SQL | ✅ | ✅ |
| Xem data | ✅ (text) | ✅ (table format) |
| Export data | ⚠️ (phức tạp) | ✅ (dễ) |
| Visual schema | ❌ | ✅ |
| Edit data | ⚠️ (khó) | ✅ (dễ) |
| Scripting | ✅ (dễ) | ⚠️ |

## Tips

- Dùng **interactive mode** (`-it`) để query nhiều lần
- Dùng **`-c`** để chạy 1 query và thoát
- Dùng **`\x`** trong interactive mode để xem output dạng expanded
- Dùng **`\timing`** để xem thời gian execute query

---

**Vậy là có thể query từ terminal! Dùng `docker exec` là cách dễ nhất. 🎯**

