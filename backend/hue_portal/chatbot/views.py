"""
Chatbot API views for handling conversational queries.
"""
import json
import logging
import uuid
from typing import Any, Dict

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from .chatbot import get_chatbot
from hue_portal.chatbot.context_manager import ConversationContext

logger = logging.getLogger(__name__)


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
    message = request.data.get("message", "").strip()
    session_id = request.data.get("session_id") or ""
    if session_id:
        session_id = str(session_id).strip()
    else:
        session_id = ""
    reset_session = request.data.get("reset_session", False)
    
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
    
    try:
        logger.info(f"[CHAT] ⏳ Starting response generation for message (length: {len(message)})")
        print(f"[CHAT] ⏳ Starting response generation for message (length: {len(message)})", flush=True)
        
        chatbot = get_chatbot()
        response = chatbot.generate_response(message, session_id=session_id)
        
        # Ensure session_id is in response
        if "session_id" not in response:
            response["session_id"] = session_id
        
        response_preview = response.get("message", "")[:100] + "..." if len(response.get("message", "")) > 100 else response.get("message", "")
        logger.info(f"[CHAT] ✅ Response generated successfully - Intent: {response.get('intent', 'unknown')}, Response length: {len(response.get('message', ''))}")
        print(f"[CHAT] ✅ Response generated successfully - Intent: {response.get('intent', 'unknown')}, Response preview: '{response_preview}'", flush=True)
        
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
    try:
        chatbot = get_chatbot()
        return Response({
            "status": "healthy",
            "service": "chatbot",
            "classifier_loaded": chatbot.intent_classifier is not None
        })
    except Exception as e:
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

