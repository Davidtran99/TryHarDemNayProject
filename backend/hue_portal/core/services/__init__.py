"""
Service layer for reusable domain operations.
"""

from .legal_ingestion import (
    ingest_uploaded_document,
    LegalIngestionResult,
    enqueue_ingestion_job,
)

__all__ = ["ingest_uploaded_document", "LegalIngestionResult", "enqueue_ingestion_job"]

