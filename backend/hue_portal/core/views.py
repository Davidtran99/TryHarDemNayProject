import json
from django.conf import settings
from django.db.models.functions import Lower
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from pathlib import Path
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from .models import Procedure, Fine, Office, Advisory, LegalSection, LegalDocument, Synonym, IngestionJob
from .serializers import (
    ProcedureSerializer,
    FineSerializer,
    OfficeSerializer,
    AdvisorySerializer,
    LegalSectionSerializer,
    LegalDocumentSerializer,
    IngestionJobSerializer,
)
from .services import enqueue_ingestion_job
from .search_ml import search_with_ml
# Chatbot moved to hue_portal.chatbot app
# Keeping import for backward compatibility
try:
    from hue_portal.chatbot.chatbot import get_chatbot
except ImportError:
    from .chatbot import get_chatbot

def normalize_query(q: str) -> str:
  return (q or "").strip()

@api_view(["GET"])
def search(request):
  """Unified search endpoint - searches across all models."""
  q = normalize_query(request.GET.get("q", ""))
  type_ = request.GET.get("type")  # Optional: filter by type
  
  if not q:
    return Response({"error": "q parameter is required"}, status=400)
  
  results = []
  
  # Search Procedures
  if not type_ or type_ == "procedure":
    proc_qs = Procedure.objects.all()
    proc_text_fields = ["title", "domain", "conditions", "dossier"]
    proc_results = search_with_ml(proc_qs, q, proc_text_fields, top_k=10, min_score=0.1)
    for obj in proc_results:
      results.append({
        "type": "procedure",
        "data": ProcedureSerializer(obj).data,
        "relevance": getattr(obj, '_ml_score', 0.5)
      })
  
  # Search Fines
  if not type_ or type_ == "fine":
    fine_qs = Fine.objects.all()
    fine_text_fields = ["name", "code", "article", "decree", "remedial"]
    fine_results = search_with_ml(fine_qs, q, fine_text_fields, top_k=10, min_score=0.1)
    for obj in fine_results:
      results.append({
        "type": "fine",
        "data": FineSerializer(obj).data,
        "relevance": getattr(obj, '_ml_score', 0.5)
      })
  
  # Search Offices
  if not type_ or type_ == "office":
    office_qs = Office.objects.all()
    office_text_fields = ["unit_name", "address", "district", "service_scope"]
    office_results = search_with_ml(office_qs, q, office_text_fields, top_k=10, min_score=0.1)
    for obj in office_results:
      results.append({
        "type": "office",
        "data": OfficeSerializer(obj).data,
        "relevance": getattr(obj, '_ml_score', 0.5)
      })
  
  # Search Advisories
  if not type_ or type_ == "advisory":
    adv_qs = Advisory.objects.all()
    adv_text_fields = ["title", "summary"]
    adv_results = search_with_ml(adv_qs, q, adv_text_fields, top_k=10, min_score=0.1)
    for obj in adv_results:
      results.append({
        "type": "advisory",
        "data": AdvisorySerializer(obj).data,
        "relevance": getattr(obj, '_ml_score', 0.5)
      })

  if not type_ or type_ == "legal":
    legal_qs = LegalSection.objects.select_related("document").all()
    legal_text_fields = ["section_title", "section_code", "content"]
    legal_results = search_with_ml(legal_qs, q, legal_text_fields, top_k=10, min_score=0.1)
    for obj in legal_results:
      results.append({
        "type": "legal",
        "data": LegalSectionSerializer(obj, context={"request": request}).data,
        "relevance": getattr(obj, '_ml_score', 0.5)
      })
  
  # Sort by relevance score
  results.sort(key=lambda x: x["relevance"], reverse=True)
  
  return Response({
    "query": q,
    "count": len(results),
    "results": results[:50]  # Limit total results
  })

@api_view(["GET"])
def procedures_list(request):
  q = normalize_query(request.GET.get("q", ""))
  domain = request.GET.get("domain")
  level = request.GET.get("level")
  qs = Procedure.objects.all()
  if domain: qs = qs.filter(domain__iexact=domain)
  if level: qs = qs.filter(level__iexact=level)
  if q:
    # Use ML-based search for better results
    text_fields = ["title", "domain", "conditions", "dossier"]
    qs = search_with_ml(qs, q, text_fields, top_k=100, min_score=0.1)
  return Response(ProcedureSerializer(qs[:100], many=True).data)

@api_view(["GET"])
def procedures_detail(request, pk:int):
  try:
    obj = Procedure.objects.get(pk=pk)
  except Procedure.DoesNotExist:
    return Response(status=404)
  return Response(ProcedureSerializer(obj).data)

@api_view(["GET"])
def fines_list(request):
  q = normalize_query(request.GET.get("q", ""))
  code = request.GET.get("code")
  qs = Fine.objects.all()
  if code: qs = qs.filter(code__iexact=code)
  if q:
    # Use ML-based search for better results
    text_fields = ["name", "code", "article", "decree", "remedial"]
    qs = search_with_ml(qs, q, text_fields, top_k=100, min_score=0.1)
  return Response(FineSerializer(qs[:100], many=True).data)

@api_view(["GET"])
def fines_detail(request, pk:int):
  try:
    obj = Fine.objects.get(pk=pk)
  except Fine.DoesNotExist:
    return Response(status=404)
  return Response(FineSerializer(obj).data)

