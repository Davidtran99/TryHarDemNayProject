#!/usr/bin/env python3
"""
Script để fix lỗi "Collision on variables and secrets names" trên HF Space.
Xóa tất cả variables và secrets có thể gây xung đột, sau đó set lại đúng cách.
"""

from __future__ import annotations

import sys
from pathlib import Path

from huggingface_hub import HfApi, login


REPO_ROOT = Path(__file__).resolve().parents[1]
OPS_DIR = REPO_ROOT / "ops"
TUNNEL_ENV = OPS_DIR / ".env.tunnel"
DEFAULT_SPACE_ID = "davidtran999/hue-portal-backend"

# Danh sách các key có thể gây xung đột
COLLISION_KEYS = [
    "DATABASE_URL",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
]


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


def get_hf_token() -> str | None:
    """Resolve Hugging Face token from env or cache file."""
    import os

    if os.environ.get("HF_TOKEN"):
        return os.environ["HF_TOKEN"].strip()
    cache_file = Path.home() / ".cache" / "huggingface" / "token"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8").strip()
    return None


def cleanup_collisions(api: HfApi, space_id: str) -> None:
    """Xóa tất cả variables và secrets có thể gây xung đột."""
    print(f"🧹 Đang dọn dẹp collisions cho Space: {space_id}")
    
    # Thử xóa nhiều lần để đảm bảo
    for attempt in range(2):
        if attempt > 0:
            print(f"\n🔄 Lần thử thứ {attempt + 1}...")
        
        for key in COLLISION_KEYS:
            # Xóa variable (thử nhiều lần)
            for _ in range(2):
                try:
                    api.delete_space_variable(repo_id=space_id, key=key)
                    print(f"  ✅ Đã xóa variable: {key}")
                    break
                except Exception as e:
                    if "not found" in str(e).lower() or "404" in str(e):
                        # Không tồn tại, không cần xóa
                        break
                    print(f"  ⚠️  Lỗi khi xóa variable {key}: {e}")
            
            # Xóa secret (thử nhiều lần)
            for _ in range(2):
                try:
                    api.delete_space_secret(repo_id=space_id, key=key)
                    print(f"  ✅ Đã xóa secret: {key}")
                    break
                except Exception as e:
                    if "not found" in str(e).lower() or "404" in str(e):
                        # Không tồn tại, không cần xóa
                        break
                    print(f"  ⚠️  Lỗi khi xóa secret {key}: {e}")
    
    print("\n✅ Hoàn tất dọn dẹp collisions")


def set_database_config(api: HfApi, space_id: str, config: dict[str, str]) -> None:
    """Set lại DATABASE_URL và POSTGRES_* đúng cách."""
    host = config.get("PG_TUNNEL_HOST") or config.get("POSTGRES_HOST", "localhost")
    port = config.get("PG_TUNNEL_PORT") or config.get("POSTGRES_PORT", "5543")
    database = config.get("PG_TUNNEL_DB") or config.get("POSTGRES_DB", "hue_portal")
    user = config.get("PG_TUNNEL_USER") or config.get("POSTGRES_USER", "hue")
    password = config.get("PG_TUNNEL_PASSWORD") or config.get("POSTGRES_PASSWORD", "")
    
    database_url = f"postgres://{user}:{password}@{host}:{port}/{database}"
    
    print(f"📝 Đang set lại database config...")
    
    # Set POSTGRES_* as variables (không nhạy cảm)
    api.add_space_variable(repo_id=space_id, key="POSTGRES_HOST", value=host)
    api.add_space_variable(repo_id=space_id, key="POSTGRES_PORT", value=str(port))
    api.add_space_variable(repo_id=space_id, key="POSTGRES_DB", value=database)
    api.add_space_variable(repo_id=space_id, key="POSTGRES_USER", value=user)
    print("  ✅ Đã set POSTGRES_* variables")
    
    # Set passwords và DATABASE_URL as secrets (nhạy cảm)
    api.add_space_secret(repo_id=space_id, key="POSTGRES_PASSWORD", value=password)
    api.add_space_secret(repo_id=space_id, key="DATABASE_URL", value=database_url)
    print("  ✅ Đã set POSTGRES_PASSWORD + DATABASE_URL secrets")
    
    print(f"✅ Hoàn tất set database config")


def main() -> None:
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix collision errors trên HF Space")
    parser.add_argument(
        "--space-id",
        default=None,
        help="ID của Space. Mặc định: davidtran999/hue-portal-backend",
    )
    parser.add_argument(
        "--skip-cleanup",
        action="store_true",
        help="Bỏ qua bước cleanup (chỉ set lại config)",
    )
    args = parser.parse_args()
    
    space_id = args.space_id or DEFAULT_SPACE_ID
    
    # Load config từ tunnel env
    config = _load_env_file(TUNNEL_ENV)
    if not config:
        print(f"⚠️  Không tìm thấy {TUNNEL_ENV}, sử dụng giá trị mặc định")
    
    # Get HF token
    hf_token = get_hf_token()
    if not hf_token:
        print("❌ Không tìm thấy HF token. Chạy `huggingface-cli login` hoặc set HF_TOKEN.")
        sys.exit(1)
    
    login(token=hf_token)
    api = HfApi()
    
    print("=" * 60)
    print(f"Fix Collision cho Space: {space_id}")
    print("=" * 60)
    
    # Cleanup collisions
    if not args.skip_cleanup:
        cleanup_collisions(api, space_id)
        print()
    
    # Set lại config đúng cách
    set_database_config(api, space_id, config)
    
    print()
    print("=" * 60)
    print("✅ Hoàn tất! Space sẽ tự động restart.")
    print(f"   Kiểm tra tại: https://huggingface.co/spaces/{space_id}")
    print("=" * 60)


if __name__ == "__main__":
    main()

