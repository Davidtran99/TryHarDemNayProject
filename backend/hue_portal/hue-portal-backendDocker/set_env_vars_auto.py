#!/usr/bin/env python3
"""
Script tự động set environment variables trên Hugging Face Spaces
Sử dụng Hugging Face Hub API

Cần: 
  - pip install huggingface_hub
  - HF_TOKEN environment variable hoặc login trước
"""

import os
import sys
import secrets
from pathlib import Path
from huggingface_hub import HfApi, login

# Space info
SPACE_ID = "davidtran999/hue-portal-backend"

# Generate secret key
DJANGO_SECRET_KEY = secrets.token_urlsafe(50)

# Environment variables cần set
# Lưu ý: DATABASE_URL sẽ được set thủ công với ngrok URL
ENV_VARS = {
    "DJANGO_SECRET_KEY": DJANGO_SECRET_KEY,
    "DJANGO_DEBUG": "false",
    "DJANGO_ALLOWED_HOSTS": "*.hf.space,davidtran999-hue-portal-backend.hf.space,localhost,127.0.0.1",
    "CORS_ALLOW_ALL_ORIGINS": "true",
    "LLM_PROVIDER": "none",
    # "DATABASE_URL": "postgres://hue:huepass@YOUR_NGROK_URL:PORT/hue_portal",  # Uncomment và điền ngrok URL
    # "REDIS_URL": "redis://YOUR_REDIS_NGROK_URL:PORT/0",  # Nếu có Redis qua ngrok
}

def _get_token_from_cache():
    """Try to get token from Hugging Face cache file."""
    try:
        cache_file = Path.home() / ".cache" / "huggingface" / "token"
        if cache_file.exists():
            token = cache_file.read_text().strip()
            if token:
                return token
    except Exception:
        pass
    return None

def main():
    print("=" * 60)
    print("Hugging Face Spaces - Auto Set Environment Variables")
    print("=" * 60)
    
    # Check for HF token - try multiple sources
    hf_token = (
        os.environ.get("HF_TOKEN") or 
        os.environ.get("HUGGINGFACE_HUB_TOKEN") or
        _get_token_from_cache()
    )
    
    if not hf_token:
        print("\n⚠️  Chưa có HF_TOKEN!")
        print("Có 2 cách:")
        print("1. Set environment variable: export HF_TOKEN=your_token")
        print("2. Login: huggingface-cli login")
        print("\nHoặc chạy script thủ công: python3 set_env_vars.py")
        return
    
    try:
        # Login
        login(token=hf_token)
        api = HfApi()
        
        print(f"\n✅ Đã login vào Hugging Face")
        print(f"Space: {SPACE_ID}")
        
        # Delete existing variables/secrets with same names to avoid collision
        print(f"\n🗑️  Xóa các biến cũ để tránh collision...")
        for key in ENV_VARS.keys():
            try:
                # Try to delete as variable first
                api.delete_space_variable(repo_id=SPACE_ID, key=key)
                print(f"  ✅ Deleted variable: {key}")
            except Exception as e:
                # Variable không tồn tại, tiếp tục
                pass
            try:
                # Try to delete as secret
                api.delete_space_secret(repo_id=SPACE_ID, key=key)
                print(f"  ✅ Deleted secret: {key}")
            except Exception as e:
                # Secret không tồn tại, tiếp tục
                pass
        
        print(f"\nĐang set các biến môi trường mới...")
        
        # Set secrets (environment variables) - chỉ dùng secrets để tránh collision
        for key, value in ENV_VARS.items():
            try:
                # Hugging Face Spaces: tất cả đều set as secret (bảo mật hơn)
                api.add_space_secret(
                    repo_id=SPACE_ID,
                    key=key,
                    value=value
                )
                if key == "DJANGO_SECRET_KEY":
                    print(f"  ✅ Set secret: {key} = {value[:20]}...")
                else:
                    print(f"  ✅ Set secret: {key} = {value}")
            except Exception as e:
                print(f"  ⚠️  Lỗi khi set {key}: {e}")
                # Fallback: hướng dẫn thủ công
                print(f"     → Set thủ công: {key} = {value}")
        
        print("\n" + "=" * 60)
        print("✅ Hoàn tất! Space sẽ tự động rebuild")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        print("\nCó thể Hugging Face API không hỗ trợ set env vars tự động.")
        print("Vui lòng chạy: python3 set_env_vars.py để xem hướng dẫn thủ công")

