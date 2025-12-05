#!/usr/bin/env python3
"""
List all variables and secrets for a Hugging Face Space.

Usage:
    export HF_TOKEN=hf_xxx
    python backend/scripts/list_hf_space_config.py --space davidtran999/hue-portal-backend
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Dict, List, Optional

import requests


def get_space_variables(space_id: str, token: str) -> Dict[str, str]:
    """Fetch all environment variables for a Space."""
    url = f"https://huggingface.co/api/spaces/{space_id}/variables"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            # Handle both list and dict responses
            if isinstance(data, list):
                return {item["key"]: item.get("value", "") for item in data}
            elif isinstance(data, dict):
                return {k: v.get("value", "") if isinstance(v, dict) else v for k, v in data.items()}
            else:
                return {}
        elif response.status_code == 404:
            return {}
        else:
            print(f"⚠️  Failed to fetch variables: {response.status_code} - {response.text}", file=sys.stderr)
            return {}
    except Exception as e:
        print(f"⚠️  Error fetching variables: {e}", file=sys.stderr)
        return {}


def get_space_secrets(space_id: str, token: str) -> List[str]:
    """Fetch all secret keys (values are hidden) for a Space."""
    url = f"https://huggingface.co/api/spaces/{space_id}/secrets"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            # Handle both list and dict responses
            if isinstance(data, list):
                return [item["key"] for item in data]
            elif isinstance(data, dict):
                return list(data.keys())
            else:
                return []
        elif response.status_code == 404:
            return []
        else:
            print(f"⚠️  Failed to fetch secrets: {response.status_code} - {response.text}", file=sys.stderr)
            return []
    except Exception as e:
        print(f"⚠️  Error fetching secrets: {e}", file=sys.stderr)
        return []


def build_parser() -> argparse.ArgumentParser:
    """Configure CLI options."""
    parser = argparse.ArgumentParser(description="List variables and secrets for a Hugging Face Space.")
    parser.add_argument(
        "--space",
        required=True,
        help="Space identifier in the form owner/space (e.g. davidtran999/hue-portal-backend).",
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

    print(f"📋 Listing configuration for: {args.space}\n")

    # Fetch variables
    variables = get_space_variables(args.space, token)
    print("🔧 Environment Variables:")
    if variables:
        for key, value in sorted(variables.items()):
            # Mask sensitive values
            if "password" in key.lower() or "secret" in key.lower() or "token" in key.lower() or "key" in key.lower():
                masked = value[:4] + "***" if len(value) > 4 else "***"
                print(f"  {key} = {masked}")
            else:
                print(f"  {key} = {value}")
    else:
        print("  (none)")

    print()

    # Fetch secrets
    secrets = get_space_secrets(args.space, token)
    print("🔐 Secrets:")
    if secrets:
        for key in sorted(secrets):
            print(f"  {key} = <hidden>")
    else:
        print("  (none)")

    print()

    # Check for collisions
    var_keys = set(variables.keys())
    secret_keys = set(secrets)
    collisions = var_keys & secret_keys

    if collisions:
        print("❌ COLLISIONS DETECTED (same name in both Variables and Secrets):")
        for key in sorted(collisions):
            print(f"  ⚠️  {key}")
        print("\n💡 Fix: Remove from Variables (keep only in Secrets)")
        sys.exit(1)
    else:
        print("✅ No collisions detected")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pylint: disable=broad-except
        print(f"❌ {exc}", file=sys.stderr)
        sys.exit(1)

