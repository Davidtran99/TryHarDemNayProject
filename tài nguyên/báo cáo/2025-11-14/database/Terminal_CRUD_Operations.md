# Hướng dẫn CRUD và Operations trong Terminal

## 🔧 Setup nhanh

### Alias để dễ dùng (thêm vào ~/.zshrc):

```bash
# Alias cho PostgreSQL
alias psql-hue='docker exec -it tryhardemnayproject-db-1 psql -U admin -d hue_portal'
alias psql-hue-query='docker exec tryhardemnayproject-db-1 psql -U admin -d hue_portal -c'
```

Reload:
```bash
source ~/.zshrc
```

## 📖 READ (SELECT) - Đọc dữ liệu

### 1. Xem tất cả records
```bash
psql-hue-query "SELECT * FROM core_fine LIMIT 10;"
```

### 2. Xem với điều kiện
```bash
psql-hue-query "SELECT * FROM core_fine WHERE code = 'V001';"
```

### 3. Xem các cột cụ thể
```bash
psql-hue-query "SELECT code, name, decree FROM core_fine LIMIT 5;"
```

### 4. Tìm kiếm với LIKE
```bash
psql-hue-query "SELECT * FROM core_fine WHERE name LIKE '%đèn đỏ%';"
```

### 5. Sắp xếp
```bash
psql-hue-query "SELECT * FROM core_fine ORDER BY code ASC LIMIT 10;"
```

### 6. Đếm records
```bash
psql-hue-query "SELECT COUNT(*) FROM core_fine;"
```

### 7. Group by
```bash
psql-hue-query "SELECT decree, COUNT(*) as count FROM core_fine GROUP BY decree;"
```

### 8. JOIN tables
```bash
psql-hue-query "SELECT f.code, f.name, o.unit_name FROM core_fine f JOIN core_office o ON 1=1 LIMIT 5;"
```

## ➕ CREATE (INSERT) - Thêm dữ liệu

### 1. Insert đơn giản
```bash
psql-hue-query "INSERT INTO core_fine (code, name, decree) VALUES ('V999', 'Test violation', 'Nghị định 100');"
```

### 2. Insert nhiều records
```bash
psql-hue-query "INSERT INTO core_fine (code, name, decree) VALUES 
('V998', 'Test 1', 'Nghị định 100'),
('V997', 'Test 2', 'Nghị định 100');"
```

### 3. Insert với SELECT
```bash
psql-hue-query "INSERT INTO core_fine (code, name, decree) 
SELECT 'V996', 'Copy from V001', decree FROM core_fine WHERE code = 'V001';"
```

### 4. Insert và return ID
```bash
psql-hue-query "INSERT INTO core_fine (code, name, decree) VALUES ('V995', 'Test', 'Nghị định 100') RETURNING id;"
```

## ✏️ UPDATE - Cập nhật dữ liệu

### 1. Update đơn giản
```bash
psql-hue-query "UPDATE core_fine SET name = 'Updated name' WHERE code = 'V999';"
```

### 2. Update nhiều cột
```bash
psql-hue-query "UPDATE core_fine SET name = 'New name', decree = 'New decree' WHERE code = 'V999';"
```

### 3. Update với điều kiện phức tạp
```bash
psql-hue-query "UPDATE core_fine SET name = 'Updated' WHERE code LIKE 'V99%';"
```

### 4. Update và return
```bash
psql-hue-query "UPDATE core_fine SET name = 'Updated' WHERE code = 'V999' RETURNING *;"
```

## 🗑️ DELETE - Xóa dữ liệu

### 1. Delete với điều kiện
```bash
psql-hue-query "DELETE FROM core_fine WHERE code = 'V999';"
```

### 2. Delete nhiều records
```bash
psql-hue-query "DELETE FROM core_fine WHERE code LIKE 'V99%';"
```

### 3. Delete và return
```bash
psql-hue-query "DELETE FROM core_fine WHERE code = 'V998' RETURNING *;"
```

### 4. Delete tất cả (cẩn thận!)
```bash
# ⚠️ CẨN THẬN: Xóa tất cả records
psql-hue-query "DELETE FROM core_fine;"
```

## 🔗 JOIN - Tham chiếu giữa tables

### 1. INNER JOIN
```bash
psql-hue-query "SELECT f.code, f.name, o.unit_name 
FROM core_fine f 
INNER JOIN core_office o ON f.id = o.id 
LIMIT 5;"
```

### 2. LEFT JOIN
```bash
psql-hue-query "SELECT f.code, f.name, o.unit_name 
FROM core_fine f 
LEFT JOIN core_office o ON f.id = o.id 
LIMIT 5;"
```

### 3. RIGHT JOIN
```bash
psql-hue-query "SELECT f.code, f.name, o.unit_name 
FROM core_fine f 
RIGHT JOIN core_office o ON f.id = o.id 
LIMIT 5;"
```

### 4. FULL OUTER JOIN
```bash
psql-hue-query "SELECT f.code, f.name, o.unit_name 
FROM core_fine f 
FULL OUTER JOIN core_office o ON f.id = o.id 
LIMIT 5;"
```

## 🔍 Tìm kiếm nâng cao

