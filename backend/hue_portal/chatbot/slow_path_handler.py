"""
Slow Path Handler - Full RAG pipeline for complex queries.
"""
import os
import time
import logging
import hashlib
from typing import Dict, Any, Optional, List, Set
import unicodedata
import re
from concurrent.futures import ThreadPoolExecutor, Future
import threading

from hue_portal.core.chatbot import get_chatbot, RESPONSE_TEMPLATES
from hue_portal.core.models import (
    Fine,
    Procedure,
    Office,
    Advisory,
    LegalSection,
    LegalDocument,
)
from hue_portal.core.search_ml import search_with_ml
from hue_portal.core.pure_semantic_search import pure_semantic_search
# Lazy import reranker to avoid blocking startup (FlagEmbedding may download model)
# from hue_portal.core.reranker import rerank_documents
from hue_portal.chatbot.llm_integration import get_llm_generator
from hue_portal.chatbot.structured_legal import format_structured_legal_answer
from hue_portal.chatbot.context_manager import ConversationContext
from hue_portal.chatbot.router import DOCUMENT_CODE_PATTERNS
from hue_portal.core.query_rewriter import get_query_rewriter
from hue_portal.core.pure_semantic_search import pure_semantic_search, parallel_vector_search
from hue_portal.core.redis_cache import get_redis_cache

logger = logging.getLogger(__name__)


