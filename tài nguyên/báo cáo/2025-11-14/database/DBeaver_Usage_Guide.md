# Hướng dẫn sử dụng DBeaver

## ✅ Kết nối thành công!

Connection "hue_portal" đã kết nối thành công với database.

## Cách xem Tables và Data

### Bước 1: Mở rộng connection

1. Trong Database Navigator (bên trái), click vào **"hue_portal"**
2. Mở rộng: `hue_portal` → `Databases` → `hue_portal` → `Schemas` → `public` → `Tables`

### Bước 2: Xem danh sách Tables

Bạn sẽ thấy các tables:
- `core_fine` - Bảng mức phạt
- `core_office` - Bảng địa chỉ điểm tiếp dân
- `core_procedure` - Bảng thủ tục
- `core_advisory` - Bảng cảnh báo
- `core_auditlog` - Bảng log
- `core_mlmetrics` - Bảng metrics ML
- `core_synonym` - Bảng từ đồng nghĩa

### Bước 3: Xem Data trong Table

**Cách 1: Double-click**
- Double-click vào tên table (ví dụ: `core_fine`)
- Data sẽ hiện ra ở tab mới

**Cách 2: Right-click**
- Right-click vào table
- Chọn **"View Data"** hoặc **"Open Data"**

**Cách 3: SQL Editor**
- Right-click table → **"Generate SQL"** → **"SELECT"**
- Hoặc click **"SQL Editor"** (icon SQL ở toolbar)
- Gõ: `SELECT * FROM core_fine LIMIT 100;`
- Click **"Execute SQL Statement"** (icon play) hoặc `Cmd + Enter`

## Chạy SQL Queries

### Mở SQL Editor

1. Click **"SQL Editor"** (icon SQL ở toolbar)
   - Hoặc: `SQL Editor` → `New SQL Script`
   - Hoặc: `Cmd + ]`

2. Gõ SQL query:
   ```sql
   -- Xem tất cả tables
   SELECT table_name 
   FROM information_schema.tables 
   WHERE table_schema = 'public';
   
   -- Xem số lượng records trong mỗi table
   SELECT 
     'core_fine' as table_name, 
     COUNT(*) as count 
   FROM core_fine
   UNION ALL
   SELECT 'core_office', COUNT(*) FROM core_office
   UNION ALL
   SELECT 'core_auditlog', COUNT(*) FROM core_auditlog;
   
   -- Xem data trong core_fine
   SELECT * FROM core_fine LIMIT 10;
   ```

3. Execute:
   - Click icon **"Execute SQL Statement"** (play button)
   - Hoặc: `Cmd + Enter`
   - Hoặc: `Ctrl + Enter`

## Export Data

### Export table ra file

1. Right-click vào table
2. Chọn **"Export Data"**
3. Chọn format:
   - **CSV** - Cho Excel
   - **Excel** - File .xlsx
   - **JSON** - File .json
   - **SQL** - File .sql
4. Chọn destination folder
5. Click **"Start"**

## Import Data

1. Right-click vào table
2. Chọn **"Import Data"**
3. Chọn file source (CSV, Excel, etc.)
4. Map columns
5. Click **"Start"**

## Tính năng hữu ích khác

### ER Diagrams

1. Right-click database → **"View Diagram"**
2. Xem schema và relationships giữa các tables

### Table Properties

1. Right-click table → **"Properties"**
2. Xem thông tin: columns, indexes, constraints, etc.

### Edit Data trực tiếp

1. Double-click table để mở data editor
2. Click vào cell để edit
3. Click **"Save"** để lưu thay đổi

## Shortcuts hữu ích

- `Cmd + ]` - New SQL Script
- `Cmd + Enter` - Execute SQL
- `Cmd + /` - Comment/Uncomment
- `Cmd + D` - Duplicate line
- `Cmd + Shift + N` - New Database Connection

## Queries mẫu

### Xem tất cả tables
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;
```

### Xem số lượng records
```sql
SELECT 
  'core_fine' as table_name, 
  COUNT(*) as records 
FROM core_fine
UNION ALL
SELECT 'core_office', COUNT(*) FROM core_office
UNION ALL
SELECT 'core_auditlog', COUNT(*) FROM core_auditlog
UNION ALL
SELECT 'core_synonym', COUNT(*) FROM core_synonym;
```

### Xem data trong core_fine
```sql
SELECT * FROM core_fine LIMIT 20;
```

### Xem data trong core_office
```sql
SELECT unit_name, address, phone 
FROM core_office 
LIMIT 10;
```

### Tìm kiếm với BM25 (nếu có tsv_body)
```sql
SELECT name, rank
FROM core_fine, 
     to_tsquery('simple', 'vượt đèn đỏ') query,
     ts_rank(tsv_body, query) rank
WHERE tsv_body @@ query
ORDER BY rank DESC
LIMIT 10;
```

---

**Chúc bạn sử dụng DBeaver thành công! 🎉**

