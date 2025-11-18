"""
Chatbot API views for handling conversational queries.
"""
import uuid
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .chatbot import get_chatbot
from hue_portal.chatbot.context_manager import ConversationContext


@api_view(["POST"])
def chat(request):
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
    session_id = request.data.get("session_id", "").strip()
    reset_session = request.data.get("reset_session", False)
    
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
        chatbot = get_chatbot()
        response = chatbot.generate_response(message, session_id=session_id)
        
        # Ensure session_id is in response
        if "session_id" not in response:
            response["session_id"] = session_id
        
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

