from django.contrib import admin
from .models import Procedure, Fine, Office, Advisory, Synonym

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

