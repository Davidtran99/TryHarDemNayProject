# PostgreSQL Apps cho macOS

Có nhiều app desktop để quản lý PostgreSQL trên macOS. Dưới đây là các lựa chọn phổ biến:

## 🍎 Native macOS Apps (Khuyến nghị)

### 1. **TablePlus** ⭐⭐⭐⭐⭐
**App đẹp nhất, native macOS**

```bash
# Cài qua Homebrew
brew install --cask tableplus

# Hoặc download từ: https://tableplus.com/
```

**Tính năng:**
- ✅ Giao diện đẹp, native macOS
- ✅ Hỗ trợ nhiều database (PostgreSQL, MySQL, SQLite, MongoDB, Redis...)
- ✅ Dark mode
- ✅ SQL editor với syntax highlighting
- ✅ Export/Import data
- ✅ Free cho personal use
- ✅ Rất nhanh và mượt

**Kết nối:**
```
Host: localhost
Port: 5433
Database: hue_portal
User: hue
Password: huepass
```

---

### 2. **Postico** ⭐⭐⭐⭐
**App chuyên dụng cho PostgreSQL**

```bash
# Cài qua Homebrew
brew install --cask postico

# Hoặc download từ: https://eggerapps.at/postico/
```

**Tính năng:**
- ✅ Native macOS app
- ✅ Chuyên dụng cho PostgreSQL
- ✅ Giao diện đơn giản, dễ dùng
- ✅ Xem/edit tables trực tiếp
- ✅ SQL queries
- ✅ Free version có đủ tính năng cơ bản
- ✅ Pro version ($39) có thêm tính năng nâng cao

**Kết nối:**
```
Host: localhost
Port: 5433
Database: hue_portal
User: hue
Password: huepass
```

---

### 3. **pgAdmin 4** ⭐⭐⭐
**Official PostgreSQL tool**

```bash
# Cài qua Homebrew
brew install --cask pgadmin4

# Hoặc download từ: https://www.pgadmin.org/download/
```

**Tính năng:**
- ✅ Official tool từ PostgreSQL team
- ✅ Web-based interface (chạy trong browser)
- ✅ SQL editor mạnh mẽ
- ✅ Query tool
- ✅ Dashboard và statistics
- ✅ Miễn phí, open source
- ⚠️ Hơi nặng và phức tạp hơn

**Kết nối:**
```
Host: localhost
Port: 5433
Database: hue_portal
User: hue
Password: huepass
```

---

## 🌐 Cross-platform Apps

### 4. **DBeaver Community** ⭐⭐⭐⭐
**Universal database tool**

```bash
# Cài qua Homebrew
brew install --cask dbeaver-community

# Hoặc download từ: https://dbeaver.io/download/
```

**Tính năng:**
- ✅ Free và open source
- ✅ Hỗ trợ nhiều database types
- ✅ SQL editor mạnh mẽ
- ✅ ER diagrams
- ✅ Data export/import
- ✅ Cross-platform (macOS, Windows, Linux)
- ⚠️ Giao diện hơi phức tạp

---

### 5. **DataGrip** (JetBrains) ⭐⭐⭐⭐⭐
**Professional IDE cho databases**

```bash
# Cài qua Homebrew
brew install --cask datagrip

# Hoặc download từ: https://www.jetbrains.com/datagrip/
```

**Tính năng:**
- ✅ Professional IDE từ JetBrains
- ✅ SQL editor cực mạnh
- ✅ Code completion, refactoring
- ✅ Database diagrams
- ✅ Version control integration
- ⚠️ Trả phí ($199/năm) - có trial 30 ngày

---

### 6. **Sequel Pro** (MySQL only) ⚠️
**Chỉ cho MySQL, không hỗ trợ PostgreSQL**

---

## 📱 Mobile Apps (iOS/Android)

### 7. **PostgresApp** (macOS Menu Bar)
**Menu bar app đơn giản**

```bash
# Cài qua Homebrew
brew install --cask postgresapp

# Hoặc download từ: https://postgresapp.com/
```

**Tính năng:**
- ✅ Chạy PostgreSQL server local
- ✅ Menu bar app
- ✅ Đơn giản, dễ dùng
- ⚠️ Chủ yếu để chạy server, không phải client

---

## 🎯 Khuyến nghị

### Cho người mới bắt đầu:
1. **TablePlus** - Đẹp, dễ dùng, free
2. **Postico** - Chuyên PostgreSQL, đơn giản

### Cho developer:
1. **DBeaver** - Free, mạnh mẽ, nhiều tính năng
2. **DataGrip** - Professional (nếu có budget)

### Cho production:
1. **pgAdmin 4** - Official tool, đầy đủ tính năng

---

## 🚀 Quick Start với TablePlus

1. **Cài đặt:**
   ```bash
   brew install --cask tableplus
   ```

2. **Mở app và tạo connection:**
   - Click "Create a new connection"
   - Chọn "PostgreSQL"
   - Điền thông tin:
     ```
     Name: Hue Portal DB
     Host: localhost
     Port: 5433
     User: hue
     Password: huepass
     Database: hue_portal
     ```
   - Click "Test" → "Connect"

3. **Xem database:**
   - Browse tables: `core_fine`, `core_office`, `core_procedure`, etc.
   - Click vào table để xem data
   - Double-click để edit records
   - Click "SQL" tab để chạy queries

---

## 📊 So sánh nhanh

| App | Price | Ease | Features | Best For |
|-----|-------|------|----------|----------|
| **TablePlus** | Free/Paid | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | General use |
| **Postico** | Free/Paid | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | PostgreSQL only |
| **DBeaver** | Free | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Developers |
| **pgAdmin 4** | Free | ⭐⭐⭐ | ⭐⭐⭐⭐ | Production |
| **DataGrip** | $199/yr | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Professional |

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

Nếu bạn chỉ cần xem data nhanh, **Django Admin** (http://localhost:8000/admin/) là cách dễ nhất và không cần cài thêm app nào!

