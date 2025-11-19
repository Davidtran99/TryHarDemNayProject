#!/usr/bin/env python3
"""
Parallel PaddleOCR runner for legal documents (CPU-friendly).

Example:
    PYTHONPATH=. ../.venv/bin/python scripts/ocr_parallel.py \
        --input media/legal_uploads/QD-69-TW/QD-69-TW/qd69_source.pdf \
        --output tmp/ocr_results \
        --workers 4
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Tuple

import fitz  # PyMuPDF
from PIL import Image

from hue_portal.core.ocr.paddle_extractor import PaddleOCRExtractor
from hue_portal.core.text.diacritics import restore_vietnamese_text


@dataclass
class PageOCRResult:
    page_index: int
    text: str


def _pixmap_to_pil(pix: fitz.Pixmap) -> Image.Image:
    mode = "RGB"
    if pix.n == 1:
        mode = "L"
    elif pix.n == 4:
        mode = "RGBA"
    return Image.frombytes(mode, [pix.width, pix.height], pix.samples)


_RESTORE_DIACRITICS = False


def _init_worker(restore_diacritics: bool):
    global _RESTORE_DIACRITICS
    _RESTORE_DIACRITICS = restore_diacritics
    PaddleOCRExtractor.get_instance()


def _process_page(task: Tuple[int, bytes, float]) -> PageOCRResult:
    page_index, page_bytes, zoom = task
    pdf = fitz.open(stream=page_bytes, filetype="pdf")
    page = pdf.load_page(0)
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    pil_img = _pixmap_to_pil(pix)
    extractor = PaddleOCRExtractor.get_instance()
    text = extractor.recognize_image(pil_img) if extractor else ""
    if _RESTORE_DIACRITICS and text:
        text = restore_vietnamese_text(text)
    return PageOCRResult(page_index=page_index, text=text)


def parallel_ocr(
    pdf_path: Path,
    output_dir: Path,
    workers: int,
    zoom: float,
    restore_diacritics: bool,
) -> None:
    pdf = fitz.open(pdf_path)
    tasks: List[Tuple[int, bytes, float]] = []
    for idx in range(pdf.page_count):
        single_pdf = fitz.open()
        single_pdf.insert_pdf(pdf, from_page=idx, to_page=idx)
        tasks.append((idx, single_pdf.tobytes(), zoom))

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{pdf_path.stem}_ocr.json"

    with mp.Pool(
        processes=workers,
        initializer=_init_worker,
        initargs=(restore_diacritics,),
    ) as pool:
        results = pool.map(_process_page, tasks)

    results.sort(key=lambda r: r.page_index)
    with output_file.open("w", encoding="utf-8") as f:
        json.dump([asdict(res) for res in results], f, ensure_ascii=False, indent=2)

    print(f"OCR complete. Saved to {output_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Parallel PaddleOCR helper.")
    parser.add_argument("--input", required=True, type=Path, help="PDF path.")
    parser.add_argument("--output", required=True, type=Path, help="Output directory.")
    parser.add_argument("--workers", type=int, default=max(1, mp.cpu_count() // 2))
    parser.add_argument("--zoom", type=float, default=2.0, help="Zoom factor for rasterization.")
    parser.add_argument(
        "--restore-diacritics",
        dest="restore_diacritics",
        action="store_true",
        help="Attempt to restore Vietnamese diacritics in OCR output.",
    )
    parser.add_argument(
        "--no-restore-diacritics",
        dest="restore_diacritics",
        action="store_false",
        help="Disable diacritic restoration.",
    )
    parser.set_defaults(restore_diacritics=True)
    args = parser.parse_args()

    parallel_ocr(
        args.input,
        args.output,
        workers=args.workers,
        zoom=args.zoom,
        restore_diacritics=args.restore_diacritics,
    )


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    main()

