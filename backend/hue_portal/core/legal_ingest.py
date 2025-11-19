"""
Utilities for ingesting legal documents using docTR OCR output.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

from django.contrib.postgres.search import SearchVector
from django.db import transaction

from hue_portal.core.models import LegalDocument, LegalSection
from hue_portal.core.ocr.doctr_extractor import DocTRExtractor, PageResult

logger = logging.getLogger(__name__)

ARTICLE_PATTERN = re.compile(r"^Điều\s+\d+[^\s]*", re.IGNORECASE)


@dataclass
class SectionDraft:
    order: int
    section_code: str
    section_title: str
    content_lines: List[str]
    page_start: Optional[int] = None
    page_end: Optional[int] = None

    def to_model(self, document: LegalDocument) -> LegalSection:
        content_text = "\n".join(self.content_lines).strip()
        excerpt = content_text[:500].strip()
        if not excerpt:
            excerpt = (self.section_title or self.section_code or "")[:200].strip()
        if not excerpt:
            excerpt = "-"
        return LegalSection(
            document=document,
            order=self.order,
            level="article",
            section_code=self.section_code,
            section_title=self.section_title,
            excerpt=excerpt,
            content=content_text,
            page_start=self.page_start,
            page_end=self.page_end,
            is_ocr=True,
        )


def _flatten_lines(pages: Iterable[PageResult]) -> List[dict]:
    flat: List[dict] = []
    for page in pages:
        before_count = len(flat)
        for block in page.blocks:
            for line in block.lines:
                text = (line.text or "").strip()
                if not text:
                    continue
                flat.append({"text": text, "page": page.page_index + 1})
        added = len(flat) - before_count
        print(f"[docTR] Trang {page.page_index + 1}: {added} dòng OCR")
    return flat


def _split_articles(lines: List[dict]) -> List[SectionDraft]:
    sections: List[SectionDraft] = []
    current: Optional[SectionDraft] = None
    order = 1

    for entry in lines:
        text = entry["text"]
        page = entry["page"]
        match = ARTICLE_PATTERN.match(text)
        if match:
            if current:
                sections.append(current)
            code = match.group(0).strip()
            current = SectionDraft(
                order=order,
                section_code=code,
                section_title=text.strip(),
                content_lines=[],
                page_start=page,
                page_end=page,
            )
            order += 1
        elif current:
            current.content_lines.append(text)
            current.page_end = page

    if current:
        sections.append(current)

    # Filter empty content
    cleaned = [
        section
        for section in sections
        if section.content_lines or section.section_title
    ]
    logger.info("Split %d Điều sections", len(cleaned))
    return cleaned


def ingest_legal_document(
    pdf_path: Path,
    code: str,
    title: str,
    doc_type: str,
    issued_date: Optional[str] = None,
    signer: str = "",
    agency: str = "",
) -> int:
    """
    OCR a PDF using docTR and ingest into LegalDocument/LegalSection tables.

    Args:
        pdf_path: Path to PDF file.
        code: Document code (unique).
        title: Human readable title.
        doc_type: Type (e.g., decision, circular).
        issued_date: Optional ISO date string.
        signer: Signer name.
        agency: Issuing agency.

    Returns:
        Number of sections created.
    """
    extractor = DocTRExtractor.get_instance()
    pages = extractor.extract_pages(pdf_path)
    lines = _flatten_lines(pages)
    if not lines:
        raise ValueError("Không tìm thấy nội dung sau OCR")

    issued = None
    if issued_date:
        try:
            issued = datetime.fromisoformat(issued_date).date()
        except ValueError:
            logger.warning("Không thể parse issued_date: %s", issued_date)

    sections = _split_articles(lines)
    raw_text = "\n".join(line["text"] for line in lines)

    with transaction.atomic():
        document, _ = LegalDocument.objects.update_or_create(
            code=code,
            defaults={
                "title": title,
                "doc_type": doc_type,
                "issued_date": issued,
                "signer": signer,
                "agency": agency,
                "raw_text": raw_text,
                "metadata": {"pages": len(pages)},
            },
        )
        document.sections.all().delete()
        section_models = [draft.to_model(document) for draft in sections]
        LegalSection.objects.bulk_create(section_models)
        LegalSection.objects.filter(document=document).update(
            tsv_body=SearchVector("section_title", "section_code", "content")
        )

    logger.info(
        "Ingested %s (%s) với %d Điều",
        document.title,
        document.code,
        len(section_models),
    )
    return len(section_models)

