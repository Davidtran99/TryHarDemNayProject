# Hướng dẫn Setup DBeaver - Từng bước

## Bước 1: Mở Connection Settings

Bạn đang ở dialog "Connect to a database" → Tab "Main" ✅

## Bước 2: Điền thông tin Server

Trong phần **"Server"**:

1. **Connect by:** Chọn **"Host"** (đã chọn sẵn ✅)

2. **Host:** 
   - Xóa "localhost" hiện tại
   - Gõ: `localhost`
   - ✅ Đúng rồi

3. **Port:**
   - ⚠️ **QUAN TRỌNG:** Đổi từ `5432` thành `5433`
   - Xóa số 5432
   - Gõ: `5433`

4. **Database:**
   - ⚠️ **QUAN TRỌNG:** Đổi từ `postgres` thành `hue_portal`
   - Xóa "postgres"
   - Gõ: `hue_portal`

5. **Show all databases:** 
   - Bỏ check (không cần check)

## Bước 3: Điền thông tin Authentication

Trong phần **"Authentication"**:

1. **Authentication:** 
   - Giữ nguyên "Database Native" ✅

2. **Username:**
   - ⚠️ **QUAN TRỌNG:** Đổi từ `postgres` thành `hue`
   - Xóa "postgres"
   - Gõ: `hue`

3. **Password:**
   - Click vào ô password (hiện đang trống)
   - Gõ: `huepass`
   - ✅ Check "Save password" (đã check sẵn)

## Bước 4: Test Connection

1. Scroll xuống dưới cùng
2. Click button **"Test Connection ..."**
3. Nếu lần đầu, DBeaver sẽ hỏi download PostgreSQL driver:
   - Click **"Download"**
   - Đợi download xong (có thể mất vài phút)
4. Sau khi download xong, click **"Test Connection"** lại
5. Nếu thành công, sẽ hiện popup: **"Connected"** ✅

## Bước 5: Lưu Connection

1. Sau khi test connection thành công
2. Click button **"Finish"** (sẽ sáng lên sau khi test thành công)
3. Connection sẽ xuất hiện trong Database Navigator (bên trái)

## Tóm tắt thông tin cần điền

```
Host: localhost
Port: 5433          ← ĐỔI TỪ 5432
Database: hue_portal  ← ĐỔI TỪ postgres
Username: hue        ← ĐỔI TỪ postgres
Password: huepass    ← ĐIỀN VÀO
```

## Lưu ý quan trọng

- ⚠️ **Port phải là 5433** (không phải 5432)
- ⚠️ **Database phải là hue_portal** (không phải postgres)
- ⚠️ **Username phải là hue** (không phải postgres)
- ✅ Password: `huepass`

## Nếu Test Connection bị lỗi

1. Kiểm tra lại tất cả thông tin đã điền đúng chưa
2. Đảm bảo PostgreSQL container đang chạy:
   ```bash
   docker ps | grep postgres
   ```
3. Nếu container không chạy:
   ```bash
   docker compose up -d db
   ```
4. Đợi vài giây rồi test connection lại

## Sau khi kết nối thành công

1. Trong Database Navigator (bên trái), mở rộng connection mới
2. Mở rộng: `hue_portal` → `Schemas` → `public` → `Tables`
3. Sẽ thấy các tables: `core_fine`, `core_office`, `core_procedure`, etc.
4. Double-click vào table để xem data

---

**Chúc bạn setup thành công! 🎉**

