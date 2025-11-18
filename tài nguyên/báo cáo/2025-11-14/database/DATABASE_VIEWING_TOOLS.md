# Công cụ xem Database trực quan

Có nhiều cách để xem database PostgreSQL một cách trực quan. Dưới đây là các phương pháp được đề xuất:

## 1. Django Admin (Khuyến nghị - Dễ nhất) ✅

Django Admin là cách dễ nhất để xem và quản lý dữ liệu trong project này.

### Setup

```bash
# Tạo superuser
cd backend/hue_portal
source ../../.venv/bin/activate
POSTGRES_PORT=5433 POSTGRES_HOST=localhost python ../../scripts/setup_admin.py

# Hoặc tạo thủ công
POSTGRES_PORT=5433 POSTGRES_HOST=localhost python manage.py createsuperuser
```

### Truy cập

1. **Start Django server** (nếu chưa chạy):
   ```bash
   cd backend/hue_portal
   source ../../.venv/bin/activate
   POSTGRES_PORT=5433 POSTGRES_HOST=localhost python manage.py runserver
   ```

2. **Mở browser**: http://localhost:8000/admin/

3. **Đăng nhập** với username/password vừa tạo

### Tính năng

- ✅ Xem tất cả models: Procedure, Fine, Office, Advisory, Synonym, AuditLog, MLMetrics
- ✅ Tìm kiếm và lọc dữ liệu
- ✅ Thêm/sửa/xóa records
- ✅ Xem chi tiết từng record
- ✅ Không cần cài thêm tool

---

## 2. TablePlus (macOS - Khuyến nghị) 🍎

TablePlus là công cụ native macOS, đẹp và mạnh mẽ.

### Cài đặt

```bash
# Cài qua Homebrew
brew install --cask tableplus

# Hoặc download từ: https://tableplus.com/
```

### Kết nối

1. Mở TablePlus
2. Click "Create a new connection"
3. Chọn "PostgreSQL"
4. Điền thông tin:
   ```
   Name: Hue Portal DB
   Host: localhost
   Port: 5433
   User: hue
   Password: huepass
   Database: hue_portal
   ```
5. Click "Test" → "Connect"

### Tính năng

- ✅ Giao diện đẹp, native macOS
- ✅ Xem/edit data trực tiếp
- ✅ SQL editor với syntax highlighting
- ✅ Export/Import data
- ✅ Dark mode
- ✅ Free cho personal use

---

## 3. Postico (macOS - Native) 🍎

Postico là PostgreSQL client chuyên dụng cho macOS.

### Cài đặt

```bash
# Cài qua Homebrew
brew install --cask postico

# Hoặc download từ: https://eggerapps.at/postico/
```

### Kết nối

1. Mở Postico
2. Click "New Favorite"
3. Điền thông tin:
   ```
   Host: localhost
   Port: 5433
   User: hue
   Password: huepass
   Database: hue_portal
   ```
4. Click "Connect"

### Tính năng

- ✅ Native macOS app
- ✅ Giao diện đơn giản, dễ dùng
- ✅ Xem/edit tables trực tiếp
- ✅ SQL queries
- ✅ Free version có đủ tính năng cơ bản

---

## 4. DBeaver (Cross-platform) 🌐

DBeaver là universal database tool, hỗ trợ nhiều loại database.

### Cài đặt

```bash
# Cài qua Homebrew
brew install --cask dbeaver-community

# Hoặc download từ: https://dbeaver.io/
```

### Kết nối

1. Mở DBeaver
2. Click "New Database Connection"
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

### Tính năng

- ✅ Free và open source
- ✅ Hỗ trợ nhiều database types
- ✅ SQL editor mạnh mẽ
- ✅ ER diagrams
- ✅ Data export/import
- ✅ Cross-platform (macOS, Windows, Linux)

---

## 5. VS Code Extension (Nếu dùng VS Code) 💻

