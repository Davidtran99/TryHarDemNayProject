#!/usr/bin/env python3
"""
Set DATABASE_URL + POSTGRES_* secrets/variables cho Hugging Face Space dựa
trên thông tin trong `ops/.env.tunnel`.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, Iterable, Tuple

from huggingface_hub import HfApi, login


REPO_ROOT = Path(__file__).resolve().parents[1]
OPS_DIR = REPO_ROOT / "ops"
TUNNEL_ENV = OPS_DIR / ".env.tunnel"
TUNNEL_ENV_TEMPLATE = OPS_DIR / "env.tunnel.example"
DEFAULT_SPACE_ID = "davidtran999/hue-portal-backend"


def _load_env_file(path: Path) -> Dict[str, str]:
    data: Dict[str, str] = {}
    if not path.exists():
        return data
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def load_config(env_path: Path) -> Dict[str, str]:
    """Load config từ env file (actual -> template) và biến môi trường."""
    config: Dict[str, str] = {}
    for path in (TUNNEL_ENV_TEMPLATE, env_path):
        config.update(_load_env_file(path))
    config.update({key: value for key, value in os.environ.items() if value})
    return config


def resolve_database_settings(config: Dict[str, str]) -> Tuple[str, str, str, str, str]:
    """Trả về (host, port, db, user, password)."""
    host = config.get("PG_TUNNEL_HOST") or config.get("POSTGRES_HOST", "localhost")
    port = config.get("PG_TUNNEL_PORT") or config.get("POSTGRES_PORT", "5543")
    database = config.get("PG_TUNNEL_DB") or config.get("POSTGRES_DB", "hue_portal")
    user = config.get("PG_TUNNEL_USER") or config.get("POSTGRES_USER", "hue")
    password = config.get("PG_TUNNEL_PASSWORD") or config.get("POSTGRES_PASSWORD", "")
    return host, port, database, user, password


def upsert_variable(api: HfApi, repo_id: str, key: str, value: str) -> None:
    """Xóa rồi set lại Space variable."""
    if not value:
        return
    try:
        api.delete_space_variable(repo_id=repo_id, key=key)
    except Exception:
        pass
    api.add_space_variable(repo_id=repo_id, key=key, value=value)


def upsert_secret(api: HfApi, repo_id: str, key: str, value: str) -> None:
    """Xóa rồi set lại Space secret."""
    if not value:
        return
    try:
        api.delete_space_secret(repo_id=repo_id, key=key)
    except Exception:
        pass
    api.add_space_secret(repo_id=repo_id, key=key, value=value)


def apply_database_settings(space_id: str, config: Dict[str, str]) -> None:
    """Đẩy DATABASE_URL + POSTGRES_* lên Space."""
    host, port, database, user, password = resolve_database_settings(config)
    database_url = f"postgres://{user}:{password}@{host}:{port}/{database}"

    hf_token = config.get("HF_TOKEN")
    if not hf_token:
        cache_file = Path.home() / ".cache" / "huggingface" / "token"
        if cache_file.exists():
            hf_token = cache_file.read_text(encoding="utf-8").strip()
    if not hf_token:
        raise RuntimeError("HF token không tìm thấy. Chạy `huggingface-cli login` hoặc set HF_TOKEN.")

    login(token=hf_token)
    api = HfApi()

    # POSTGRES_* variables (host/port/db/user) + secret (password) để backend dùng.
    variable_pairs: Iterable[Tuple[str, str]] = (
        ("POSTGRES_HOST", host),
        ("POSTGRES_PORT", str(port)),
        ("POSTGRES_DB", database),
        ("POSTGRES_USER", user),
    )
    for key, value in variable_pairs:
        upsert_variable(api, space_id, key, value)

    upsert_secret(api, space_id, "POSTGRES_PASSWORD", password)
    upsert_secret(api, space_id, "DATABASE_URL", database_url)

    print(f"✅ Đã cập nhật DATABASE_URL + POSTGRES_* cho Space {space_id}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Set DATABASE_URL cho HF Space.")
    parser.add_argument(
        "--space-id",
        default=None,
        help="ID của Space (vd: username/space-name). Mặc định đọc từ env hoặc template.",
    )
    parser.add_argument(
        "--env-file",
        default=TUNNEL_ENV,
        type=Path,
        help="Đường dẫn file chứa thông tin tunnel. Mặc định: ops/.env.tunnel.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    env_path: Path = args.env_file
    if not env_path.exists():
        raise SystemExit(f"Không tìm thấy {env_path}. Copy ops/env.tunnel.example -> ops/.env.tunnel trước.")

    config = load_config(env_path)
    space_id = args.space_id or config.get("HF_SPACE_ID") or DEFAULT_SPACE_ID

    try:
        apply_database_settings(space_id, config)
    except Exception as exc:
        raise SystemExit(f"Không thể cập nhật secrets: {exc}") from exc


if __name__ == "__main__":
    main()
