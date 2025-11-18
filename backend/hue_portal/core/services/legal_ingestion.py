"""
Utilities to ingest uploaded legal documents into persistent storage.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, date
from io import BytesIO
from typing import BinaryIO, Dict, Optional
from pathlib import Path
import re

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from hue_portal.core.models import (
    LegalDocument,
    LegalSection,
    LegalDocumentImage,
    IngestionJob,
)
from hue_portal.core.etl.legal_document_loader import load_legal_document
from hue_portal.core.tasks import process_ingestion_job


@dataclass
class LegalIngestionResult:
    document: LegalDocument
    created: bool
    sections_count: int
    images_count: int


def _parse_date(value: Optional[str | date]) -> Optional[date]:
    if isinstance(value, date):
        return value
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _sha256(data: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(data)
    return digest.hexdigest()


def _normalize_text(text: str) -> str:
    cleaned = re.sub(r"\s+", "", text or "")
    return cleaned.lower()


DOC_TYPE_KEYWORDS = {
    "decision": ["quyết định"],
    "circular": ["thông tư"],
    "guideline": ["hướng dẫn"],
    "plan": ["kế hoạch"],
}


def _auto_fill_metadata(
    *, text: str, title: str, issued_by: str, issued_at: Optional[date], doc_type: str
) -> tuple[str, str, Optional[date], str]:
    head = (text or "")[:2000]
    if not issued_by:
        match = re.search(r"(BỘ\s+[A-ZÂĂÊÔƠƯ\s]+|ỦY BAN\s+NHÂN DÂN\s+[^\n]+)", head, re.IGNORECASE)
        if match:
            issued_by = match.group(0).strip()

    if not issued_at:
        match = re.search(
            r"(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})", head,
        )
        if match:
            day, month, year = match.groups()
            issued_at = _parse_date(f"{year}-{int(month):02d}-{int(day):02d}")
        else:
            match = re.search(
                r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})",
                head,
                re.IGNORECASE,
            )
            if match:
                day, month, year = match.groups()
                issued_at = _parse_date(f"{year}-{int(month):02d}-{int(day):02d}")

    if doc_type == "other":
        lower = head.lower()
        for dtype, keywords in DOC_TYPE_KEYWORDS.items():
            if any(keyword in lower for keyword in keywords):
                doc_type = dtype
                break

    if not title or title == (DOC_TYPE_KEYWORDS.get(doc_type, [title])[0] if doc_type != "other" else ""):
        match = re.search(r"(QUYẾT ĐỊNH|THÔNG TƯ|HƯỚNG DẪN|KẾ HOẠCH)[^\n]+", head, re.IGNORECASE)
        if match:
            title = match.group(0).strip().title()

    return title, issued_by, issued_at, doc_type


def ingest_uploaded_document(
    *,
    file_obj: BinaryIO,
    filename: str,
    metadata: Dict,
) -> LegalIngestionResult:
    """
    Ingest uploaded PDF/DOCX file, storing raw file, sections, and extracted images.

    Args:
        file_obj: Binary file-like object positioned at start.
        filename: Original filename.
        metadata: dict containing code, title, doc_type, summary, issued_by, issued_at, source_url, extra_metadata.
    """
    code = metadata.get("code", "").strip()
    if not code:
        raise ValueError("Document code is required.")

    title = metadata.get("title") or code
    doc_type = metadata.get("doc_type", "other")
    issued_at = _parse_date(metadata.get("issued_at"))
    summary = metadata.get("summary", "")
    issued_by = metadata.get("issued_by", "")
    source_url = metadata.get("source_url", "")
    extra_metadata = metadata.get("metadata") or {}

    file_bytes = file_obj.read()
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    checksum = _sha256(file_bytes)
    mime_type = metadata.get("mime_type") or getattr(file_obj, "content_type", "")
    size = len(file_bytes)

    extracted = load_legal_document(BytesIO(file_bytes), filename=filename)
    title, issued_by, issued_at, doc_type = _auto_fill_metadata(
        text=extracted.text, title=title, issued_by=issued_by, issued_at=issued_at, doc_type=doc_type
    )
    normalized_text = _normalize_text(extracted.text)
    content_checksum = _sha256(normalized_text.encode("utf-8"))

    duplicate = (
        LegalDocument.objects.filter(content_checksum=content_checksum)
        .exclude(code=code)
        .first()
    )
    if duplicate:
        raise ValueError(f"Nội dung trùng với văn bản hiện có: {duplicate.code}")

    with transaction.atomic():
        doc, created = LegalDocument.objects.get_or_create(
            code=code,
            defaults={
                "title": title,
                "doc_type": doc_type,
                "summary": summary,
                "issued_by": issued_by,
                "issued_at": issued_at,
                "source_url": source_url,
                "metadata": extra_metadata,
            },
        )

        # Update metadata if document already existed (keep latest info)
        doc.title = title
        doc.doc_type = doc_type
        doc.summary = summary
        doc.issued_by = issued_by
        doc.issued_at = issued_at
        doc.source_url = source_url
        doc.metadata = extra_metadata
        doc.page_count = extracted.page_count
        doc.raw_text = extracted.text
        doc.raw_text_ocr = extracted.ocr_text or ""
        doc.file_checksum = checksum
        doc.content_checksum = content_checksum
        doc.file_size = size
        doc.mime_type = mime_type
        doc.original_filename = filename
        doc.updated_at = timezone.now()

        # Save binary file
        content = ContentFile(file_bytes)
        storage_name = f"{code}/{filename}"
        doc.uploaded_file.save(storage_name, content, save=False)
        doc.source_file = doc.uploaded_file.name
        doc.save()

        # Replace sections
        doc.sections.all().delete()
        sections = []
        for idx, section in enumerate(extracted.sections, start=1):
            sections.append(
                LegalSection(
                    document=doc,
                    section_code=section.code,
                    section_title=section.title,
                    level=section.level,
                    order=idx,
                    content=section.content,
                    excerpt=section.content[:400],
                    page_start=section.page_start,
                    page_end=section.page_end,
                    is_ocr=section.is_ocr,
                    metadata=section.metadata or {},
                )
            )
        LegalSection.objects.bulk_create(sections, batch_size=200)

        # Replace images
        doc.images.all().delete()
        images = []
        for idx, image in enumerate(extracted.images, start=1):
            image_content = ContentFile(image.data)
            image_name = f"{code}/img_{idx}.{image.extension}"
            img_instance = LegalDocumentImage(
                document=doc,
                page_number=image.page_number,
                description=image.description,
                width=image.width,
                height=image.height,
                checksum=_sha256(image.data),
            )
            img_instance.image.save(image_name, image_content, save=False)
            images.append(img_instance)
        LegalDocumentImage.objects.bulk_create(images, batch_size=100)

    return LegalIngestionResult(
        document=doc,
        created=created,
        sections_count=len(sections),
        images_count=len(images),
    )


def enqueue_ingestion_job(*, file_obj, filename: str, metadata: Dict) -> IngestionJob:
    """
    Persist uploaded file to a temporary job folder and enqueue Celery processing.
    """

    job = IngestionJob.objects.create(
        code=metadata.get("code", ""),
        filename=filename,
        metadata=metadata,
        status=IngestionJob.STATUS_PENDING,
    )

    temp_dir = Path(settings.MEDIA_ROOT) / "ingestion_jobs" / str(job.id)
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / filename

    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    if hasattr(file_obj, "chunks"):
        with temp_path.open("wb") as dest:
            for chunk in file_obj.chunks():
                dest.write(chunk)
    else:
        data = file_obj.read()
        with temp_path.open("wb") as dest:
            dest.write(data)

    job.storage_path = str(temp_path)
    job.save(update_fields=["storage_path"])
    process_ingestion_job.delay(str(job.id))
    return job

