# Hướng Dẫn Chỉnh Sửa Ảnh Vệ Tinh

## 📋 Yêu Cầu

Script này sử dụng thư viện **Pillow (PIL)** để chỉnh sửa ảnh.

## 🔧 Cài Đặt

### Cách 1: Cài đặt Pillow
```bash
pip install Pillow
```

### Cách 2: Nếu đã có virtual environment
```bash
cd /Users/davidtran/Downloads/TryHarDemNayProject
pip install Pillow
```

## 🚀 Sử Dụng

### Bước 1: Đặt ảnh vệ tinh vào thư mục project
- Đặt file ảnh (PNG, JPG, JPEG) vào thư mục gốc của project
- Ví dụ: `satellite_image.png`

### Bước 2: Chạy script
```bash
python edit_satellite_image.py satellite_image.png
```

Hoặc chỉ định tên file output:
```bash
python edit_satellite_image.py satellite_image.png output_annotated.png
```

### Bước 3: Điều chỉnh tọa độ (QUAN TRỌNG)

Script sẽ tự động thêm labels, nhưng bạn **CẦN điều chỉnh tọa độ** trong file `edit_satellite_image.py` để labels khớp với vị trí thực tế trong ảnh của bạn.

**Cách điều chỉnh:**

1. Mở file `edit_satellite_image.py`
2. Tìm phần `# ĐIỀU CHỈNH TỌA ĐỘ TẠI ĐÂY`
3. Điều chỉnh các giá trị `x` và `y` cho từng yếu tố:
   - `lake_large_x`, `lake_large_y` - Vị trí label cho hồ lớn
   - `lake_small_x`, `lake_small_y` - Vị trí label cho hồ nhỏ
   - `house_wood1_x`, `house_wood1_y` - Vị trí label cho nhà gỗ 1
   - `house_wood2_x`, `house_wood2_y` - Vị trí label cho nhà gỗ 2 (hình chữ L)
   - `bridge_x`, `bridge_y` - Vị trí label cho cầu gỗ
   - `gate_x`, `gate_y` - Vị trí label cho cổng gỗ
   - Và các yếu tố khác...

**Công thức tính tọa độ:**
- Tọa độ tính từ góc trên-trái (0, 0)
- `x` tăng từ trái sang phải
- `y` tăng từ trên xuống dưới
- Ví dụ: `width * 0.5` = giữa chiều ngang, `height * 0.3` = 30% từ trên xuống

**Cách xác định tọa độ chính xác:**
1. Mở ảnh gốc trong một editor ảnh (Photoshop, GIMP, hoặc Preview trên Mac)
2. Di chuột vào vị trí cần đặt label, xem tọa độ (thường hiển thị ở góc dưới)
3. Ghi lại tọa độ và cập nhật vào script

## 📝 Các Labels Sẽ Được Thêm

Script sẽ tự động thêm các labels sau:

1. **HỒ LỚN** (màu vàng) - Hình chữ nhật
2. **HỒ NHỎ** (màu vàng) - Hình oval
3. **NHÀ TRẮNG** (màu trắng) - Ở giữa hồ lớn
4. **CANO** (màu trắng) - Ở giữa hồ nhỏ
5. **NHÀ GỖ 1** (màu xanh lá) - Nhà gỗ thứ nhất
6. **NHÀ GỖ 2** (màu xanh lá) - Nhà gỗ hình chữ L
7. **CẦU GỖ** (màu xanh dương) - Đường dọc
8. **CỔNG GỖ** (màu đỏ) - Có mái hoa giấy
9. **ĐẤT ĐẮP CAO** (màu vàng) - Park
10. **CÂY THÔNG VÀNG** (màu xanh lá) - Dotted line

## 🎨 Tùy Chỉnh

Bạn có thể tùy chỉnh:
- **Màu sắc:** Thay đổi các biến `RED`, `BLUE`, `GREEN`, `YELLOW`, `WHITE`, `BLACK`
- **Font size:** Thay đổi kích thước trong `ImageFont.truetype(..., size)`
- **Vị trí labels:** Điều chỉnh tọa độ `x`, `y`
- **Thêm mũi tên:** Bỏ comment các dòng `draw_arrow()` và điều chỉnh tọa độ

## ⚠️ Lưu Ý

1. **Tọa độ:** Script sử dụng tọa độ tương đối (%), bạn có thể thay đổi thành tọa độ tuyệt đối (pixel) nếu biết chính xác
2. **Font:** Script sẽ thử load font hệ thống, nếu không có sẽ dùng font mặc định
3. **Chất lượng:** Ảnh output được lưu với quality=95 để giữ chất lượng tốt

## 🐛 Xử Lý Lỗi

### Lỗi: "No module named 'PIL'"
```bash
pip install Pillow
```

### Lỗi: "File not found"
- Kiểm tra đường dẫn file ảnh
- Đảm bảo file ảnh tồn tại trong thư mục

### Labels không khớp vị trí
- Điều chỉnh tọa độ trong script
- Hoặc mở ảnh trong editor và xem tọa độ chính xác

## 📞 Hỗ Trợ

Nếu gặp vấn đề, vui lòng:
1. Kiểm tra lại đường dẫn file
2. Đảm bảo đã cài đặt Pillow
3. Kiểm tra tọa độ trong script

