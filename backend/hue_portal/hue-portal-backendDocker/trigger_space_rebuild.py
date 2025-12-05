#!/usr/bin/env python3
"""
Script to trigger Hugging Face Space rebuild.
This will force Space to pull latest code and rebuild with new dependencies.
"""
import os
import sys
from pathlib import Path
from huggingface_hub import HfApi, login

DEFAULT_SPACE_ID = "davidtran999/hue-portal-backend"

def get_hf_token() -> str:
    """Get HF token from environment or cache."""
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    if token:
        return token
    
    # Try to read from cache
    cache_file = Path.home() / ".cache" / "huggingface" / "token"
    if cache_file.exists():
        return cache_file.read_text().strip()
    
    return None

def trigger_rebuild(space_id: str) -> bool:
    """Trigger Space rebuild by restarting it."""
    hf_token = get_hf_token()
    if not hf_token:
        print("❌ Không tìm thấy HF token. Chạy `huggingface-cli login` hoặc set HF_TOKEN.")
        return False
    
    try:
        login(token=hf_token)
        api = HfApi(token=hf_token)
        
        print(f"🔄 Đang trigger rebuild cho Space: {space_id}")
        
        # Restart Space bằng cách restart runtime
        # Note: HF API không có method trực tiếp để restart, nhưng có thể dùng restart endpoint
        # Hoặc đơn giản là thay đổi một env var để trigger rebuild
        print("💡 Trigger rebuild bằng cách restart Space runtime...")
        print("   (Space sẽ tự động rebuild khi detect thay đổi trong repo)")
        
        # Alternative: Update a dummy env var to trigger rebuild
        try:
            # Thử restart bằng cách update một variable nhỏ
            api.add_space_variable(repo_id=space_id, key="_REBUILD_TRIGGER", value=str(int(Path(__file__).stat().st_mtime)))
            print("✅ Đã trigger rebuild bằng cách update env var")
            print(f"   Space sẽ tự động rebuild trong vài phút.")
            print(f"   Kiểm tra tại: https://huggingface.co/spaces/{space_id}")
            return True
        except Exception as e:
            print(f"⚠️  Không thể trigger rebuild tự động: {e}")
            print("💡 Vui lòng trigger rebuild thủ công:")
            print(f"   1. Vào https://huggingface.co/spaces/{space_id}/settings")
            print("   2. Click nút 'Restart this Space' hoặc 'Rebuild'")
            return False
            
    except Exception as e:
        print(f"❌ Lỗi khi trigger rebuild: {e}")
        return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Trigger HF Space rebuild")
    parser.add_argument(
        "--space-id",
        default=DEFAULT_SPACE_ID,
        help="ID của Space",
    )
    args = parser.parse_args()
    
    trigger_rebuild(args.space_id)

