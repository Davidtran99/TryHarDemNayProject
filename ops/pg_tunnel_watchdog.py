#!/usr/bin/env python3
"""
Watchdog giữ kết nối PostgreSQL tunnel luôn sẵn sàng.
- Định kỳ chạy `pg_isready` qua host/port trong ops/.env.tunnel
- Nếu lỗi, tự động gọi `start_ngrok_and_set_db.py` để tạo tunnel & cập nhật HF
- Ghi log vào ops/logs/tunnel_watchdog.log để tiện theo dõi
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
OPS_DIR = REPO_ROOT / "ops"
TUNNEL_ENV = OPS_DIR / ".env.tunnel"
START_SCRIPT = REPO_ROOT / "hue-portal-backend" / "start_ngrok_and_set_db.py"
LOG_PATH = OPS_DIR / "logs" / "tunnel_watchdog.log"
DEFAULT_INTERVAL = 300  # 5 phút


def _load_env(path: Path) -> Dict[str, str]:
    """Đọc file dotenv đơn giản và trả về dict."""
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


def _setup_logger() -> logging.Logger:
    """Cấu hình logger ghi ra file + stdout."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("pg_tunnel_watchdog")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
        file_handler.setFormatter(formatter)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
    return logger


def _pg_isready_command(config: Dict[str, str], pg_isready_bin: str) -> Tuple[list[str], Dict[str, str]]:
    """Tạo command và env để chạy pg_isready."""
    host = config.get("PG_TUNNEL_HOST") or config.get("POSTGRES_HOST", "localhost")
    port = config.get("PG_TUNNEL_PORT") or config.get("POSTGRES_PORT", "5543")
    database = config.get("PG_TUNNEL_DB") or config.get("POSTGRES_DB", "hue_portal")
    user = config.get("PG_TUNNEL_USER") or config.get("POSTGRES_USER", "hue")
    password = config.get("PG_TUNNEL_PASSWORD") or config.get("POSTGRES_PASSWORD", "")

    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password

    cmd: list[str] = [
        pg_isready_bin,
        "-h",
        host,
        "-p",
        str(port),
        "-d",
        database,
        "-U",
        user,
    ]
    return cmd, env


def check_pg_isready(config: Dict[str, str], pg_isready_bin: str, logger: logging.Logger) -> bool:
    """Chạy pg_isready, nếu thiếu binary sẽ fallback psycopg2."""
    cmd, env = _pg_isready_command(config, pg_isready_bin)
    logger.info("🔍 Kiểm tra pg_isready: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
            check=False,
        )
        logger.info("pg_isready output: %s", result.stdout.strip() or result.stderr.strip())
        return result.returncode == 0
    except FileNotFoundError:
        logger.warning("pg_isready không có sẵn. Fallback sang psycopg2.")
        return _probe_with_psycopg2(config, logger)
    except subprocess.TimeoutExpired:
        logger.error("pg_isready timeout.")
        return False


def _probe_with_psycopg2(config: Dict[str, str], logger: logging.Logger) -> bool:
    """Fallback đơn giản bằng psycopg2."""
    try:
        import psycopg2

        host = config.get("PG_TUNNEL_HOST") or config.get("POSTGRES_HOST", "localhost")
        port = config.get("PG_TUNNEL_PORT") or config.get("POSTGRES_PORT", "5543")
        database = config.get("PG_TUNNEL_DB") or config.get("POSTGRES_DB", "hue_portal")
        user = config.get("PG_TUNNEL_USER") or config.get("POSTGRES_USER", "hue")
        password = config.get("PG_TUNNEL_PASSWORD") or config.get("POSTGRES_PASSWORD", "")

        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            connect_timeout=5,
        )
        conn.close()
        logger.info("psycopg2 probe thành công.")
        return True
    except Exception as exc:
        logger.error("psycopg2 probe thất bại: %s", exc)
        return False


def restart_tunnel(logger: logging.Logger) -> bool:
    """Gọi script start_ngrok_and_set_db.py để tái tạo tunnel."""
    logger.warning("🔁 Tunnel lỗi, đang gọi start_ngrok_and_set_db.py ...")
    try:
        result = subprocess.run(
            [sys.executable, str(START_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        logger.info("start_ngrok stdout: %s", result.stdout.strip())
        if result.stderr:
            logger.info("start_ngrok stderr: %s", result.stderr.strip())
        if result.returncode != 0:
            logger.error("start_ngrok_and_set_db.py trả về mã %s", result.returncode)
            return False
        return True
    except subprocess.TimeoutExpired:
        logger.error("start_ngrok_and_set_db.py timeout (180s).")
        return False
    except Exception as exc:
        logger.exception("Không thể khởi động lại tunnel: %s", exc)
        return False


def watchdog_loop(interval: int, once: bool, pg_isready_bin: str) -> None:
    """Vòng lặp watchdog chính."""
    logger = _setup_logger()
    if not TUNNEL_ENV.exists():
        logger.error("Chưa có %s. Copy ops/env.tunnel.example -> ops/.env.tunnel trước.", TUNNEL_ENV)
        sys.exit(1)

    while True:
        config = _load_env(TUNNEL_ENV)
        if not config.get("PG_TUNNEL_HOST") or not config.get("PG_TUNNEL_PORT"):
            logger.warning("Thiếu thông tin tunnel trong %s. Chạy start_ngrok_and_set_db.py trước.", TUNNEL_ENV)
        else:
            healthy = check_pg_isready(config, pg_isready_bin, logger)
            if healthy:
                logger.info("✅ Tunnel hoạt động bình thường.")
            else:
                logger.error("❌ pg_isready báo lỗi, tiến hành khởi động lại tunnel.")
                if restart_tunnel(logger):
                    logger.info("✅ Đã restart tunnel thành công.")
                else:
                    logger.error("🚨 Không thể restart tunnel. Kiểm tra log ở trên.")

        if once:
            break
        time.sleep(interval)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="PostgreSQL tunnel watchdog")
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL,
        help="Khoảng thời gian giữa các lần kiểm tra (giây). Mặc định 300s.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Chạy một lần rồi thoát (dùng cho cron).",
    )
    parser.add_argument(
        "--pg-isready-bin",
        default=os.environ.get("PG_ISREADY_BIN", "pg_isready"),
        help="Đường dẫn tới binary pg_isready (mặc định: pg_isready trong PATH).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    watchdog_loop(interval=args.interval, once=args.once, pg_isready_bin=args.pg_isready_bin)


if __name__ == "__main__":
    main()


