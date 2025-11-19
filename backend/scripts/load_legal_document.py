#!/usr/bin/env python3
"""
Helper script to OCR + ingest a legal document into the database.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hue_portal.hue_portal.settings")

import django  # noqa: E402

django.setup()

from hue_portal.core.legal_ingest import ingest_legal_document  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest legal document via docTR OCR.")
    parser.add_argument("--pdf", required=True, type=Path, help="Path to PDF file.")
    parser.add_argument("--code", required=True, help="Document code (unique).")
    parser.add_argument("--title", required=True, help="Document title.")
    parser.add_argument(
        "--doc-type", default="decision", help="Document type (decision/circular/...)."
    )
    parser.add_argument("--issued-date", help="Issued date (YYYY-MM-DD).")
    parser.add_argument("--signer", default="", help="Signer name.")
    parser.add_argument("--agency", default="", help="Issuing agency.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    count = ingest_legal_document(
        pdf_path=args.pdf,
        code=args.code,
        title=args.title,
        doc_type=args.doc_type,
        issued_date=args.issued_date,
        signer=args.signer,
        agency=args.agency,
    )
    print(f"Đã ingest {count} Điều vào DB.")


if __name__ == "__main__":
    main()

