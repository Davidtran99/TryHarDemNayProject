# DBeaver Connection với User Admin

## ✅ User admin đã được tạo

User `admin` đã được tạo trong PostgreSQL với quyền SUPERUSER.

## Thông tin kết nối với admin:

```
Host: localhost
Port: 5433          ← SỬA TỪ 5422
Database: hue_portal
Username: admin     ← ĐÚNG RỒI
Password: admin123  ← ĐIỀN VÀO
```

## Cần sửa trong DBeaver:

### 1. Port
- **Hiện tại:** `5422` ❌
- **Sửa thành:** `5433` ✅

### 2. Password
- **Hiện tại:** (trống) ❌
- **Sửa thành:** `admin123` ✅
- Click vào ô Password → Gõ: admin123

## ✅ Đã đúng:
- Host: `localhost` ✅
- Database: `hue_portal` ✅
- Username: `admin` ✅

## Sau khi sửa:

1. Sửa Port: `5422` → `5433`
2. Điền Password: `admin123`
3. Click **"Test Connection ..."**
4. Nếu hỏi download driver → Click **"Download"**
5. Đợi download xong → Click **"Test Connection"** lại
6. Nếu thành công → Click **"Finish"**

## User admin có quyền:

- ✅ SUPERUSER (toàn quyền)
- ✅ Có thể truy cập tất cả databases
- ✅ Có thể tạo/xóa users
- ✅ Có thể tạo/xóa databases
- ✅ Có thể truy cập tất cả tables trong `hue_portal`

## Lưu ý:

- Password: `admin123` (không phải `huepass`)
- Username: `admin` (đã đúng rồi)
- Port: `5433` (quan trọng!)

---

**Sửa Port và điền Password là xong! 🎉**

