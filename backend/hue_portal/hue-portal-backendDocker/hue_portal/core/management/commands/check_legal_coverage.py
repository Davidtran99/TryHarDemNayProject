"""
Management command to check data coverage for the 4 legal documents.
"""
from __future__ import annotations

from typing import Any, Dict, List
from django.core.management.base import BaseCommand
from django.db.models import Q, Count
from hue_portal.core.models import LegalDocument, LegalSection


# Target legal documents
TARGET_DOCUMENTS = [
    "QD-69-TW",
    "TT-02-CAND",
    "TT-02-BIEN-SOAN",
    "264-QD-TW",
]


class Command(BaseCommand):
    help = "Check data coverage for 4 legal documents in the database"

    def handle(self, *args: Any, **options: Any) -> None:
        self.stdout.write(self.style.MIGRATE_HEADING("Checking legal document coverage..."))

        total_issues = 0
        for doc_code in TARGET_DOCUMENTS:
            issues = self._check_document(doc_code)
            total_issues += len(issues)
            if issues:
                self.stdout.write(self.style.WARNING(f"\n⚠️ Issues found for {doc_code}:"))
                for issue in issues:
                    self.stdout.write(f"  - {issue}")
            else:
                self.stdout.write(self.style.SUCCESS(f"✅ {doc_code}: OK"))

        if total_issues == 0:
            self.stdout.write(self.style.SUCCESS("\n✅ All documents have complete coverage!"))
        else:
            self.stdout.write(
                self.style.WARNING(f"\n⚠️ Found {total_issues} total issues across documents.")
            )

    def _check_document(self, doc_code: str) -> List[str]:
        """Check a single document for coverage issues."""
        issues: List[str] = []

        try:
            doc = LegalDocument.objects.get(code=doc_code)
        except LegalDocument.DoesNotExist:
            issues.append(f"Document {doc_code} not found in database")
            return issues

        # Check document-level fields
        if not doc.code:
            issues.append("Missing 'code' field")
        if not doc.title:
            issues.append("Missing 'title' field")
        if not doc.raw_text:
            issues.append("Missing 'raw_text' field")
        if not doc.tsv_body:
            issues.append("Missing 'tsv_body' (search vector not populated)")

        # Check sections
        sections = doc.sections.all()
        section_count = sections.count()

        if section_count == 0:
            issues.append("No sections found for this document")
            return issues

        self.stdout.write(f"\n  {doc_code}: {section_count} sections found")

        # Check section-level fields
        missing_content = sections.filter(Q(content__isnull=True) | Q(content="")).count()
        if missing_content > 0:
            issues.append(f"{missing_content} sections missing 'content' field")

        missing_section_code = sections.filter(
            Q(section_code__isnull=True) | Q(section_code="")
        ).count()
        if missing_section_code > 0:
            issues.append(f"{missing_section_code} sections missing 'section_code' field")

        missing_tsv = sections.filter(tsv_body__isnull=True).count()
        if missing_tsv > 0:
            issues.append(f"{missing_tsv} sections missing 'tsv_body' (search vector not populated)")

        # Check embeddings (dimension 1024)
        sections_with_embedding = sections.exclude(embedding__isnull=True).count()
        sections_without_embedding = section_count - sections_with_embedding

        if sections_without_embedding > 0:
            issues.append(
                f"{sections_without_embedding} sections missing 'embedding' "
                f"({sections_with_embedding}/{section_count} have embeddings)"
            )

        # Check for potential data quality issues
        # Look for sections that might be truncated (very short content)
        very_short_sections = sections.filter(content__length__lt=50).count()
        if very_short_sections > 0:
            issues.append(
                f"{very_short_sections} sections have very short content (<50 chars) - "
                "may be truncated"
            )

        # Check section ordering
        sections_ordered = sections.order_by("order")
        prev_order = -1
        order_gaps = 0
        for section in sections_ordered:
            if section.order <= prev_order:
                order_gaps += 1
            prev_order = section.order

        if order_gaps > 0:
            issues.append(f"Found {order_gaps} potential ordering issues in sections")

        return issues

