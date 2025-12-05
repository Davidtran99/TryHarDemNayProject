#!/usr/bin/env python3
"""
Start (or reuse) an ngrok TCP tunnel for PostgreSQL and push DATABASE_URL to
the configured Hugging Face Space. Connection settings are now loaded from
`.env`/`ops/.env.tunnel` so credentials are no longer hard-coded.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests
from huggingface_hub import HfApi, login


REPO_ROOT = Path(__file__).resolve().parents[1]
OPS_DIR = REPO_ROOT / "ops"
ENV_PATHS = [
    OPS_DIR / "env.tunnel.example",
    REPO_ROOT / ".env",
    OPS_DIR / ".env.tunnel",
]
TUNNEL_ENV_PATH = OPS_DIR / ".env.tunnel"
DEFAULT_SPACE_ID = "davidtran999/hue-portal-backend"


def _load_env_file(path: Path) -> Dict[str, str]:
    """Load KEY=VALUE pairs from a dotenv-style file."""
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


def load_config() -> Dict[str, str]:
    """Aggregate config from .env files and environment variables."""
    config: Dict[str, str] = {}
    for path in ENV_PATHS:
        config.update(_load_env_file(path))
    for key, value in os.environ.items():
        if value:
            config[key] = value
    return config


def write_env_file(path: Path, data: Dict[str, str]) -> None:
    """Persist config back to disk in KEY=VALUE format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{key}={value}" for key, value in sorted(data.items())]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def log(message: str) -> None:
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[PG-TUNNEL {timestamp}] {message}", flush=True)


def get_ngrok_url() -> Tuple[Optional[str], Optional[str]]:
    """Fetch the current TCP tunnel from the local ngrok API."""
    try:
        response = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=2)
        if response.status_code == 200:
            for tunnel in response.json().get("tunnels", []):
                if tunnel.get("proto") != "tcp":
                    continue
                public_url = tunnel.get("public_url", "")
                if public_url.startswith("tcp://"):
                    host_port = public_url.replace("tcp://", "").split(":")
                    if len(host_port) == 2:
                        return host_port[0], host_port[1]
        return None, None
    except Exception as exc:  # pragma: no cover - defensive logging only
        log(f"⚠️  Không thể lấy ngrok URL từ API: {exc}")
        return None, None

    
