# BÁO CÁO CHỨC NĂNG HỆ THỐNG
## Hệ thống Tra cứu Thông tin - Công an Tỉnh Thừa Thiên Huế

---

**Ngày báo cáo:** 13/11/2025  
**Phiên bản hệ thống:** 1.0  
**Trạng thái:** Đang vận hành

---

## 1. TỔNG QUAN HỆ THỐNG

Hệ thống Tra cứu Thông tin là nền tảng số hóa dịch vụ công, cung cấp giải pháp tra cứu thông tin toàn diện cho người dân và cán bộ công an tỉnh Thừa Thiên Huế. Hệ thống tích hợp công nghệ Machine Learning để cung cấp trải nghiệm tra cứu thông minh, nhanh chóng và chính xác.

### 1.1. Mục tiêu
- **Số hóa dịch vụ công:** Chuyển đổi các thủ tục tra cứu truyền thống sang môi trường số
- **Nâng cao trải nghiệm người dùng:** Cung cấp giao diện hiện đại, dễ sử dụng
- **Tăng hiệu quả:** Giảm thời gian tra cứu, tăng độ chính xác thông tin
- **Bảo mật cao:** Vận hành hoàn toàn nội bộ, không phụ thuộc dịch vụ bên ngoài

### 1.2. Đối tượng sử dụng
- **Người dân:** Tra cứu thủ tục, mức phạt, thông tin đơn vị
- **Cán bộ công an:** Hỗ trợ tư vấn, tra cứu nhanh trong quá trình làm việc

---

## 2. CÁC MODULE CHỨC NĂNG CHÍNH

### 2.1. Chatbot Tư vấn Thông minh

**Mô tả:** Hệ thống chatbot sử dụng công nghệ Machine Learning để hiểu và trả lời câu hỏi tự nhiên bằng tiếng Việt.

**Tính năng:**
- ✅ **Phân loại ý định tự động:** Nhận diện 6 loại câu hỏi (mức phạt, thủ tục, danh bạ, cảnh báo, chào hỏi, câu hỏi chung)
- ✅ **Tìm kiếm ngữ nghĩa:** Tìm kết quả phù hợp dựa trên ý nghĩa, không chỉ từ khóa
- ✅ **Xử lý tiếng Việt:** Hỗ trợ cả có dấu và không dấu ("mức phạt" = "muc phat")
- ✅ **Gợi ý câu hỏi:** Hiển thị các câu hỏi mẫu theo từng chủ đề
- ✅ **Hiển thị kết quả trực quan:** Trả về kết quả kèm link chi tiết, phân loại theo màu sắc

**Ví dụ sử dụng:**
- "Mức phạt vượt đèn đỏ là bao nhiêu?"
- "Thủ tục đăng ký cư trú cần giấy tờ gì?"
- "Địa chỉ công an phường ở đâu?"

**Lợi ích:**
- Người dùng không cần biết cấu trúc dữ liệu, chỉ cần hỏi tự nhiên
- Tiết kiệm thời gian tra cứu

---

### 2.2. Tra cứu Thủ tục Hành chính

**Mô tả:** Module tra cứu thông tin chi tiết về các thủ tục hành chính trong lĩnh vực công an.

**Thông tin cung cấp:**
- 📋 **Tên thủ tục:** Tên đầy đủ và chính xác
- 🏢 **Lĩnh vực:** ANTT, Cư trú, PCCC, Giao thông
- 📍 **Cấp độ:** Tỉnh, Huyện, Xã
- ✅ **Điều kiện:** Các điều kiện cần thiết để thực hiện thủ tục
- 📄 **Hồ sơ:** Danh sách giấy tờ cần chuẩn bị
- 💰 **Lệ phí:** Mức phí (nếu có)
- ⏱️ **Thời hạn:** Thời gian xử lý
- 🏛️ **Cơ quan thực hiện:** Đơn vị tiếp nhận
- 🔗 **Nguồn:** Link tham khảo chính thức

**Tính năng tìm kiếm:**
- Tìm kiếm theo từ khóa (tên, lĩnh vực, điều kiện)
- Lọc theo lĩnh vực (domain)
- Lọc theo cấp độ (level)
- Tìm kiếm thông minh với ML (hiểu ngữ nghĩa)

---

### 2.3. Tra cứu Mức phạt

**Mô tả:** Hệ thống tra cứu mức phạt vi phạm hành chính trong lĩnh vực công an và giao thông.

**Thông tin cung cấp:**
- 📝 **Tên hành vi:** Mô tả chi tiết hành vi vi phạm
- 🔢 **Mã vi phạm:** Mã số theo quy định
- 📜 **Điều/Khoản:** Tham chiếu điều luật
- 📋 **Nghị định:** Nghị định quy định
- 💵 **Mức phạt:** Phạm vi từ tối thiểu đến tối đa
- 🎯 **Điểm trừ:** Điểm trừ bằng lái (nếu có)
- 🔧 **Biện pháp khắc phục:** Các biện pháp bổ sung
- 🔗 **Nguồn:** Link tham khảo chính thức

**Tính năng tìm kiếm:**
- Tìm kiếm theo tên hành vi
- Tìm kiếm theo mã vi phạm
- Tìm kiếm theo điều luật
- Tìm kiếm thông minh với ML

---

### 2.4. Danh bạ Đơn vị

**Mô tả:** Tra cứu thông tin liên hệ và địa chỉ các đơn vị công an trong tỉnh.

