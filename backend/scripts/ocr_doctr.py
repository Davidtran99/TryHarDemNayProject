#!/usr/bin/env python3
"""
docTR OCR CLI helper.

Example:
    PYTHONPATH=. ../.venv/bin/python scripts/ocr_doctr.py \
        --pdf ../tài\ nguyên/QD-69-TW\ về\ kỷ\ luật\ đảng\ viên.pdf \
        --pages 0,1 \
        --output tmp/doctr_qd69.json
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Optional

from hue_portal.core.ocr.doctr_extractor import run_doctr_ocr


def parse_pages(value: Optional[str]) -> Optional[List[int]]:
    if not value:
        return None
    pages: List[int] = []
    for segment in value.split(","):
        segment = segment.strip()
        if not segment:
            continue
        if "-" in segment:
            start_str, end_str = segment.split("-", 1)
            start = int(start_str)
            end = int(end_str)
            pages.extend(range(start, end + 1))
        else:
            pages.append(int(segment))
    return pages


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run docTR OCR on a PDF file.")
    parser.add_argument("--pdf", required=True, type=Path, help="Path to PDF file.")
    parser.add_argument(
        "--pages",
        type=str,
        help="Comma-separated page indexes or ranges (e.g. 0,1,2-4). Default: all pages.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tmp/doctr_output.json"),
        help="Path to JSON output.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pages = parse_pages(args.pages)
    run_doctr_ocr(args.pdf, args.output, page_indices=pages)
    print(f"docTR OCR saved to {args.output}")


if __name__ == "__main__":
    main()