@api_view(["GET"])
def offices_list(request):
  q = normalize_query(request.GET.get("q", ""))
  district = request.GET.get("district")
  qs = Office.objects.all()
  if district: qs = qs.filter(district__iexact=district)
  if q:
    # Use ML-based search for better results
    text_fields = ["unit_name", "address", "district", "service_scope"]
    qs = search_with_ml(qs, q, text_fields, top_k=100, min_score=0.1)
  return Response(OfficeSerializer(qs[:100], many=True).data)

@api_view(["GET"])
def offices_detail(request, pk:int):
  try:
    obj = Office.objects.get(pk=pk)
  except Office.DoesNotExist:
    return Response(status=404)
  return Response(OfficeSerializer(obj).data)

@api_view(["GET"])
def advisories_list(request):
  q = normalize_query(request.GET.get("q", ""))
  qs = Advisory.objects.all().order_by("-published_at")
  if q:
    # Use ML-based search for better results
    text_fields = ["title", "summary"]
    qs = search_with_ml(qs, q, text_fields, top_k=100, min_score=0.1)
  return Response(AdvisorySerializer(qs[:100], many=True).data)

@api_view(["GET"])
def advisories_detail(request, pk:int):
  try:
    obj = Advisory.objects.get(pk=pk)
  except Advisory.DoesNotExist:
    return Response(status=404)
  return Response(AdvisorySerializer(obj).data)

@api_view(["GET"])
def legal_sections_list(request):
  q = normalize_query(request.GET.get("q", ""))
  document_code = request.GET.get("document_code")
  section_code = request.GET.get("section_code")
  qs = LegalSection.objects.select_related("document").all()
  if document_code:
    qs = qs.filter(document__code__iexact=document_code)
  if section_code:
    qs = qs.filter(section_code__icontains=section_code)
  if q:
    text_fields = ["section_title", "section_code", "content"]
    qs = search_with_ml(qs, q, text_fields, top_k=100, min_score=0.1)
  return Response(LegalSectionSerializer(qs[:100], many=True, context={"request": request}).data)

@api_view(["GET"])
def legal_sections_detail(request, pk:int):
  try:
    obj = LegalSection.objects.select_related("document").get(pk=pk)
  except LegalSection.DoesNotExist:
    return Response(status=404)
  return Response(LegalSectionSerializer(obj, context={"request": request}).data)

@api_view(["GET"])
def legal_document_download(request, pk:int):
  try:
    doc = LegalDocument.objects.get(pk=pk)
  except LegalDocument.DoesNotExist:
    raise Http404("Document not found")
  if not doc.source_file:
    raise Http404("Document missing source file")
  file_path = Path(doc.source_file)
  if not file_path.exists():
    raise Http404("Source file not found on server")
  response = FileResponse(open(file_path, "rb"), as_attachment=True, filename=file_path.name)
  return response


def _has_upload_access(request):
  if getattr(request, "user", None) and request.user.is_authenticated:
    return True
  expected = getattr(settings, "LEGAL_UPLOAD_TOKEN", "")
  header_token = request.headers.get("X-Upload-Token")
  return bool(expected and header_token and header_token == expected)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def legal_document_upload(request):
  if not _has_upload_access(request):
    return Response({"error": "unauthorized"}, status=403)

  upload = request.FILES.get("file")
  if not upload:
    return Response({"error": "file is required"}, status=400)

  code = (request.data.get("code") or "").strip()
  if not code:
    return Response({"error": "code is required"}, status=400)

  metadata = {
    "code": code,
    "title": request.data.get("title") or code,
    "doc_type": request.data.get("doc_type", "other"),
    "summary": request.data.get("summary", ""),
    "issued_by": request.data.get("issued_by", ""),
    "issued_at": request.data.get("issued_at"),
    "source_url": request.data.get("source_url", ""),
    "mime_type": request.data.get("mime_type") or getattr(upload, "content_type", ""),
    "metadata": {},
  }
  extra_meta = request.data.get("metadata")
  if extra_meta:
    try:
      metadata["metadata"] = json.loads(extra_meta) if isinstance(extra_meta, str) else extra_meta
    except Exception:
      return Response({"error": "metadata must be valid JSON"}, status=400)

  try:
    job = enqueue_ingestion_job(
      file_obj=upload,
      filename=upload.name,
      metadata=metadata,
    )
  except ValueError as exc:
    return Response({"error": str(exc)}, status=400)
  except Exception as exc:
    return Response({"error": str(exc)}, status=500)

  serialized = IngestionJobSerializer(job, context={"request": request}).data
  return Response(serialized, status=202)


@api_view(["GET"])
def legal_ingestion_job_detail(request, job_id):
  job = get_object_or_404(IngestionJob, id=job_id)
  return Response(IngestionJobSerializer(job, context={"request": request}).data)


@api_view(["GET"])
def legal_ingestion_job_list(request):
  code = request.GET.get("code")
  qs = IngestionJob.objects.all()
  if code:
    qs = qs.filter(code=code)
  qs = qs.order_by("-created_at")[:20]
  serializer = IngestionJobSerializer(qs, many=True, context={"request": request})
  return Response(serializer.data)

@api_view(["POST"])
def chat(request):
  """Chatbot endpoint for natural language queries."""
  message = request.data.get("message", "").strip()
  if not message:
    return Response({"error": "message is required"}, status=400)
  
  try:
    chatbot = get_chatbot()
    response = chatbot.generate_response(message)
    return Response(response)
  except Exception as e:
    return Response({
      "message": "Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.",
      "intent": "error",
      "error": str(e),
      "results": [],
      "count": 0
    }, status=500)

