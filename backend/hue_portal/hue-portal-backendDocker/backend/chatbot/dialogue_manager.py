"""
Dialogue management for multi-turn conversations.
"""
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum


class DialogueState(Enum):
    """Dialogue states."""
    INITIAL = "initial"
    COLLECTING_INFO = "collecting_info"
    CLARIFYING = "clarifying"
    PROVIDING_ANSWER = "providing_answer"
    FOLLOW_UP = "follow_up"
    COMPLETED = "completed"


class DialogueManager:
    """Manages dialogue state and multi-turn conversations."""
    
    def __init__(self):
        self.state = DialogueState.INITIAL
        self.slots = {}  # Slot filling for missing information
        self.context_switch_detected = False
    
    def update_state(
        self,
        query: str,
        intent: str,
        results_count: int,
        confidence: float,
        recent_messages: Optional[List[Dict[str, Any]]] = None
    ) -> DialogueState:
        """
        Update dialogue state based on current query and context.
        
        Args:
            query: Current user query.
            intent: Detected intent.
            results_count: Number of results found.
            confidence: Confidence score.
            recent_messages: Recent conversation messages.
        
        Returns:
            Updated dialogue state.
        """
        # Detect context switching
        if recent_messages and len(recent_messages) > 0:
            last_intent = recent_messages[-1].get("intent")
            if last_intent and last_intent != intent and intent != "greeting":
                self.context_switch_detected = True
                self.state = DialogueState.INITIAL
                self.slots = {}
                return self.state
        
        # State transitions
        if results_count == 0 and confidence < 0.5:
            # No results and low confidence - need clarification
            self.state = DialogueState.CLARIFYING
        elif results_count > 0 and confidence >= 0.7:
            # Good results - providing answer
            self.state = DialogueState.PROVIDING_ANSWER
        elif results_count > 0 and confidence < 0.7:
            # Some results but uncertain - might need follow-up
            self.state = DialogueState.FOLLOW_UP
        else:
            self.state = DialogueState.PROVIDING_ANSWER
        
        return self.state
    
    def needs_clarification(
        self,
        query: str,
        intent: str,
        results_count: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if clarification is needed.
        
        Args:
            query: User query.
            intent: Detected intent.
            results_count: Number of results.
        
        Returns:
            Tuple of (needs_clarification, clarification_message).
        """
        if results_count == 0:
            # No results - ask for clarification
            clarification_messages = {
                "search_fine": "Bạn có thể cho biết cụ thể hơn về loại vi phạm không? Ví dụ: vượt đèn đỏ, không đội mũ bảo hiểm...",
                "search_procedure": "Bạn muốn tìm thủ tục nào? Ví dụ: đăng ký cư trú, thủ tục ANTT...",
                "search_office": "Bạn muốn tìm đơn vị nào? Ví dụ: công an phường, điểm tiếp dân...",
                "search_advisory": "Bạn muốn tìm cảnh báo về chủ đề gì?",
            }
            message = clarification_messages.get(intent, "Bạn có thể cung cấp thêm thông tin không?")
            return (True, message)
        
        return (False, None)
    
    def detect_missing_slots(
        self,
        intent: str,
        query: str,
        results_count: int
    ) -> Dict[str, Any]:
        """
        Detect missing information slots.
        
        Args:
            intent: Detected intent.
            query: User query.
            results_count: Number of results.
        
        Returns:
            Dictionary of missing slots.
        """
        missing_slots = {}
        
        if intent == "search_fine":
            # Check for fine code or fine name
            if "v001" not in query.lower() and "v002" not in query.lower():
                if not any(kw in query.lower() for kw in ["vượt đèn đỏ", "mũ bảo hiểm", "nồng độ cồn"]):
                    missing_slots["fine_specification"] = True
        
        elif intent == "search_procedure":
            # Check for procedure name or domain
            if not any(kw in query.lower() for kw in ["cư trú", "antt", "pccc", "đăng ký"]):
                missing_slots["procedure_specification"] = True
        
        elif intent == "search_office":
            # Check for office name or location
            if not any(kw in query.lower() for kw in ["phường", "huyện", "tỉnh", "điểm tiếp dân"]):
                missing_slots["office_specification"] = True
        
        return missing_slots
    
    def handle_follow_up(
        self,
        query: str,
        recent_messages: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Generate follow-up question if needed.
        
        Args:
            query: Current query.
            recent_messages: Recent conversation messages.
        
        Returns:
            Follow-up question or None.
        """
        if not recent_messages:
            return None
        
        # Check if query is very short (likely a follow-up)
        if len(query.split()) <= 3:
            last_message = recent_messages[-1]
            last_intent = last_message.get("intent")
            
            if last_intent == "search_fine":
                return "Bạn muốn biết thêm thông tin gì về mức phạt này? (ví dụ: điều luật, biện pháp khắc phục)"
            elif last_intent == "search_procedure":
                return "Bạn muốn biết thêm thông tin gì về thủ tục này? (ví dụ: hồ sơ, lệ phí, thời hạn)"
        
        return None
    
    def reset(self):
        """Reset dialogue manager state."""
        self.state = DialogueState.INITIAL
        self.slots = {}
        self.context_switch_detected = False

