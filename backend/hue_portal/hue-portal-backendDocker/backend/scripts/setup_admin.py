#!/usr/bin/env python
"""
Script để tạo superuser cho Django Admin
Chạy từ thư mục backend/hue_portal
"""
import os
import sys
import django

# Thêm thư mục hue_portal vào path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUE_PORTAL_DIR = os.path.join(BASE_DIR, 'hue_portal')
sys.path.insert(0, HUE_PORTAL_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hue_portal.settings')
django.setup()

from django.contrib.auth.models import User

def create_superuser(username='admin', email='admin@example.com', password='admin123'):
    """Tạo superuser nếu chưa có"""
    if User.objects.filter(username=username).exists():
        user = User.objects.get(username=username)
        if user.is_superuser:
            print(f"✅ Superuser '{username}' đã tồn tại.")
            print(f"   Username: {username}")
            print(f"   Email: {user.email}")
            print(f"\n🌐 Truy cập Django Admin tại: http://localhost:8000/admin/")
            return True
        else:
            # Nâng cấp user thành superuser
            user.is_superuser = True
            user.is_staff = True
            user.set_password(password)
            user.save()
            print(f"✅ Đã nâng cấp user '{username}' thành superuser.")
    else:
        User.objects.create_superuser(username=username, email=email, password=password)
        print(f"✅ Đã tạo superuser mới:")
    
    print(f"   Username: {username}")
    print(f"   Email: {email}")
    print(f"   Password: {password}")
    print(f"\n🌐 Truy cập Django Admin tại: http://localhost:8000/admin/")
    print(f"\n💡 Để start server: cd backend/hue_portal && POSTGRES_PORT=5433 POSTGRES_HOST=localhost python manage.py runserver")
    return True

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Tạo superuser cho Django Admin')
    parser.add_argument('--username', default='admin', help='Username (default: admin)')
    parser.add_argument('--email', default='admin@example.com', help='Email (default: admin@example.com)')
    parser.add_argument('--password', default='admin123', help='Password (default: admin123)')
    args = parser.parse_args()
    
    create_superuser(args.username, args.email, args.password)

