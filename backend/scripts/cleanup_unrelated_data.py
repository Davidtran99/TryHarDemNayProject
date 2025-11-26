#!/usr/bin/env python3
"""
Script để xóa tất cả dữ liệu không liên quan đến 4 file legal documents được chỉ định.
Chỉ giữ lại:
1. 1. BIÊN SOẠN THÔNG TƯ 02.docx
2. 264-QD_TW_644732 sửa đổi bổ sung QĐ 69 về kỷ luật đảng viên.doc
3. QD-69-TW về kỷ luật đảng viên.pdf
4. THÔNG TƯ 02 VỀ XỬ LÝ ĐIỀU LỆNH TRONG CAND.docx
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"

# Add backend directory to sys.path for Django
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hue_portal.hue_portal.settings")

import django
django.setup()

from django.db import transaction
from hue_portal.core.models import (
    Fine,
    Office,
    Procedure,
    Advisory,
    LegalDocument,
    LegalSection,
    LegalDocumentImage,
)


# Danh sách các file được giữ lại (theo code hoặc original_filename)
KEEP_DOCUMENT_CODES = [
    "QD-69-TW",
    "TT-02-CAND",
    "TT-02-BIEN-SOAN",
    "264-QD-TW",
]

KEEP_FILENAMES = [
    "QD-69-TW về kỷ luật đảng viên.pdf",
    "THÔNG TƯ 02 VỀ XỬ LÝ ĐIỀU LỆNH TRONG CAND.docx",
    "1. BIÊN SOẠN THÔNG TƯ 02.docx",
    "264-QD_TW_644732 sửa đổi bổ sung QĐ 69 về kỷ luật đảng viên.doc",
]


def get_keep_document_ids() -> set[int]:
    """Lấy IDs của các LegalDocument cần giữ lại."""
    keep_ids = set()
    
    # Tìm theo code
    for code in KEEP_DOCUMENT_CODES:
        docs = LegalDocument.objects.filter(code=code)
        for doc in docs:
            keep_ids.add(doc.id)
            print(f"✅ Giữ lại document: {doc.code} - {doc.title}")
    
    # Tìm theo original_filename
    for filename in KEEP_FILENAMES:
        docs = LegalDocument.objects.filter(original_filename__icontains=filename.split("/")[-1])
        for doc in docs:
            keep_ids.add(doc.id)
            if doc.id not in keep_ids:
                print(f"✅ Giữ lại document: {doc.code} - {doc.title} (theo filename)")
    
    return keep_ids


def cleanup_unrelated_data(dry_run: bool = False) -> None:
    """Xóa tất cả dữ liệu không liên quan đến 4 file được chỉ định."""
    print("=" * 60)
    print("🧹 Dọn dẹp dữ liệu không liên quan")
    print("=" * 60)
    
    if dry_run:
        print("⚠️  DRY RUN MODE - Không thực sự xóa dữ liệu")
        print()
    
    # Lấy IDs của documents cần giữ lại
    keep_doc_ids = get_keep_document_ids()
    print(f"\n📋 Sẽ giữ lại {len(keep_doc_ids)} document(s)")
    
    if not keep_doc_ids:
        print("⚠️  Không tìm thấy document nào cần giữ lại!")
        print("   Có thể các file chưa được load vào database.")
        print("   Chạy: python backend/scripts/load_legal_documents.py")
        return
    
    with transaction.atomic():
        # 1. Xóa tất cả Fines
        fines_count = Fine.objects.count()
        if not dry_run:
            Fine.objects.all().delete()
        print(f"🗑️  {'Sẽ xóa' if dry_run else 'Đã xóa'} {fines_count} Fine(s)")
        
        # 2. Xóa tất cả Procedures
        procedures_count = Procedure.objects.count()
        if not dry_run:
            Procedure.objects.all().delete()
        print(f"🗑️  {'Sẽ xóa' if dry_run else 'Đã xóa'} {procedures_count} Procedure(s)")
        
        # 3. Xóa tất cả Advisories
        advisories_count = Advisory.objects.count()
        if not dry_run:
            Advisory.objects.all().delete()
        print(f"🗑️  {'Sẽ xóa' if dry_run else 'Đã xóa'} {advisories_count} Advisory(ies)")
        
        # 4. Xóa tất cả Offices
        offices_count = Office.objects.count()
        if not dry_run:
            Office.objects.all().delete()
        print(f"🗑️  {'Sẽ xóa' if dry_run else 'Đã xóa'} {offices_count} Office(s)")
        
        # 5. Xóa LegalDocumentImage của documents không được giữ lại
        images_to_delete = LegalDocumentImage.objects.exclude(document_id__in=keep_doc_ids)
        images_count = images_to_delete.count()
        if not dry_run:
            images_to_delete.delete()
        print(f"🗑️  {'Sẽ xóa' if dry_run else 'Đã xóa'} {images_count} LegalDocumentImage(s)")
        
        # 6. Xóa LegalSection của documents không được giữ lại
        sections_to_delete = LegalSection.objects.exclude(document_id__in=keep_doc_ids)
        sections_count = sections_to_delete.count()
        if not dry_run:
            sections_to_delete.delete()
        print(f"🗑️  {'Sẽ xóa' if dry_run else 'Đã xóa'} {sections_count} LegalSection(s)")
        
        # 7. Xóa LegalDocument không được giữ lại
        docs_to_delete = LegalDocument.objects.exclude(id__in=keep_doc_ids)
        docs_count = docs_to_delete.count()
        if not dry_run:
            # Liệt kê các document sẽ bị xóa
            print(f"\n📄 Các document sẽ bị xóa ({docs_count}):")
            for doc in docs_to_delete:
                print(f"   - {doc.code}: {doc.title}")
            docs_to_delete.delete()
        print(f"🗑️  {'Sẽ xóa' if dry_run else 'Đã xóa'} {docs_count} LegalDocument(s)")
        
        if dry_run:
            print("\n⚠️  DRY RUN - Không có dữ liệu nào bị xóa thực sự")
            print("   Chạy lại không có --dry-run để thực sự xóa")
        else:
            print("\n✅ Hoàn tất dọn dẹp!")
            print(f"   Giữ lại {len(keep_doc_ids)} document(s)")
            print("\n📝 Bước tiếp theo:")
            print("   1. Regenerate embeddings: python backend/scripts/generate_embeddings.py")
            print("   2. Rebuild FAISS index: python backend/scripts/build_faiss_index.py")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Xóa dữ liệu không liên quan đến 4 file legal documents")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chỉ hiển thị sẽ xóa gì, không thực sự xóa",
    )
    args = parser.parse_args()
    
    cleanup_unrelated_data(dry_run=args.dry_run)


if __name__ == "__main__":
    main()




