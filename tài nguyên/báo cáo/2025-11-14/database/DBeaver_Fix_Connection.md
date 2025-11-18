# Fix DBeaver Connection Error: "localhost 2"

## Vấn đề

Lỗi: "Connection to 'localhost 2' cannot be established"

## Nguyên nhân

- Connection name có thể là "localhost 2" (có số 2)
- Có thể có nhiều connection với tên tương tự
- Connection settings có thể không đúng

## Giải pháp

### Bước 1: Xóa connection cũ (nếu có)

1. Trong DBeaver, mở **Database Navigator** (bên trái)
2. Tìm connection có tên "localhost" hoặc "localhost 2"
3. Right-click → **Delete**
4. Xác nhận xóa

### Bước 2: Tạo connection mới với tên rõ ràng

1. Click **"New Database Connection"** (icon database)
   - Hoặc: `Database` → `New Database Connection`
   - Hoặc: `Cmd + Shift + N`

2. Chọn **"PostgreSQL"** → Click **"Next"**

3. **Tab "Main":**
   ```
   Host: localhost
   Port: 5433
   Database: hue_portal
   Username: hue
   Password: huepass
   ```

4. **Tab "Connection name" (ở trên cùng):**
   - Đổi tên thành: `Hue Portal DB` (hoặc tên khác, không có số)
   - **QUAN TRỌNG:** Không để tên là "localhost" hoặc "localhost 2"

5. Click **"Test Connection"**
   - Nếu hỏi download driver → Click **"Download"**
   - Đợi download xong
   - Click **"Test Connection"** lại

6. Nếu thành công → Click **"Finish"**

### Bước 3: Kiểm tra Connection Settings

Nếu vẫn lỗi, kiểm tra:

1. **Right-click connection** → **Edit Connection**

2. **Tab "Main":**
   - ✅ Host: `localhost` (không có khoảng trắng)
   - ✅ Port: `5433` (không phải 5432)
   - ✅ Database: `hue_portal` (chính xác)
   - ✅ Username: `hue` (chính xác)
   - ✅ Password: `huepass` (chính xác)
   - ✅ **Show all databases**: Bỏ check (nếu có)

3. **Tab "Driver properties":**
   - Kiểm tra driver version
   - Nếu cần, click **"Download"** để update driver

4. **Tab "SSH" và "SSL":**
   - Không cần check (để mặc định)

### Bước 4: Test từ Terminal trước

Trước khi kết nối DBeaver, test từ terminal:

```bash
# Test connection
docker exec tryhardemnayproject-db-1 psql -U hue -d hue_portal -c "SELECT 'OK' as status;"
```

Nếu terminal kết nối được → Vấn đề ở DBeaver settings.
Nếu terminal cũng lỗi → Vấn đề ở database container.

## Connection Info (Chính xác)

```
Connection Name: Hue Portal DB (hoặc tên khác, không có số)
Host: localhost
Port: 5433
Database: hue_portal
Username: hue
Password: huepass
```

## Troubleshooting nâng cao

### Nếu vẫn lỗi "Communications link failure"

1. **Kiểm tra container:**
   ```bash
   docker ps | grep postgres
   ```

2. **Restart container:**
   ```bash
   docker restart tryhardemnayproject-db-1
   sleep 5
   ```

3. **Kiểm tra port:**
   ```bash
   lsof -i :5433
   ```

4. **Trong DBeaver:**
   - Đóng tất cả connections
   - Restart DBeaver
   - Tạo connection mới

### Nếu lỗi "Driver not found"

1. `Database` → `Driver Manager`
2. Tìm "PostgreSQL"
3. Nếu không có → Click **"New Driver"** → Chọn PostgreSQL
4. Download driver version mới nhất
5. Apply và test connection lại

## Quick Fix Checklist

- [ ] Xóa connection cũ có tên "localhost 2"
- [ ] Tạo connection mới với tên rõ ràng (không có số)
- [ ] Kiểm tra Host: `localhost` (không có khoảng trắng)
- [ ] Kiểm tra Port: `5433` (không phải 5432)
- [ ] Kiểm tra Database: `hue_portal` (chính xác)
- [ ] Kiểm tra Username: `hue` (chính xác)
- [ ] Kiểm tra Password: `huepass` (chính xác)
- [ ] Download PostgreSQL driver nếu chưa có
- [ ] Test connection từ terminal trước
- [ ] Restart DBeaver nếu cần

## Sau khi kết nối thành công

1. Mở rộng connection: `Hue Portal DB` → `Schemas` → `public` → `Tables`
2. Xem các tables: `core_fine`, `core_office`, `core_procedure`, etc.
3. Double-click table để xem data
4. Click "SQL Editor" để chạy queries

---

**Lưu ý:** Tên connection không nên có số hoặc ký tự đặc biệt. Dùng tên mô tả như "Hue Portal DB" sẽ dễ quản lý hơn.

