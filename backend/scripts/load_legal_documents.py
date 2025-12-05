#!/usr/bin/env python3
"""
Load PDF/DOCX legal documents into the database with full text + sections.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
# Only add BACKEND_DIR to sys.path (not hue_portal subdirectory)
# Django needs to find hue_portal package (which is in backend/hue_portal)
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hue_portal.hue_portal.settings")

import django
django.setup()

from django.core.management import call_command  # noqa: E402


def parse_manifest(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Manifest must be a list of document entries.")
    return data


def ingest_document(root: Path, entry: Dict[str, Any], dry_run: bool = False) -> None:
    source_file = root / entry["source_file"]
    if not source_file.exists():
        raise FileNotFoundError(source_file)

    if dry_run:
        print(f"▶ (dry-run) Would ingest {entry['code']} from {source_file}")
        return

    args = {
        "file": str(source_file),
        "code": entry["code"],
        "title": entry.get("title"),
        "doc_type": entry.get("doc_type", "other"),
        "summary": entry.get("summary", ""),
        "issued_by": entry.get("issued_by", ""),
        "issued_at": entry.get("issued_at"),
        "source_url": entry.get("source_url", ""),
        "metadata": json.dumps(entry.get("metadata", {})),
    }
    print(f"▶ Loading {entry['code']} from {source_file}")
    call_command("load_legal_document", **args)


def main():
    parser = argparse.ArgumentParser(description="Load legal documents into DB.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).with_name("legal_documents_manifest.json"),
        help="Path to JSON manifest describing documents.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=PROJECT_ROOT,
        help="Root directory for relative source_file paths.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse files without DB writes.")
    args = parser.parse_args()

    manifest = parse_manifest(args.manifest)
    for entry in manifest:
        ingest_document(args.root, entry, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

