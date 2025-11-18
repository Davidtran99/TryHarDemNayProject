#!/usr/bin/env python3
"""
Script helper để lấy tọa độ từ ảnh khi click chuột
"""

from PIL import Image, ImageDraw, ImageTk
import tkinter as tk
import sys

def get_coordinates_from_image(image_path):
    """
    Mở ảnh và cho phép click để lấy tọa độ
    """
    # Mở ảnh
    img = Image.open(image_path)
    width, height = img.size
    
    # Tạo window
    root = tk.Tk()
    root.title("Click vào ảnh để lấy tọa độ - Nhấn ESC để thoát")
    
    # Resize ảnh nếu quá lớn
    max_width = 1200
    max_height = 800
    if width > max_width or height > max_height:
        ratio = min(max_width/width, max_height/height)
        new_width = int(width * ratio)
        new_height = int(height * ratio)
        img_display = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        scale_x = width / new_width
        scale_y = height / new_height
    else:
        img_display = img
        scale_x = 1
        scale_y = 1
    
    # Convert để hiển thị
    photo = ImageTk.PhotoImage(img_display)
    
    # Label để hiển thị ảnh
    label = tk.Label(root, image=photo)
    label.pack()
    
    # Label hiển thị tọa độ
    coord_label = tk.Label(root, text="Click vào ảnh để lấy tọa độ", 
                          font=("Arial", 12), fg="blue")
    coord_label.pack()
    
    def on_click(event):
        # Lấy tọa độ từ click
        x = int(event.x * scale_x)
        y = int(event.y * scale_y)
        
        # Hiển thị tọa độ
        coord_label.config(text=f"Tọa độ: ({x}, {y}) | Tương đối: ({x/width:.2%}, {y/height:.2%})")
        
        # In ra console
        print(f"\n📍 Tọa độ: ({x}, {y})")
        print(f"📊 Tương đối: width * {x/width:.3f}, height * {y/height:.3f}")
        print(f"💻 Code: x = width * {x/width:.3f}, y = height * {y/height:.3f}")
    
    def on_escape(event):
        root.quit()
    
    # Bind events
    label.bind("<Button-1>", on_click)
    root.bind("<Escape>", on_escape)
    
    print(f"\n🖼️  Ảnh: {image_path}")
    print(f"📏 Kích thước: {width}x{height} pixels")
    print(f"👆 Click vào ảnh để lấy tọa độ")
    print(f"❌ Nhấn ESC để thoát\n")
    
    root.mainloop()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Cách sử dụng: python get_coordinates.py <đường_dẫn_ảnh>")
        print("Ví dụ: python get_coordinates.py 'Screenshot 2025-11-15 at 13.20.27.png'")
    else:
        get_coordinates_from_image(sys.argv[1])

