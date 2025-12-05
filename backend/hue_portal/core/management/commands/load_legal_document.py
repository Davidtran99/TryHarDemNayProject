import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from hue_portal.core.services import ingest_uploaded_document


class Command(BaseCommand):
    help = "Ingest a legal document (PDF/DOCX) into the database."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Path to PDF/DOCX file.")
        parser.add_argument("--code", required=True, help="Unique document code.")
        parser.add_argument("--title", help="Document title.")
        parser.add_argument("--doc-type", default="other", help="Document type tag.")
        parser.add_argument("--summary", default="", help="Short summary.")
        parser.add_argument("--issued-by", default="", help="Issuing authority.")
        parser.add_argument("--issued-at", help="Issued date (YYYY-MM-DD or DD/MM/YYYY).")
        parser.add_argument("--source-url", default="", help="Original source URL.")
        parser.add_argument("--metadata", help="JSON string with extra metadata.")

    def handle(self, *args, **options):
        file_path = Path(options["file"])
        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        metadata = {
            "code": options["code"],
            "title": options.get("title") or options["code"],
            "doc_type": options["doc_type"],
            "summary": options["summary"],
            "issued_by": options["issued_by"],
            "issued_at": options.get("issued_at"),
            "source_url": options["source_url"],
            "metadata": {},
        }
        if options.get("metadata"):
            try:
                metadata["metadata"] = json.loads(options["metadata"])
            except json.JSONDecodeError as exc:
                raise CommandError(f"Invalid metadata JSON: {exc}") from exc

        with file_path.open("rb") as file_obj:
            result = ingest_uploaded_document(
                file_obj=file_obj,
                filename=file_path.name,
                metadata=metadata,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Ingested document {result.document.code}. "
                f"Sections: {result.sections_count}, Images: {result.images_count}."
            )
        )

