from django.core.management.base import BaseCommand, CommandError

from hue_portal.core.models import LegalDocument
from hue_portal.core.services import ingest_uploaded_document


class Command(BaseCommand):
    help = "Re-run ingestion on an existing legal document using the stored file"

    def add_arguments(self, parser):
        parser.add_argument("--code", required=True, help="Document code to reprocess")

    def handle(self, *args, **options):
        code = options["code"]
        try:
            doc = LegalDocument.objects.get(code=code)
        except LegalDocument.DoesNotExist as exc:
            raise CommandError(f"Legal document {code} not found") from exc

        if not doc.uploaded_file:
            raise CommandError("Document does not have an uploaded file to reprocess")

        metadata = {
            "code": doc.code,
            "title": doc.title,
            "doc_type": doc.doc_type,
            "summary": doc.summary,
            "issued_by": doc.issued_by,
            "issued_at": doc.issued_at.isoformat() if doc.issued_at else "",
            "source_url": doc.source_url,
            "metadata": doc.metadata,
            "mime_type": doc.mime_type,
        }

        with doc.uploaded_file.open("rb") as handle:
            ingest_uploaded_document(
                file_obj=handle,
                filename=doc.original_filename or doc.uploaded_file.name,
                metadata=metadata,
            )

        self.stdout.write(self.style.SUCCESS(f"Reprocessed document {code}"))

