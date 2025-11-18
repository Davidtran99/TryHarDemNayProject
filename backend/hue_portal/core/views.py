from django.db.models.functions import Lower
from django.db.models import Q
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Procedure, Fine, Office, Advisory, Synonym
from .serializers import ProcedureSerializer, FineSerializer, OfficeSerializer, AdvisorySerializer
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

