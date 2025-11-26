from django.urls import path
from . import views

urlpatterns = [
    path("search/", views.search),
    path("chat/", views.chat),
    path("procedures/", views.procedures_list),
    path("procedures/<int:pk>/", views.procedures_detail),
    path("fines/", views.fines_list),
    path("fines/<int:pk>/", views.fines_detail),
    path("offices/", views.offices_list),
    path("offices/<int:pk>/", views.offices_detail),
    path("advisories/", views.advisories_list),
    path("advisories/<int:pk>/", views.advisories_detail),
    path("legal-sections/", views.legal_sections_list),
    path("legal-sections/<int:pk>/", views.legal_sections_detail),
    path(
        "legal-documents/<int:pk>/download/",
        views.legal_document_download,
        name="legal-document-download",
    ),
    path("legal-documents/upload/", views.legal_document_upload),
    path("legal-ingestion-jobs/", views.legal_ingestion_job_list),
    path("legal-ingestion-jobs/<uuid:job_id>/", views.legal_ingestion_job_detail),
]
