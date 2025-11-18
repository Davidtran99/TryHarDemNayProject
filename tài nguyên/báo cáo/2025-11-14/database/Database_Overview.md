# Database Overview - Giải thích Database

## 🎯 Database này là gì?

**PostgreSQL Database** cho hệ thống **Chatbot Công an Thừa Thiên Huế**

- **Mục đích:** Lưu trữ dữ liệu để chatbot trả lời câu hỏi của người dân
- **Công nghệ:** PostgreSQL 15.14
- **Vị trí:** Chạy trong Docker container
- **Port:** 5433 (external)

## 📊 Các Tables và chức năng

### 1. `core_fine` - Bảng Mức phạt

**Là gì?** Lưu thông tin về các mức phạt vi phạm giao thông

**Dữ liệu:**
- Mã vi phạm (V001, V002, ...)
- Tên vi phạm (Vượt đèn đỏ, Đi quá tốc độ, ...)
- Điều luật, Nghị định
- Mức phạt min/max
- Điểm trừ bằng lái

**Ví dụ:**
```
V001 - Vượt đèn đỏ
V002 - Đi quá tốc độ trong khu vực đông dân cư
V003 - Điều khiển xe khi nồng độ cồn vượt mức
```

**Dùng để:** Chatbot trả lời câu hỏi "Phạt bao nhiêu nếu vượt đèn đỏ?"

---

### 2. `core_office` - Bảng Địa chỉ điểm tiếp dân

**Là gì?** Lưu thông tin các địa điểm tiếp công dân của Công an

**Dữ liệu:**
- Tên đơn vị
- Địa chỉ
- Quận/Huyện
- Giờ làm việc
- Số điện thoại
- Email
- Tọa độ (latitude, longitude)

**Ví dụ:**
```
Công an tỉnh Thừa Thiên Huế - Tiếp công dân
Địa chỉ: ...
SĐT: ...
```

**Dùng để:** Chatbot trả lời "Điểm tiếp dân ở đâu?", "Số điện thoại là gì?"

---

### 3. `core_procedure` - Bảng Thủ tục

**Là gì?** Lưu thông tin các thủ tục hành chính

**Dữ liệu:**
- Tên thủ tục
- Lĩnh vực (ANTT, PCCC, Cư trú, ...)
- Cấp độ
- Điều kiện
- Hồ sơ cần thiết
- Thời hạn xử lý
- Lệ phí
- Nơi nộp

**Ví dụ:**
```
Thủ tục đăng ký cư trú
- Điều kiện: ...
- Hồ sơ: CMND, Sổ hộ khẩu, ...
- Thời hạn: 7 ngày
```

**Dùng để:** Chatbot trả lời "Làm thủ tục cư trú cần gì?", "Thủ tục như thế nào?"

**Status:** ❌ Chưa có data (0 records)

---

### 4. `core_advisory` - Bảng Cảnh báo

**Là gì?** Lưu thông tin các cảnh báo, thủ đoạn lừa đảo

**Dữ liệu:**
- Tiêu đề
- Tóm tắt
- Nội dung chi tiết
- Ngày đăng

**Ví dụ:**
```
Cảnh báo: Lừa đảo giả danh Công an
- Thủ đoạn: Gọi điện giả danh Công an yêu cầu chuyển tiền
- Cách phòng tránh: ...
```

**Dùng để:** Chatbot trả lời "Cảnh báo lừa đảo", "Thủ đoạn scam"

**Status:** ❌ Chưa có data (0 records)

---

### 5. `core_synonym` - Bảng Từ đồng nghĩa

**Là gì?** Lưu các từ đồng nghĩa để cải thiện tìm kiếm

**Dữ liệu:**
- Từ khóa gốc
- Từ đồng nghĩa

**Ví dụ:**
```
keyword: "mức phạt"
alias: "tiền phạt", "phạt", "xử phạt"
```

**Dùng để:** Khi user gõ "tiền phạt", hệ thống tự động tìm "mức phạt"

**Status:** ✅ Có data (18 records)

---

### 6. `core_auditlog` - Bảng Log

**Là gì?** Lưu log tất cả requests đến chatbot

**Dữ liệu:**
- Path (API endpoint)
- Query (câu hỏi của user)
- Intent (phân loại câu hỏi)
- Confidence (độ tin cậy)
- Latency (thời gian xử lý)
- Status code
- Timestamp

**Ví dụ:**
```
Query: "mức phạt vượt đèn đỏ"
Intent: "search_fine"
Confidence: 0.95
Latency: 120ms
```

**Dùng để:** 
- Phân tích hành vi người dùng
- Cải thiện chatbot
- Monitoring performance

**Status:** ✅ Có data (198 records)

---

### 7. `core_mlmetrics` - Bảng ML Metrics

**Là gì?** Lưu metrics tổng hợp hàng ngày về hiệu suất ML

**Dữ liệu:**
- Ngày
- Tổng số requests
- Độ chính xác intent
- Latency trung bình
- Tỷ lệ lỗi
- Breakdown theo intent

**Dùng để:**
- Dashboard monitoring
- Phân tích hiệu suất
- Báo cáo

**Status:** ⚠️ Bình thường (0 records - sẽ có sau khi có requests)

---

## 🔄 Luồng hoạt động

```
User hỏi: "Phạt bao nhiêu nếu vượt đèn đỏ?"
    ↓
Chatbot phân tích intent → "search_fine"
    ↓
Tìm kiếm trong core_fine → Tìm "Vượt đèn đỏ"
    ↓
Trả về kết quả cho user
    ↓
Log vào core_auditlog
```

## 📈 Tình trạng Data

| Table | Records | Mô tả | Status |
|-------|---------|-------|--------|
| `core_fine` | 20 | Mức phạt | ✅ Đủ để test |
| `core_office` | 12 | Địa chỉ | ✅ Đủ để test |
| `core_procedure` | 0 | Thủ tục | ❌ Cần thêm |
| `core_advisory` | 0 | Cảnh báo | ❌ Cần thêm |
| `core_synonym` | 18 | Từ đồng nghĩa | ✅ OK |
| `core_auditlog` | 198 | Log | ✅ Đang tích lũy |
| `core_mlmetrics` | 0 | Metrics | ⚠️ Sẽ có sau |

## 🎯 Tóm lại

**Database này là:**
- Kho dữ liệu cho chatbot Công an Thừa Thiên Huế
- Lưu trữ: mức phạt, thủ tục, địa chỉ, cảnh báo
- Hỗ trợ: tìm kiếm, phân loại intent, monitoring

**Các tables:**
- `core_fine`, `core_office` → Data chính (đã có)
- `core_procedure`, `core_advisory` → Data chính (chưa có)
- `core_synonym` → Hỗ trợ tìm kiếm
- `core_auditlog`, `core_mlmetrics` → Monitoring

---

**Đây là database backend cho chatbot, lưu trữ tất cả thông tin để chatbot trả lời câu hỏi! 🤖**

