"""
Slow Path Handler - Full RAG pipeline for complex queries.
"""
import time
import logging
from typing import Dict, Any, Optional, List
import unicodedata
import re

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
# Lazy import reranker to avoid blocking startup (FlagEmbedding may download model)
# from hue_portal.core.reranker import rerank_documents
from hue_portal.chatbot.llm_integration import get_llm_generator
from hue_portal.chatbot.structured_legal import format_structured_legal_answer
from hue_portal.chatbot.context_manager import ConversationContext

logger = logging.getLogger(__name__)


class SlowPathHandler:
    """Handle Slow Path queries with full RAG pipeline."""
    
    def __init__(self):
        self.chatbot = get_chatbot()
        self.llm_generator = get_llm_generator()
    
    def handle(self, query: str, intent: str, session_id: Optional[str] = None) -> Dict[str, Any]:
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
        
        Returns:
            Response dict with message, intent, results, etc.
        """
        query = query.strip()
        
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
        
        # Search based on intent - retrieve top-8 for reranking
        search_result = self._search_by_intent(intent, query, limit=8)  # Increased to 8 for reranker
        
        # Fast path for high-confidence legal queries (skip for complex queries)
        fast_path_response = None
        if intent == "search_legal" and not self._is_complex_query(query):
            fast_path_response = self._maybe_fast_path_response(search_result["results"], query)
            if fast_path_response:
                fast_path_response["intent"] = intent
                fast_path_response["_source"] = "fast_path"
                return fast_path_response
        
        # Rerank results from top-8 to top-3 for legal queries (reduces prompt size by ~40%)
        # Always rerank if we have legal results (even if <= 3, reranker improves relevance)
        if intent == "search_legal":
            try:
                # Lazy import to avoid blocking startup (FlagEmbedding may download model)
                from hue_portal.core.reranker import rerank_documents
                
                legal_results = [r for r in search_result["results"] if r.get("type") == "legal"]
                if len(legal_results) > 0:
                    # Rerank to top-3 (or all if we have fewer)
                    top_k = min(3, len(legal_results))
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
        
        # Get conversation context if available
        context = None
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
            except Exception:
                pass
        
        # Generate response message using LLM if available and we have documents
        message = None
        if self.llm_generator and search_result["count"] > 0:
            # For legal queries, use structured output (now with top-3 reranked results)
            if intent == "search_legal" and search_result["results"]:
                legal_docs = [r["data"] for r in search_result["results"] if r.get("type") == "legal"][:3]  # Top-3 after reranking
                if legal_docs:
                    structured_answer = self.llm_generator.generate_structured_legal_answer(
                        query,
                        legal_docs,
                        prefill_summary=None
                    )
                    if structured_answer:
                        message = format_structured_legal_answer(structured_answer)
            
            # For other intents or if structured failed, use regular LLM generation
            if not message:
                documents = [r["data"] for r in search_result["results"][:3]]  # Top-3 after reranking
                message = self.llm_generator.generate_answer(
                    query,
                    context=context,
                    documents=documents
                )
        
        # Fallback to template if LLM not available or failed
        if not message:
            if search_result["count"] > 0:
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
    
    def _search_by_intent(self, intent: str, query: str, limit: int = 5) -> Dict[str, Any]:
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
            filtered = False
            if detected_code:
                filtered_qs = qs.filter(document__code__iexact=detected_code)
                if filtered_qs.exists():
                    qs = filtered_qs
                    filtered = True
                    logger.info(
                        "[SEARCH] Prefiltering legal sections for document code %s (query='%s')",
                        detected_code,
                        query,
                    )
                else:
                    logger.info(
                        "[SEARCH] Document code %s detected but no sections found locally, falling back to full corpus",
                        detected_code,
                    )
            else:
                logger.debug("[SEARCH] No document code detected for query: %s", query)
            # Retrieve top-8 for reranking (will be reduced to top-3 after rerank)
            search_results = search_with_ml(
                qs,
                keywords,
                text_fields,
                top_k=limit,  # limit=8 for reranking, will be reduced to 3
                min_score=0.02,  # Lower threshold for legal
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
            "count": len(results)
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

