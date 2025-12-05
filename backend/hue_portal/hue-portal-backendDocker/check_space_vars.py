#!/usr/bin/env python3
"""
Script để kiểm tra tất cả variables và secrets trên HF Space để tìm collisions.
"""

from __future__ import annotations

import sys
from pathlib import Path

from huggingface_hub import HfApi, login


DEFAULT_SPACE_ID = "davidtran999/hue-portal-backend"


def get_hf_token() -> str | None:
    """Resolve Hugging Face token from env or cache file."""
    import os

    if os.environ.get("HF_TOKEN"):
        return os.environ["HF_TOKEN"].strip()
    cache_file = Path.home() / ".cache" / "huggingface" / "token"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8").strip()
    return None


def check_collisions(space_id: str) -> None:
    """Kiểm tra và liệt kê tất cả variables và secrets để tìm collisions."""
    hf_token = get_hf_token()
    if not hf_token:
        print("❌ Không tìm thấy HF token. Chạy `huggingface-cli login` hoặc set HF_TOKEN.")
        sys.exit(1)
    
    login(token=hf_token)
    api = HfApi()
    
    print(f"🔍 Đang kiểm tra Space: {space_id}")
    print("=" * 60)
    
    # Lấy tất cả variables
    try:
        variables = api.get_space_variables(repo_id=space_id)
        print(f"\n📋 Variables ({len(variables)}):")
        var_keys = set()
        for key, value in variables.items():
            var_keys.add(key)
            masked_value = value[:20] + "..." if len(value) > 20 else value
            print(f"  - {key}: {masked_value}")
    except Exception as e:
        print(f"⚠️  Không thể lấy variables: {e}")
        var_keys = set()
    
    # Lấy tất cả secrets
    try:
        secrets = api.get_space_secrets(repo_id=space_id)
        print(f"\n🔐 Secrets ({len(secrets)}):")
        secret_keys = set()
        for key in secrets.keys():
            secret_keys.add(key)
            print(f"  - {key}: ***")
    except Exception as e:
        print(f"⚠️  Không thể lấy secrets: {e}")
        secret_keys = set()
    
    # Tìm collisions
    collisions = var_keys & secret_keys
    if collisions:
        print(f"\n❌ Tìm thấy {len(collisions)} collision(s):")
        for key in collisions:
            print(f"  - {key} (có cả variable và secret)")
    else:
        print(f"\n✅ Không có collision nào!")
    
    print("=" * 60)


def main() -> None:
    import argparse
    
    parser = argparse.ArgumentParser(description="Kiểm tra collisions trên HF Space")
    parser.add_argument(
        "--space-id",
        default=DEFAULT_SPACE_ID,
        help="ID của Space",
    )
    args = parser.parse_args()
    
    check_collisions(args.space_id)


if __name__ == "__main__":
    main()