Nếu bạn dùng VS Code, có thể dùng extension để xem database.

### Cài đặt

1. Mở VS Code
2. Extensions (Cmd+Shift+X)
3. Tìm "PostgreSQL" hoặc "SQLTools"
4. Cài extension:
   - **SQLTools** + **SQLTools PostgreSQL/Cockroach Driver**
   - Hoặc **PostgreSQL** by Chris Kolkman

### Kết nối (SQLTools)

1. Click SQLTools icon ở sidebar
2. Click "Add New Connection"
3. Chọn "PostgreSQL"
4. Điền thông tin:
   ```
   Name: Hue Portal
   Server: localhost
   Port: 5433
   Database: hue_portal
   Username: hue
   Password: huepass
   ```
5. Click "Test Connection" → "Save"

### Tính năng

- ✅ Xem database trong VS Code
- ✅ SQL queries
- ✅ Không cần mở app riêng
- ✅ Tích hợp với code editor

---

## 6. pgAdmin (Web-based) 🌐

pgAdmin là công cụ web-based chính thức của PostgreSQL.

### Cài đặt

```bash
# Cài qua Homebrew
brew install --cask pgadmin4

# Hoặc download từ: https://www.pgadmin.org/
```

### Kết nối

1. Mở pgAdmin (sẽ mở trong browser)
2. Click "Add New Server"
3. Tab "General":
   ```
   Name: Hue Portal
   ```
4. Tab "Connection":
   ```
   Host: localhost
   Port: 5433
   Database: hue_portal
   Username: hue
   Password: huepass
   ```
5. Click "Save"

### Tính năng

- ✅ Official PostgreSQL tool
- ✅ Web-based interface
- ✅ SQL editor
- ✅ Query tool
- ✅ Dashboard và statistics
- ✅ Miễn phí

---

## 7. Adminer (Web-based - Minimal) 🌐

Adminer là tool web-based nhẹ, có thể chạy trong Docker.

### Chạy qua Docker

```bash
docker run --rm -d \
  --name adminer \
  -p 8080:8080 \
  adminer
```

### Truy cập

1. Mở browser: http://localhost:8080
2. Chọn "PostgreSQL"
3. Điền thông tin:
   ```
   System: PostgreSQL
   Server: host.docker.internal:5433
   Username: hue
   Password: huepass
   Database: hue_portal
   ```
4. Click "Login"

### Tính năng

- ✅ Rất nhẹ (single PHP file)
- ✅ Web-based
- ✅ Đơn giản, dễ dùng
- ✅ Không cần cài đặt (chạy qua Docker)

---

## So sánh nhanh

| Tool | Platform | Dễ dùng | Tính năng | Khuyến nghị |
|------|----------|---------|-----------|-------------|
| **Django Admin** | Web | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ✅ Cho project này |
| **TablePlus** | macOS | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ Cho macOS |
| **Postico** | macOS | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ Cho PostgreSQL |
| **DBeaver** | All | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ Universal |
| **VS Code Extension** | All | ⭐⭐⭐ | ⭐⭐⭐ | ✅ Nếu dùng VS Code |
| **pgAdmin** | All | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⚠️ Hơi nặng |
| **Adminer** | Web | ⭐⭐⭐⭐ | ⭐⭐⭐ | ✅ Minimal |

---

## Connection Info (Tóm tắt)

```
Host: localhost
Port: 5433 (external), 5432 (internal)
Database: hue_portal
Username: hue
Password: huepass
```

**Lưu ý:** Port 5433 là port external (để kết nối từ host machine). Nếu kết nối từ Docker container, dùng port 5432.

---

## Khuyến nghị

1. **Bắt đầu với Django Admin** - Dễ nhất, không cần cài thêm
2. **Nếu cần tool mạnh hơn** - Dùng TablePlus (macOS) hoặc DBeaver (cross-platform)
3. **Nếu dùng VS Code** - Cài SQLTools extension

