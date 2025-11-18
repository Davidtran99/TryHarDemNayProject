#!/usr/bin/env python3
"""
Script để chỉnh sửa hình ảnh vệ tinh - thêm labels, annotations, và chú thích
"""

from PIL import Image, ImageDraw, ImageFont
import os
import sys

def edit_satellite_image(input_path, output_path):
    """
    Chỉnh sửa hình ảnh vệ tinh với các annotations và labels
    
    Args:
        input_path: Đường dẫn đến ảnh gốc
        output_path: Đường dẫn lưu ảnh đã chỉnh sửa
    """
    try:
        # Mở ảnh
        img = Image.open(input_path)
        draw = ImageDraw.Draw(img)
        
        # Thử load font, nếu không có thì dùng font mặc định
        try:
            # Font cho tiếng Việt (cần font hỗ trợ Unicode)
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
        
        print("📝 Đang thêm labels và annotations vào ảnh...")
        print("⚠️  Lưu ý: Bạn cần điều chỉnh tọa độ (x, y) dựa trên vị trí thực tế trong ảnh của bạn")
        print("\nCác yếu tố sẽ được thêm:")
        print("1. Labels cho 2 hồ nước")
        print("2. Labels cho nhà gỗ (2 nhà, 1 nhà chữ L)")
        print("3. Labels cho cầu gỗ và cổng gỗ")
        print("4. Labels cho các yếu tố khác")
        print("\n💡 Bạn có thể chỉnh sửa tọa độ trong script này")
        
        # ============================================
        # ĐIỀU CHỈNH TỌA ĐỘ TẠI ĐÂY
        # ============================================
        # Tọa độ được tính theo pixel từ góc trên-trái (0,0)
        # Bạn cần xem ảnh và điều chỉnh các giá trị này
        
        # Hồ lớn (upper-left-center)
        lake_large_x = width * 0.3
        lake_large_y = height * 0.25
        lake_large_label = "HỒ LỚN\n(Hình chữ nhật)"
        
        # Hồ nhỏ (right-center)
        lake_small_x = width * 0.65
        lake_small_y = height * 0.35
        lake_small_label = "HỒ NHỎ\n(Hình oval)"
        
        # Nhà ở giữa hồ lớn (center of left lake)
        house_center_x = width * 0.3
        house_center_y = height * 0.25
        house_center_label = "NHÀ TRẮNG\n(Ở giữa hồ)"
        
        # Cano ở hồ nhỏ (center of right lake)
        canoe_x = width * 0.65
        canoe_y = height * 0.35
        canoe_label = "CANO\n(Ở giữa hồ)"
        
        # Nhà gỗ 1 (hình chữ nhật) - giữa 2 hồ, gần hồ lớn
        house_wood1_x = width * 0.4
        house_wood1_y = height * 0.35
        house_wood1_label = "NHÀ GỖ 1"
        
        # Nhà gỗ 2 (hình chữ L) - giữa 2 hồ, bên phải hồ lớn
        house_wood2_x = width * 0.45
        house_wood2_y = height * 0.4
        house_wood2_label = "NHÀ GỖ 2\n(Hình chữ L)"
        
        # Cầu gỗ riêng biệt (đường dọc) - far left, vertical
        bridge_x = width * 0.08
        bridge_y = height * 0.5
        bridge_label = "CẦU GỖ\n(Đường dọc)"
        
        # Cổng gỗ - ở lối vào cầu gỗ (vị trí đã được chỉ định)
        gate_x = width * 0.12
        gate_y = height * 0.55
        gate_label = "CỔNG GỖ\n(Có mái hoa giấy)"
        
        # Khu vực đất đắp cao (bottom-center)
        park_x = width * 0.5
        park_y = height * 0.75
        park_label = "ĐẤT ĐẮP CAO\n(Park)"
        
        # Ghi chú: Hồ sẽ bị lấp (hồ nhỏ)
        lake_fill_note_x = width * 0.65
        lake_fill_note_y = height * 0.45
        lake_fill_note_label = "⚠️ HỒ NÀY\nSẼ BỊ LẤP"
        
        # Cây thông (dotted line) - dọc theo bờ đê
        pine_x = width * 0.35
        pine_y = height * 0.2
        pine_label = "CÂY THÔNG VÀNG\n(Dotted line)"
        
        # ============================================
        # VẼ LABELS VÀ ANNOTATIONS
        # ============================================
        
        def draw_label(draw, x, y, text, bg_color=WHITE, text_color=BLACK, font=font_medium):
            """Vẽ label với background và border"""
            # Tính kích thước text
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Vẽ background với padding
            padding = 8
            rect_x1 = x - padding
            rect_y1 = y - padding
            rect_x2 = x + text_width + padding
            rect_y2 = y + text_height + padding
            
            # Vẽ background
            draw.rectangle([rect_x1, rect_y1, rect_x2, rect_y2], fill=bg_color, outline=RED, width=2)
            
            # Vẽ text
            draw.text((x, y), text, fill=text_color, font=font)
        
        def draw_arrow(draw, x1, y1, x2, y2, color=RED, width=3):
            """Vẽ mũi tên từ (x1,y1) đến (x2,y2)"""
            draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
            # Vẽ đầu mũi tên (đơn giản)
            arrow_size = 10
            if abs(x2 - x1) > abs(y2 - y1):  # Mũi tên ngang
                if x2 > x1:
                    draw.polygon([(x2, y2), (x2 - arrow_size, y2 - arrow_size//2), 
                                 (x2 - arrow_size, y2 + arrow_size//2)], fill=color)
                else:
                    draw.polygon([(x2, y2), (x2 + arrow_size, y2 - arrow_size//2), 
                                 (x2 + arrow_size, y2 + arrow_size//2)], fill=color)
            else:  # Mũi tên dọc
                if y2 > y1:
                    draw.polygon([(x2, y2), (x2 - arrow_size//2, y2 - arrow_size), 
                                 (x2 + arrow_size//2, y2 - arrow_size)], fill=color)
                else:
                    draw.polygon([(x2, y2), (x2 - arrow_size//2, y2 + arrow_size), 
                                 (x2 + arrow_size//2, y2 + arrow_size)], fill=color)
        
        # Vẽ labels cho các yếu tố
        draw_label(draw, int(lake_large_x), int(lake_large_y), lake_large_label, 
                  bg_color=YELLOW, text_color=BLACK, font=font_medium)
        
        draw_label(draw, int(lake_small_x), int(lake_small_y), lake_small_label, 
                  bg_color=YELLOW, text_color=BLACK, font=font_medium)
        
        draw_label(draw, int(house_center_x), int(house_center_y), house_center_label, 
                  bg_color=WHITE, text_color=BLACK, font=font_small)
        
        draw_label(draw, int(canoe_x), int(canoe_y), canoe_label, 
                  bg_color=WHITE, text_color=BLACK, font=font_small)
        
        draw_label(draw, int(house_wood1_x), int(house_wood1_y), house_wood1_label, 
                  bg_color=GREEN, text_color=WHITE, font=font_medium)
        
        draw_label(draw, int(house_wood2_x), int(house_wood2_y), house_wood2_label, 
                  bg_color=GREEN, text_color=WHITE, font=font_medium)
        
        draw_label(draw, int(bridge_x), int(bridge_y), bridge_label, 
                  bg_color=BLUE, text_color=WHITE, font=font_medium)
        
        draw_label(draw, int(gate_x), int(gate_y), gate_label, 
                  bg_color=RED, text_color=WHITE, font=font_medium)
        
        draw_label(draw, int(park_x), int(park_y), park_label, 
                  bg_color=YELLOW, text_color=BLACK, font=font_medium)
        
        draw_label(draw, int(pine_x), int(pine_y), pine_label, 
                  bg_color=GREEN, text_color=WHITE, font=font_small)
        
        # Vẽ label cảnh báo về hồ sẽ bị lấp
        draw_label(draw, int(lake_fill_note_x), int(lake_fill_note_y), lake_fill_note_label, 
                  bg_color=RED, text_color=WHITE, font=font_medium)
        
        # Vẽ mũi tên chỉ vào các yếu tố (nếu cần)
        # Ví dụ: mũi tên từ label đến vị trí thực tế
        # draw_arrow(draw, int(lake_large_x), int(lake_large_y), 
        #           int(lake_large_x - 50), int(lake_large_y - 50), color=RED)
        
        # Vẽ title
        title = "BẢN VẼ THIẾT KẾ - PHÂN TÍCH HÌNH ẢNH VỆ TINH"
        title_bbox = draw.textbbox((0, 0), title, font=font_large)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (width - title_width) // 2
        draw_label(draw, int(title_x), 20, title, 
                  bg_color=BLACK, text_color=WHITE, font=font_large)
        
        # Lưu ảnh
        img.save(output_path, quality=95)
        print(f"\n✅ Đã lưu ảnh đã chỉnh sửa tại: {output_path}")
        print(f"📏 Kích thước ảnh: {width}x{height} pixels")
        
    except FileNotFoundError:
        print(f"❌ Không tìm thấy file: {input_path}")
        print("💡 Vui lòng đảm bảo file ảnh tồn tại trong thư mục")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Hàm main"""
    if len(sys.argv) < 2:
        print("📖 Cách sử dụng:")
        print("  python edit_satellite_image.py <đường_dẫn_ảnh_gốc> [đường_dẫn_ảnh_output]")
        print("\nVí dụ:")
        print("  python edit_satellite_image.py satellite_image.png")
        print("  python edit_satellite_image.py satellite_image.png output_annotated.png")
        print("\n💡 Nếu không chỉ định output, file sẽ được lưu với tên: <tên_file>_annotated.png")
        return
    
    input_path = sys.argv[1]
    
    if not os.path.exists(input_path):
        print(f"❌ File không tồn tại: {input_path}")
        return
    
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        # Tạo tên file output tự động
        base_name = os.path.splitext(input_path)[0]
        ext = os.path.splitext(input_path)[1]
        output_path = f"{base_name}_annotated{ext}"
    
    edit_satellite_image(input_path, output_path)
    print("\n✨ Hoàn thành! Bạn có thể mở file để xem kết quả.")
    print("⚠️  Lưu ý: Có thể cần điều chỉnh tọa độ trong script để labels khớp với vị trí thực tế trong ảnh của bạn.")

if __name__ == "__main__":
    main()

