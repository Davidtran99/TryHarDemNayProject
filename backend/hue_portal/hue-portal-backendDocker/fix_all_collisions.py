#!/usr/bin/env python3
"""
Script mạnh hơn để fix TẤT CẢ collisions trên HF Space.
Sử dụng API để list tất cả variables và secrets, tìm collisions, và xóa chúng.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from huggingface_hub import HfApi, login


DEFAULT_SPACE_ID = "davidtran999/hue-portal-backend"
REPO_ROOT = Path(__file__).resolve().parents[1]
OPS_DIR = REPO_ROOT / "ops"
TUNNEL_ENV = OPS_DIR / ".env.tunnel"


def get_hf_token() -> str | None:
    """Resolve Hugging Face token from env or cache file."""
    import os

    if os.environ.get("HF_TOKEN"):
        return os.environ["HF_TOKEN"].strip()
    cache_file = Path.home() / ".cache" / "huggingface" / "token"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8").strip()
    return None


def list_all_space_config(api: HfApi, space_id: str) -> tuple[dict, dict]:
    """
    List tất cả variables và secrets trên Space.
    Returns: (variables_dict, secrets_dict)
    """
    variables = {}
    secrets = {}
    
    try:
        # Lấy variables - sử dụng get_space_runtime
        # Note: huggingface_hub có thể không có method trực tiếp để list tất cả
        # Nhưng chúng ta có thể thử dùng Space runtime API
        space_info = api.space_info(repo_id=space_id)
        print(f"📋 Space info: {space_info}")
    except Exception as e:
        print(f"⚠️  Không thể lấy space info: {e}")
    
    # Thay vì list, chúng ta sẽ xóa tất cả keys có thể gây collision
    # và set lại từ đầu
    return variables, secrets


def find_and_delete_all_collisions(api: HfApi, space_id: str) -> None:
    """
    Tìm và xóa TẤT CẢ collisions bằng cách:
    1. Xóa tất cả database-related keys (variables và secrets)
    2. Đợi một chút
    3. Xóa lại lần nữa để đảm bảo
    """
    print(f"🧹 Đang dọn dẹp TẤT CẢ collisions cho Space: {space_id}")
    print("=" * 60)
    
    # Danh sách đầy đủ các keys có thể gây collision
    # Bao gồm cả database keys VÀ các keys khác đang bị duplicate
    all_possible_keys = [
        # Database keys
        "DATABASE_URL",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "DB_HOST",
        "DB_PORT",
        "DB_USER",
        "DB_PASSWORD",
        "DB_NAME",
        "PGHOST",
        "PGPORT",
        "PGUSER",
        "PGPASSWORD",
        "PGDATABASE",
        # Django keys đang bị duplicate
        "DJANGO_DEBUG",
        "DJANGO_ALLOWED_HOSTS",
        "CORS_ALLOW_ALL_ORIGINS",
        "LLM_PROVIDER",
        # Các keys khác có thể bị duplicate
        "CORS_ALLOWED_ORIGINS",
        "DJANGO_SECRET_KEY",
    ]
    
    # Xóa 3 lần để đảm bảo
    for round_num in range(1, 4):
        print(f"\n🔄 Round {round_num}/3: Xóa tất cả variables và secrets...")
        
        deleted_vars = []
        deleted_secrets = []
        
        for key in all_possible_keys:
            # Xóa variable
            for attempt in range(3):
                try:
                    api.delete_space_variable(repo_id=space_id, key=key)
                    if key not in deleted_vars:
                        deleted_vars.append(key)
                    break
                except Exception as e:
                    error_str = str(e).lower()
                    if "not found" in error_str or "404" in error_str or "does not exist" in error_str:
                        # Không tồn tại, OK
                        break
                    if attempt < 2:
                        time.sleep(0.5)
                    else:
                        # Lần cuối, log lỗi nhưng tiếp tục
                        pass
            
            # Xóa secret
            for attempt in range(3):
                try:
                    api.delete_space_secret(repo_id=space_id, key=key)
                    if key not in deleted_secrets:
                        deleted_secrets.append(key)
                    break
                except Exception as e:
                    error_str = str(e).lower()
                    if "not found" in error_str or "404" in error_str or "does not exist" in error_str:
                        # Không tồn tại, OK
                        break
                    if attempt < 2:
                        time.sleep(0.5)
                    else:
                        # Lần cuối, log lỗi nhưng tiếp tục
                        pass
        
        if deleted_vars:
            print(f"  ✅ Đã xóa {len(deleted_vars)} variables: {', '.join(deleted_vars)}")
        if deleted_secrets:
            print(f"  ✅ Đã xóa {len(deleted_secrets)} secrets: {', '.join(deleted_secrets)}")
        
        if round_num < 3:
            print(f"  ⏳ Đợi 2 giây trước round tiếp theo...")
            time.sleep(2)
    
    print("\n✅ Hoàn tất dọn dẹp collisions")


def set_database_config(api: HfApi, space_id: str) -> None:
    """Set lại DATABASE_URL và POSTGRES_* đúng cách từ tunnel env."""
    def _load_env_file(path: Path) -> dict[str, str]:
        """Load KEY=VALUE pairs from a dotenv-style file."""
        data: dict[str, str] = {}
        if not path.exists():
            return data
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip().strip('"').strip("'")
        return data
    
    config = _load_env_file(TUNNEL_ENV)
    
    host = config.get("PG_TUNNEL_HOST") or config.get("POSTGRES_HOST", "localhost")
    port = config.get("PG_TUNNEL_PORT") or config.get("POSTGRES_PORT", "5543")
    database = config.get("PG_TUNNEL_DB") or config.get("POSTGRES_DB", "hue_portal")
    user = config.get("PG_TUNNEL_USER") or config.get("POSTGRES_USER", "hue")
    password = config.get("PG_TUNNEL_PASSWORD") or config.get("POSTGRES_PASSWORD", "huepass123")
    
    database_url = f"postgres://{user}:{password}@{host}:{port}/{database}"
    
    print(f"\n📝 Đang set lại database config...")
    print(f"   Host: {host}:{port}")
    print(f"   Database: {database}")
    print(f"   User: {user}")
    
    # Đợi một chút để đảm bảo deletions đã hoàn tất
    time.sleep(1)
    
    # Set POSTGRES_* as variables (không nhạy cảm)
    try:
        api.add_space_variable(repo_id=space_id, key="POSTGRES_HOST", value=host)
        api.add_space_variable(repo_id=space_id, key="POSTGRES_PORT", value=str(port))
        api.add_space_variable(repo_id=space_id, key="POSTGRES_DB", value=database)
        api.add_space_variable(repo_id=space_id, key="POSTGRES_USER", value=user)
        print("  ✅ Đã set POSTGRES_* variables")
    except Exception as e:
        print(f"  ⚠️  Lỗi khi set variables: {e}")
    
    # Đợi một chút
    time.sleep(0.5)
    
    # Set passwords và DATABASE_URL as secrets (nhạy cảm)
    try:
        api.add_space_secret(repo_id=space_id, key="POSTGRES_PASSWORD", value=password)
        api.add_space_secret(repo_id=space_id, key="DATABASE_URL", value=database_url)
        print("  ✅ Đã set POSTGRES_PASSWORD + DATABASE_URL secrets")
    except Exception as e:
        print(f"  ⚠️  Lỗi khi set secrets: {e}")
    
    print(f"✅ Hoàn tất set database config")


def main() -> None:
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix TẤT CẢ collisions trên HF Space")
    parser.add_argument(
        "--space-id",
        default=DEFAULT_SPACE_ID,
        help="ID của Space",
    )
    args = parser.parse_args()
    
    # Get HF token
    hf_token = get_hf_token()
    if not hf_token:
        print("❌ Không tìm thấy HF token. Chạy `huggingface-cli login` hoặc set HF_TOKEN.")
        sys.exit(1)
    
    login(token=hf_token)
    api = HfApi()
    
    print("=" * 60)
    print(f"Fix TẤT CẢ Collisions cho Space: {args.space_id}")
    print("=" * 60)
    
    # Xóa tất cả collisions
    find_and_delete_all_collisions(api, args.space_id)
    
    # Đợi một chút
    print("\n⏳ Đợi 3 giây trước khi set lại config...")
    time.sleep(3)
    
    # Set lại config đúng cách
    set_database_config(api, args.space_id)
    
    print()
    print("=" * 60)
    print("✅ Hoàn tất! Space sẽ tự động restart.")
    print(f"   Kiểm tra tại: https://huggingface.co/spaces/{args.space_id}/settings")
    print("=" * 60)
    print("\n💡 Lưu ý:")
    print("   - Đợi 30-60 giây để HF Space xử lý")
    print("   - Refresh trang Settings (F5 hoặc Cmd+Shift+R)")
    print("   - Nếu vẫn còn lỗi, có thể cần đợi thêm hoặc liên hệ HF support")


if __name__ == "__main__":
    main()