### 1. Tìm kiếm với BM25 (Full-text search)
```bash
psql-hue-query "SELECT name, rank 
FROM core_fine, 
     to_tsquery('simple', 'vượt đèn đỏ') query,
     ts_rank(tsv_body, query) rank
WHERE tsv_body @@ query
ORDER BY rank DESC
LIMIT 5;"
```

### 2. Tìm kiếm với ILIKE (case-insensitive)
```bash
psql-hue-query "SELECT * FROM core_fine WHERE name ILIKE '%đèn%';"
```

### 3. Tìm kiếm với regex
```bash
psql-hue-query "SELECT * FROM core_fine WHERE name ~ 'đèn|tốc độ';"
```

## 📊 Aggregations

### 1. COUNT
```bash
psql-hue-query "SELECT COUNT(*) as total FROM core_fine;"
```

### 2. SUM, AVG, MIN, MAX
```bash
psql-hue-query "SELECT 
  COUNT(*) as count,
  MIN(id) as min_id,
  MAX(id) as max_id
FROM core_fine;"
```

### 3. GROUP BY
```bash
psql-hue-query "SELECT decree, COUNT(*) as count 
FROM core_fine 
GROUP BY decree 
ORDER BY count DESC;"
```

### 4. HAVING
```bash
psql-hue-query "SELECT decree, COUNT(*) as count 
FROM core_fine 
GROUP BY decree 
HAVING COUNT(*) > 1;"
```

## 🗂️ Schema Operations

### 1. Xem tất cả tables
```bash
psql-hue-query "\dt"
```

### 2. Xem cấu trúc table
```bash
psql-hue-query "\d core_fine"
```

### 3. Xem indexes
```bash
psql-hue-query "\d+ core_fine"
```

### 4. Xem constraints
```bash
psql-hue-query "SELECT conname, contype 
FROM pg_constraint 
WHERE conrelid = 'core_fine'::regclass;"
```

## 🔐 Transactions

### 1. Begin transaction
```bash
psql-hue << EOF
BEGIN;
INSERT INTO core_fine (code, name, decree) VALUES ('V994', 'Test', 'Nghị định 100');
SELECT * FROM core_fine WHERE code = 'V994';
COMMIT;
EOF
```

### 2. Rollback
```bash
psql-hue << EOF
BEGIN;
INSERT INTO core_fine (code, name, decree) VALUES ('V993', 'Test', 'Nghị định 100');
ROLLBACK;
SELECT * FROM core_fine WHERE code = 'V993';
EOF
```

## 📤 Export Data

### 1. Export ra CSV
```bash
docker exec tryhardemnayproject-db-1 psql -U admin -d hue_portal -c "COPY (SELECT * FROM core_fine LIMIT 10) TO STDOUT WITH CSV HEADER;" > output.csv
```

### 2. Export ra JSON (cần extension)
```bash
psql-hue-query "SELECT json_agg(row_to_json(t)) 
FROM (SELECT * FROM core_fine LIMIT 5) t;" > output.json
```

## 📥 Import Data

### 1. Import từ CSV
```bash
docker exec -i tryhardemnayproject-db-1 psql -U admin -d hue_portal -c "COPY core_fine(code, name, decree) FROM STDIN WITH CSV HEADER;" < input.csv
```

## 🔧 Utilities

### 1. Xem version
```bash
psql-hue-query "SELECT version();"
```

### 2. Xem databases
```bash
psql-hue-query "\l"
```

### 3. Xem users
```bash
psql-hue-query "\du"
```

### 4. Xem extensions
```bash
psql-hue-query "\dx"
```

### 5. Xem size của tables
```bash
psql-hue-query "SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

## 💡 Tips & Tricks

### 1. Format output đẹp hơn
```bash
psql-hue-query "\x"  # Expanded display
psql-hue-query "SELECT * FROM core_fine LIMIT 1;"
```

### 2. Timing queries
```bash
psql-hue << EOF
\timing
SELECT * FROM core_fine LIMIT 1000;
EOF
```

### 3. Save query result
```bash
psql-hue-query "SELECT * FROM core_fine LIMIT 10;" > result.txt
```

### 4. Chạy từ file SQL
```bash
docker exec -i tryhardemnayproject-db-1 psql -U admin -d hue_portal < query.sql
```

### 5. Multi-line query
```bash
psql-hue << EOF
SELECT 
  code,
  name,
  decree
FROM core_fine
WHERE code LIKE 'V%'
ORDER BY code
LIMIT 10;
EOF
```

## 🎯 Ví dụ thực tế

### 1. Backup một table
```bash
docker exec tryhardemnayproject-db-1 pg_dump -U admin -d hue_portal -t core_fine > backup_fine.sql
```

### 2. Restore table
```bash
docker exec -i tryhardemnayproject-db-1 psql -U admin -d hue_portal < backup_fine.sql
```

### 3. Tìm duplicate
```bash
psql-hue-query "SELECT code, COUNT(*) as count 
FROM core_fine 
GROUP BY code 
HAVING COUNT(*) > 1;"
```

### 4. Xóa duplicate (giữ lại 1)
```bash
psql-hue << EOF
DELETE FROM core_fine a
USING core_fine b
WHERE a.id < b.id AND a.code = b.code;
EOF
```

---

**Với các commands này, bạn có thể làm mọi thứ với database từ terminal! 🚀**

