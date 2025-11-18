# PostgreSQL Apps Cross-Platform (Mac + Windows)

Các app hỗ trợ cả macOS và Windows:

## 🏆 Top Recommendations

### 1. **DBeaver Community** ⭐⭐⭐⭐⭐ (Khuyến nghị #1)
**Free, mạnh mẽ, hỗ trợ đầy đủ**

**Download:**
- macOS: https://dbeaver.io/download/ (hoặc `brew install --cask dbeaver-community`)
- Windows: https://dbeaver.io/download/

**Tính năng:**
- ✅ **Free và open source**
- ✅ Hỗ trợ nhiều database (PostgreSQL, MySQL, SQLite, MongoDB, Redis...)
- ✅ SQL editor mạnh mẽ với syntax highlighting
- ✅ ER diagrams
- ✅ Data export/import (CSV, Excel, JSON, SQL...)
- ✅ Query builder
- ✅ Dark mode
- ✅ Cross-platform: macOS, Windows, Linux
- ✅ Cộng đồng lớn, nhiều plugins

**Kết nối:**
```
Host: localhost
Port: 5433
Database: hue_portal
User: hue
Password: huepass
```

---

### 2. **DataGrip** (JetBrains) ⭐⭐⭐⭐⭐
**Professional IDE, trả phí nhưng mạnh nhất**

**Download:**
- macOS: https://www.jetbrains.com/datagrip/download/
- Windows: https://www.jetbrains.com/datagrip/download/

**Tính năng:**
- ✅ Professional IDE từ JetBrains
- ✅ SQL editor cực mạnh với code completion
- ✅ Refactoring, find usages
- ✅ Database diagrams
- ✅ Version control integration (Git)
- ✅ Debugging và profiling
- ✅ Cross-platform: macOS, Windows, Linux
- ⚠️ **Trả phí:** $199/năm (có trial 30 ngày)
- ✅ Student license miễn phí

---

### 3. **pgAdmin 4** ⭐⭐⭐⭐
**Official PostgreSQL tool, free**

**Download:**
- macOS: https://www.pgadmin.org/download/pgadmin-4-macos/
- Windows: https://www.pgadmin.org/download/pgadmin-4-windows/

**Tính năng:**
- ✅ **Official tool từ PostgreSQL team**
- ✅ Free và open source
- ✅ Web-based interface (chạy trong browser)
- ✅ SQL editor mạnh mẽ
- ✅ Query tool
- ✅ Dashboard và statistics
- ✅ Backup/restore
- ✅ Cross-platform: macOS, Windows, Linux
- ⚠️ Hơi nặng và phức tạp hơn

---

### 4. **TablePlus** ⭐⭐⭐⭐⭐
**Đẹp nhất, nhưng có giới hạn free**

**Download:**
- macOS: https://tableplus.com/ (hoặc `brew install --cask tableplus`)
- Windows: https://tableplus.com/

**Tính năng:**
- ✅ Giao diện đẹp, modern UI
- ✅ Hỗ trợ nhiều database
- ✅ SQL editor với syntax highlighting
- ✅ Export/Import data
- ✅ Dark mode
- ✅ Cross-platform: macOS, Windows, Linux
- ⚠️ **Free version:** Giới hạn 2 tabs, 2 queries
- 💰 **Paid:** $89 one-time (unlimited)

---

### 5. **HeidiSQL** ⭐⭐⭐
**Nhẹ, đơn giản (Windows chính, có bản Mac)**

**Download:**
- Windows: https://www.heidisql.com/download.php
- macOS: Có bản beta (không chính thức)

**Tính năng:**
- ✅ Nhẹ, nhanh
- ✅ Giao diện đơn giản
- ✅ Free và open source
- ⚠️ Chủ yếu cho Windows, Mac version không ổn định

---

### 6. **Adminer** ⭐⭐⭐
**Web-based, chạy mọi nơi**

**Download:**
- Single PHP file: https://www.adminer.org/
- Hoặc chạy qua Docker: `docker run --rm -d -p 8080:8080 adminer`

**Tính năng:**
- ✅ Rất nhẹ (single PHP file)
- ✅ Web-based (chạy trong browser)
- ✅ Cross-platform (bất kỳ OS nào có browser)
- ✅ Free
- ⚠️ Giao diện đơn giản, ít tính năng

---

## 📊 So sánh nhanh

| App | Price | Mac | Windows | Ease | Features | Best For |
|-----|-------|-----|---------|------|----------|----------|
| **DBeaver** | Free | ✅ | ✅ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **Khuyến nghị #1** |
| **DataGrip** | $199/yr | ✅ | ✅ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Professional |
| **pgAdmin 4** | Free | ✅ | ✅ | ⭐⭐⭐ | ⭐⭐⭐⭐ | Official tool |
| **TablePlus** | Free/Paid | ✅ | ✅ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Beautiful UI |
| **HeidiSQL** | Free | ⚠️ | ✅ | ⭐⭐⭐⭐ | ⭐⭐⭐ | Windows chính |
| **Adminer** | Free | ✅ | ✅ | ⭐⭐⭐ | ⭐⭐⭐ | Web-based |

---

## 🎯 Khuyến nghị cho bạn

### Nếu muốn **FREE và mạnh mẽ:**
👉 **DBeaver Community** - Tốt nhất cho cross-platform, free, đầy đủ tính năng

### Nếu muốn **đẹp và dễ dùng:**
👉 **TablePlus** - Giao diện đẹp nhất, nhưng free version có giới hạn

### Nếu muốn **Professional:**
👉 **DataGrip** - Mạnh nhất, nhưng trả phí (có trial 30 ngày)

### Nếu muốn **Official tool:**
👉 **pgAdmin 4** - Tool chính thức từ PostgreSQL team

---

## 🚀 Quick Start với DBeaver (Khuyến nghị)

### Cài đặt:

**macOS:**
```bash
brew install --cask dbeaver-community
```

**Windows:**
- Download từ: https://dbeaver.io/download/
- Chọn "Windows 64 bit installer"
- Chạy installer và cài đặt

### Kết nối:

1. Mở DBeaver
2. Click "New Database Connection" (icon database ở góc trên bên trái)
3. Chọn "PostgreSQL"
4. Điền thông tin:
   ```
   Host: localhost
   Port: 5433
   Database: hue_portal
   Username: hue
   Password: huepass
   ```
5. Click "Test Connection" → "Finish"

### Sử dụng:

- **Xem tables:** Mở rộng connection → Schemas → public → Tables
- **Xem data:** Double-click vào table
- **Chạy SQL:** Click "SQL Editor" (icon SQL ở toolbar)
- **Export data:** Right-click table → "Export Data"

---

## 🔗 Connection Info (Tóm tắt)

```
Host: localhost
Port: 5433
Database: hue_portal
Username: hue
Password: huepass
```

**Lưu ý:** Port 5433 là port external (để kết nối từ host machine). Nếu kết nối từ Docker container, dùng port 5432.

---

## 💡 Tip

**DBeaver** là lựa chọn tốt nhất cho cross-platform vì:
- ✅ Free 100%
- ✅ Mạnh mẽ, đầy đủ tính năng
- ✅ Hỗ trợ tốt cả Mac và Windows
- ✅ Cộng đồng lớn, nhiều tài liệu
- ✅ Cập nhật thường xuyên

