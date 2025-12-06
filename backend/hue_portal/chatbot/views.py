"""
Chatbot API views for handling conversational queries.
"""
import json
import logging
import uuid
from typing import Any, Dict, Optional

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .chatbot import get_chatbot
from hue_portal.chatbot.context_manager import ConversationContext

logger = logging.getLogger(__name__)


class ChatThrottle(AnonRateThrottle):
    """
    Custom throttle for chat endpoint.
    Rate: 30 requests per minute for HF Space CPU constraints.
    """
    rate = '30/minute'


def _apply_selected_document_code(session_id: Optional[str], code: Optional[str]) -> None:
    """Persist or clear the selected document code for a session."""
    if not session_id:
        return
    if not code:
        return
    normalized = str(code).strip()
    if not normalized:
        ConversationContext.clear_session_metadata_keys(session_id, ["selected_document_code"])
        return
    if normalized == "__other__":
        ConversationContext.clear_session_metadata_keys(session_id, ["selected_document_code"])
        return
    ConversationContext.update_session_metadata(
        session_id,
        {"selected_document_code": normalized.upper()},
    )


def _apply_selected_topic(session_id: Optional[str], topic: Optional[str]) -> None:
    """Persist or clear the selected topic for a session."""
    if not session_id:
        return
    if not topic:
        ConversationContext.clear_session_metadata_keys(session_id, ["selected_topic"])
        return
    normalized = str(topic).strip()
    if not normalized:
        ConversationContext.clear_session_metadata_keys(session_id, ["selected_topic"])
        return
    ConversationContext.update_session_metadata(
        session_id,
        {"selected_topic": normalized},
    )


def _apply_selected_detail(session_id: Optional[str], detail: Optional[str]) -> None:
    """Persist or clear the selected detail for a session."""
    if not session_id:
        return
    if not detail:
        ConversationContext.clear_session_metadata_keys(session_id, ["selected_detail"])
        return
    normalized = str(detail).strip()
    if not normalized:
        ConversationContext.clear_session_metadata_keys(session_id, ["selected_detail"])
        return
    ConversationContext.update_session_metadata(
        session_id,
        {"selected_detail": normalized},
    )


