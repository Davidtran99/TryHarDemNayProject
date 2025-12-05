"""
Chatbot wrapper that integrates core chatbot with router, LLM, and context management.
"""
import os
import copy
import logging
from typing import Dict, Any, Optional
from hue_portal.core.chatbot import Chatbot as CoreChatbot, get_chatbot as get_core_chatbot
from hue_portal.chatbot.router import decide_route, IntentRoute, RouteDecision
from hue_portal.chatbot.context_manager import ConversationContext
from hue_portal.chatbot.llm_integration import LLMGenerator
from hue_portal.core.models import LegalSection
from hue_portal.chatbot.exact_match_cache import ExactMatchCache
from hue_portal.chatbot.slow_path_handler import SlowPathHandler

logger = logging.getLogger(__name__)

EXACT_MATCH_CACHE = ExactMatchCache(
    max_size=int(os.environ.get("EXACT_MATCH_CACHE_MAX", "256")),
    ttl_seconds=int(os.environ.get("EXACT_MATCH_CACHE_TTL_SECONDS", "43200")),
)


class Chatbot(CoreChatbot):
    """
    Enhanced chatbot with session support, routing, and RAG capabilities.
    """
    
    def __init__(self):
        super().__init__()
        self.llm_generator = None
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize LLM generator if needed."""
        try:
            self.llm_generator = LLMGenerator()
        except Exception as e:
            print(f"⚠️ LLM generator not available: {e}")
            self.llm_generator = None
    
    def generate_response(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate chatbot response with session support and routing.
        
        Args:
            query: User query string
            session_id: Optional session ID for conversation context
        
        Returns:
            Response dictionary with message, intent, results, etc.
        """
        query = query.strip()
        
        # Save user message to context
        if session_id:
            try:
                ConversationContext.add_message(
                    session_id=session_id,
                    role="user",
                    content=query
                )
            except Exception as e:
                print(f"⚠️ Failed to save user message: {e}")
        
        # Classify intent
        intent, confidence = self.classify_intent(query)
        
        # Router decision
        route_decision = decide_route(query, intent, confidence)
        
        # Use forced intent if router suggests it
        if route_decision.forced_intent:
            intent = route_decision.forced_intent
        
        # Instant exact-match cache lookup
        cached_response = EXACT_MATCH_CACHE.get(query, intent)
        if cached_response:
            cached_response["_cache"] = "exact_match"
            cached_response["_source"] = cached_response.get("_source", "cache")
            cached_response.setdefault("routing", route_decision.route.value)
            logger.info(
                "[CACHE] Hit for intent=%s route=%s source=%s",
                intent,
                route_decision.route.value,
                cached_response["_source"],
            )
            if session_id:
                cached_response["session_id"] = session_id
            if session_id:
                try:
                    ConversationContext.add_message(
                        session_id=session_id,
                        role="bot",
                        content=cached_response.get("message", ""),
                        intent=intent,
                    )
                except Exception as e:
                    print(f"⚠️ Failed to save cached bot message: {e}")
            return cached_response
        
        # Always send legal intent through Slow Path RAG
        if intent == "search_legal":
            response = self._run_slow_path_legal(query, intent, session_id, route_decision)
        elif route_decision.route == IntentRoute.GREETING:
            response = {
                "message": "Xin chào! Tôi có thể giúp bạn tra cứu các thông tin liên quan về các văn bản quy định pháp luật về xử lí kỷ luật cán bộ đảng viên",
                "intent": "greeting",
                "confidence": 0.9,
                "results": [],
                "count": 0,
                "routing": "greeting"
            }
        
        elif route_decision.route == IntentRoute.SMALL_TALK:
            # Xử lý follow-up questions trong context
            follow_up_keywords = ["có điều khoản", "liên quan", "khác", "nữa", "thêm", "tóm tắt", "tải file"]
            query_lower = query.lower()
            is_follow_up = any(kw in query_lower for kw in follow_up_keywords)
            
            response = None
            
            # Nếu là follow-up question, thử tìm context từ conversation trước
            if is_follow_up and session_id:
                try:
                    recent_messages = ConversationContext.get_recent_messages(session_id, limit=5)
                    # Tìm message bot cuối cùng có results
                    for msg in reversed(recent_messages):
                        if msg.role == "bot" and msg.intent == "search_legal":
                            # Có context về legal query trước đó, thử search lại với query mới
                            enhanced_query = f"{query} {msg.content[:100]}"
                            search_result = self.search_by_intent("search_legal", enhanced_query, limit=3)
                            if search_result["count"] > 0:
                                # Tìm thấy results, trả về
                                top_result = search_result["results"][0]
                                top_data = top_result.get("data", {})
                                doc_code = top_data.get("document_code", "")
                                doc_title = top_data.get("document_title", "văn bản pháp luật")
                                section_code = top_data.get("section_code", "")
                                section_title = top_data.get("section_title", "")
                                content = top_data.get("content", "") or top_data.get("excerpt", "")
                                
                                if "tóm tắt" in query_lower:
                                    content_preview = content[:400] + "..." if len(content) > 400 else content
                                    message = (
                                        f"**Tóm tắt {section_code}**: {section_title or 'Nội dung chính'}\n\n"
                                        f"{content_preview}\n\n"
                                        f"Nguồn: {doc_title}" + (f" ({doc_code})" if doc_code else "")
                                    )
                                elif "tải" in query_lower or "download" in query_lower:
                                    message = (
                                        f"Bạn có thể tải file gốc của {doc_title}" + (f" ({doc_code})" if doc_code else "") +
                                        f" từ link download trong kết quả tìm kiếm."
                                    )
                                else:
                                    # Câu hỏi "có điều khoản liên quan nào khác không?"
                                    if search_result["count"] > 1:
                                        message = (
                                            f"Có, tôi tìm thấy {search_result['count']} điều khoản liên quan:\n\n"
                                        )
                                        for i, result in enumerate(search_result["results"][:3], 1):
                                            data = result.get("data", {})
                                            sec_code = data.get("section_code", "")
                                            sec_title = data.get("section_title", "")
                                            message += f"{i}. **{sec_code}**: {sec_title or 'Nội dung liên quan'}\n"
                                        message += f"\nNguồn: {doc_title}" + (f" ({doc_code})" if doc_code else "")
                                    else:
                                        message = (
                                            f"Tôi đã tìm thấy điều khoản liên quan:\n\n"
                                            f"**{section_code}**: {section_title or 'Nội dung liên quan'}\n\n"
                                            f"{content[:300]}...\n\n"
                                            f"Nguồn: {doc_title}" + (f" ({doc_code})" if doc_code else "")
                                        )
                                
                                response = {
                                    "message": message,
                                    "intent": "search_legal",
                                    "confidence": 0.85,
                                    "results": search_result["results"][:3],
                                    "count": search_result["count"],
                                    "routing": "follow_up"
                                }
                                break
                except Exception as e:
                    logger.warning(f"[FOLLOW_UP] Failed to process follow-up: {e}")
            
            # Nếu không phải follow-up hoặc không tìm thấy context, trả về message thân thiện
            if response is None:
                # Detect off-topic questions (nấu ăn, chả trứng, etc.)
                off_topic_keywords = ["nấu", "nau", "chả trứng", "cha trung", "món ăn", "mon an", "công thức", "cong thuc", 
                                     "cách làm", "cach lam", "đổ chả", "do cha", "trứng", "trung"]
                is_off_topic = any(kw in query_lower for kw in off_topic_keywords)
                
                if is_off_topic:
                    message = (
                        "Xin lỗi, tôi là chatbot chuyên về tra cứu các văn bản quy định pháp luật "
                        "về xử lí kỷ luật cán bộ đảng viên của Phòng Thanh Tra - Công An Thành Phố Huế.\n\n"
                        "Tôi không thể trả lời các câu hỏi về nấu ăn, công thức nấu ăn hay các chủ đề khác ngoài phạm vi pháp luật.\n\n"
                        "Bạn có muốn tra cứu thông tin về:\n"
                        "- Các quy định về xử lí kỷ luật cán bộ đảng viên\n"
                        "- Các điều khoản trong Thông tư 02 về xử lý điều lệnh trong CAND\n"
                        "- Hoặc các văn bản pháp luật liên quan khác?"
                    )
                else:
                    message = "Tôi có thể giúp bạn tra cứu các văn bản quy định pháp luật về xử lí kỷ luật cán bộ đảng viên. Bạn muốn tìm gì?"
                
                response = {
                    "message": message,
                    "intent": intent,
                    "confidence": confidence,
                    "results": [],
                    "count": 0,
                    "routing": "small_talk"
                }
        
        else:  # IntentRoute.SEARCH
            # Use core chatbot search for other intents
                search_result = self.search_by_intent(intent, query, limit=5)
                
                # Generate response message
                if search_result["count"] > 0:
                    template = self._get_response_template(intent)
                    message = template.format(
                        count=search_result["count"],
                        query=query
                    )
                else:
                    message = f"Xin lỗi, tôi không tìm thấy thông tin liên quan đến '{query}'. Vui lòng thử lại với từ khóa khác."
                
                response = {
                    "message": message,
                    "intent": intent,
                    "confidence": confidence,
                    "results": search_result["results"],
                    "count": search_result["count"],
                    "routing": "search"
                }
        
        # Add session_id
        if session_id:
            response["session_id"] = session_id
        
        # Save bot response to context
        if session_id:
            try:
                ConversationContext.add_message(
                    session_id=session_id,
                    role="bot",
                    content=response.get("message", ""),
                    intent=intent
                )
            except Exception as e:
                print(f"⚠️ Failed to save bot message: {e}")
        
        self._cache_response(query, intent, response)
        
        return response
    
    def _run_slow_path_legal(
        self,
        query: str,
        intent: str,
        session_id: Optional[str],
        route_decision: RouteDecision,
    ) -> Dict[str, Any]:
        """Execute Slow Path legal handler (with fast-path + structured output)."""
        slow_handler = SlowPathHandler()
        response = slow_handler.handle(query, intent, session_id)
        response.setdefault("routing", "slow_path")
        response.setdefault(
            "_routing",
            {
                "path": "slow_path",
                "method": getattr(route_decision, "rationale", "router"),
                "confidence": route_decision.confidence,
            },
        )
        logger.info(
            "[LEGAL] Slow path response - source=%s count=%s routing=%s",
            response.get("_source"),
            response.get("count"),
            response.get("_routing"),
        )
        return response
    
    def _cache_response(self, query: str, intent: str, response: Dict[str, Any]) -> None:
        """Store response in exact-match cache if eligible."""
        if not self._should_cache_response(intent, response):
            logger.debug(
                "[CACHE] Skip storing response (intent=%s, results=%s)",
                intent,
                response.get("count"),
            )
            return
        payload = copy.deepcopy(response)
        payload.pop("session_id", None)
        payload.pop("_cache", None)
        EXACT_MATCH_CACHE.set(query, intent, payload)
        logger.info(
            "[CACHE] Stored response for intent=%s (results=%s, source=%s)",
            intent,
            response.get("count"),
            response.get("_source"),
        )
    
    def _should_cache_response(self, intent: str, response: Dict[str, Any]) -> bool:
        """Determine if response should be cached for exact matches."""
        cacheable_intents = {
            "search_legal",
            "search_fine",
            "search_procedure",
            "search_office",
            "search_advisory",
        }
        if intent not in cacheable_intents:
            return False
        if response.get("count", 0) <= 0:
            return False
        if not response.get("results"):
            return False
        return True
    
    def _handle_legal_query(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle legal document queries with RAG pipeline.
        
        Args:
            query: User query
            session_id: Optional session ID
        
        Returns:
            Response dictionary
        """
        # Search legal sections
        qs = LegalSection.objects.select_related("document").all()
        text_fields = ["section_title", "section_code", "content"]
        legal_sections = self._search_legal_sections(qs, query, text_fields, top_k=5)
        
        if not legal_sections:
            return {
                "message": f"Xin lỗi, tôi không tìm thấy văn bản pháp luật liên quan đến '{query}'.",
                "intent": "search_legal",
                "confidence": 0.5,
                "results": [],
                "count": 0,
                "routing": "search"
            }
        
        # Try LLM generation if available
        if self.llm_generator and self.llm_generator.provider != "none":
            try:
                answer = self.llm_generator.generate_structured_legal_answer(
                    query=query,
                    documents=legal_sections,
                    max_attempts=2
                )
                message = answer.summary
            except Exception as e:
                print(f"⚠️ LLM generation failed: {e}")
                message = self._format_legal_results(legal_sections, query)
        else:
            # Template-based response
            message = self._format_legal_results(legal_sections, query)
        
        # Format results
        results = []
        for section in legal_sections:
            doc = section.document
            results.append({
                "type": "legal",
                "data": {
                    "id": section.id,
                    "section_code": section.section_code,
                    "section_title": section.section_title or "",
                    "content": section.content[:500] + "..." if len(section.content) > 500 else section.content,
                    "excerpt": section.excerpt or "",
                    "document_code": doc.code if doc else "",
                    "document_title": doc.title if doc else "",
                    "page_start": section.page_start,
                    "page_end": section.page_end,
                    "download_url": f"/api/legal-documents/{doc.id}/download/" if doc and doc.id else None,
                    "source_url": doc.source_url if doc else ""
                }
            })
        
        return {
            "message": message,
            "intent": "search_legal",
            "confidence": 0.9,
            "results": results,
            "count": len(results),
            "routing": "search"
        }
    
    def _search_legal_sections(self, qs, query: str, text_fields: list, top_k: int = 5):
        """Search legal sections using ML search."""
        from hue_portal.core.search_ml import search_with_ml
        return search_with_ml(qs, query, text_fields, top_k=top_k, min_score=0.1)
    
    def _format_legal_results(self, sections, query: str) -> str:
        """Format legal sections into response message."""
        if not sections:
            return f"Xin lỗi, tôi không tìm thấy văn bản pháp luật liên quan đến '{query}'."
        
        doc = sections[0].document
        doc_info = f"{doc.code}: {doc.title}" if doc else "Văn bản pháp luật"
        
        message = f"Tôi tìm thấy {len(sections)} điều khoản liên quan đến '{query}' trong {doc_info}:\n\n"
        
        for i, section in enumerate(sections[:3], 1):
            section_text = f"{section.section_code}: {section.section_title or ''}\n"
            section_text += section.content[:200] + "..." if len(section.content) > 200 else section.content
            message += f"{i}. {section_text}\n\n"
        
        if len(sections) > 3:
            message += f"... và {len(sections) - 3} điều khoản khác."
        
        return message
    
    def _get_response_template(self, intent: str) -> str:
        """Get response template for intent."""
        templates = {
            "search_fine": "Tôi tìm thấy {count} mức phạt liên quan đến '{query}':",
            "search_procedure": "Tôi tìm thấy {count} thủ tục liên quan đến '{query}':",
            "search_office": "Tôi tìm thấy {count} đơn vị liên quan đến '{query}':",
            "search_advisory": "Tôi tìm thấy {count} cảnh báo liên quan đến '{query}':",
        }
        return templates.get(intent, "Tôi tìm thấy {count} kết quả liên quan đến '{query}':")


# Global chatbot instance
_chatbot_instance = None


def get_chatbot() -> Chatbot:
    """Get or create enhanced chatbot instance."""
    global _chatbot_instance
    if _chatbot_instance is None:
        _chatbot_instance = Chatbot()
    return _chatbot_instance



