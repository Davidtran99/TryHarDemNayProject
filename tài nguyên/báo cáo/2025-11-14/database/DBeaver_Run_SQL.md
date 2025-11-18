# Cách chạy SQL trong DBeaver

## ⚠️ Lưu ý

**SQL queries phải chạy trong DBeaver, KHÔNG chạy trong terminal!**

Terminal không hiểu SQL - đó là lý do bạn thấy lỗi "command not found: SELECT".

## Cách chạy SQL trong DBeaver

### Bước 1: Mở SQL Editor

**Có 3 cách:**

1. **Từ Toolbar:**
   - Click icon **"SQL Editor"** (icon SQL ở toolbar bên phải)
   - Hoặc: `SQL Editor` → `New SQL Script`

2. **Từ Menu:**
   - `SQL Editor` → `New SQL Script`
   - Hoặc: `Cmd + ]`

3. **Từ Connection:**
   - Right-click connection "hue_portal"
   - Chọn **"SQL Editor"** → **"New SQL Script"**

### Bước 2: Gõ SQL Query

Trong SQL Editor, gõ query:

```sql
SELECT * FROM core_fine LIMIT 10;
```

### Bước 3: Execute Query

**Có 3 cách:**

1. **Click icon Play:**
   - Click icon **"Execute SQL Statement"** (play button ở toolbar)
   
2. **Keyboard shortcut:**
   - `Cmd + Enter` (macOS)
   - Hoặc `Ctrl + Enter` (Windows/Linux)

3. **Menu:**
   - `SQL Editor` → `Execute SQL Statement`

### Bước 4: Xem kết quả

- Kết quả sẽ hiện ở tab "Data" bên dưới SQL Editor
- Có thể scroll để xem tất cả rows

## Ví dụ Queries

### 1. Xem tất cả tables
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;
```

### 2. Xem data trong core_fine
```sql
SELECT * FROM core_fine LIMIT 10;
```

### 3. Xem số lượng records
```sql
SELECT 
  'core_fine' as table_name, 
  COUNT(*) as records 
FROM core_fine
UNION ALL
SELECT 'core_office', COUNT(*) FROM core_office
UNION ALL
SELECT 'core_auditlog', COUNT(*) FROM core_auditlog;
```

### 4. Xem data trong core_office
```sql
SELECT unit_name, address, phone 
FROM core_office 
LIMIT 10;
```

### 5. Tìm kiếm với BM25
```sql
SELECT name, rank
FROM core_fine, 
     to_tsquery('simple', 'vượt đèn đỏ') query,
     ts_rank(tsv_body, query) rank
WHERE tsv_body @@ query
ORDER BY rank DESC
LIMIT 10;
```

## Xem Data trực tiếp (không cần SQL)

### Cách 1: Double-click table
1. Mở rộng: `hue_portal` → `Databases` → `hue_portal` → `Schemas` → `public` → `Tables`
2. Double-click vào table (ví dụ: `core_fine`)
3. Data sẽ hiện ra tự động

### Cách 2: Right-click → View Data
1. Right-click vào table
2. Chọn **"View Data"** hoặc **"Open Data"**

## Tips

- ✅ **Chạy SQL trong DBeaver** - Đúng
- ❌ **Chạy SQL trong Terminal** - Sai (terminal không hiểu SQL)

- Để chạy nhiều queries cùng lúc, chọn queries và execute
- Để format SQL, right-click → **"Format SQL"**
- Để comment/uncomment: `Cmd + /`

---

**Nhớ: SQL phải chạy trong DBeaver, không phải terminal! 🎯**

