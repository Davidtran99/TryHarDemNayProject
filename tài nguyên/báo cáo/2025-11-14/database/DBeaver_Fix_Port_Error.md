# Fix Lỗi: Connection refused - Port 5422

## ❌ Lỗi hiện tại

**"Connection to localhost:5422 refused"**

## 🔍 Nguyên nhân

Port trong DBeaver đang là `5422` (SAI)  
Database đang chạy trên port `5433` (ĐÚNG)

## ✅ Giải pháp

### Sửa Port trong DBeaver:

1. **Đóng dialog lỗi** (click "OK")

2. **Mở lại connection settings:**
   - Right-click connection trong Database Navigator
   - Chọn **"Edit Connection"**
   - Hoặc tạo connection mới

3. **Trong tab "Main":**
   - Tìm ô **"Port"**
   - **Xóa số 5422**
   - **Gõ: 5433**

4. **Kiểm tra lại tất cả thông tin:**
   ```
   Host: localhost
   Port: 5433          ← QUAN TRỌNG: Phải là 5433
   Database: hue_portal
   Username: admin
   Password: admin123
   ```

5. **Click "Test Connection ..."**

6. **Nếu thành công → Click "Finish"**

## ⚠️ Lưu ý quan trọng

- **Port phải là 5433** (không phải 5422)
- Database container đang expose port 5433 ra ngoài
- Port 5422 không có service nào đang chạy → Connection refused

## Kiểm tra database đang chạy

```bash
docker ps | grep postgres
# Sẽ thấy: 0.0.0.0:5433->5432/tcp
```

Port mapping: `5433` (external) → `5432` (internal container)

## Thông tin kết nối đúng

```
Host: localhost
Port: 5433          ← ĐÂY LÀ QUAN TRỌNG NHẤT
Database: hue_portal
Username: admin
Password: admin123
```

---

**Sửa Port từ 5422 → 5433 là sẽ kết nối được! ✅**

