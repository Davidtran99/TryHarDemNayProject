"""
Chatbot wrapper that integrates core chatbot with router, LLM, and context management.
"""
import os
import copy
import logging
import json
import time
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

DEBUG_LOG_PATH = "/Users/davidtran/Downloads/TryHarDemNayProject/.cursor/debug.log"
DEBUG_SESSION_ID = "debug-session"
DEBUG_RUN_ID = "pre-fix"

#region agent log
def _agent_debug_log(hypothesis_id: str, location: str, message: str, data: Dict[str, Any]) -> None:
    """Append instrumentation logs to .cursor/debug.log in NDJSON format."""
    try:
        payload = {
            "sessionId": DEBUG_SESSION_ID,
            "runId": DEBUG_RUN_ID,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        # Silently ignore logging errors to avoid impacting runtime behavior.
        pass
#endregion


class Chatbot(CoreChatbot):
    """
    Enhanced chatbot with session support, routing, and RAG capabilities.
    """
    
    def __init__(self):
        super().__init__()
        self.llm_generator = None
        # In-memory cache: nhớ câu trả lời legal gần nhất cho từng session
        # để xử lý nhanh các câu hỏi follow-up như "tóm tắt", "có điều khoản liên quan không", ...
        self._last_legal_answer_by_session: Dict[str, str] = {}
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
        
        # Router decision (using raw intent)
        route_decision = decide_route(query, intent, confidence)
        
        # Use forced intent if router suggests it
        if route_decision.forced_intent:
            intent = route_decision.forced_intent

        # Map all domain search intents về search_legal để chỉ tra cứu tài liệu legal
        domain_search_intents = {
            "search_fine",
            "search_procedure",
            "search_office",
            "search_advisory",
            "general_query",  # mọi câu hỏi nội dung đều coi là tra cứu legal
        }
        if intent in domain_search_intents:
            intent = "search_legal"
            # Ép router cũng coi đây là truy vấn search_legal
            route_decision.route = IntentRoute.SEARCH
            route_decision.forced_intent = "search_legal"
        
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
            # Xử lý follow-up questions trong context cho các câu như:
            # - "Có điều khoản liên quan nào khác không?"
            # - "Tóm tắt nội dung chính của điều này?"
            follow_up_keywords = [
                "có điều khoản",
                "liên quan",
                "khác",
                "nữa",
                "thêm",
                "tóm tắt",
                "tải file",
                "tải",
                "download",
            ]
            query_lower = query.lower()
            is_follow_up = any(kw in query_lower for kw in follow_up_keywords)
            #region agent log
            _agent_debug_log(
                hypothesis_id="H1",
                location="chatbot.py:120",
                message="follow_up_detection",
                data={
                    "query": query,
                    "is_follow_up": is_follow_up,
                    "session_id_present": bool(session_id),
                },
            )
            #endregion

            response = None

            # Nếu là follow-up question, ưu tiên dùng context legal gần nhất trong session
            if is_follow_up and session_id:
                previous_answer = self._last_legal_answer_by_session.get(session_id, "")

                # Nếu in-memory cache trống, thử fallback sang ConversationContext (DB)
                if not previous_answer:
                    try:
                        recent_messages = ConversationContext.get_recent_messages(session_id, limit=5)
                        # Tìm message bot cuối cùng có intent search_legal
                        for msg in reversed(recent_messages):
                            if msg.role == "bot" and msg.intent == "search_legal":
                                previous_answer = msg.content or ""
                                break
                    except Exception as e:
                        logger.warning("[FOLLOW_UP] Failed to load context from DB: %s", e)

                if previous_answer:
                    if "tóm tắt" in query_lower:
                        # Ưu tiên dùng LLM để tóm tắt lại câu trả lời trước đó
                        summary_message = None
                        if getattr(self, "llm_generator", None):
                            try:
                                prompt = (
                                    "Bạn là chuyên gia pháp luật. Hãy tóm tắt ngắn gọn, rõ ràng nội dung chính của đoạn sau "
                                    "(giữ nguyên tinh thần và các mức, tỷ lệ, hình thức kỷ luật nếu có):\n\n"
                                    f"{previous_answer}"
                                )
                                summary_message = self.llm_generator.generate_answer(
                                    prompt,
                                    context=None,
                                    documents=None,
                                )
                            except Exception as e:
                                logger.warning("[FOLLOW_UP] LLM summary failed: %s", e)

                        if summary_message:
                            message = summary_message
                        else:
                            # Fallback: cắt ngắn nội dung trước đó
                            content_preview = (
                                previous_answer[:400] + "..." if len(previous_answer) > 400 else previous_answer
                            )
                            message = "Tóm tắt nội dung chính của điều khoản trước đó:\n\n" f"{content_preview}"
                    elif "tải" in query_lower:
                        message = (
                            "Bạn có thể tải file gốc của văn bản tại mục Quản lý văn bản trên hệ thống "
                            "hoặc liên hệ cán bộ phụ trách để được cung cấp bản đầy đủ."
                        )
                    else:
                        message = (
                            "Trong câu trả lời trước, tôi đã trích dẫn điều khoản chính liên quan. "
                            "Nếu bạn cần điều khoản khác (ví dụ về thẩm quyền, trình tự, hồ sơ), "
                            "hãy nêu rõ nội dung muốn tìm để tôi trợ giúp nhanh nhất."
                        )

                    response = {
                        "message": message,
                        "intent": "search_legal",
                        "confidence": 0.85,
                        "results": [],
                        "count": 0,
                        "routing": "follow_up",
                    }

            # Nếu không phải follow-up hoặc không tìm thấy context, trả về message thân thiện mặc định
            if response is None:
                #region agent log
                _agent_debug_log(
                    hypothesis_id="H1",
                    location="chatbot.py:187",
                    message="follow_up_fallback_small_talk",
                    data={
                        "is_follow_up": is_follow_up,
                        "session_id_present": bool(session_id),
                    },
                )
                #endregion
                response = {
                    "message": "Tôi có thể giúp bạn tra cứu các văn bản quy định pháp luật về xử lí kỷ luật cán bộ đảng viên. Bạn muốn tìm gì?",
                    "intent": intent,
                    "confidence": confidence,
                    "results": [],
                    "count": 0,
                    "routing": "small_talk",
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
        
        # Nếu là legal query, lưu lại câu trả lời gần nhất theo session để phục vụ follow-up nhanh
        if session_id and intent == "search_legal":
            try:
                self._last_legal_answer_by_session[session_id] = response.get("message", "") or ""
            except Exception:
                # Không để việc cache in-memory làm hỏng flow chính
                pass

        # Add session_id
        if session_id:
            response["session_id"] = session_id
        
        # Save bot response to context (DB)
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



