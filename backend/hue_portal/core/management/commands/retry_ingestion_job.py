from django.core.management.base import BaseCommand, CommandError

from hue_portal.core.models import IngestionJob
from hue_portal.core.tasks import process_ingestion_job


class Command(BaseCommand):
    help = "Retry a failed ingestion job by ID"

    def add_arguments(self, parser):
        parser.add_argument("job_id", help="UUID of the ingestion job to retry")

    def handle(self, job_id, **options):
        try:
            job = IngestionJob.objects.get(id=job_id)
        except IngestionJob.DoesNotExist as exc:
            raise CommandError(f"Ingestion job {job_id} not found") from exc

        job.status = IngestionJob.STATUS_PENDING
        job.error_message = ""
        job.progress = 0
        job.save(update_fields=["status", "error_message", "progress", "updated_at"])
        process_ingestion_job.delay(str(job.id))
        self.stdout.write(self.style.SUCCESS(f"Re-queued ingestion job {job.id}"))

