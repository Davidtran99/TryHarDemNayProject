# Sửa nhanh DBeaver Connection

## ⚠️ Cần sửa 3 chỗ:

### 1. Port
- **Hiện tại:** `5422` ❌
- **Sửa thành:** `5433` ✅
- Click vào ô Port → Xóa 5422 → Gõ 5433

### 2. Username
- **Hiện tại:** `admin` ❌
- **Sửa thành:** `hue` ✅
- Click vào ô Username → Xóa admin → Gõ hue

### 3. Password
- **Hiện tại:** (trống) ❌
- **Sửa thành:** `huepass` ✅
- Click vào ô Password → Gõ: huepass

## ✅ Đã đúng:
- Host: `localhost` ✅
- Database: `hue_portal` ✅

## Sau khi sửa xong:

1. Click **"Test Connection ..."** (button ở dưới)
2. Nếu hỏi download driver → Click **"Download"**
3. Đợi download xong → Click **"Test Connection"** lại
4. Nếu thành công → Click **"Finish"**

## Thông tin đúng (copy để check):

```
Host: localhost
Port: 5433
Database: hue_portal
Username: hue
Password: huepass
```