@csrf_exempt
def chat_simple(request: HttpRequest) -> JsonResponse:
    """
    Lightweight POST-only endpoint to help Spaces hit the chatbot without DRF.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        payload: Dict[str, Any] = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        return JsonResponse(
            {"error": "Invalid JSON body", "details": str(exc)},
            status=400,
        )

    message: str = str(payload.get("message", "")).strip()
    session_id_raw = payload.get("session_id") or ""
    session_id: str = str(session_id_raw).strip() if session_id_raw else ""
    reset_session: bool = bool(payload.get("reset_session", False))
    selected_document_code = payload.get("selected_document_code") or payload.get("clarification_option")
    if isinstance(selected_document_code, str):
        selected_document_code = selected_document_code.strip()
    else:
        selected_document_code = None
    
    selected_topic = payload.get("selected_topic") or payload.get("topic_option")
    if isinstance(selected_topic, str):
        selected_topic = selected_topic.strip()
    else:
        selected_topic = None

    if not message:
        return JsonResponse({"error": "message is required"}, status=400)

    if reset_session:
        session_id = ""

    if not session_id:
        session_id = str(uuid.uuid4())
    else:
        try:
            uuid.UUID(session_id)
        except ValueError:
            session_id = str(uuid.uuid4())
    
    if selected_document_code is not None:
        _apply_selected_document_code(session_id, selected_document_code)
    
    if selected_topic is not None:
        _apply_selected_topic(session_id, selected_topic)

    try:
        chatbot = get_chatbot()
        response = chatbot.generate_response(message, session_id=session_id)
    except Exception as exc:
        return JsonResponse(
            {
                "message": "Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.",
                "intent": "error",
                "error": str(exc),
                "results": [],
                "count": 0,
                "session_id": session_id,
            },
            status=500,
        )

    if "session_id" not in response:
        response["session_id"] = session_id

    return JsonResponse(response, status=200)


@api_view(["POST"])
@throttle_classes([ChatThrottle])
def chat(request: Request) -> Response:
    """
    Chatbot endpoint for natural language queries with session support.
    
    Request body:
        {
            "message": "Mức phạt vượt đèn đỏ là bao nhiêu?",
            "session_id": "optional-uuid-string",
            "reset_session": false
        }
    
    Response:
        {
            "message": "Tôi tìm thấy 1 mức phạt liên quan đến '...':",
            "intent": "search_fine",
            "confidence": 0.95,
            "results": [...],
            "count": 1,
            "session_id": "uuid-string"
        }
    """
    # Log immediately when request arrives
    print(f"[CHAT] 🔔 Request received at /api/chatbot/chat/", flush=True)
    logger.info("[CHAT] 🔔 Request received at /api/chatbot/chat/")
    
    # Log raw request data for debugging
    raw_data = dict(request.data) if hasattr(request.data, 'get') else {}
    logger.info(f"[CHAT] 📥 Raw request data keys: {list(raw_data.keys())}, Content-Type: {request.content_type}")
    print(f"[CHAT] 📥 Raw request data keys: {list(raw_data.keys())}, Content-Type: {request.content_type}", flush=True)
    
    message = request.data.get("message", "").strip()
    session_id = request.data.get("session_id") or ""
    if session_id:
        session_id = str(session_id).strip()
    else:
        session_id = ""
    reset_session = request.data.get("reset_session", False)
    selected_document_code = request.data.get("selected_document_code") or request.data.get("clarification_option")
    if isinstance(selected_document_code, str):
        selected_document_code = selected_document_code.strip()
    else:
        selected_document_code = None
    
    selected_topic = request.data.get("selected_topic") or request.data.get("topic_option")
    if isinstance(selected_topic, str):
        selected_topic = selected_topic.strip()
    else:
        selected_topic = None
    
    selected_detail = request.data.get("selected_detail") or request.data.get("detail_option")
    if isinstance(selected_detail, str):
        selected_detail = selected_detail.strip()
    else:
        selected_detail = None
    
    # Log received message for debugging
    message_preview = message[:100] + "..." if len(message) > 100 else message
    logger.info(f"[CHAT] 📨 Received POST request - Message: '{message_preview}' (length: {len(message)}), Session: {session_id[:8] if session_id else 'new'}")
    print(f"[CHAT] 📨 Received POST request - Message: '{message_preview}' (length: {len(message)}), Session: {session_id[:8] if session_id else 'new'}", flush=True)
    
    if not message:
        return Response(
            {"error": "message is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Handle session reset
    if reset_session:
        session_id = None
    
    # Generate new session_id if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
    else:
        # Validate session_id format
        try:
            uuid.UUID(session_id)
        except ValueError:
            # Invalid UUID format, generate new one
            session_id = str(uuid.uuid4())
    
    if selected_document_code is not None:
        _apply_selected_document_code(session_id, selected_document_code)
    
    if selected_topic is not None:
        _apply_selected_topic(session_id, selected_topic)
    
    try:
        logger.info(f"[CHAT] ⏳ Starting response generation for message (length: {len(message)})")
        print(f"[CHAT] ⏳ Starting response generation for message (length: {len(message)})", flush=True)
        
        chatbot = get_chatbot()
        response = chatbot.generate_response(message, session_id=session_id)
        
        # Validate response - ensure it's a dict with required fields
        if not response or not isinstance(response, dict):
            logger.error("[CHAT] ❌ Invalid response from chatbot.generate_response: %s", type(response))
            response = {
                "message": "Xin lỗi, có lỗi xảy ra khi xử lý câu hỏi của bạn. Vui lòng thử lại.",
                "intent": "error",
                "results": [],
                "count": 0,
                "session_id": session_id,
            }
        
        # Ensure required fields exist
        if "message" not in response and "clarification" not in response:
            logger.warning("[CHAT] ⚠️ Response missing 'message' field, adding default")
            response["message"] = "Xin lỗi, không thể tìm thấy thông tin."
        
        # Ensure session_id is in response
        if "session_id" not in response:
            response["session_id"] = session_id
        
        # Ensure intent exists
        if "intent" not in response:
            response["intent"] = "unknown"
        
        # Ensure results and count exist
        if "results" not in response:
            response["results"] = []
        if "count" not in response:
            response["count"] = len(response.get("results", []))
        
        # Enhanced logging for search_legal queries
        intent = response.get("intent", "unknown")
        if intent == "search_legal":
            count = response.get("count", 0)
            results = response.get("results", [])
            answer = response.get("message", "")
            has_denial = any(
                phrase in answer.lower()
                for phrase in ["không tìm thấy", "chưa có dữ liệu", "không có thông tin", "xin lỗi"]
            )
            
            # Extract document codes from results
            doc_codes = []
            for result in results:
                data = result.get("data", {})
                if "document_code" in data:
                    doc_codes.append(data["document_code"])
                elif "code" in data:
                    doc_codes.append(data["code"])
            
            logger.info(
                f"[CHAT] 📚 Legal query details - "
                f"Query: '{message[:80]}...', "
                f"Count: {count}, "
                f"Doc codes: {doc_codes}, "
                f"Has denial: {has_denial}, "
                f"Answer length: {len(answer)}"
            )
            print(
                f"[CHAT] 📚 Legal query: '{message[:60]}...' -> "
                f"{count} sections, docs: {doc_codes}, "
                f"denial: {has_denial}",
                flush=True
            )
        
        full_message = response.get("message", "") or ""
        response_preview = (
            f"{full_message[:100]}..." if len(full_message) > 100 else full_message
        )
        routing_info = response.get("_routing", {})
        routing_path = routing_info.get("path", response.get("routing", "slow_path"))
        routing_method = routing_info.get("method", "default")
        source = response.get("_source", "unknown")
        cache_flag = response.get("_cache")
        
        logger.info(
            f"[CHAT] ✅ Response generated successfully - Intent: {intent}, Path: {routing_path}, "
            f"Method: {routing_method}, Source: {source}, Cache: {cache_flag}, "
            f"Response length: {len(full_message)}"
        )
        print(
            f"[CHAT] ✅ Response generated successfully - Intent: {intent}, Path: {routing_path}, "
            f"Method: {routing_method}, Source: {source}, Cache: {cache_flag}, "
            f"Response preview: '{response_preview}'",
            flush=True,
        )
        
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {
                "message": "Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.",
                "intent": "error",
                "error": str(e),
                "results": [],
                "count": 0,
                "session_id": session_id
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
def health(request):
    """
    Health check endpoint for chatbot service.
    """
    print(f"[HEALTH] 🔔 Health check request received", flush=True)
    logger.info("[HEALTH] 🔔 Health check request received")
    
    try:
        print(f"[HEALTH] ⏳ Getting chatbot instance...", flush=True)
        # Don't call get_chatbot() to avoid blocking - just return healthy if we can import
        return Response({
            "status": "healthy",
            "service": "chatbot",
            "classifier_loaded": False  # Don't check to avoid blocking
        })
    except Exception as e:
        print(f"[HEALTH] ❌ Error: {e}", flush=True)
        logger.exception("[HEALTH] ❌ Error in health check")
        return Response(
            {"status": "unhealthy", "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
def test_init(request: Request) -> Response:
    """
    Force chatbot initialization to validate startup on Hugging Face Spaces.
    """
    try:
        chatbot = get_chatbot()
        return Response(
            {
                "status": "initialized",
                "classifier_loaded": chatbot.intent_classifier is not None,
            },
            status=status.HTTP_200_OK,
        )
    except Exception as exc:
        return Response(
            {"status": "error", "message": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def test_generate(request: Request) -> Response:
    """
    Generate a quick response for smoke-testing LLM connectivity.
    """
    message = request.data.get("message", "").strip()
    if not message:
        return Response(
            {"error": "message is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    session_id = str(request.data.get("session_id") or uuid.uuid4())

    try:
        chatbot = get_chatbot()
        response = chatbot.generate_response(message, session_id=session_id)
        response.setdefault("session_id", session_id)
        return Response(response, status=status.HTTP_200_OK)
    except Exception as exc:
        return Response(
            {
                "message": "Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.",
                "intent": "error",
                "error": str(exc),
                "results": [],
                "count": 0,
                "session_id": session_id,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def model_status(request: Request) -> Response:
    """
    Provide lightweight diagnostics about the current chatbot instance.
    """
    try:
        chatbot = get_chatbot()
        status_payload = {
            "intent_classifier_loaded": chatbot.intent_classifier is not None,
            "knowledge_base_ready": getattr(chatbot, "knowledge_base", None) is not None,
            "llm_provider": getattr(chatbot, "llm_provider", "unknown"),
        }
        return Response(status_payload, status=status.HTTP_200_OK)
    except Exception as exc:
        return Response(
            {"status": "error", "message": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def analytics(request: Request) -> Response:
    """
    Get Dual-Path RAG analytics and routing statistics.
    
    Query params:
        days: Number of days to analyze (default: 7)
        type: Type of analytics ('routing', 'golden', 'performance', 'all')
    """
    from hue_portal.chatbot.analytics import get_routing_stats, get_golden_dataset_stats, get_performance_metrics
    
    try:
        days = int(request.query_params.get('days', 7))
        analytics_type = request.query_params.get('type', 'all')
        
        result = {}
        
        if analytics_type in ['routing', 'all']:
            result['routing'] = get_routing_stats(days=days)
        
        if analytics_type in ['golden', 'all']:
            result['golden_dataset'] = get_golden_dataset_stats()
        
        if analytics_type in ['performance', 'all']:
            result['performance'] = get_performance_metrics(days=days)
        
        return Response(result, status=status.HTTP_200_OK)
    except Exception as exc:
        return Response(
            {"status": "error", "message": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

