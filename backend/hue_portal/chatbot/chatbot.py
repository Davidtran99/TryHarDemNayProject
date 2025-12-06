"""
Chatbot wrapper that integrates core chatbot with router, LLM, and context management.
"""
import os
import copy
import logging
import json
import time
import unicodedata
import re
from typing import Dict, Any, Optional
from hue_portal.core.chatbot import Chatbot as CoreChatbot, get_chatbot as get_core_chatbot
from hue_portal.chatbot.router import decide_route, IntentRoute, RouteDecision, DOCUMENT_CODE_PATTERNS
from hue_portal.chatbot.context_manager import ConversationContext
from hue_portal.chatbot.llm_integration import LLMGenerator
from hue_portal.core.models import LegalSection, LegalDocument
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
def _agent_debug_log(hypothesis_id: str, location: str, message: str, data: Dict[str, Any]):
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
        pass
#endregion


class Chatbot(CoreChatbot):
    """
    Enhanced chatbot with session support, routing, and RAG capabilities.
    """
    
    def __init__(self):
        super().__init__()
        self.llm_generator = None
        # Cache in-memory: giữ câu trả lời legal gần nhất theo session để xử lý follow-up nhanh
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
        
        session_metadata: Dict[str, Any] = {}
        selected_doc_code: Optional[str] = None
        if session_id:
            try:
                session_metadata = ConversationContext.get_session_metadata(session_id)
                selected_doc_code = session_metadata.get("selected_document_code")
            except Exception:
                session_metadata = {}
        
        # Classify intent
        intent, confidence = self.classify_intent(query)
        
        # Router decision (using raw intent)
        route_decision = decide_route(query, intent, confidence)
        
        # Use forced intent if router suggests it
        if route_decision.forced_intent:
            intent = route_decision.forced_intent

        # Nếu session đã có selected_document_code (user đã chọn văn bản ở wizard)
        # thì ép intent về search_legal CHỈ KHI query không phải greeting/small_talk
        # Tránh ép greeting thành search_legal (gây chậm và sai logic)
        if selected_doc_code and route_decision.route != IntentRoute.GREETING:
            # Chỉ ép intent nếu không phải greeting đơn giản
            query_lower = query.lower().strip()
            is_simple_greeting = (
                len(query_lower.split()) <= 3 and
                any(greeting in query_lower for greeting in ["xin chào", "xin chao", "chào", "chao", "hello", "hi", "hey"]) and
                not any(kw in query_lower for kw in ["phạt", "mức phạt", "vi phạm", "thủ tục", "hồ sơ", "địa chỉ", "công an", "cảnh báo", "kỷ luật", "đảng"])
            )
            if not is_simple_greeting:
                intent = "search_legal"
                route_decision.route = IntentRoute.SEARCH
                route_decision.forced_intent = "search_legal"
            else:
                # Reset selected_doc_code nếu user gửi greeting mới
                if session_id:
                    try:
                        ConversationContext.update_session_metadata(
                            session_id,
                            {"selected_document_code": None, "selected_topic": None, "wizard_stage": None}
                        )
                        selected_doc_code = None
                        logger.info("[WIZARD] Reset selected_doc_code for new greeting")
                    except Exception:
                        pass

        # Map tất cả intent tra cứu nội dung về search_legal
        domain_search_intents = {
            "search_fine",
            "search_procedure",
            "search_office",
            "search_advisory",
            "general_query",
        }
        if intent in domain_search_intents:
            intent = "search_legal"
            route_decision.route = IntentRoute.SEARCH
            route_decision.forced_intent = "search_legal"
        
        # Instant exact-match cache lookup
        # ⚠️ Tắt cache cho intent search_legal để luôn đi qua wizard / Slow Path,
        # tránh trả lại các câu trả lời cũ không có options.
        cached_response = None
        if intent != "search_legal":
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

        # Wizard / option-first ngay tại chatbot layer:
        # Multi-stage wizard flow:
        # Stage 1: Choose document (if no document selected)
        # Stage 2: Choose topic/section (if document selected but no topic)
        # Stage 3: Choose detail (if topic selected, ask for more details)
        # Final: Answer (when user says "Không" or after detail selection)
        
        has_doc_code_in_query = self._query_has_document_code(query)
        wizard_stage = session_metadata.get("wizard_stage") if session_metadata else None
        selected_topic = session_metadata.get("selected_topic") if session_metadata else None
        wizard_depth = session_metadata.get("wizard_depth", 0) if session_metadata else 0
        
        print(f"[WIZARD] Chatbot layer check - intent={intent}, wizard_stage={wizard_stage}, selected_doc_code={selected_doc_code}, selected_topic={selected_topic}, has_doc_code_in_query={has_doc_code_in_query}, query='{query[:50]}'")
        
        # Reset wizard state if new query doesn't have document code and wizard_stage is "answer"
        # This handles the case where user asks a new question after completing a previous wizard flow
        # CRITICAL: Check conditions and reset BEFORE Stage 1 check
        should_reset = (
            intent == "search_legal" 
            and not has_doc_code_in_query 
            and wizard_stage == "answer"
        )
        print(f"[WIZARD] Reset check - intent={intent}, has_doc_code={has_doc_code_in_query}, wizard_stage={wizard_stage}, should_reset={should_reset}")  # v2.0-fix
        
        if should_reset:
            print("[WIZARD] 🔄 New query detected, resetting wizard state for fresh start")
            selected_doc_code = None
            selected_topic = None
            wizard_stage = None
            # Update session metadata FIRST before continuing
            if session_id:
                try:
                    ConversationContext.update_session_metadata(
                        session_id,
                        {
                            "selected_document_code": None,
                            "selected_topic": None,
                            "wizard_stage": None,
                            "wizard_depth": 0,
                        }
                    )
                    print("[WIZARD] ✅ Wizard state reset in session metadata")
                except Exception as e:
                    print(f"⚠️ Failed to reset wizard state: {e}")
            # Also update session_metadata dict for current function scope
            if session_metadata:
                session_metadata["selected_document_code"] = None
                session_metadata["selected_topic"] = None
                session_metadata["wizard_stage"] = None
                session_metadata["wizard_depth"] = 0
        
        # Stage 1: Choose document (if no document selected and no code in query)
        # Use direct semantic search from slow_path_handler (Query Rewrite disabled for performance)
        if intent == "search_legal" and not selected_doc_code and not has_doc_code_in_query:
            print("[WIZARD] ✅ Stage 1: Using direct semantic search from slow_path_handler")
            # Delegate to slow_path_handler which uses direct semantic search (no query rewrite)
            try:
                slow_handler = SlowPathHandler()
                response = slow_handler.handle(
                    query=query,
                    intent=intent,
                    session_id=session_id,
                    selected_document_code=None,  # No document selected yet
                )
            except Exception as e:
                logger.error("[WIZARD] Error in slow_path_handler: %s", e, exc_info=True)
                print(f"⚠️ [WIZARD] Error in slow_path_handler: {e}")
                response = None
            
            # Ensure response has wizard metadata and required fields
            if response and isinstance(response, dict):
                # Ensure message field exists
                if not response.get("message") and not response.get("clarification"):
                    response["message"] = "Tôi đã tìm thấy các văn bản pháp luật liên quan. Bạn hãy chọn văn bản muốn tra cứu:"
                
                response.setdefault("wizard_stage", "choose_document")
                response.setdefault("routing", "legal_wizard")
                response.setdefault("type", "options")
                response.setdefault("intent", intent)
                response.setdefault("results", [])
                response.setdefault("count", 0)
                
                # Update session metadata
                if session_id:
                    try:
                        ConversationContext.update_session_metadata(
                            session_id,
                            {
                                "wizard_stage": "choose_document",
                                "wizard_depth": 1,
                            }
                        )
                    except Exception as e:
                        logger.warning("[WIZARD] Failed to update session metadata: %s", e)
                
                # Save bot message to context
                if session_id:
                    try:
                        bot_message = response.get("message") or response.get("clarification", {}).get("message", "")
                        if bot_message:
                            ConversationContext.add_message(
                                session_id=session_id,
                                role="bot",
                                content=bot_message,
                                intent=intent,
                            )
                    except Exception as e:
                        print(f"⚠️ Failed to save wizard bot message: {e}")
                
                return response
            
            # Fallback response if slow_handler failed or returned invalid response
            logger.warning("[WIZARD] slow_path_handler returned invalid response, using fallback")
            return {
                "message": "Tôi đã tìm thấy các văn bản pháp luật liên quan. Bạn hãy chọn văn bản muốn tra cứu:",
                "intent": intent,
                "results": [],
                "count": 0,
                "type": "options",
                "wizard_stage": "choose_document",
                "routing": "legal_wizard",
                "clarification": {
                    "message": "Tôi đã tìm thấy các văn bản pháp luật liên quan. Bạn hãy chọn văn bản muốn tra cứu:",
                    "options": [
                        {
                            "code": "264-QD-TW",
                            "title": "Quyết định 264-QĐ/TW về kỷ luật đảng viên",
                            "reason": "Quy định chung về xử lý kỷ luật đối với đảng viên vi phạm.",
                        },
                        {
                            "code": "QD-69-TW",
                            "title": "Quy định 69-QĐ/TW về kỷ luật tổ chức đảng, đảng viên",
                            "reason": "Quy định chi tiết về các hành vi vi phạm và hình thức kỷ luật.",
                        },
                        {
                            "code": "TT-02-CAND",
                            "title": "Thông tư 02/2021/TT-BCA về điều lệnh CAND",
                            "reason": "Quy định về điều lệnh, lễ tiết, tác phong trong CAND.",
                        },
                    ],
                },
            }
        
        # Stage 2: Choose topic/section (if document selected but no topic yet)
        # Skip if wizard_stage is already "answer" (user wants final answer)
        if intent == "search_legal" and selected_doc_code and not selected_topic and not has_doc_code_in_query and wizard_stage != "answer":
            print("[WIZARD] ✅ Stage 2 triggered: Choose topic/section")
            
            # Get document title
            document_title = selected_doc_code
            try:
                doc = LegalDocument.objects.filter(code=selected_doc_code).first()
                if doc:
                    document_title = getattr(doc, "title", "") or selected_doc_code
            except Exception:
                pass
            
            # Extract keywords from query for parallel search
            search_keywords_from_query = []
            if self.llm_generator:
                try:
                    conversation_context = None
                    if session_id:
                        try:
                            recent_messages = ConversationContext.get_recent_messages(session_id, limit=5)
                            conversation_context = [
                                {"role": msg.role, "content": msg.content}
                                for msg in recent_messages
                            ]
                        except Exception:
                            pass
                    
                    search_keywords_from_query = self.llm_generator.extract_search_keywords(
                        query=query,
                        selected_options=None,  # No options selected yet
                        conversation_context=conversation_context,
                    )
                    print(f"[WIZARD] Extracted keywords: {search_keywords_from_query[:5]}")
                except Exception as exc:
                    logger.warning("[WIZARD] Keyword extraction failed: %s", exc)
            
            # Fallback to simple keyword extraction
            if not search_keywords_from_query:
                search_keywords_from_query = self.chatbot.extract_keywords(query)
            
            # Trigger parallel search for document (if not already done)
            slow_handler = SlowPathHandler()
            prefetched_results = slow_handler._get_prefetched_results(session_id, "document_results")
            
            if not prefetched_results:
                # Trigger parallel search now
                slow_handler._parallel_search_prepare(
                    document_code=selected_doc_code,
                    keywords=search_keywords_from_query,
                    session_id=session_id,
                )
                logger.info("[WIZARD] Triggered parallel search for document")
            
            # Get prefetched search results from parallel search (if available)
            prefetched_results = slow_handler._get_prefetched_results(session_id, "document_results")
            search_results = []
            
            if prefetched_results:
                search_results = prefetched_results.get("results", [])
                logger.info("[WIZARD] Using prefetched results: %d sections", len(search_results))
            else:
                # Fallback: search synchronously if prefetch not ready
                search_result = slow_handler._search_by_intent(
                    intent="search_legal",
                    query=query,
                    limit=20,
                    preferred_document_code=selected_doc_code.upper(),
                )
                search_results = search_result.get("results", [])
                logger.info("[WIZARD] Fallback search: %d sections", len(search_results))
            
            # Extract keywords for topic options
            conversation_context = None
            if session_id:
                try:
                    recent_messages = ConversationContext.get_recent_messages(session_id, limit=5)
                    conversation_context = [
                        {"role": msg.role, "content": msg.content}
                        for msg in recent_messages
                    ]
                except Exception:
                    pass
            
            # Use LLM to generate topic options
            topic_options = []
            intro_message = f"Bạn muốn tìm điều khoản/chủ đề nào cụ thể trong {document_title}?"
            search_keywords = []
            
            if self.llm_generator:
                try:
                    llm_payload = self.llm_generator.suggest_topic_options(
                        query=query,
                        document_code=selected_doc_code,
                        document_title=document_title,
                        search_results=search_results[:10],  # Top 10 for options
                        conversation_context=conversation_context,
                        max_options=3,
                    )
                    if llm_payload:
                        intro_message = llm_payload.get("message") or intro_message
                        topic_options = llm_payload.get("options", [])
                        search_keywords = llm_payload.get("search_keywords", [])
                        print(f"[WIZARD] ✅ LLM generated {len(topic_options)} topic options")
                except Exception as exc:
                    logger.warning("[WIZARD] LLM topic suggestion failed: %s", exc)
            
            # Fallback: build options from search results
            if not topic_options and search_results:
                for result in search_results[:3]:
                    data = result.get("data", {})
                    section_title = data.get("section_title") or data.get("title") or ""
                    article = data.get("article") or data.get("article_number") or ""
                    if section_title or article:
                        topic_options.append({
                            "title": section_title or article,
                            "article": article,
                            "reason": data.get("excerpt", "")[:100] or "",
                            "keywords": [],
                        })
            
            # If still no options, create generic ones
            if not topic_options:
                topic_options = [
                    {
                        "title": "Các điều khoản liên quan",
                        "article": "",
                        "reason": "Tìm kiếm các điều khoản liên quan đến câu hỏi của bạn",
                        "keywords": [],
                    }
                ]
            
            # Trigger parallel search for selected keywords
            if search_keywords:
                slow_handler._parallel_search_topic(
                    document_code=selected_doc_code,
                    topic_keywords=search_keywords,
                    session_id=session_id,
                )
            
            response = {
                "message": intro_message,
                "intent": intent,
                "confidence": confidence,
                "results": [],
                "count": 0,
                "routing": "legal_wizard",
                "type": "options",
                "wizard_stage": "choose_topic",
                "clarification": {
                    "message": intro_message,
                    "options": topic_options,
                },
                "options": topic_options,
            }
            if session_id:
                response["session_id"] = session_id
                try:
                    ConversationContext.add_message(
                        session_id=session_id,
                        role="bot",
                        content=intro_message,
                        intent=intent,
                    )
                    ConversationContext.update_session_metadata(
                        session_id,
                        {
                            "wizard_stage": "choose_topic",
                        },
                    )
                except Exception as e:
                    print(f"⚠️ Failed to save Stage 2 bot message: {e}")
            return response
        
        # Stage 3: Choose detail (if topic selected, ask if user wants more details)
        # Skip if wizard_stage is already "answer" (user wants final answer)
        if intent == "search_legal" and selected_doc_code and selected_topic and wizard_stage != "answer":
            # Check if user is asking for more details or saying "Không"
            query_lower = query.lower()
            wants_more = any(kw in query_lower for kw in ["có", "cần", "muốn", "thêm", "chi tiết", "nữa"])
            says_no = any(kw in query_lower for kw in ["không", "khong", "thôi", "đủ", "xong"])
            
            if says_no or wizard_depth >= 2:
                # User doesn't want more details or already asked twice - proceed to final answer
                print("[WIZARD] ✅ User wants final answer, proceeding to slow_path")
                # Clear wizard stage to allow normal answer flow
                if session_id:
                    try:
                        ConversationContext.update_session_metadata(
                            session_id,
                            {
                                "wizard_stage": "answer",
                            },
                        )
                    except Exception:
                        pass
            elif wants_more or wizard_depth == 0:
                # User wants more details - generate detail options
                print("[WIZARD] ✅ Stage 3 triggered: Choose detail")
                
                # Get conversation context
                conversation_context = None
                if session_id:
                    try:
                        recent_messages = ConversationContext.get_recent_messages(session_id, limit=5)
                        conversation_context = [
                            {"role": msg.role, "content": msg.content}
                            for msg in recent_messages
                        ]
                    except Exception:
                        pass
                
                # Use LLM to generate detail options
                detail_options = []
                intro_message = "Bạn muốn chi tiết gì cho chủ đề này nữa không?"
                search_keywords = []
                
                if self.llm_generator:
                    try:
                        llm_payload = self.llm_generator.suggest_detail_options(
                            query=query,
                            selected_document_code=selected_doc_code,
                            selected_topic=selected_topic,
                            conversation_context=conversation_context,
                            max_options=3,
                        )
                        if llm_payload:
                            intro_message = llm_payload.get("message") or intro_message
                            detail_options = llm_payload.get("options", [])
                            search_keywords = llm_payload.get("search_keywords", [])
                            print(f"[WIZARD] ✅ LLM generated {len(detail_options)} detail options")
                    except Exception as exc:
                        logger.warning("[WIZARD] LLM detail suggestion failed: %s", exc)
                
                # Fallback options
                if not detail_options:
                    detail_options = [
                        {
                            "title": "Thẩm quyền xử lý",
                            "reason": "Tìm hiểu về thẩm quyền xử lý kỷ luật",
                            "keywords": ["thẩm quyền", "xử lý"],
                        },
                        {
                            "title": "Trình tự, thủ tục",
                            "reason": "Tìm hiểu về trình tự, thủ tục xử lý",
                            "keywords": ["trình tự", "thủ tục"],
                        },
                        {
                            "title": "Hình thức kỷ luật",
                            "reason": "Tìm hiểu về các hình thức kỷ luật",
                            "keywords": ["hình thức", "kỷ luật"],
                        },
                    ]
                
                # Trigger parallel search for detail keywords
                if search_keywords and session_id:
                    slow_handler = SlowPathHandler()
                    slow_handler._parallel_search_topic(
                        document_code=selected_doc_code,
                        topic_keywords=search_keywords,
                        session_id=session_id,
                    )
                
                response = {
                    "message": intro_message,
                    "intent": intent,
                    "confidence": confidence,
                    "results": [],
                    "count": 0,
                    "routing": "legal_wizard",
                    "type": "options",
                    "wizard_stage": "choose_detail",
                    "clarification": {
                        "message": intro_message,
                        "options": detail_options,
                    },
                    "options": detail_options,
                }
                if session_id:
                    response["session_id"] = session_id
                    try:
                        ConversationContext.add_message(
                            session_id=session_id,
                            role="bot",
                            content=intro_message,
                            intent=intent,
                        )
                        ConversationContext.update_session_metadata(
                            session_id,
                            {
                                "wizard_stage": "choose_detail",
                                "wizard_depth": wizard_depth + 1,
                            },
                        )
                    except Exception as e:
                        print(f"⚠️ Failed to save Stage 3 bot message: {e}")
                return response
        
        # Always send legal intent through Slow Path RAG
        if intent == "search_legal":
            response = self._run_slow_path_legal(
                query,
                intent,
                session_id,
                route_decision,
                session_metadata=session_metadata,
            )
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
                hypothesis_id="H2",
                location="chatbot.py:119",
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

                # Nếu chưa có trong cache in-memory, fallback sang ConversationContext DB
                if not previous_answer:
                    try:
                        recent_messages = ConversationContext.get_recent_messages(session_id, limit=5)
                        for msg in reversed(recent_messages):
                            if msg.role == "bot" and msg.intent == "search_legal":
                                previous_answer = msg.content or ""
                                break
                    except Exception as e:
                        logger.warning("[FOLLOW_UP] Failed to load context from DB: %s", e)

                if previous_answer:
                    if "tóm tắt" in query_lower:
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
            
            # Nếu không phải follow-up hoặc không tìm thấy context, trả về message thân thiện
            if response is None:
                #region agent log
                _agent_debug_log(
                    hypothesis_id="H1",
                    location="chatbot.py:193",
                    message="follow_up_fallback",
                    data={
                        "is_follow_up": is_follow_up,
                        "session_id_present": bool(session_id),
                    },
                )
                #endregion
                # Detect off-topic questions (nấu ăn, chả trứng, etc.)
                off_topic_keywords = ["nấu", "nau", "chả trứng", "cha trung", "món ăn", "mon an", "công thức", "cong thuc", 
                                     "cách làm", "cach lam", "đổ chả", "do cha", "trứng", "trung"]
                is_off_topic = any(kw in query_lower for kw in off_topic_keywords)
                
                if is_off_topic:
                    # Ngoài phạm vi → từ chối lịch sự + gợi ý wizard với các văn bản pháp lý chính
                    intro_message = (
                        "Xin lỗi, tôi là chatbot chuyên về tra cứu các văn bản quy định pháp luật "
                        "về xử lí kỷ luật cán bộ đảng viên của Phòng Thanh Tra - Công An Thành Phố Huế.\n\n"
                        "Tôi không thể trả lời các câu hỏi về nấu ăn, công thức nấu ăn hay các chủ đề khác ngoài phạm vi pháp luật.\n\n"
                        "Tuy nhiên, tôi có thể giúp bạn tra cứu một số văn bản pháp luật quan trọng. "
                        "Bạn hãy chọn văn bản muốn xem trước:"
                    )
                    clarification_options = [
                        {
                            "code": "264-QD-TW",
                            "title": "Quyết định 264-QĐ/TW về kỷ luật đảng viên",
                            "reason": "Quy định chung về xử lý kỷ luật đối với đảng viên vi phạm.",
                        },
                        {
                            "code": "QD-69-TW",
                            "title": "Quy định 69-QĐ/TW về kỷ luật tổ chức đảng, đảng viên",
                            "reason": "Quy định chi tiết về các hành vi vi phạm và hình thức kỷ luật.",
                        },
                        {
                            "code": "TT-02-CAND",
                            "title": "Thông tư 02/2021/TT-BCA về điều lệnh CAND",
                            "reason": "Quy định về điều lệnh, lễ tiết, tác phong trong CAND.",
                        },
                        {
                            "code": "__other__",
                            "title": "Khác",
                            "reason": "Tôi muốn hỏi văn bản hoặc chủ đề pháp luật khác.",
                        },
                    ]
                    response = {
                        "message": intro_message,
                        "intent": intent,
                        "confidence": confidence,
                        "results": [],
                        "count": 0,
                        "routing": "small_talk_offtopic_wizard",
                        "type": "options",
                        "wizard_stage": "choose_document",
                        "clarification": {
                            "message": intro_message,
                            "options": clarification_options,
                        },
                        "options": clarification_options,
                    }
                else:
                    message = (
                        "Tôi có thể giúp bạn tra cứu các văn bản quy định pháp luật về xử lí kỷ luật cán bộ đảng viên. "
                        "Bạn muốn tìm gì?"
                    )
                response = {
                    "message": message,
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
        
        if session_id and intent == "search_legal":
            try:
                self._last_legal_answer_by_session[session_id] = response.get("message", "") or ""
            except Exception:
                pass

        # Đánh dấu loại payload cho frontend: answer hay options (wizard)
        if response.get("clarification") or response.get("type") == "options":
            response.setdefault("type", "options")
        else:
            response.setdefault("type", "answer")

        # Add session_id
        if session_id:
            response["session_id"] = session_id
        
        # Save bot response to context
        if session_id:
            try:
                bot_message = response.get("message") or response.get("clarification", {}).get("message", "")
                ConversationContext.add_message(
                    session_id=session_id,
                    role="bot",
                    content=bot_message,
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
        session_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute Slow Path legal handler (with fast-path + structured output)."""
        slow_handler = SlowPathHandler()
        selected_doc_code = None
        if session_metadata:
            selected_doc_code = session_metadata.get("selected_document_code")
        response = slow_handler.handle(
            query,
            intent,
            session_id,
            selected_document_code=selected_doc_code,
        )
        response.setdefault("routing", "slow_path")
        response.setdefault(
            "_routing",
            {
                "path": "slow_path",
                "method": getattr(route_decision, "rationale", "router"),
                "confidence": route_decision.confidence,
            },
        )

        # Cập nhật metadata wizard đơn giản: nếu đang hỏi người dùng chọn văn bản
        # thì đánh dấu stage = choose_document; nếu đã trả lời thì stage = answer.
        if session_id:
            try:
                if response.get("clarification") or response.get("type") == "options":
                    ConversationContext.update_session_metadata(
                        session_id,
                        {
                            "wizard_stage": "choose_document",
                        },
                    )
                else:
                    ConversationContext.update_session_metadata(
                        session_id,
                        {
                            "wizard_stage": "answer",
                            "last_answer_type": response.get("intent"),
                        },
                    )
            except Exception:
                # Không để lỗi metadata làm hỏng luồng trả lời chính
                pass

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
        if response.get("clarification"):
            return False
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

    def _query_has_document_code(self, query: str) -> bool:
        """
        Check if the raw query string explicitly contains a known document code pattern
        (ví dụ: '264/QĐ-TW', 'QD-69-TW', 'TT-02-CAND').
        """
        if not query:
            return False
        # Remove accents để regex đơn giản hơn
        normalized = unicodedata.normalize("NFD", query)
        normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
        normalized = normalized.upper()
        for pattern in DOCUMENT_CODE_PATTERNS:
            try:
                if re.search(pattern, normalized):
                    return True
            except re.error:
                continue
        return False
    
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



