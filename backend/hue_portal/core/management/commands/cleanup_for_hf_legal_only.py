from __future__ import annotations

"""
Management command to clean structured data for HF Space demo.

This command:
- Deletes all records from structured models: Fine, Procedure, Office, Advisory.
- Keeps only the four specified LegalDocument and related LegalSection/LegalDocumentImage.

Intended to be idempotent and safe to re-run.
"""

from typing import List

from django.core.management.base import BaseCommand

from hue_portal.core.models import (
    Advisory,
    Fine,
    LegalDocument,
    LegalDocumentImage,
    LegalSection,
    Office,
    Procedure,
)


LEGAL_CODES_TO_KEEP: List[str] = [
    "TT-02-BIEN-SOAN",
    "264-QD-TW",
    "QD-69-TW",
    "TT-02-CAND",
]


class Command(BaseCommand):
    """Clean database so that only 4 legal documents and their sections remain."""

    help = (
        "Xóa dữ liệu không liên quan cho demo HF Space:\n"
        "- Xóa toàn bộ Fine/Procedure/Office/Advisory.\n"
        "- Giữ lại duy nhất 4 LegalDocument được chỉ định và các LegalSection/LegalDocumentImage liên quan."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Chỉ in ra số lượng sẽ xóa, không thực hiện xóa.",
        )

    def handle(self, *args, **options) -> None:
        dry_run: bool = bool(options.get("dry_run"))

        # 1. Wipe structured data
        self.stdout.write(self.style.MIGRATE_HEADING("🧹 Xóa dữ liệu structured (Fine/Procedure/Office/Advisory)..."))
        structured_models = [Fine, Procedure, Office, Advisory]

        for model in structured_models:
            qs = model.objects.all()
            count = qs.count()
            if dry_run:
                self.stdout.write(f"[DRY-RUN] Sẽ xóa {count} bản ghi từ {model.__name__}")
            else:
                deleted, _ = qs.delete()
                self.stdout.write(f"Đã xóa {deleted} bản ghi từ {model.__name__}")

        # 2. Remove legal documents not in the keep-list
        self.stdout.write(self.style.MIGRATE_HEADING("🧹 Xóa LegalDocument/LegalSection/LegalDocumentImage không thuộc 4 mã chỉ định..."))

        keep_codes_display = ", ".join(LEGAL_CODES_TO_KEEP)
        self.stdout.write(f"Giữ lại các mã: {keep_codes_display}")

        # Sections & images will be cascaded when deleting documents, but we log counts explicitly.
        sections_to_delete = LegalSection.objects.exclude(document__code__in=LEGAL_CODES_TO_KEEP)
        images_to_delete = LegalDocumentImage.objects.exclude(document__code__in=LEGAL_CODES_TO_KEEP)
        docs_to_delete = LegalDocument.objects.exclude(code__in=LEGAL_CODES_TO_KEEP)

        sec_count = sections_to_delete.count()
        img_count = images_to_delete.count()
        doc_count = docs_to_delete.count()

        if dry_run:
            self.stdout.write(
                f"[DRY-RUN] Sẽ xóa {doc_count} LegalDocument, "
                f"{sec_count} LegalSection, {img_count} LegalDocumentImage (nếu tồn tại)."
            )
        else:
            # Delete sections and images explicitly for clearer logging, then documents.
            deleted_sections, _ = sections_to_delete.delete()
            deleted_images, _ = images_to_delete.delete()
            deleted_docs, _ = docs_to_delete.delete()
            self.stdout.write(
                f"Đã xóa {deleted_docs} LegalDocument, "
                f"{deleted_sections} LegalSection, {deleted_images} LegalDocumentImage."
            )

        # 3. Final summary of remaining legal documents
        remaining_docs = list(
            LegalDocument.objects.filter(code__in=LEGAL_CODES_TO_KEEP).values_list("code", "title")
        )
        self.stdout.write(self.style.SUCCESS("✅ Hoàn tất dọn dữ liệu cho HF Space."))
        self.stdout.write(f"Còn lại {len(remaining_docs)} LegalDocument:")
        for code, title in remaining_docs:
            self.stdout.write(f"- {code}: {title}")


