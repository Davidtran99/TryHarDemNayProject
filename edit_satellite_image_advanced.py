#!/usr/bin/env python3
"""
Script nâng cấp: Tự động nhận diện và đặt labels chính xác bằng Computer Vision
Sử dụng OpenCV để phát hiện các annotation màu đỏ và tự động đặt labels
"""

from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2
import os
import sys

def detect_red_annotations(image_path):
    """
    Phát hiện các annotation màu đỏ trong ảnh bằng OpenCV
    Trả về danh sách các bounding boxes và loại annotation
    """
    # Đọc ảnh bằng OpenCV
    img_cv = cv2.imread(image_path)
    if img_cv is None:
        raise ValueError(f"Không thể đọc file: {image_path}")
    
    # Chuyển sang HSV để dễ phát hiện màu đỏ
    hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
    
    # Phạm vi màu đỏ trong HSV (2 phạm vi vì màu đỏ nằm ở cả 2 đầu của spectrum)
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 50, 50])
    upper_red2 = np.array([180, 255, 255])
    
    # Tạo mask cho màu đỏ
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = cv2.bitwise_or(mask1, mask2)
    
    # Làm mịn mask
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    # Tìm contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    annotations = []
    
    for contour in contours:
        # Lọc các contour quá nhỏ (nhiễu)
        area = cv2.contourArea(contour)
        if area < 50:  # Bỏ qua các vùng quá nhỏ
            continue
        
        # Lấy bounding box
        x, y, w, h = cv2.boundingRect(contour)
        
        # Phân loại annotation dựa trên hình dạng và kích thước
        aspect_ratio = w / h if h > 0 else 0
        annotation_type = classify_annotation(x, y, w, h, area, aspect_ratio, contour, img_cv.shape)
        
        if annotation_type:
            annotations.append({
                'bbox': (x, y, w, h),
                'center': (x + w//2, y + h//2),
                'type': annotation_type,
                'area': area
            })
    
    return annotations, mask

def classify_annotation(x, y, w, h, area, aspect_ratio, contour, img_shape):
    """
    Phân loại annotation dựa trên hình dạng, kích thước và vị trí
    """
    img_height, img_width = img_shape[:2]
    
    # Tính vị trí tương đối
    rel_x = x / img_width
    rel_y = y / img_height
    rel_center_x = (x + w/2) / img_width
    rel_center_y = (y + h/2) / img_height
    
    # Hồ lớn (hình chữ nhật lớn, ở upper-left-center)
    if area > 5000 and 0.15 < rel_x < 0.4 and 0.1 < rel_y < 0.4:
        if 0.8 < aspect_ratio < 1.5 or 0.6 < aspect_ratio < 1.2:
            return 'lake_large'
    
    # Hồ nhỏ (hình oval, ở right-center)
    if area > 2000 and 0.5 < rel_x < 0.85 and 0.2 < rel_y < 0.5:
        if 0.7 < aspect_ratio < 1.5:
            return 'lake_small'
    
    # Nhà ở giữa hồ lớn (hình chữ nhật nhỏ, ở giữa hồ lớn)
    if 500 < area < 3000 and 0.2 < rel_center_x < 0.4 and 0.15 < rel_center_y < 0.35:
        if 0.7 < aspect_ratio < 1.5:
            return 'house_center'
    
    # Cano ở hồ nhỏ (hình oval nhỏ, ở giữa hồ nhỏ)
    if 100 < area < 800 and 0.55 < rel_center_x < 0.75 and 0.25 < rel_center_y < 0.45:
        if 0.6 < aspect_ratio < 1.4:
            return 'canoe'
    
    # Nhà gỗ 1 (hình chữ nhật, giữa 2 hồ)
    if 300 < area < 2000 and 0.35 < rel_center_x < 0.5 and 0.3 < rel_center_y < 0.5:
        if 0.6 < aspect_ratio < 1.5:
            return 'house_wood1'
    
    # Nhà gỗ 2 (hình chữ L, giữa 2 hồ, bên phải hồ lớn)
    # Kiểm tra hình chữ L bằng cách phân tích contour
    if 300 < area < 2000 and 0.4 < rel_center_x < 0.55 and 0.35 < rel_center_y < 0.55:
        # Kiểm tra xem có phải hình L không (có góc vuông)
        approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
        if len(approx) >= 4:  # Có nhiều góc
            return 'house_wood2_L'
    
    # Cầu gỗ (đường thẳng dọc, far left)
    if area > 200 and 0.02 < rel_x < 0.15:
        if aspect_ratio < 0.3 or h > w * 3:  # Dọc
            return 'bridge_vertical'
    
    # Cổng gỗ (ở cuối cầu gỗ dọc, phía dưới)
    # Cùng vị trí x với cầu gỗ, nhưng ở cuối (y lớn hơn)
    if 200 < area < 2000 and 0.02 < rel_center_x < 0.18:
        # Ở cuối cầu gỗ (phía dưới), y từ 0.5 đến 0.85
        if 0.5 < rel_center_y < 0.85:
            # Có thể là hình chữ L hoặc hình chữ nhật
            approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
            # Nếu là hình chữ L (nhiều góc) hoặc hình chữ nhật (4 góc)
            if len(approx) >= 4:
                return 'gate'
    
    # Khu vực đất đắp cao (vùng sáng, bottom-center)
    if area > 1000 and 0.4 < rel_center_x < 0.6 and 0.65 < rel_center_y < 0.85:
        return 'park'
    
    return None

def detect_dotted_lines(image_path):
    """
    Phát hiện các đường chấm chấm (dotted lines) - cây thông
    """
    img_cv = cv2.imread(image_path)
    hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
    
    # Mask cho màu đỏ
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 50, 50])
    upper_red2 = np.array([180, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = cv2.bitwise_or(mask1, mask2)
    
    # Tìm các điểm đỏ nhỏ (dots)
    kernel = np.ones((2, 2), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    # Tìm contours của các dots
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Lọc các dots nhỏ (cây thông)
    dots = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if 10 < area < 200:  # Dots nhỏ
            x, y, w, h = cv2.boundingRect(contour)
            dots.append((x + w//2, y + h//2))
    
    # Tìm đường chấm chấm (dots gần nhau tạo thành đường)
    if len(dots) > 10:
        # Tính trung bình vị trí của các dots
        avg_x = sum(d[0] for d in dots) / len(dots)
        avg_y = sum(d[1] for d in dots) / len(dots)
        return (int(avg_x), int(avg_y))
    
    return None

def edit_satellite_image_advanced(input_path, output_path):
    """
    Chỉnh sửa ảnh vệ tinh với nhận diện tự động
    """
    print("🔍 Đang phân tích ảnh và phát hiện các annotation...")
    
    # Phát hiện các annotation màu đỏ
    annotations, mask = detect_red_annotations(input_path)
    
    print(f"✅ Đã phát hiện {len(annotations)} annotation(s)")
    
    # Phát hiện đường chấm chấm (cây thông)
    pine_location = detect_dotted_lines(input_path)
    
    # Mở ảnh bằng PIL để vẽ labels
    img = Image.open(input_path)
    draw = ImageDraw.Draw(img)
    
    # Load font
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        font_medium = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except:
        try:
            font_large = ImageFont.truetype("arial.ttf", 24)
            font_medium = ImageFont.truetype("arial.ttf", 18)
            font_small = ImageFont.truetype("arial.ttf", 14)
        except:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
    
    width, height = img.size
    
    # Màu sắc
    RED = (255, 0, 0)
    BLUE = (0, 0, 255)
    GREEN = (0, 255, 0)
    YELLOW = (255, 255, 0)
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    ORANGE = (255, 165, 0)
    
    def draw_label(draw, x, y, text, bg_color=WHITE, text_color=BLACK, font=font_medium):
        """Vẽ label với background và border"""
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        padding = 8
        rect_x1 = x - padding
        rect_y1 = y - padding
        rect_x2 = x + text_width + padding
        rect_y2 = y + text_height + padding
        
        draw.rectangle([rect_x1, rect_y1, rect_x2, rect_y2], fill=bg_color, outline=RED, width=2)
        draw.text((x, y), text, fill=text_color, font=font)
    
    # Mapping labels
    label_map = {
        'lake_large': ('HỒ LỚN\n(Hình chữ nhật)', YELLOW, BLACK, font_medium),
        'lake_small': ('HỒ NHỎ\n(Hình oval)', YELLOW, BLACK, font_medium),
        'house_center': ('NHÀ TRẮNG\n(Ở giữa hồ)', WHITE, BLACK, font_small),
        'canoe': ('CANO\n(Ở giữa hồ)', WHITE, BLACK, font_small),
        'house_wood1': ('NHÀ GỖ 1', GREEN, WHITE, font_medium),
        'house_wood2_L': ('NHÀ GỖ 2\n(Hình chữ L)', GREEN, WHITE, font_medium),
        'bridge_vertical': ('CẦU GỖ\n(Đường dọc)', BLUE, WHITE, font_medium),
        'gate': ('CỔNG GỖ\n(Có mái hoa giấy)', RED, WHITE, font_medium),
        'park': ('ĐẤT ĐẮP CAO\n(Park)', YELLOW, BLACK, font_medium),
    }
    
    # Tìm cầu gỗ để xác định vị trí cổng gỗ
    bridge_vertical = None
    for ann in annotations:
        if ann['type'] == 'bridge_vertical':
            bridge_vertical = ann
            break
    
    # Vẽ labels cho các annotation đã phát hiện
    detected_types = {}
    for ann in annotations:
        ann_type = ann['type']
        if ann_type and ann_type in label_map:
            # Tránh duplicate
            if ann_type not in detected_types:
                center_x, center_y = ann['center']
                text, bg_color, text_color, font = label_map[ann_type]
                
                # Điều chỉnh vị trí label để không che annotation
                label_x = center_x + 20
                label_y = center_y - 20
                
                # Đặc biệt cho cổng gỗ: đặt ở cuối cầu gỗ
                if ann_type == 'gate' and bridge_vertical:
                    # Cổng gỗ ở cuối (phía dưới) cầu gỗ
                    bridge_x, bridge_y, bridge_w, bridge_h = bridge_vertical['bbox']
                    # Cuối cầu gỗ là bottom của bounding box
                    gate_y = bridge_y + bridge_h
                    label_x = center_x + 20
                    label_y = gate_y + 10  # Đặt label ngay dưới cổng gỗ
                
                draw_label(draw, label_x, label_y, text, bg_color, text_color, font)
                detected_types[ann_type] = True
                
                print(f"  ✓ Đã đặt label: {ann_type} tại ({center_x}, {center_y})")
    
    # Vẽ label cho cây thông nếu phát hiện được
    if pine_location:
        pine_x, pine_y = pine_location
        draw_label(draw, pine_x + 20, pine_y - 20, 'CÂY THÔNG VÀNG\n(Dotted line)', 
                  GREEN, WHITE, font_small)
        print(f"  ✓ Đã đặt label: Cây thông tại ({pine_x}, {pine_y})")
    
    # Thêm label cảnh báo về hồ sẽ bị lấp
    for ann in annotations:
        if ann['type'] == 'lake_small':
            center_x, center_y = ann['center']
            draw_label(draw, center_x + 20, center_y + 30, '⚠️ HỒ NÀY\nSẼ BỊ LẤP', 
                      RED, WHITE, font_medium)
            break
    
    # Vẽ title
    title = "BẢN VẼ THIẾT KẾ - TỰ ĐỘNG NHẬN DIỆN"
    title_bbox = draw.textbbox((0, 0), title, font=font_large)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    draw_label(draw, title_x, 20, title, BLACK, WHITE, font_large)
    
    # Lưu ảnh
    img.save(output_path, quality=95)
    print(f"\n✅ Đã lưu ảnh đã chỉnh sửa tại: {output_path}")
    print(f"📏 Kích thước ảnh: {width}x{height} pixels")
    print(f"📊 Đã phát hiện và đặt {len(detected_types)} label(s)")

def main():
    """Hàm main"""
    if len(sys.argv) < 2:
        print("📖 Cách sử dụng:")
        print("  python edit_satellite_image_advanced.py <đường_dẫn_ảnh_gốc> [đường_dẫn_ảnh_output]")
        print("\nVí dụ:")
        print("  python edit_satellite_image_advanced.py satellite_image.png")
        return
    
    input_path = sys.argv[1]
    
    if not os.path.exists(input_path):
        print(f"❌ File không tồn tại: {input_path}")
        return
    
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        base_name = os.path.splitext(input_path)[0]
        ext = os.path.splitext(input_path)[1]
        output_path = f"{base_name}_auto_detected{ext}"
    
    try:
        edit_satellite_image_advanced(input_path, output_path)
        print("\n✨ Hoàn thành!")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

