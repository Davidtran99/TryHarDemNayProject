# Hướng dẫn kết nối DBeaver với PostgreSQL

## DBeaver đã được cài đặt ✅

DBeaver Community Edition đã được cài đặt trên máy của bạn.

## Cách mở DBeaver

1. **Từ Applications:**
   - Mở Finder → Applications → DBeaver

2. **Từ Spotlight:**
   - Nhấn `Cmd + Space`
   - Gõ "DBeaver"
   - Nhấn Enter

3. **Từ Terminal:**
   ```bash
   open -a DBeaver
   ```

## Kết nối với PostgreSQL Database

### Bước 1: Tạo Connection mới

1. Mở DBeaver
2. Click **"New Database Connection"** (icon database ở góc trên bên trái)
   - Hoặc: `Database` → `New Database Connection`
   - Hoặc: `Cmd + Shift + N`

### Bước 2: Chọn PostgreSQL

1. Trong danh sách databases, chọn **"PostgreSQL"**
2. Click **"Next"**

### Bước 3: Điền thông tin kết nối

**Main Tab:**
```
Host: localhost
Port: 5433
Database: hue_portal
Username: hue
Password: huepass
```

**Lưu ý:** 
- Port **5433** (không phải 5432) vì đây là port external
- Nếu kết nối từ Docker container, dùng port 5432

### Bước 4: Test Connection

1. Click **"Test Connection"**
2. Nếu lần đầu, DBeaver sẽ hỏi download PostgreSQL driver → Click **"Download"**
3. Đợi download xong → Click **"Test Connection"** lại
4. Nếu thành công, sẽ hiện: **"Connected"** ✅

### Bước 5: Lưu Connection

1. Click **"Finish"**
2. Connection sẽ xuất hiện trong Database Navigator (bên trái)

## Sử dụng DBeaver

### Xem Tables

1. Mở rộng connection: `hue_portal` → `Schemas` → `public` → `Tables`
2. Click vào table để xem data
3. Double-click vào table để mở data editor

### Chạy SQL Queries

1. Click **"SQL Editor"** (icon SQL ở toolbar)
   - Hoặc: `SQL Editor` → `New SQL Script`
   - Hoặc: `Cmd + ]`
2. Gõ SQL query
3. Click **"Execute SQL Statement"** (icon play) hoặc `Cmd + Enter`

### Export Data

1. Right-click vào table
2. Chọn **"Export Data"**
3. Chọn format (CSV, Excel, JSON, SQL, etc.)
4. Chọn destination và click **"Start"**

### Import Data

1. Right-click vào table
2. Chọn **"Import Data"**
3. Chọn file source
4. Map columns và click **"Start"**

## Connection Info (Tóm tắt)

```
Host: localhost
Port: 5433
Database: hue_portal
Username: hue
Password: huepass
```

## Troubleshooting

### Lỗi: "Connection refused" hoặc "Connection lost"

**Nguyên nhân:** PostgreSQL container chưa chạy hoặc có vấn đề kết nối

**Giải pháp:**

1. **Kiểm tra container đang chạy:**
   ```bash
   docker ps | grep postgres
   ```

2. **Nếu container không chạy, start lại:**
   ```bash
   cd /Users/davidtran/Downloads/TryHarDemNayProject
   docker compose up -d db
   ```

3. **Đợi vài giây để container khởi động hoàn toàn:**
   ```bash
   sleep 5
   docker exec tryhardemnayproject-db-1 psql -U hue -d hue_portal -c "SELECT 1;"
   ```

4. **Kiểm tra port đang listen:**
   ```bash
   lsof -i :5433
   # Hoặc
   netstat -an | grep 5433
   ```

5. **Trong DBeaver:**
   - Click **"Retry"** để thử kết nối lại
   - Hoặc đóng dialog và test connection lại từ connection settings

### Lỗi: "Password authentication failed"

**Nguyên nhân:** Sai username/password

**Giải pháp:** Kiểm tra lại:
- Username: `hue` (không có khoảng trắng)
- Password: `huepass` (không có khoảng trắng)
- Database: `hue_portal`

### Lỗi: "Connection timeout"

**Nguyên nhân:** Port không đúng hoặc firewall

**Giải pháp:**
- Kiểm tra port: `5433` (external, không phải 5432)
- Kiểm tra container đang chạy: `docker ps`
- Kiểm tra port mapping: `0.0.0.0:5433->5432/tcp`

### Lỗi: "Communications link failure"

**Nguyên nhân:** Driver chưa được download hoặc có vấn đề

**Giải pháp:**

1. **Download PostgreSQL driver:**
   - Trong DBeaver, khi test connection lần đầu, sẽ có popup hỏi download driver
   - Click **"Download"** và đợi download xong

2. **Kiểm tra driver đã cài:**
   - `Database` → `Driver Manager`
   - Tìm "PostgreSQL" → Kiểm tra version và status

3. **Update driver nếu cần:**
   - Right-click connection → `Edit Connection`
   - Tab `Driver properties` → Check driver version
   - Nếu cần, download version mới hơn

### Kiểm tra kết nối từ Terminal

Trước khi kết nối DBeaver, test từ terminal:

```bash
# Test connection
docker exec tryhardemnayproject-db-1 psql -U hue -d hue_portal -c "SELECT version();"

# Hoặc từ host machine (nếu có psql client)
psql -h localhost -p 5433 -U hue -d hue_portal
# Password: huepass
```

Nếu terminal kết nối được nhưng DBeaver không được → Vấn đề ở DBeaver driver hoặc settings.

## Tính năng hữu ích

- ✅ **SQL Editor** với syntax highlighting
- ✅ **Data Editor** để xem/edit data trực tiếp
- ✅ **ER Diagrams** để xem database schema
- ✅ **Query Manager** để quản lý queries
- ✅ **Export/Import** data nhiều format
- ✅ **Dark Mode** (Preferences → Appearance → Theme)

## Shortcuts hữu ích

- `Cmd + Shift + N` - New Database Connection
- `Cmd + ]` - New SQL Script
- `Cmd + Enter` - Execute SQL
- `Cmd + /` - Comment/Uncomment
- `Cmd + D` - Duplicate line

## Next Steps

1. Kết nối với database
2. Explore các tables: `core_fine`, `core_office`, `core_procedure`, etc.
3. Chạy queries để xem data
4. Export data nếu cần

---

**Chúc bạn sử dụng DBeaver thành công! 🎉**

