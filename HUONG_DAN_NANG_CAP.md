# Hướng Dẫn Nâng Cấp Model Nhận Diện Ảnh Vệ Tinh

## 🎯 Vấn Đề

Model hiện tại:
- ❌ Chưa nhận diện chính xác các yếu tố trong ảnh
- ❌ Vị trí labels quá khác biệt so với mô tả trong prompt
- ❌ Phải điều chỉnh tọa độ thủ công

## ✨ Giải Pháp Nâng Cấp

### 1. **Script Nâng Cấp: `edit_satellite_image_advanced.py`**

Script mới sử dụng **Computer Vision** để:
- ✅ **Tự động phát hiện** các annotation màu đỏ trong ảnh
- ✅ **Phân loại** các yếu tố dựa trên hình dạng, kích thước, vị trí
- ✅ **Đặt labels chính xác** tại vị trí thực tế của các annotation
- ✅ **Không cần điều chỉnh tọa độ thủ công**

### 2. **Công Nghệ Sử Dụng**

#### OpenCV (Computer Vision)
- **Phát hiện màu đỏ**: Sử dụng HSV color space để phát hiện các annotation màu đỏ
- **Contour Detection**: Tìm các hình dạng trong ảnh
- **Shape Classification**: Phân loại dựa trên aspect ratio, area, vị trí

#### Phân Loại Thông Minh
Script tự động phân loại các yếu tố dựa trên:
- **Hình dạng** (aspect ratio)
- **Kích thước** (area)
- **Vị trí tương đối** (relative position)
- **Đặc điểm hình học** (contour analysis)

## 📦 Cài Đặt

### Bước 1: Cài đặt thư viện

```bash
pip install opencv-python numpy Pillow
```

Hoặc cài từ file requirements:
```bash
pip install -r requirements_image_processing.txt
```

### Bước 2: Chạy script nâng cấp

```bash
python3 edit_satellite_image_advanced.py "Screenshot 2025-11-15 at 13.20.27.png"
```

## 🔍 Cách Hoạt Động

### 1. Phát Hiện Annotation Màu Đỏ
- Chuyển ảnh sang HSV color space
- Tạo mask cho màu đỏ (2 phạm vi: 0-10 và 170-180 độ)
- Tìm contours của các vùng màu đỏ

### 2. Phân Loại Annotation
Script phân loại dựa trên:

| Yếu Tố | Đặc Điểm Nhận Diện |
|--------|-------------------|
| **Hồ lớn** | Area > 5000, upper-left-center, aspect ratio 0.8-1.5 |
| **Hồ nhỏ** | Area > 2000, right-center, aspect ratio 0.7-1.5 |
| **Nhà giữa hồ** | Area 500-3000, ở giữa hồ lớn |
| **Cano** | Area 100-800, hình oval, ở giữa hồ nhỏ |
| **Nhà gỗ 1** | Area 300-2000, hình chữ nhật, giữa 2 hồ |
| **Nhà gỗ 2 (L)** | Area 300-2000, hình chữ L (nhiều góc), giữa 2 hồ |
| **Cầu gỗ** | Area > 200, far left, aspect ratio < 0.3 (dọc) |
| **Cổng gỗ** | Area 200-1500, hình chữ L, gần cầu gỗ |
| **Đất đắp cao** | Area > 1000, bottom-center |

### 3. Đặt Labels Tự Động
- Labels được đặt tại vị trí center của annotation
- Tự động offset để không che annotation
- Màu sắc và font phù hợp với từng loại

## 🎨 So Sánh 2 Phiên Bản

| Tính Năng | Script Cũ | Script Mới |
|-----------|-----------|------------|
| **Nhận diện** | Thủ công (tọa độ cố định) | ✅ Tự động (CV) |
| **Độ chính xác** | Phụ thuộc tọa độ | ✅ Dựa trên annotation thực tế |
| **Điều chỉnh** | Phải sửa code | ✅ Tự động |
| **Phát hiện** | Không | ✅ Tự động phát hiện annotation |
| **Phân loại** | Không | ✅ Phân loại thông minh |