class SlowPathHandler:
    """Handle Slow Path queries with full RAG pipeline."""
    
    def __init__(self):
        self.chatbot = get_chatbot()
        self.llm_generator = get_llm_generator()
        # Thread pool for parallel search (max 2 workers to avoid overwhelming DB)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="parallel_search")
        # Cache for prefetched results by session_id (in-memory fallback)
        self._prefetched_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = threading.Lock()
        # Redis cache for prefetch results
        self.redis_cache = get_redis_cache()
        # Prefetch cache TTL (30 minutes default)
        self.prefetch_cache_ttl = int(os.environ.get("CACHE_PREFETCH_TTL", "1800"))
    
    def handle(
        self,
        query: str,
        intent: str,
        session_id: Optional[str] = None,
        selected_document_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Full RAG pipeline:
        1. Search (hybrid: BM25 + vector)
        2. Retrieve top 20 documents
        3. LLM generation with structured output (for legal queries)
        4. Guardrails validation
        5. Retry up to 3 times if needed
        
        Args:
            query: User query.
            intent: Detected intent.
            session_id: Optional session ID for context.
            selected_document_code: Selected document code from wizard.
        
        Returns:
            Response dict with message, intent, results, etc.
        """
        query = query.strip()
        selected_document_code_normalized = (
            selected_document_code.strip().upper() if selected_document_code else None
        )
        
        # Handle greetings
        if intent == "greeting":
            query_lower = query.lower().strip()
            query_words = query_lower.split()
            is_simple_greeting = (
                len(query_words) <= 3 and 
                any(greeting in query_lower for greeting in ["xin chào", "chào", "hello", "hi"]) and
                not any(kw in query_lower for kw in ["phạt", "mức phạt", "vi phạm", "thủ tục", "hồ sơ", "địa chỉ", "công an", "cảnh báo"])
            )
            if is_simple_greeting:
                return {
                    "message": RESPONSE_TEMPLATES["greeting"],
                    "intent": "greeting",
                    "results": [],
                    "count": 0,
                    "_source": "slow_path"
                }
        
        # Wizard / option-first cho mọi câu hỏi pháp lý chung:
        # Nếu:
        #   - intent là search_legal
        #   - chưa có selected_document_code trong session
        #   - trong câu hỏi không ghi rõ mã văn bản
        # Thì: luôn trả về payload options để người dùng chọn văn bản trước,
        # chưa generate câu trả lời chi tiết.
        has_explicit_code = self._has_explicit_document_code_in_query(query)
        logger.info(
            "[WIZARD] Checking wizard conditions - intent=%s, selected_code=%s, has_explicit_code=%s, query='%s'",
            intent,
            selected_document_code_normalized,
            has_explicit_code,
            query[:50],
        )
        if (
            intent == "search_legal"
            and not selected_document_code_normalized
            and not has_explicit_code
        ):
            # DISABLED: Query Rewrite Strategy (mất 5-10s, gây timeout)
            # Sử dụng pure semantic search trực tiếp với query gốc để nhanh hơn
            logger.info("[SEARCH] Using direct semantic search (Query Rewrite disabled for performance)")
            
            try:
                from hue_portal.core.models import LegalSection
                
                # Search all legal sections (no document filter yet)
                qs = LegalSection.objects.all()
                text_fields = ["section_title", "section_code", "content"]
                
                # Use direct semantic search with original query (no rewrite)
                # Use _single_query_search directly to get (section, score) tuples
                from hue_portal.core.pure_semantic_search import _single_query_search
                search_results = _single_query_search(
                    query,
                    qs,
                    top_k=10,
                    text_fields=text_fields
                )
                
                # Extract unique document codes from results
                doc_codes_seen: Set[str] = set()
                document_options: List[Dict[str, Any]] = []
                
                # search_results is List[Tuple[section, score]]
                for section, score in search_results:
                    doc = getattr(section, "document", None)
                    if not doc:
                        continue
                    
                    doc_code = getattr(doc, "code", "").upper()
                    if not doc_code or doc_code in doc_codes_seen:
                        continue
                    
                    doc_codes_seen.add(doc_code)
                    
                    # Get document metadata
                    doc_title = getattr(doc, "title", "") or doc_code
                    doc_summary = getattr(doc, "summary", "") or ""
                    if not doc_summary:
                        metadata = getattr(doc, "metadata", {}) or {}
                        if isinstance(metadata, dict):
                            doc_summary = metadata.get("summary", "")
                    
                    document_options.append({
                        "code": doc_code,
                        "title": doc_title,
                        "summary": doc_summary,
                        "score": float(score),
                        "doc_type": getattr(doc, "doc_type", "") or "",
                    })
                    
                    # Limit to top 5 documents
                    if len(document_options) >= 5:
                        break
                
                # If no documents found, use canonical fallback
                if not document_options:
                    logger.warning("[QUERY_REWRITE] No documents found, using canonical fallback")
                    canonical_candidates = [
                        {
                            "code": "264-QD-TW",
                            "title": "Quyết định 264-QĐ/TW về kỷ luật đảng viên",
                            "summary": "",
                            "doc_type": "",
                        },
                        {
                            "code": "QD-69-TW",
                            "title": "Quy định 69-QĐ/TW về kỷ luật tổ chức đảng, đảng viên",
                            "summary": "",
                            "doc_type": "",
                        },
                        {
                            "code": "TT-02-CAND",
                            "title": "Thông tư 02/2021/TT-BCA về điều lệnh CAND",
                            "summary": "",
                            "doc_type": "",
                        },
                    ]
                    clarification_payload = self._build_clarification_payload(
                        query, canonical_candidates
                    )
                    if clarification_payload:
                        clarification_payload.setdefault("intent", intent)
                        clarification_payload.setdefault("_source", "clarification")
                        clarification_payload.setdefault("routing", "clarification")
                        clarification_payload.setdefault("confidence", 0.3)
                        return clarification_payload
                
                # Build options from search results
                options = [
                    {
                        "code": opt["code"],
                        "title": opt["title"],
                        "reason": opt.get("summary") or f"Độ liên quan: {opt['score']:.2f}",
                    }
                    for opt in document_options
                ]
                
                # Add "Khác" option
                if not any(opt.get("code") == "__other__" for opt in options):
                    options.append({
                        "code": "__other__",
                        "title": "Khác",
                        "reason": "Tôi muốn hỏi văn bản hoặc chủ đề pháp luật khác.",
                    })
                
                message = (
                    "Tôi đã tìm thấy các văn bản pháp luật liên quan đến câu hỏi của bạn.\n\n"
                    "Bạn hãy chọn văn bản muốn tra cứu để tôi trả lời chi tiết hơn:"
                )
                
                logger.info(
                    "[SEARCH] ✅ Found %d documents using direct semantic search",
                    len(document_options)
                )
                
                return {
                    "type": "options",
                    "wizard_stage": "choose_document",
                    "message": message,
                    "options": options,
                    "clarification": {
                        "message": message,
                        "options": options,
                    },
                    "results": [],
                    "count": 0,
                    "intent": intent,
                    "_source": "direct_search",
                    "routing": "direct_search",
                    "confidence": 0.85,  # Slightly lower than query rewrite but still good
                }
                
            except Exception as exc:
                logger.error(
                    "[SEARCH] Error in direct semantic search: %s, falling back to LLM suggestions",
                    exc,
                    exc_info=True
                )
                # Fallback to original LLM-based clarification
                canonical_candidates: List[Dict[str, Any]] = []
                try:
                    canonical_docs = list(
                        LegalDocument.objects.filter(
                            code__in=["264-QD-TW", "QD-69-TW", "TT-02-CAND"]
                        )
                    )
                    for doc in canonical_docs:
                        summary = getattr(doc, "summary", "") or ""
                        metadata = getattr(doc, "metadata", {}) or {}
                        if not summary and isinstance(metadata, dict):
                            summary = metadata.get("summary", "")
                        canonical_candidates.append(
                            {
                                "code": doc.code,
                                "title": getattr(doc, "title", "") or doc.code,
                                "summary": summary,
                                "doc_type": getattr(doc, "doc_type", "") or "",
                                "section_title": "",
                            }
                        )
                except Exception as e:
                    logger.warning("[CLARIFICATION] Canonical documents lookup failed: %s", e)
                
                if not canonical_candidates:
                    canonical_candidates = [
                        {
                            "code": "264-QD-TW",
                            "title": "Quyết định 264-QĐ/TW về kỷ luật đảng viên",
                            "summary": "",
                            "doc_type": "",
                            "section_title": "",
                        },
                        {
                            "code": "QD-69-TW",
                            "title": "Quy định 69-QĐ/TW về kỷ luật tổ chức đảng, đảng viên",
                            "summary": "",
                            "doc_type": "",
                            "section_title": "",
                        },
                        {
                            "code": "TT-02-CAND",
                            "title": "Thông tư 02/2021/TT-BCA về điều lệnh CAND",
                            "summary": "",
                            "doc_type": "",
                            "section_title": "",
                        },
                    ]
                
                clarification_payload = self._build_clarification_payload(
                    query, canonical_candidates
                )
                if clarification_payload:
                    clarification_payload.setdefault("intent", intent)
                    clarification_payload.setdefault("_source", "clarification_fallback")
                    clarification_payload.setdefault("routing", "clarification")
                    clarification_payload.setdefault("confidence", 0.3)
                    return clarification_payload

        # Search based on intent - retrieve top-15 for reranking (balance speed and RAM)
        search_result = self._search_by_intent(
            intent,
            query,
            limit=15,
            preferred_document_code=selected_document_code_normalized,
        )  # Balance: 15 for good recall, not too slow
        
        # Fast path for high-confidence legal queries (skip for complex queries)
        fast_path_response = None
        if intent == "search_legal" and not self._is_complex_query(query):
            fast_path_response = self._maybe_fast_path_response(search_result["results"], query)
            if fast_path_response:
                fast_path_response["intent"] = intent
                fast_path_response["_source"] = "fast_path"
                return fast_path_response
        
        # Rerank results - DISABLED for speed (can enable via ENABLE_RERANKER env var)
        # Reranker adds 1-3 seconds delay, skip for faster responses
        enable_reranker = os.environ.get("ENABLE_RERANKER", "false").lower() == "true"
        if intent == "search_legal" and enable_reranker:
            try:
                # Lazy import to avoid blocking startup (FlagEmbedding may download model)
                from hue_portal.core.reranker import rerank_documents
                
                legal_results = [r for r in search_result["results"] if r.get("type") == "legal"]
                if len(legal_results) > 0:
                    # Rerank to top-4 (balance speed and context quality)
                    top_k = min(4, len(legal_results))
                    reranked = rerank_documents(query, legal_results, top_k=top_k)
                    # Update search_result with reranked results (keep non-legal results)
                    non_legal = [r for r in search_result["results"] if r.get("type") != "legal"]
                    search_result["results"] = reranked + non_legal
                    search_result["count"] = len(search_result["results"])
                    logger.info(
                        "[RERANKER] Reranked %d legal results to top-%d for query: %s",
                        len(legal_results),
                        top_k,
                        query[:50]
                    )
            except Exception as e:
                logger.warning("[RERANKER] Reranking failed: %s, using original results", e)
        elif intent == "search_legal":
            # Skip reranking for speed - just use top results by score
            logger.debug("[RERANKER] Skipped reranking for speed (ENABLE_RERANKER=false)")
        
        # BƯỚC 1: Bypass LLM khi có results tốt (tránh context overflow + tăng tốc 30-40%)
        # Chỉ áp dụng cho legal queries có results với score cao
        if intent == "search_legal" and search_result["count"] > 0:
            top_result = search_result["results"][0]
            top_score = top_result.get("score", 0.0) or 0.0
            top_data = top_result.get("data", {})
            doc_code = (top_data.get("document_code") or "").upper()
            content = top_data.get("content", "") or top_data.get("excerpt", "")
            
            # Bypass LLM nếu:
            # 1. Có document code (TT-02-CAND, etc.) và content đủ dài
            # 2. Score >= 0.4 (giảm threshold để dễ trigger hơn)
            # 3. Hoặc có keywords quan trọng (%, hạ bậc, thi đua, tỷ lệ) với score >= 0.3
            should_bypass = False
            query_lower = query.lower()
            has_keywords = any(kw in query_lower for kw in ["%", "phần trăm", "tỷ lệ", "12%", "20%", "10%", "hạ bậc", "thi đua", "xếp loại", "vi phạm", "cán bộ"])
            
            # Điều kiện bypass dễ hơn: có doc_code + content đủ dài + score hợp lý
            if doc_code and len(content) > 100:
                if top_score >= 0.4:
                    should_bypass = True
                elif has_keywords and top_score >= 0.3:
                    should_bypass = True
            # Hoặc có keywords quan trọng + content đủ dài
            elif has_keywords and len(content) > 100 and top_score >= 0.3:
                should_bypass = True
            
            if should_bypass:
                # Template trả thẳng cho query về tỷ lệ vi phạm + hạ bậc thi đua
                if any(kw in query_lower for kw in ["12%", "tỷ lệ", "phần trăm", "hạ bậc", "thi đua"]):
                    # Query về tỷ lệ vi phạm và hạ bậc thi đua
                    section_code = top_data.get("section_code", "")
                    section_title = top_data.get("section_title", "")
                    doc_title = top_data.get("document_title", "văn bản pháp luật")
                    
                    # Trích xuất đoạn liên quan từ content
                    content_preview = content[:600] + "..." if len(content) > 600 else content
                    
                    answer = (
                        f"Theo {doc_title} ({doc_code}):\n\n"
                        f"{section_code}: {section_title}\n\n"
                        f"{content_preview}\n\n"
                        f"Nguồn: {section_code}, {doc_title} ({doc_code})"
                    )
                else:
                    # Template chung cho legal queries
                    section_code = top_data.get("section_code", "Điều liên quan")
                    section_title = top_data.get("section_title", "")
                    doc_title = top_data.get("document_title", "văn bản pháp luật")
                    content_preview = content[:500] + "..." if len(content) > 500 else content
                    
                    answer = (
                        f"Kết quả chính xác nhất:\n\n"
                        f"- Văn bản: {doc_title} ({doc_code})\n"
                        f"- Điều khoản: {section_code}" + (f" – {section_title}" if section_title else "") + "\n\n"
                        f"{content_preview}\n\n"
                        f"Nguồn: {section_code}, {doc_title} ({doc_code})"
                    )
                
                logger.info(
                    "[BYPASS_LLM] Using raw template for legal query (score=%.3f, doc=%s, query='%s')",
                    top_score,
                    doc_code,
                    query[:50]
                )
                
                return {
                    "message": answer,
                    "intent": intent,
                    "confidence": min(0.99, top_score + 0.05),
                    "results": search_result["results"][:3],
                    "count": min(3, search_result["count"]),
                    "_source": "raw_template",
                    "routing": "raw_template"
                }
        
        # Get conversation context if available
        context = None
        context_summary = ""
        if session_id:
            try:
                recent_messages = ConversationContext.get_recent_messages(session_id, limit=5)
                context = [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "intent": msg.intent
                    }
                    for msg in recent_messages
                ]
                # Tạo context summary để đưa vào prompt nếu có conversation history
                if len(context) > 1:
                    context_parts = []
                    for msg in reversed(context[-3:]):  # Chỉ lấy 3 message gần nhất
                        if msg["role"] == "user":
                            context_parts.append(f"Người dùng: {msg['content'][:100]}")
                        elif msg["role"] == "bot":
                            context_parts.append(f"Bot: {msg['content'][:100]}")
                    if context_parts:
                        context_summary = "\n\nNgữ cảnh cuộc trò chuyện trước đó:\n" + "\n".join(context_parts)
            except Exception as exc:
                logger.warning("[CONTEXT] Failed to load conversation context: %s", exc)
        
        # Enhance query with context if available
        enhanced_query = query
        if context_summary:
            enhanced_query = query + context_summary
        
        # Generate response message using LLM if available and we have documents
        message = None
        if self.llm_generator and search_result["count"] > 0:
            # For legal queries, use structured output (top-4 for good context and speed)
            if intent == "search_legal" and search_result["results"]:
                legal_docs = [r["data"] for r in search_result["results"] if r.get("type") == "legal"][:4]  # Top-4 for balance
                if legal_docs:
                    structured_answer = self.llm_generator.generate_structured_legal_answer(
                        enhanced_query,  # Dùng enhanced_query có context
                        legal_docs,
                        prefill_summary=None
                    )
                    if structured_answer:
                        message = format_structured_legal_answer(structured_answer)
            
            # For other intents or if structured failed, use regular LLM generation
            if not message:
                documents = [r["data"] for r in search_result["results"][:4]]  # Top-4 for balance
                message = self.llm_generator.generate_answer(
                    enhanced_query,  # Dùng enhanced_query có context
                    context=context,
                    documents=documents
                )
        
        # Fallback to template if LLM not available or failed
        if not message:
            if search_result["count"] > 0:
                # Đặc biệt xử lý legal queries: format tốt hơn thay vì dùng template chung
                if intent == "search_legal" and search_result["results"]:
                    top_result = search_result["results"][0]
                    top_data = top_result.get("data", {})
                    doc_code = top_data.get("document_code", "")
                    doc_title = top_data.get("document_title", "văn bản pháp luật")
                    section_code = top_data.get("section_code", "")
                    section_title = top_data.get("section_title", "")
                    content = top_data.get("content", "") or top_data.get("excerpt", "")
                    
                    if content and len(content) > 50:
                        content_preview = content[:400] + "..." if len(content) > 400 else content
                        message = (
                            f"Tôi tìm thấy {search_result['count']} điều khoản liên quan đến '{query}':\n\n"
                            f"**{section_code}**: {section_title or 'Nội dung liên quan'}\n\n"
                            f"{content_preview}\n\n"
                            f"Nguồn: {doc_title}" + (f" ({doc_code})" if doc_code else "")
                        )
                    else:
                        template = RESPONSE_TEMPLATES.get(intent, RESPONSE_TEMPLATES["general_query"])
                        message = template.format(
                            count=search_result["count"],
                            query=query
                        )
                else:
                    template = RESPONSE_TEMPLATES.get(intent, RESPONSE_TEMPLATES["general_query"])
                    message = template.format(
                        count=search_result["count"],
                        query=query
                    )
            else:
                message = RESPONSE_TEMPLATES["no_results"].format(query=query)
        
        # Limit results to top 5 for response
        results = search_result["results"][:5]
        
        response = {
            "message": message,
            "intent": intent,
            "confidence": 0.95,  # High confidence for Slow Path (thorough search)
            "results": results,
            "count": len(results),
            "_source": "slow_path"
        }
        
        return response
    
    def _maybe_request_clarification(
        self,
        query: str,
        search_result: Dict[str, Any],
        selected_document_code: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Quyết định có nên hỏi người dùng chọn văn bản (wizard step: choose_document).

        Nguyên tắc option-first:
        - Nếu user CHƯA chọn văn bản trong session
        - Và trong câu hỏi KHÔNG ghi rõ mã văn bản
        - Và search có trả về kết quả
        => Ưu tiên trả về danh sách văn bản để người dùng chọn, thay vì trả lời thẳng.
        """
        if selected_document_code:
            return None
        if not search_result or search_result.get("count", 0) == 0:
            return None

        # Nếu người dùng đã ghi rõ mã văn bản trong câu hỏi (ví dụ: 264/QĐ-TW)
        # thì không cần hỏi lại – ưu tiên dùng chính mã đó.
        if self._has_explicit_document_code_in_query(query):
            return None

        # Ưu tiên dùng danh sách văn bản "chuẩn" (canonical) nếu có trong DB.
        # Tuy nhiên, để đảm bảo wizard luôn hoạt động (option-first),
        # nếu DB chưa đủ dữ liệu thì vẫn build danh sách tĩnh fallback.
        fallback_candidates: List[Dict[str, Any]] = []
        try:
            fallback_docs = list(
                LegalDocument.objects.filter(
                    code__in=["264-QD-TW", "QD-69-TW", "TT-02-CAND"]
                )
            )
            for doc in fallback_docs:
                summary = getattr(doc, "summary", "") or ""
                metadata = getattr(doc, "metadata", {}) or {}
                if not summary and isinstance(metadata, dict):
                    summary = metadata.get("summary", "")
                fallback_candidates.append(
                    {
                        "code": doc.code,
                        "title": getattr(doc, "title", "") or doc.code,
                        "summary": summary,
                        "doc_type": getattr(doc, "doc_type", "") or "",
                        "section_title": "",
                    }
                )
        except Exception as exc:
            logger.warning(
                "[CLARIFICATION] Fallback documents lookup failed, using static list: %s",
                exc,
            )

        # Nếu DB chưa có đủ thông tin, luôn cung cấp danh sách tĩnh tối thiểu,
        # để wizard option-first vẫn hoạt động.
        if not fallback_candidates:
            fallback_candidates = [
                {
                    "code": "264-QD-TW",
                    "title": "Quyết định 264-QĐ/TW về kỷ luật đảng viên",
                    "summary": "",
                    "doc_type": "",
                    "section_title": "",
                },
                {
                    "code": "QD-69-TW",
                    "title": "Quy định 69-QĐ/TW về kỷ luật tổ chức đảng, đảng viên",
                    "summary": "",
                    "doc_type": "",
                    "section_title": "",
                },
                {
                    "code": "TT-02-CAND",
                    "title": "Thông tư 02/2021/TT-BCA về điều lệnh CAND",
                    "summary": "",
                    "doc_type": "",
                    "section_title": "",
                },
            ]

        payload = self._build_clarification_payload(query, fallback_candidates)
        if payload:
            logger.info(
                "[CLARIFICATION] Requesting user choice among canonical documents: %s",
                [c["code"] for c in fallback_candidates],
            )
        return payload

    def _has_explicit_document_code_in_query(self, query: str) -> bool:
        """
        Check if the raw query string explicitly contains a known document code
        pattern (e.g. '264/QĐ-TW', 'QD-69-TW', 'TT-02-CAND').

        Khác với _detect_document_code (dò toàn bộ bảng LegalDocument theo token),
        hàm này chỉ dựa trên các regex cố định để tránh over-detect cho câu hỏi
        chung chung như 'xử lí kỷ luật đảng viên thế nào'.
        """
        normalized = self._remove_accents(query).upper()
        if not normalized:
            return False
        for pattern in DOCUMENT_CODE_PATTERNS:
            try:
                if re.search(pattern, normalized):
                    return True
            except re.error:
                # Nếu pattern không hợp lệ thì bỏ qua, không chặn flow
                continue
        return False

    def _collect_document_candidates(
        self,
        legal_results: List[Dict[str, Any]],
        limit: int = 4,
    ) -> List[Dict[str, Any]]:
        """Collect unique document candidates from legal results."""
        ordered_codes: List[str] = []
        seen: set[str] = set()
        for result in legal_results:
            data = result.get("data", {})
            code = (data.get("document_code") or "").strip()
            if not code:
                continue
            upper = code.upper()
            if upper in seen:
                continue
            ordered_codes.append(code)
            seen.add(upper)
            if len(ordered_codes) >= limit:
                break
        if len(ordered_codes) < 2:
            return []
        try:
            documents = {
                doc.code.upper(): doc
                for doc in LegalDocument.objects.filter(code__in=ordered_codes)
            }
        except Exception as exc:
            logger.warning("[CLARIFICATION] Unable to load documents for candidates: %s", exc)
            documents = {}
        candidates: List[Dict[str, Any]] = []
        for code in ordered_codes:
            upper = code.upper()
            doc_obj = documents.get(upper)
            section = next(
                (
                    res
                    for res in legal_results
                    if (res.get("data", {}).get("document_code") or "").strip().upper() == upper
                ),
                None,
            )
            data = section.get("data", {}) if section else {}
            summary = ""
            if doc_obj:
                summary = doc_obj.summary or ""
                if not summary and isinstance(doc_obj.metadata, dict):
                    summary = doc_obj.metadata.get("summary", "")
            if not summary:
                summary = data.get("excerpt") or data.get("content", "")[:200]
            candidates.append(
                {
                    "code": code,
                    "title": data.get("document_title") or (doc_obj.title if doc_obj else code),
                    "summary": summary,
                    "doc_type": doc_obj.doc_type if doc_obj else "",
                    "section_title": data.get("section_title") or "",
                }
            )
        return candidates

    def _build_clarification_payload(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not candidates:
            return None
        default_message = (
            "Tôi tìm thấy một số văn bản có thể phù hợp. "
            "Bạn vui lòng chọn văn bản muốn tra cứu để tôi trả lời chính xác hơn."
        )
        llm_payload = self._call_clarification_llm(query, candidates)
        message = default_message
        options: List[Dict[str, Any]] = []

        # Ưu tiên dùng gợi ý từ LLM, nhưng phải luôn đảm bảo có options fallback
        if llm_payload:
            message = llm_payload.get("message") or default_message
            raw_options = llm_payload.get("options")
            if isinstance(raw_options, list):
                options = [
                    {
                        "code": (opt.get("code") or candidate.get("code", "")).upper(),
                        "title": opt.get("title") or opt.get("document_title") or candidate.get("title", ""),
                        "reason": opt.get("reason")
                        or opt.get("summary")
                        or candidate.get("summary")
                        or candidate.get("section_title")
                        or "",
                    }
                    for opt, candidate in zip(
                        raw_options,
                        candidates[: len(raw_options)],
                    )
                    if (opt.get("code") or candidate.get("code"))
                    and (opt.get("title") or opt.get("document_title") or candidate.get("title"))
                ]

        # Nếu LLM không trả về options hợp lệ → fallback build từ candidates
        if not options:
            options = [
                {
                    "code": candidate["code"].upper(),
                    "title": candidate["title"],
                    "reason": candidate.get("summary") or candidate.get("section_title") or "",
                }
                for candidate in candidates[:3]
            ]
        if not any(opt.get("code") == "__other__" for opt in options):
            options.append(
                {
                    "code": "__other__",
                    "title": "Khác",
                    "reason": "Tôi muốn hỏi văn bản hoặc chủ đề khác",
                }
            )
        return {
            # Wizard-style payload: ưu tiên dạng options cho UI
            "type": "options",
            "wizard_stage": "choose_document",
            "message": message,
            "options": options,
            "clarification": {
                "message": message,
                "options": options,
            },
            "results": [],
            "count": 0,
        }

    def _call_clarification_llm(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not self.llm_generator:
            return None
        try:
            return self.llm_generator.suggest_clarification_topics(
                query,
                candidates,
                max_options=3,
            )
        except Exception as exc:
            logger.warning("[CLARIFICATION] LLM suggestion failed: %s", exc)
            return None
    
    def _parallel_search_prepare(
        self,
        document_code: str,
        keywords: List[str],
        session_id: Optional[str] = None,
    ) -> None:
        """
        Trigger parallel search in background when user selects a document option.
        Stores results in cache for Stage 2 (choose topic).
        
        Args:
            document_code: Selected document code
            keywords: Keywords extracted from query/options
            session_id: Session ID for caching results
        """
        if not session_id:
            return
        
        def _search_task():
            try:
                logger.info(
                    "[PARALLEL_SEARCH] Starting background search for doc=%s, keywords=%s",
                    document_code,
                    keywords[:5],
                )
                
                # Check Redis cache first
                cache_key = f"prefetch:{document_code.upper()}:{hashlib.sha256(' '.join(keywords).encode()).hexdigest()[:16]}"
                cached_result = None
                if self.redis_cache and self.redis_cache.is_available():
                    cached_result = self.redis_cache.get(cache_key)
                    if cached_result:
                        logger.info(
                            "[PARALLEL_SEARCH] ✅ Cache hit for doc=%s",
                            document_code
                        )
                        # Store in in-memory cache too
                        with self._cache_lock:
                            if session_id not in self._prefetched_cache:
                                self._prefetched_cache[session_id] = {}
                            self._prefetched_cache[session_id]["document_results"] = cached_result
                        return
                
                # Search in the selected document
                query_text = " ".join(keywords) if keywords else ""
                search_result = self._search_by_intent(
                    intent="search_legal",
                    query=query_text,
                    limit=20,  # Get more results for topic options
                    preferred_document_code=document_code.upper(),
                )
                
                # Prepare cache data
                cache_data = {
                    "document_code": document_code,
                    "results": search_result.get("results", []),
                    "count": search_result.get("count", 0),
                    "timestamp": time.time(),
                }
                
                # Store in Redis cache
                if self.redis_cache and self.redis_cache.is_available():
                    self.redis_cache.set(cache_key, cache_data, ttl_seconds=self.prefetch_cache_ttl)
                    logger.debug(
                        "[PARALLEL_SEARCH] Cached prefetch results (TTL: %ds)",
                        self.prefetch_cache_ttl
                    )
                
                # Store in in-memory cache (fallback)
                with self._cache_lock:
                    if session_id not in self._prefetched_cache:
                        self._prefetched_cache[session_id] = {}
                    self._prefetched_cache[session_id]["document_results"] = cache_data
                
                logger.info(
                    "[PARALLEL_SEARCH] Completed background search for doc=%s, found %d results",
                    document_code,
                    search_result.get("count", 0),
                )
            except Exception as exc:
                logger.warning("[PARALLEL_SEARCH] Background search failed: %s", exc)
        
        # Submit to thread pool
        self._executor.submit(_search_task)
    
    def _parallel_search_topic(
        self,
        document_code: str,
        topic_keywords: List[str],
        session_id: Optional[str] = None,
    ) -> None:
        """
        Trigger parallel search when user selects a topic option.
        Stores results for final answer generation.
        
        Args:
            document_code: Selected document code
            topic_keywords: Keywords from selected topic
            session_id: Session ID for caching results
        """
        if not session_id:
            return
        
        def _search_task():
            try:
                logger.info(
                    "[PARALLEL_SEARCH] Starting topic search for doc=%s, keywords=%s",
                    document_code,
                    topic_keywords[:5],
                )
                
                # Search with topic keywords
                query_text = " ".join(topic_keywords) if topic_keywords else ""
                search_result = self._search_by_intent(
                    intent="search_legal",
                    query=query_text,
                    limit=10,
                    preferred_document_code=document_code.upper(),
                )
                
                # Store in cache
                with self._cache_lock:
                    if session_id not in self._prefetched_cache:
                        self._prefetched_cache[session_id] = {}
                    self._prefetched_cache[session_id]["topic_results"] = {
                        "document_code": document_code,
                        "keywords": topic_keywords,
                        "results": search_result.get("results", []),
                        "count": search_result.get("count", 0),
                        "timestamp": time.time(),
                    }
                
                logger.info(
                    "[PARALLEL_SEARCH] Completed topic search, found %d results",
                    search_result.get("count", 0),
                )
            except Exception as exc:
                logger.warning("[PARALLEL_SEARCH] Topic search failed: %s", exc)
        
        # Submit to thread pool
        self._executor.submit(_search_task)
    
    def _get_prefetched_results(
        self,
        session_id: Optional[str],
        result_type: str = "document_results",
    ) -> Optional[Dict[str, Any]]:
        """
        Get prefetched search results from cache.
        
        Args:
            session_id: Session ID
            result_type: "document_results" or "topic_results"
        
        Returns:
            Cached results dict or None
        """
        if not session_id:
            return None
        
        with self._cache_lock:
            cache_entry = self._prefetched_cache.get(session_id)
            if not cache_entry:
                return None
            
            results = cache_entry.get(result_type)
            if not results:
                return None
            
            # Check if results are still fresh (within 5 minutes)
            timestamp = results.get("timestamp", 0)
            if time.time() - timestamp > 300:  # 5 minutes
                logger.debug("[PARALLEL_SEARCH] Prefetched results expired for session=%s", session_id)
                return None
            
            return results
    
    def _clear_prefetched_cache(self, session_id: Optional[str]) -> None:
        """Clear prefetched cache for a session."""
        if not session_id:
            return
        
        with self._cache_lock:
            if session_id in self._prefetched_cache:
                del self._prefetched_cache[session_id]
                logger.debug("[PARALLEL_SEARCH] Cleared cache for session=%s", session_id)
    
    def _search_by_intent(
        self,
        intent: str,
        query: str,
        limit: int = 5,
        preferred_document_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search based on classified intent. Reduced limit from 20 to 5 for faster inference on free tier."""
        # Use original query for better matching
        keywords = query.strip()
        extracted = " ".join(self.chatbot.extract_keywords(query))
        if extracted and len(extracted) > 2:
            keywords = f"{keywords} {extracted}"
        
        results = []
        
        if intent == "search_fine":
            qs = Fine.objects.all()
            text_fields = ["name", "code", "article", "decree", "remedial"]
            search_results = search_with_ml(qs, keywords, text_fields, top_k=limit, min_score=0.1)
            results = [{"type": "fine", "data": {
                "id": f.id,
                "name": f.name,
                "code": f.code,
                "min_fine": float(f.min_fine) if f.min_fine else None,
                "max_fine": float(f.max_fine) if f.max_fine else None,
                "article": f.article,
                "decree": f.decree,
            }} for f in search_results]
        
        elif intent == "search_procedure":
            qs = Procedure.objects.all()
            text_fields = ["title", "domain", "conditions", "dossier"]
            search_results = search_with_ml(qs, keywords, text_fields, top_k=limit, min_score=0.1)
            results = [{"type": "procedure", "data": {
                "id": p.id,
                "title": p.title,
                "domain": p.domain,
                "level": p.level,
            }} for p in search_results]
        
        elif intent == "search_office":
            qs = Office.objects.all()
            text_fields = ["unit_name", "address", "district", "service_scope"]
            search_results = search_with_ml(qs, keywords, text_fields, top_k=limit, min_score=0.1)
            results = [{"type": "office", "data": {
                "id": o.id,
                "unit_name": o.unit_name,
                "address": o.address,
                "district": o.district,
                "phone": o.phone,
                "working_hours": o.working_hours,
            }} for o in search_results]
        
        elif intent == "search_advisory":
            qs = Advisory.objects.all()
            text_fields = ["title", "summary"]
            search_results = search_with_ml(qs, keywords, text_fields, top_k=limit, min_score=0.1)
            results = [{"type": "advisory", "data": {
                "id": a.id,
                "title": a.title,
                "summary": a.summary,
            }} for a in search_results]
        
        elif intent == "search_legal":
            qs = LegalSection.objects.all()
            text_fields = ["section_title", "section_code", "content"]
            detected_code = self._detect_document_code(query)
            effective_code = preferred_document_code or detected_code
            filtered = False
            if effective_code:
                filtered_qs = qs.filter(document__code__iexact=effective_code)
                if filtered_qs.exists():
                    qs = filtered_qs
                    filtered = True
                    logger.info(
                        "[SEARCH] Prefiltering legal sections for document code %s (query='%s')",
                        effective_code,
                        query,
                    )
                else:
                    logger.info(
                        "[SEARCH] Document code %s detected but no sections found locally, falling back to full corpus",
                        effective_code,
                    )
            else:
                logger.debug("[SEARCH] No document code detected for query: %s", query)
            # Use pure semantic search (100% vector, no BM25)
            search_results = pure_semantic_search(
                [keywords],
                qs,
                top_k=limit,  # limit=15 for reranking, will be reduced to 4
                text_fields=text_fields
            )
            results = self._format_legal_results(search_results, detected_code, query=query)
            logger.info(
                "[SEARCH] Legal intent processed (query='%s', code=%s, filtered=%s, results=%d)",
                query,
                detected_code or "None",
                filtered,
                len(results),
            )
        
        return {
            "intent": intent,
            "query": query,
            "keywords": keywords,
            "results": results,
            "count": len(results),
            "detected_code": detected_code,
        }
    
    def _should_save_to_golden(self, query: str, response: Dict) -> bool:
        """
        Decide if response should be saved to golden dataset.
        
        Criteria:
        - High confidence (>0.95)
        - Has results
        - Response is complete and well-formed
        - Not already in golden dataset
        """
        try:
            from hue_portal.core.models import GoldenQuery
            
            # Check if already exists
            query_normalized = self._normalize_query(query)
            if GoldenQuery.objects.filter(query_normalized=query_normalized, is_active=True).exists():
                return False
            
            # Check criteria
            has_results = response.get("count", 0) > 0
            has_message = bool(response.get("message", "").strip())
            confidence = response.get("confidence", 0.0)
            
            # Only save if high quality
            if has_results and has_message and confidence >= 0.95:
                # Additional check: message should be substantial (not just template)
                message = response.get("message", "")
                if len(message) > 50:  # Substantial response
                    return True
            
            return False
        except Exception as e:
            logger.warning(f"Error checking if should save to golden: {e}")
            return False
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for matching."""
        normalized = query.lower().strip()
        # Remove accents
        normalized = unicodedata.normalize("NFD", normalized)
        normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
        # Remove extra spaces
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    def _detect_document_code(self, query: str) -> Optional[str]:
        """Detect known document code mentioned in the query."""
        normalized_query = self._remove_accents(query).upper()
        if not normalized_query:
            return None
        try:
            codes = LegalDocument.objects.values_list("code", flat=True)
        except Exception as exc:
            logger.debug("Unable to fetch document codes: %s", exc)
            return None
        
        for code in codes:
            if not code:
                continue
            tokens = self._split_code_tokens(code)
            if tokens and all(token in normalized_query for token in tokens):
                logger.info("[SEARCH] Detected document code %s in query", code)
                return code
        return None
    
    def _split_code_tokens(self, code: str) -> List[str]:
        """Split a document code into uppercase accentless tokens."""
        normalized = self._remove_accents(code).upper()
        return [tok for tok in re.split(r"[-/\s]+", normalized) if tok]
    
    def _remove_accents(self, text: str) -> str:
        if not text:
            return ""
        normalized = unicodedata.normalize("NFD", text)
        return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    
    def _format_legal_results(
        self,
        search_results: List[Any],
        detected_code: Optional[str],
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Build legal result payload and apply ordering/boosting based on doc code and keywords."""
        entries: List[Dict[str, Any]] = []
        upper_detected = detected_code.upper() if detected_code else None
        
        # Keywords that indicate important legal concepts (boost score if found)
        important_keywords = []
        if query:
            query_lower = query.lower()
            # Keywords for percentage/threshold queries
            if any(kw in query_lower for kw in ["%", "phần trăm", "tỷ lệ", "12%", "20%", "10%"]):
                important_keywords.extend(["%", "phần trăm", "tỷ lệ", "12", "20", "10"])
            # Keywords for ranking/demotion queries
            if any(kw in query_lower for kw in ["hạ bậc", "thi đua", "xếp loại", "đánh giá"]):
                important_keywords.extend(["hạ bậc", "thi đua", "xếp loại", "đánh giá"])
        
        for ls in search_results:
            doc = ls.document
            doc_code = doc.code if doc else None
            score = getattr(ls, "_ml_score", getattr(ls, "rank", 0.0)) or 0.0
            
            # Boost score if content contains important keywords
            content_text = (ls.content or ls.section_title or "").lower()
            keyword_boost = 0.0
            if important_keywords and content_text:
                for kw in important_keywords:
                    if kw.lower() in content_text:
                        keyword_boost += 0.15  # Boost 0.15 per keyword match
                        logger.debug(
                            "[BOOST] Keyword '%s' found in section %s, boosting score",
                            kw,
                            ls.section_code,
                        )
            
            entries.append(
                {
                    "type": "legal",
                    "score": float(score) + keyword_boost,
                    "data": {
                        "id": ls.id,
                        "section_code": ls.section_code,
                        "section_title": ls.section_title,
                        "content": ls.content[:500] if ls.content else "",
                        "excerpt": ls.excerpt,
                        "document_code": doc_code,
                        "document_title": doc.title if doc else None,
                        "page_start": ls.page_start,
                        "page_end": ls.page_end,
                    },
                }
            )
        
        if upper_detected:
            exact_matches = [
                r for r in entries if (r["data"].get("document_code") or "").upper() == upper_detected
            ]
            if exact_matches:
                others = [r for r in entries if r not in exact_matches]
                entries = exact_matches + others
            else:
                for entry in entries:
                    doc_code = (entry["data"].get("document_code") or "").upper()
                    if doc_code == upper_detected:
                        entry["score"] = (entry.get("score") or 0.1) * 10
                entries.sort(key=lambda r: r.get("score") or 0, reverse=True)
        else:
            # Sort by boosted score
            entries.sort(key=lambda r: r.get("score") or 0, reverse=True)
        return entries
    
    def _is_complex_query(self, query: str) -> bool:
        """
        Detect if query is complex and requires LLM reasoning (not suitable for Fast Path).
        
        Complex queries contain keywords like: %, bậc, thi đua, tỷ lệ, liên đới, tăng nặng, giảm nhẹ, đơn vị vi phạm
        """
        if not query:
            return False
        query_lower = query.lower()
        complex_keywords = [
            "%", "phần trăm",
            "bậc", "hạ bậc", "nâng bậc",
            "thi đua", "xếp loại", "đánh giá",
            "tỷ lệ", "tỉ lệ",
            "liên đới", "liên quan",
            "tăng nặng", "tăng nặng hình phạt",
            "giảm nhẹ", "giảm nhẹ hình phạt",
            "đơn vị vi phạm", "đơn vị có",
        ]
        for keyword in complex_keywords:
            if keyword in query_lower:
                logger.info(
                    "[FAST_PATH] Complex query detected (keyword: '%s'), forcing Slow Path",
                    keyword,
                )
                return True
        return False
    
    def _maybe_fast_path_response(
        self, results: List[Dict[str, Any]], query: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Return fast-path response if results are confident enough."""
        if not results:
            return None
        
        # Double-check: if query is complex, never use Fast Path
        if query and self._is_complex_query(query):
            return None
        top_result = results[0]
        top_score = top_result.get("score", 0.0) or 0.0
        doc_code = (top_result.get("data", {}).get("document_code") or "").upper()
        
        if top_score >= 0.88 and doc_code:
            logger.info(
                "[FAST_PATH] Top score hit (%.3f) for document %s", top_score, doc_code
            )
            message = self._format_fast_legal_message(top_result)
            return {
                "message": message,
                "results": results[:3],
                "count": min(3, len(results)),
                "confidence": min(0.99, top_score + 0.05),
            }
        
        top_three = results[:3]
        if len(top_three) >= 2:
            doc_codes = [
                (res.get("data", {}).get("document_code") or "").upper()
                for res in top_three
                if res.get("data", {}).get("document_code")
            ]
            if doc_codes and len(set(doc_codes)) == 1:
                logger.info(
                    "[FAST_PATH] Top-%d results share same document %s",
                    len(top_three),
                    doc_codes[0],
                )
                message = self._format_fast_legal_message(top_three[0])
                return {
                    "message": message,
                    "results": top_three,
                    "count": len(top_three),
                    "confidence": min(0.97, (top_three[0].get("score") or 0.9) + 0.04),
                }
        return None
    
    def _format_fast_legal_message(self, result: Dict[str, Any]) -> str:
        """Format a concise legal answer without LLM."""
        data = result.get("data", {})
        doc_title = data.get("document_title") or "văn bản pháp luật"
        doc_code = data.get("document_code") or ""
        section_code = data.get("section_code") or "Điều liên quan"
        section_title = data.get("section_title") or ""
        content = (data.get("content") or data.get("excerpt") or "").strip()
        if len(content) > 400:
            trimmed = content[:400].rsplit(" ", 1)[0]
            content = f"{trimmed}..."
        intro = "Kết quả chính xác nhất:"
        lines = [intro]
        if doc_title or doc_code:
            lines.append(f"- Văn bản: {doc_title or 'văn bản pháp luật'}" + (f" ({doc_code})" if doc_code else ""))
        section_label = section_code
        if section_title:
            section_label = f"{section_code} – {section_title}"
        lines.append(f"- Điều khoản: {section_label}")
        lines.append("")
        lines.append(content)
        citation_doc = doc_title or doc_code or "nguồn chính thức"
        lines.append(f"\nNguồn: {section_label}, {citation_doc}.")
        return "\n".join(lines)