def start_ngrok(local_port: int, config: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
    """Ensure ngrok is running and return the public host/port."""
    host, port = get_ngrok_url()
    if host and port:
        log(f"🔁 Ngrok đã chạy sẵn: tcp://{host}:{port}")
        return host, port
    
    ngrok_bin = config.get("NGROK_BIN", "ngrok")
    region = config.get("NGROK_REGION")
    cmd = [ngrok_bin, "tcp", str(local_port)]
    if region:
        cmd.extend(["--region", region])

    log(f"🚀 Đang start ngrok ({' '.join(cmd)}) ...")
    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        log("❌ Không tìm thấy binary ngrok. Cài đặt: brew install ngrok/ngrok/ngrok")
        return None, None
    except Exception as exc:
        log(f"❌ Lỗi khi start ngrok: {exc}")
        return None, None

    time.sleep(3)
    host, port = get_ngrok_url()
    if host and port:
        log(f"✅ Ngrok sẵn sàng: tcp://{host}:{port}")
        return host, port
    
    log("❌ Không thể lấy ngrok URL sau khi start")
            return None, None
            

def get_hf_token(config: Dict[str, str]) -> Optional[str]:
    """Resolve Hugging Face token from env or cache file."""
    if config.get("HF_TOKEN"):
        return config["HF_TOKEN"].strip()
    cache_file = Path.home() / ".cache" / "huggingface" / "token"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8").strip()
    return None


def save_tunnel_env(
    host: str,
    port: str,
    config: Dict[str, str],
    db_user: str,
    db_password: str,
    db_name: str,
    local_port: int,
) -> None:
    """Persist the latest tunnel metadata to ops/.env.tunnel."""
    current = _load_env_file(TUNNEL_ENV_PATH)
    database_url = f"postgres://{db_user}:{db_password}@{host}:{port}/{db_name}"
    current.update(
        {
            "HF_SPACE_ID": config.get("HF_SPACE_ID", DEFAULT_SPACE_ID),
            "POSTGRES_HOST": config.get("POSTGRES_HOST", "localhost"),
            "POSTGRES_PORT": str(local_port),
            "POSTGRES_USER": db_user,
            "POSTGRES_PASSWORD": db_password,
            "POSTGRES_DB": db_name,
            "PG_TUNNEL_HOST": host,
            "PG_TUNNEL_PORT": port,
            "PG_TUNNEL_USER": db_user,
            "PG_TUNNEL_PASSWORD": db_password,
            "PG_TUNNEL_DB": db_name,
            "PG_TUNNEL_LOCAL_PORT": str(local_port),
            "DATABASE_URL": database_url,
            "PG_TUNNEL_LAST_UPDATED": datetime.utcnow().isoformat(),
        }
    )
    write_env_file(TUNNEL_ENV_PATH, current)
    log(f"💾 Đã lưu metadata tunnel vào {TUNNEL_ENV_PATH.relative_to(REPO_ROOT)}")


def set_database_url(space_id: str, database_url: str, hf_token: str) -> bool:
    """Push DATABASE_URL secret to Hugging Face Space."""
    try:
        log("🔐 Đang đăng nhập Hugging Face CLI...")
        login(token=hf_token)
        api = HfApi()
        
        log("🗑️  Xóa DATABASE_URL cũ (variable + secret nếu tồn tại)...")
        try:
            api.delete_space_variable(repo_id=space_id, key="DATABASE_URL")
        except Exception:
            pass
        try:
            api.delete_space_secret(repo_id=space_id, key="DATABASE_URL")
        except Exception:
            pass
        
        log("📝 Set DATABASE_URL mới trên Space...")
        api.add_space_secret(repo_id=space_id, key="DATABASE_URL", value=database_url)
        log("✅ Đã cập nhật DATABASE_URL thành công.")
        return True
    except Exception as exc:
        log(f"❌ Lỗi khi cập nhật DATABASE_URL: {exc}")
        return False


def main() -> None:
    config = load_config()
    space_id = config.get("HF_SPACE_ID", DEFAULT_SPACE_ID)
    local_port = int(config.get("PG_TUNNEL_LOCAL_PORT", config.get("POSTGRES_PORT", 5543)))
    db_user = config.get("PG_TUNNEL_USER", config.get("POSTGRES_USER", "hue"))
    db_password = config.get("PG_TUNNEL_PASSWORD", config.get("POSTGRES_PASSWORD", "huepass123"))
    db_name = config.get("PG_TUNNEL_DB", config.get("POSTGRES_DB", "hue_portal"))

    log("=" * 60)
    log("Ngrok Auto Start & HF DATABASE_URL sync")
    log("=" * 60)

    host, port = start_ngrok(local_port, config)
    if not host or not port:
        log(f"❌ Không thể start tunnel. Chạy thủ công: ngrok tcp {local_port}")
        sys.exit(1)

    save_tunnel_env(host, port, config, db_user, db_password, db_name, local_port)
    database_url = f"postgres://{db_user}:{db_password}@{host}:{port}/{db_name}"

    hf_token = get_hf_token(config)
    if not hf_token:
        log("⚠️  Không tìm thấy HF token, bỏ qua bước cập nhật Space.")
        log(f"   DATABASE_URL mới: {database_url}")
        return
    
    if set_database_url(space_id, database_url, hf_token):
        log(f"📌 Ngrok URL: tcp://{host}:{port}")
        log(f"📌 DATABASE_URL đã đẩy lên Space {space_id}")
    else:
        log("⚠️  Không thể cập nhật DATABASE_URL, xem log ở trên để biết chi tiết.")


if __name__ == "__main__":
    main()