## 🚀 Nâng Cấp Thêm (Tùy Chọn)

### 1. **YOLOv8 (Object Detection)**
Nếu muốn nhận diện chính xác hơn, có thể tích hợp YOLOv8:

```bash
pip install ultralytics
```

**Ưu điểm:**
- Nhận diện chính xác hơn
- Có thể train trên dữ liệu riêng
- Phát hiện nhiều loại đối tượng

**Nhược điểm:**
- Cần GPU để chạy nhanh
- Cần dữ liệu training

### 2. **SAM (Segment Anything Model)**
Meta's Segment Anything Model cho segmentation chính xác:

```bash
pip install segment-anything
```

**Ưu điểm:**
- Segmentation rất chính xác
- Không cần training

**Nhược điểm:**
- Model lớn (~2.4GB)
- Cần GPU

### 3. **Template Matching**
Để phát hiện các annotation giống nhau:

```python
import cv2
result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
```

## 📝 Tùy Chỉnh

### Điều Chỉnh Ngưỡng Phát Hiện

Trong file `edit_satellite_image_advanced.py`, bạn có thể điều chỉnh:

1. **Ngưỡng màu đỏ** (dòng ~30-35):
```python
lower_red1 = np.array([0, 50, 50])  # Điều chỉnh để phát hiện đỏ tốt hơn
upper_red1 = np.array([10, 255, 255])
```

2. **Ngưỡng area** (trong hàm `classify_annotation`):
```python
if area > 5000:  # Điều chỉnh ngưỡng area
```

3. **Vị trí tương đối** (trong hàm `classify_annotation`):
```python
if 0.15 < rel_x < 0.4:  # Điều chỉnh vị trí
```

## 🐛 Xử Lý Lỗi

### Lỗi: "Không phát hiện được annotation"
- Kiểm tra màu đỏ trong ảnh có đúng không
- Điều chỉnh ngưỡng HSV
- Kiểm tra ảnh có đủ độ phân giải không

### Lỗi: "Labels đặt sai vị trí"
- Điều chỉnh offset trong hàm `draw_label`
- Kiểm tra logic phân loại trong `classify_annotation`

### Lỗi: "Phát hiện nhầm"
- Điều chỉnh các ngưỡng area, aspect ratio
- Thêm điều kiện phân loại cụ thể hơn

## 📊 Kết Quả

Sau khi chạy script nâng cấp:
- ✅ Labels được đặt **chính xác** tại vị trí annotation
- ✅ **Không cần** điều chỉnh tọa độ thủ công
- ✅ **Tự động phát hiện** tất cả các yếu tố
- ✅ **Phân loại thông minh** dựa trên đặc điểm

## 🔄 So Sánh Kết Quả

**Script cũ:**
- Labels ở vị trí ước tính
- Phải điều chỉnh thủ công
- Không chính xác

**Script mới:**
- Labels ở vị trí thực tế của annotation
- Tự động hoàn toàn
- Chính xác cao

## 💡 Tips

1. **Test với ảnh khác**: Script có thể cần điều chỉnh ngưỡng cho ảnh khác
2. **Kiểm tra mask**: Có thể lưu mask để debug:
```python
cv2.imwrite('mask.png', mask)
```
3. **Visualize contours**: Vẽ contours để xem phát hiện:
```python
cv2.drawContours(img_cv, contours, -1, (0, 255, 0), 2)
```

## 📞 Hỗ Trợ

Nếu gặp vấn đề:
1. Kiểm tra OpenCV đã được cài đặt
2. Kiểm tra ảnh có annotation màu đỏ rõ ràng
3. Điều chỉnh ngưỡng phát hiện
4. Xem log output để debug

