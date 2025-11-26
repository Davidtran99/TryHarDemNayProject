from __future__ import annotations

import os
from pathlib import Path

from celery import shared_task
from django.utils import timezone

from hue_portal.core.models import IngestionJob


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=30, retry_kwargs={"max_retries": 3})
def process_ingestion_job(self, job_id: str) -> None:
    job = IngestionJob.objects.filter(id=job_id).first()
    if not job:
        return

    job.status = IngestionJob.STATUS_RUNNING
    job.started_at = timezone.now()
    job.progress = 10
    job.save(update_fields=["status", "started_at", "progress", "updated_at"])

    try:
        storage_path = Path(job.storage_path)
        if not storage_path.exists():
            raise FileNotFoundError(f"Job file missing: {storage_path}")
        from hue_portal.core.services.legal_ingestion import ingest_uploaded_document

        with storage_path.open("rb") as handle:
            result = ingest_uploaded_document(
                file_obj=handle,
                filename=job.filename,
                metadata=job.metadata or {},
            )
        job.status = IngestionJob.STATUS_COMPLETED
        job.document = result.document
        job.finished_at = timezone.now()
        job.progress = 100
        job.stats = {"sections": result.sections_count, "images": result.images_count}
        job.save(
            update_fields=[
                "status",
                "document",
                "finished_at",
                "progress",
                "stats",
                "updated_at",
            ]
        )
        if os.getenv("DELETE_JOB_FILES_ON_SUCCESS", "false").lower() == "true":
            storage_path.unlink(missing_ok=True)
    except Exception as exc:  # pragma: no cover - logging path
        job.status = IngestionJob.STATUS_FAILED
        job.error_message = str(exc)
        job.finished_at = timezone.now()
        job.progress = 100
        job.save(
            update_fields=[
                "status",
                "error_message",
                "finished_at",
                "progress",
                "updated_at",
            ]
        )
        raise

