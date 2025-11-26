from django.contrib import admin
from .models import (
    Procedure,
    Fine,
    Office,
    Advisory,
    Synonym,
    LegalDocument,
    LegalSection,
    LegalDocumentImage,
    IngestionJob,
)

@admin.register(Procedure)
class ProcedureAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "domain", "level", "updated_at")
    search_fields = ("title", "conditions", "dossier")
    list_filter = ("domain", "level")

@admin.register(Fine)
class FineAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "decree")
    search_fields = ("code", "name", "article")

@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    list_display = ("id", "unit_name", "district", "phone")
    search_fields = ("unit_name", "address", "district")
    list_filter = ("district",)

@admin.register(Advisory)
class AdvisoryAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "published_at")
    search_fields = ("title", "summary")

@admin.register(Synonym)
class SynonymAdmin(admin.ModelAdmin):
    list_display = ("id", "keyword", "alias")
    search_fields = ("keyword", "alias")


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "title", "doc_type", "issued_at")
    search_fields = ("code", "title", "summary", "issued_by")
    list_filter = ("doc_type", "issued_by")


@admin.register(LegalSection)
class LegalSectionAdmin(admin.ModelAdmin):
    list_display = ("id", "document", "section_code", "level", "order")
    list_filter = ("level",)
    search_fields = ("section_code", "section_title", "content")
    autocomplete_fields = ("document",)


@admin.register(LegalDocumentImage)
class LegalDocumentImageAdmin(admin.ModelAdmin):
    list_display = ("id", "document", "page_number", "width", "height")
    search_fields = ("document__code", "description")
    list_filter = ("page_number",)


from .tasks import process_ingestion_job


@admin.register(IngestionJob)
class IngestionJobAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "status", "filename", "created_at", "finished_at")
    search_fields = ("code", "filename", "error_message")
    list_filter = ("status", "created_at")
    autocomplete_fields = ("document",)
    readonly_fields = ("storage_path", "error_message", "stats")
    actions = ["retry_jobs"]

    @admin.action(description="Retry selected ingestion jobs")
    def retry_jobs(self, request, queryset):
        for job in queryset:
            job.status = job.STATUS_PENDING
            job.progress = 0
            job.error_message = ""
            job.save(update_fields=["status", "progress", "error_message", "updated_at"])
            process_ingestion_job.delay(str(job.id))
        self.message_user(request, f"Đã requeue {queryset.count()} tác vụ")
