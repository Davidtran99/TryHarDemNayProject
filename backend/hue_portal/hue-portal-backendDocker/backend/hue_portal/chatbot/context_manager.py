"""
Context manager for conversation sessions and messages.
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
from hue_portal.core.models import ConversationSession, ConversationMessage


class ConversationContext:
    """Manages conversation sessions and context."""
    
    @staticmethod
    def get_session(session_id: Optional[str] = None, user_id: Optional[str] = None) -> ConversationSession:
        """
        Get or create a conversation session.
        
        Args:
            session_id: Optional session ID (UUID string). If None, creates new session.
            user_id: Optional user ID for tracking.
        
        Returns:
            ConversationSession instance.
        """
        if session_id:
            try:
                # Try to get existing session
                session = ConversationSession.objects.get(session_id=session_id)
                # Update updated_at timestamp
                session.save(update_fields=["updated_at"])
                return session
            except ConversationSession.DoesNotExist:
                # Create new session with provided session_id
                return ConversationSession.objects.create(
                    session_id=session_id,
                    user_id=user_id
                )
        else:
            # Create new session
            return ConversationSession.objects.create(user_id=user_id)
    
    @staticmethod
    def add_message(
        session_id: str,
        role: str,
        content: str,
        intent: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationMessage:
        """
        Add a message to a conversation session.
        
        Args:
            session_id: Session ID (UUID string).
            role: Message role ('user' or 'bot').
            content: Message content.
            intent: Detected intent (optional).
            entities: Extracted entities (optional).
            metadata: Additional metadata (optional).
        
        Returns:
            ConversationMessage instance.
        """
        session = ConversationContext.get_session(session_id=session_id)
        
        return ConversationMessage.objects.create(
            session=session,
            role=role,
            content=content,
            intent=intent or "",
            entities=entities or {},
            metadata=metadata or {}
        )
    
    @staticmethod
    def get_recent_messages(session_id: str, limit: int = 10) -> List[ConversationMessage]:
        """
        Get recent messages from a session.
        
        Args:
            session_id: Session ID (UUID string).
            limit: Maximum number of messages to return.
        
        Returns:
            List of ConversationMessage instances, ordered by timestamp (oldest first).
        """
        try:
            session = ConversationSession.objects.get(session_id=session_id)
            return list(session.messages.all()[:limit])
        except ConversationSession.DoesNotExist:
            return []
    
    @staticmethod
    def get_context_summary(session_id: str, max_messages: int = 5) -> Dict[str, Any]:
        """
        Create a summary of conversation context.
        
        Args:
            session_id: Session ID (UUID string).
            max_messages: Maximum number of messages to include in summary.
        
        Returns:
            Dictionary with context summary including:
            - recent_messages: List of recent messages
            - entities: Aggregated entities from conversation
            - intents: List of intents mentioned
            - message_count: Total number of messages
        """
        messages = ConversationContext.get_recent_messages(session_id, limit=max_messages)
        
        # Aggregate entities
        all_entities = {}
        intents = []
        
        for msg in messages:
            if msg.entities:
                for key, value in msg.entities.items():
                    if key not in all_entities:
                        all_entities[key] = []
                    if value not in all_entities[key]:
                        all_entities[key].append(value)
            
            if msg.intent:
                if msg.intent not in intents:
                    intents.append(msg.intent)
        
        return {
            "recent_messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "intent": msg.intent,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in messages
            ],
            "entities": all_entities,
            "intents": intents,
            "message_count": len(messages)
        }
    
    @staticmethod
    def extract_entities(query: str) -> Dict[str, Any]:
        """
        Extract entities from a query (basic implementation).
        This is a placeholder - will be enhanced by entity_extraction.py
        
        Args:
            query: User query string.
        
        Returns:
            Dictionary with extracted entities.
        """
        entities = {}
        query_lower = query.lower()
        
        # Basic fine code extraction (V001, V002, etc.)
        import re
        fine_codes = re.findall(r'\bV\d{3}\b', query, re.IGNORECASE)
        if fine_codes:
            entities["fine_codes"] = fine_codes
        
        # Basic procedure keywords
        procedure_keywords = ["thủ tục", "hồ sơ", "giấy tờ"]
        if any(kw in query_lower for kw in procedure_keywords):
            entities["has_procedure"] = True
        
        # Basic fine keywords
        fine_keywords = ["phạt", "mức phạt", "vi phạm"]
        if any(kw in query_lower for kw in fine_keywords):
            entities["has_fine"] = True
        
        return entities

