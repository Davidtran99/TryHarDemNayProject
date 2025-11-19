"""
docTR-based OCR extractor for legal documents.

Provides a cached predictor and utilities to export structured JSON
(`page -> blocks -> lines -> words`) ready for downstream ETL.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from hue_portal.core.text.diacritics import restore_vietnamese_text

logger = logging.getLogger(__name__)

try:
    from doctr.io import DocumentFile
    from doctr.models import ocr_predictor
except ImportError:  # pragma: no cover - optional dependency
    DocumentFile = None  # type: ignore
    ocr_predictor = None  # type: ignore
    logger.warning(
        "docTR libraries not available. Install `python-doctr` to enable docTR OCR."
    )


@dataclass
class WordResult:
    text: str
    confidence: float
    box: List[float]


@dataclass
class LineResult:
    text: str
    confidence: float
    box: List[float]
    words: List[WordResult]


@dataclass
class BlockResult:
    lines: List[LineResult]
    box: List[float]


@dataclass
class PageResult:
    page_index: int
    width: int
    height: int
    blocks: List[BlockResult]


class DocTRExtractor:
    """Singleton wrapper around docTR's ocr_predictor."""

    _instance: Optional["DocTRExtractor"] = None

    def __init__(
        self,
        det_arch: str = "db_resnet50",
        reco_arch: str = "crnn_vgg16_bn",
        assume_straight_pages: bool = True,
        export_as_straight_boxes: bool = True,
    ) -> None:
        if ocr_predictor is None:
            raise RuntimeError("python-doctr is not installed.")
        logger.info(
            "Initializing docTR predictor det=%s reco=%s", det_arch, reco_arch
        )
        self._det_arch = det_arch
        self._reco_arch = reco_arch
        self._predictor = ocr_predictor(
            det_arch=det_arch,
            reco_arch=reco_arch,
            pretrained=True,
            assume_straight_pages=assume_straight_pages,
            export_as_straight_boxes=export_as_straight_boxes,
        )

    @classmethod
    def get_instance(cls) -> "DocTRExtractor":
        if cls._instance is None:
            det_arch = os.getenv("DOCTR_DET_ARCH", "db_resnet50")
            reco_arch = os.getenv("DOCTR_RECO_ARCH", "crnn_vgg16_bn")
            cls._instance = cls(det_arch=det_arch, reco_arch=reco_arch)
        return cls._instance

    def extract_pages(
        self,
        pdf_path: Path,
        page_indices: Optional[Sequence[int]] = None,
    ) -> List[PageResult]:
        if DocumentFile is None:
            raise RuntimeError("python-doctr is not installed.")
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        document = DocumentFile.from_pdf(str(pdf_path))
        if page_indices:
            doc_pages = [document[i] for i in page_indices]
        else:
            doc_pages = list(document)
        logger.info(
            "Running docTR on %s (%d pages)", pdf_path.name, len(doc_pages)
        )
        result = self._predictor(doc_pages)
        pages: List[PageResult] = []
        for idx, (page, pred_page) in enumerate(zip(doc_pages, result.pages)):
            blocks: List[BlockResult] = []
            for block in pred_page.blocks:
                lines: List[LineResult] = []
                for line in block.lines:
                    words: List[WordResult] = []
                    for word in line.words:
                        words.append(
                            WordResult(
                                text=restore_vietnamese_text(word.value),
                                confidence=float(word.confidence or 0.0),
                                box=list(word.geometry or []),
                            )
                        )
                    line_text = " ".join(word.text for word in words).strip()
                    avg_conf = (
                        sum(w.confidence for w in words) / len(words)
                        if words
                        else 0.0
                    )
                    lines.append(
                        LineResult(
                            text=line_text,
                            confidence=avg_conf,
                            box=list(line.geometry or []),
                            words=words,
                        )
                    )
                blocks.append(
                    BlockResult(
                        lines=lines,
                        box=list(block.geometry or []),
                    )
                )
            width = getattr(page, "shape", (0, 0))[1]
            height = getattr(page, "shape", (0, 0))[0]
            pages.append(
                PageResult(
                    page_index=page_indices[idx] if page_indices else idx,
                    width=int(width),
                    height=int(height),
                    blocks=blocks,
                )
            )
        return pages

    def extract_as_dict(
        self, pdf_path: Path, page_indices: Optional[Sequence[int]] = None
    ) -> Dict[str, Any]:
        pages = self.extract_pages(pdf_path, page_indices)
        return {
            "pdf": str(pdf_path),
            "pages": [asdict(page) for page in pages],
        }


def run_doctr_ocr(
    pdf_path: Path,
    output_path: Path,
    page_indices: Optional[Sequence[int]] = None,
) -> Dict[str, Any]:
    """Convenience function to extract and write JSON output."""
    extractor = DocTRExtractor.get_instance()
    data = extractor.extract_as_dict(pdf_path, page_indices)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    import json

    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    logger.info("docTR OCR saved to %s", output_path)
    return data