**Thông tin cung cấp:**
- 🏢 **Tên đơn vị:** Tên đầy đủ đơn vị
- 📍 **Địa chỉ:** Địa chỉ chi tiết
- 🗺️ **Quận/Huyện:** Phân loại theo địa bàn
- ⏰ **Giờ làm việc:** Thời gian tiếp dân
- 📞 **Số điện thoại:** Hotline liên hệ
- 📧 **Email:** Địa chỉ email (nếu có)
- 🗺️ **Tọa độ:** Vĩ độ, kinh độ (hỗ trợ chỉ đường)
- 📋 **Phạm vi phục vụ:** Lĩnh vực công tác

**Tính năng tìm kiếm:**
- Tìm kiếm theo tên đơn vị
- Tìm kiếm theo địa chỉ
- Lọc theo quận/huyện
- Tìm kiếm thông minh với ML

---

### 2.5. Cảnh báo An ninh

**Mô tả:** Cung cấp thông tin cảnh báo về các thủ đoạn lừa đảo, scam mới nhất.

**Thông tin cung cấp:**
- ⚠️ **Tiêu đề:** Tên thủ đoạn lừa đảo
- 📄 **Tóm tắt:** Mô tả chi tiết thủ đoạn
- 📅 **Ngày đăng:** Thời gian cảnh báo
- 🔗 **Nguồn:** Link tham khảo chính thức

**Tính năng:**
- Hiển thị theo thời gian (mới nhất trước)
- Tìm kiếm theo từ khóa
- Tìm kiếm thông minh với ML

---

### 2.6. Tìm kiếm Thống nhất (Unified Search)

**Mô tả:** Tìm kiếm xuyên suốt tất cả các module trong một lần truy vấn.

**Tính năng:**
- 🔍 **Tìm kiếm đa module:** Tìm trong tất cả 4 loại dữ liệu (Thủ tục, Mức phạt, Đơn vị, Cảnh báo)
- 🎯 **Xếp hạng thông minh:** Kết quả được sắp xếp theo độ liên quan
- 🏷️ **Phân loại tự động:** Mỗi kết quả được gắn nhãn loại dữ liệu
- 📊 **Giới hạn kết quả:** Hiển thị tối đa 50 kết quả phù hợp nhất

**Lợi ích:**
- Người dùng không cần biết thông tin thuộc module nào
- Tiết kiệm thời gian, không cần tìm kiếm nhiều lần
- Kết quả được sắp xếp theo độ liên quan, dễ tìm thấy thông tin cần thiết

---

## 3. TÍNH NĂNG NỔI BẬT

### 3.1. Công nghệ Machine Learning

**Intent Classification (Phân loại ý định):**
- Tự động nhận diện loại câu hỏi của người dùng
- Độ chính xác: ~85%
- Hỗ trợ 6 loại ý định khác nhau

---

## 4. KIẾN TRÚC HỆ THỐNG

### 4.1. Frontend (Giao diện Người dùng)

**Công nghệ:**
- React 18+ (Framework JavaScript)
- Vite (Build tool hiện đại)
- Ant Design (UI Component Library)
- React Router (Điều hướng)

**Tính năng:**
- Single Page Application (SPA)
- Client-side routing
- API integration
- Responsive design

### 4.2. Backend (Hệ thống Xử lý)

**Công nghệ:**
- Django 4+ (Python Web Framework)
- Django REST Framework (API)
- PostgreSQL (Database)
- scikit-learn (Machine Learning)

**Tính năng:**
- RESTful API
- ML model integration
- Database ORM
- Authentication & Authorization

### 4.3. Database (Cơ sở Dữ liệu)

**Cấu trúc:**
- **Procedure:** Thủ tục hành chính
- **Fine:** Mức phạt
- **Office:** Đơn vị công an
- **Advisory:** Cảnh báo an ninh
- **Synonym:** Từ đồng nghĩa (hỗ trợ tìm kiếm)
- **AuditLog:** Nhật ký truy cập

---

## 6. THỐNG KÊ HỆ THỐNG

| Chỉ số | Giá trị |
|--------|---------|
| Số module chức năng | 6 module |
| Loại dữ liệu tra cứu | 4 loại (Thủ tục, Mức phạt, Đơn vị, Cảnh báo) |
| Độ chính xác ML | ~85% |
| Thời gian phản hồi | <500ms |
| Hỗ trợ ngôn ngữ | Tiếng Việt (có/không dấu) |
| Loại ý định chatbot | 6 loại |
| Giao diện | Responsive (Mobile, Tablet, Desktop) |

---

## 7. KẾT LUẬN

Hệ thống Tra cứu Thông tin - Công an Tỉnh Thừa Thiên Huế là một giải pháp số hóa dịch vụ công hiện đại, tích hợp công nghệ Machine Learning để cung cấp trải nghiệm tra cứu thông minh và tiện lợi.

**Điểm mạnh:**
- ✅ Công nghệ hiện đại, áp dụng ML cho tìm kiếm thông minh
- ✅ Giao diện thân thiện, dễ sử dụng
- ✅ Bảo mật cao, vận hành nội bộ
- ✅ Đầy đủ chức năng tra cứu cần thiết
- ✅ Hiệu suất tốt, phản hồi nhanh

**Hướng phát triển:**
- Mở rộng dữ liệu tra cứu
- Nâng cao độ chính xác ML model
- Bổ sung tính năng phân tích, thống kê
- Tối ưu hóa hiệu suất hệ thống

---

**Người lập báo cáo:** Hệ thống  
**Ngày:** 13/11/2025  
**Phiên bản:** 1.0

