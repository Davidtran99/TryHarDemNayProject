# Danh Sách Công Cụ Web Để Tạo Labels

## 🎯 Công Cụ Tự Tạo (Trong Project)

### ✅ `image_label_tool.html` - Công Cụ Của Bạn

**Cách sử dụng:**
1. Mở file `image_label_tool.html` trong trình duyệt
2. Click "Chọn Ảnh" để upload ảnh vệ tinh
3. Nhập tên label, click "Thêm Label", sau đó click vào vị trí trên ảnh
4. Kéo thả label đến vị trí mong muốn
5. Click "Xuất Tọa Độ" để lấy code Python
6. Copy code và paste vào script Python

**Ưu điểm:**
- ✅ Hoàn toàn miễn phí
- ✅ Không cần đăng ký
- ✅ Dữ liệu không rời khỏi máy tính
- ✅ Xuất code Python trực tiếp
- ✅ Tải ảnh có labels

**Mở file:**
```bash
# Mở trong trình duyệt
open image_label_tool.html
# hoặc
python3 -m http.server 8000
# Sau đó mở: http://localhost:8000/image_label_tool.html
```

---

## 🌐 Công Cụ Online (Khuyến Nghị)

### 1. **Annotely** ⭐⭐⭐⭐⭐
- **URL:** https://annotely.com/
- **Tính năng:**
  - Kéo thả labels
  - Vẽ tự do
  - Thêm text, mũi tên
  - Xuất ảnh
- **Ưu điểm:** Đơn giản, dễ dùng
- **Nhược điểm:** Cần internet

### 2. **VIA (VGG Image Annotator)** ⭐⭐⭐⭐⭐
- **URL:** https://www.robots.ox.ac.uk/~vgg/software/via/
- **Tính năng:**
  - Chạy trực tiếp trên trình duyệt
  - Hỗ trợ nhiều loại annotation
  - Xuất JSON, CSV
- **Ưu điểm:** Mạnh mẽ, chuyên nghiệp
- **Nhược điểm:** Hơi phức tạp

### 3. **PixLab Annotate** ⭐⭐⭐⭐
- **URL:** https://pixlab.io/annotate
- **Tính năng:**
  - Annotation cho ML
  - Segmentation
  - Bounding boxes
- **Ưu điểm:** Phù hợp cho ML
- **Nhược điểm:** Cần đăng ký (miễn phí)

### 4. **Anota** ⭐⭐⭐⭐
- **URL:** https://useanota.com/
- **Tính năng:**
  - Không cần đăng nhập
  - Kéo thả ảnh
  - Chú thích nhanh
- **Ưu điểm:** Nhanh, đơn giản
- **Nhược điểm:** Tính năng hạn chế

### 5. **LabelMe** ⭐⭐⭐⭐
- **URL:** http://labelme.csail.mit.edu/Release3.0/
- **Tính năng:**
  - Annotation chuyên nghiệp
  - Hỗ trợ nhiều format
  - Có thể chạy local
- **Ưu điểm:** Rất mạnh mẽ
- **Nhược điểm:** Cần cài đặt (có web version)

### 6. **Fotor** ⭐⭐⭐
- **URL:** https://www.fotor.com/features/annotate-image/
- **Tính năng:**
  - Thêm text, mũi tên
  - Hình dạng
  - Làm nổi bật
- **Ưu điểm:** Dễ dùng
- **Nhược điểm:** Tính năng annotation hạn chế

### 7. **Zillin** ⭐⭐⭐⭐
- **URL:** https://zillin.io/
- **Tính năng:**
  - Tạo dataset cho ML
  - Annotation chuyên nghiệp
  - Mã hóa end-to-end
- **Ưu điểm:** Bảo mật cao
- **Nhược điểm:** Cần đăng ký

### 8. **CVAT (Computer Vision Annotation Tool)** ⭐⭐⭐⭐⭐
- **URL:** https://cvat.org/
- **Tính năng:**
  - Rất mạnh mẽ
  - Hỗ trợ video
  - Team collaboration
- **Ưu điểm:** Chuyên nghiệp nhất
- **Nhược điểm:** Phức tạp, cần server

---

## 📊 So Sánh Nhanh

| Công Cụ | Miễn Phí | Đăng Ký | Offline | Xuất Code | Độ Khó |
|---------|----------|---------|---------|-----------|--------|
| **image_label_tool.html** | ✅ | ❌ | ✅ | ✅ Python | ⭐ Dễ |
| **Annotely** | ✅ | ❌ | ❌ | ❌ | ⭐ Dễ |
| **VIA** | ✅ | ❌ | ✅ | ✅ JSON | ⭐⭐ Trung bình |
| **PixLab** | ✅ | ✅ | ❌ | ✅ | ⭐⭐ Trung bình |
| **Anota** | ✅ | ❌ | ❌ | ❌ | ⭐ Dễ |
| **LabelMe** | ✅ | ❌ | ✅ | ✅ | ⭐⭐⭐ Khó |
| **CVAT** | ✅ | ✅ | ❌ | ✅ | ⭐⭐⭐⭐ Rất khó |

---

## 🎯 Khuyến Nghị

### Cho Dự Án Của Bạn:

1. **Sử dụng `image_label_tool.html`** (trong project)
   - ✅ Phù hợp nhất
   - ✅ Xuất code Python trực tiếp
   - ✅ Không cần internet
   - ✅ Dữ liệu an toàn

2. **Nếu cần tính năng nâng cao:**
   - **VIA** - Cho annotation phức tạp
   - **LabelMe** - Cho dataset lớn
   - **CVAT** - Cho team collaboration

3. **Nếu cần nhanh chóng:**
   - **Annotely** - Đơn giản nhất
   - **Anota** - Không cần đăng ký

---

## 🚀 Cách Sử Dụng Tool Của Bạn

### Bước 1: Mở Tool
```bash
# Cách 1: Mở trực tiếp
open image_label_tool.html

# Cách 2: Dùng local server
python3 -m http.server 8000
# Mở: http://localhost:8000/image_label_tool.html
```

### Bước 2: Upload Ảnh
- Click "Chọn Ảnh"
- Chọn file ảnh vệ tinh

### Bước 3: Tạo Labels
- Nhập tên label (ví dụ: "HỒ LỚN")
- Click "Thêm Label"
- Click vào vị trí trên ảnh
- Kéo thả để di chuyển

### Bước 4: Xuất Code
- Click "Xuất Tọa Độ"
- Copy code Python
- Paste vào script Python

### Bước 5: Tải Ảnh (Tùy chọn)
- Click "Tải Ảnh Có Labels"
- Ảnh sẽ được tải về với tất cả labels

---

## 💡 Tips

1. **Sử dụng tool của bạn** cho công việc hàng ngày
2. **Sử dụng VIA** nếu cần annotation phức tạp
3. **Sử dụng CVAT** nếu làm việc nhóm
4. **Backup labels** bằng cách xuất code Python

---

## 📝 Lưu Ý

- Tool của bạn lưu tọa độ **tương đối** (theo % width/height)
- Code xuất ra có thể paste trực tiếp vào script Python
- Labels có thể kéo thả để điều chỉnh vị trí
- Có thể xóa từng label hoặc xóa tất cả