if __name__ == "__main__":
    main()


Script tự động set environment variables trên Hugging Face Spaces
Sử dụng Hugging Face Hub API

Cần: 
  - pip install huggingface_hub
  - HF_TOKEN environment variable hoặc login trước
"""

import os
import sys
import secrets
from pathlib import Path
from huggingface_hub import HfApi, login

# Space info
SPACE_ID = "davidtran999/hue-portal-backend"

# Generate secret key
DJANGO_SECRET_KEY = secrets.token_urlsafe(50)

# Environment variables cần set
# Lưu ý: DATABASE_URL sẽ được set thủ công với ngrok URL
ENV_VARS = {
    "DJANGO_SECRET_KEY": DJANGO_SECRET_KEY,
    "DJANGO_DEBUG": "false",
    "DJANGO_ALLOWED_HOSTS": "*.hf.space,davidtran999-hue-portal-backend.hf.space,localhost,127.0.0.1",
    "CORS_ALLOW_ALL_ORIGINS": "true",
    "LLM_PROVIDER": "none",
    # "DATABASE_URL": "postgres://hue:huepass@YOUR_NGROK_URL:PORT/hue_portal",  # Uncomment và điền ngrok URL
    # "REDIS_URL": "redis://YOUR_REDIS_NGROK_URL:PORT/0",  # Nếu có Redis qua ngrok
}

def _get_token_from_cache():
    """Try to get token from Hugging Face cache file."""
    try:
        cache_file = Path.home() / ".cache" / "huggingface" / "token"
        if cache_file.exists():
            token = cache_file.read_text().strip()
            if token:
                return token
    except Exception:
        pass
    return None

def main():
    print("=" * 60)
    print("Hugging Face Spaces - Auto Set Environment Variables")
    print("=" * 60)
    
    # Check for HF token - try multiple sources
    hf_token = (
        os.environ.get("HF_TOKEN") or 
        os.environ.get("HUGGINGFACE_HUB_TOKEN") or
        _get_token_from_cache()
    )
    
    if not hf_token:
        print("\n⚠️  Chưa có HF_TOKEN!")
        print("Có 2 cách:")
        print("1. Set environment variable: export HF_TOKEN=your_token")
        print("2. Login: huggingface-cli login")
        print("\nHoặc chạy script thủ công: python3 set_env_vars.py")
        return
    
    try:
        # Login
        login(token=hf_token)
        api = HfApi()
        
        print(f"\n✅ Đã login vào Hugging Face")
        print(f"Space: {SPACE_ID}")
        
        # Delete existing variables/secrets with same names to avoid collision
        print(f"\n🗑️  Xóa các biến cũ để tránh collision...")
        for key in ENV_VARS.keys():
            try:
                # Try to delete as variable first
                api.delete_space_variable(repo_id=SPACE_ID, key=key)
                print(f"  ✅ Deleted variable: {key}")
            except Exception as e:
                # Variable không tồn tại, tiếp tục
                pass
            try:
                # Try to delete as secret
                api.delete_space_secret(repo_id=SPACE_ID, key=key)
                print(f"  ✅ Deleted secret: {key}")
            except Exception as e:
                # Secret không tồn tại, tiếp tục
                pass
        
        print(f"\nĐang set các biến môi trường mới...")
        
        # Set secrets (environment variables) - chỉ dùng secrets để tránh collision
        for key, value in ENV_VARS.items():
            try:
                # Hugging Face Spaces: tất cả đều set as secret (bảo mật hơn)
                api.add_space_secret(
                    repo_id=SPACE_ID,
                    key=key,
                    value=value
                )
                if key == "DJANGO_SECRET_KEY":
                    print(f"  ✅ Set secret: {key} = {value[:20]}...")
                else:
                    print(f"  ✅ Set secret: {key} = {value}")
            except Exception as e:
                print(f"  ⚠️  Lỗi khi set {key}: {e}")
                # Fallback: hướng dẫn thủ công
                print(f"     → Set thủ công: {key} = {value}")
        
        print("\n" + "=" * 60)
        print("✅ Hoàn tất! Space sẽ tự động rebuild")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        print("\nCó thể Hugging Face API không hỗ trợ set env vars tự động.")
        print("Vui lòng chạy: python3 set_env_vars.py để xem hướng dẫn thủ công")

if __name__ == "__main__":
    main()
