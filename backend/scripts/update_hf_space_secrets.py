#!/usr/bin/env python3
"""
Utility to push Hugging Face Space secrets from a local env file.

Usage:
    export HF_TOKEN=hf_xxx   # token with write access to the Space
    python backend/scripts/update_hf_space_secrets.py \
        --space davidttran999/hue-portal-backendDocker \
        --secrets-file ops/hf.secrets.env
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Dict

import requests


def parse_env_file(path: Path) -> Dict[str, str]:
    """
    Load KEY=VALUE pairs from the provided file.

    Blank lines and comments starting with `#` are ignored.
    """
    if not path.exists():
        raise FileNotFoundError(f"Secrets file not found: {path}")

    secrets: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"Invalid secret line (missing '='): {raw_line}")
        key, value = line.split("=", 1)
        secrets[key.strip()] = value.strip()

    if not secrets:
        raise ValueError(f"No secrets detected in {path}")
    return secrets


def upsert_secret(space_id: str, token: str, key: str, value: str) -> None:
    """Create or update a secret for the given Hugging Face Space."""
    url = f"https://huggingface.co/api/spaces/{space_id}/secrets"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json={"key": key, "value": value}, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to upsert secret '{key}'. "
            f"Status {response.status_code}: {response.text}"
        )


def build_parser() -> argparse.ArgumentParser:
    """Configure CLI options."""
    parser = argparse.ArgumentParser(description="Sync secrets to a Hugging Face Space.")
    parser.add_argument(
        "--space",
        required=True,
        help="Space identifier in the form owner/space (e.g. davidttran999/hue-portal-backendDocker).",
    )
    parser.add_argument(
        "--secrets-file",
        default="ops/hf.secrets.env",
        help="Path to file containing KEY=VALUE entries (default: %(default)s).",
    )
    parser.add_argument(
        "--token-env",
        default="HF_TOKEN",
        help="Environment variable that stores the Hugging Face access token (default: %(default)s).",
    )
    return parser


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    token = os.environ.get(args.token_env)
    if not token:
        parser.error(f"Environment variable {args.token_env} is not set.")

    secrets = parse_env_file(Path(args.secrets_file).expanduser())
    for key, value in secrets.items():
        upsert_secret(args.space, token, key, value)
        print(f"✅ Synced secret '{key}' to {args.space}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pylint: disable=broad-except
        print(f"❌ {exc}", file=sys.stderr)
        sys.exit(1)

