"""
RAG (Retrieval-Augmented Generation) pipeline for answer generation.
"""
import re
import unicodedata
from typing import List, Dict, Any, Optional
from .hybrid_search import hybrid_search
from .models import Procedure, Fine, Office, Advisory, LegalSection
from hue_portal.chatbot.chatbot import format_fine_amount
from hue_portal.chatbot.llm_integration import get_llm_generator
from hue_portal.chatbot.structured_legal import format_structured_legal_answer


def retrieve_top_k_documents(
    query: str,
    content_type: str,
    top_k: int = 5
) -> List[Any]:
    """
    Retrieve top-k documents using hybrid search.
    
    Args:
        query: Search query.
        content_type: Type of content ('procedure', 'fine', 'office', 'advisory').
        top_k: Number of documents to retrieve.
    
    Returns:
        List of document objects.
    """
    # Get appropriate queryset
    if content_type == 'procedure':
        queryset = Procedure.objects.all()
        text_fields = ['title', 'domain', 'conditions', 'dossier']
    elif content_type == 'fine':
        queryset = Fine.objects.all()
        text_fields = ['name', 'code', 'article', 'decree', 'remedial']
    elif content_type == 'office':
        queryset = Office.objects.all()
        text_fields = ['unit_name', 'address', 'district', 'service_scope']
    elif content_type == 'advisory':
        queryset = Advisory.objects.all()
        text_fields = ['title', 'summary']
    elif content_type == 'legal':
        queryset = LegalSection.objects.select_related("document").all()
        text_fields = ['section_title', 'section_code', 'content']
    else:
        return []
    
    # Use hybrid search with text_fields for exact match boost
    try:
        from .config.hybrid_search_config import get_config
        config = get_config(content_type)
        results = hybrid_search(
            queryset, 
            query, 
            top_k=top_k,
            bm25_weight=config.bm25_weight,
            vector_weight=config.vector_weight,
            min_hybrid_score=config.min_hybrid_score,
            text_fields=text_fields
        )
        return results
    except Exception as e:
        print(f"Error in retrieval: {e}")
        return []


def generate_answer_template(
    query: str,
    documents: List[Any],
    content_type: str,
    context: Optional[List[Dict[str, Any]]] = None,
    use_llm: bool = True
) -> str:
    """
    Generate answer using LLM (if available) or template-based summarization.
    
    Args:
        query: Original query.
        documents: Retrieved documents.
        content_type: Type of content.
        context: Optional conversation context.
        use_llm: Whether to try LLM generation first.
    
    Returns:
        Generated answer text.
    """
    def _invoke_llm(documents_for_prompt: List[Any]) -> Optional[str]:
        """Call configured LLM provider safely."""
        try:
            import traceback
            from hue_portal.chatbot.llm_integration import get_llm_generator

            llm = get_llm_generator()
            if not llm:
                print("[RAG] ⚠️ LLM not available, using template", flush=True)
                return None

            print(f"[RAG] Using LLM provider: {llm.provider}", flush=True)
            llm_answer = llm.generate_answer(
                query,
                context=context,
                documents=documents_for_prompt
            )
            if llm_answer:
                print(f"[RAG] ✅ LLM answer generated (length: {len(llm_answer)})", flush=True)
                return llm_answer

            print("[RAG] ⚠️ LLM returned None, using template", flush=True)
        except Exception as exc:
            import traceback

            error_trace = traceback.format_exc()
            print(f"[RAG] ❌ LLM generation failed, using template: {exc}", flush=True)
            print(f"[RAG] ❌ Trace: {error_trace}", flush=True)
        return None

    llm_enabled = use_llm or content_type == 'general'
    if llm_enabled:
        llm_documents = documents if documents else []
        llm_answer = _invoke_llm(llm_documents)
        if llm_answer:
            return llm_answer
    
    # If no documents, fall back gracefully
    if not documents:
        if content_type == 'general':
            return (
                f"Tôi chưa có dữ liệu pháp luật liên quan đến '{query}', "
                "nhưng vẫn sẵn sàng trò chuyện hoặc hỗ trợ bạn ở chủ đề khác. "
                "Bạn có thể mô tả cụ thể hơn để tôi giúp tốt hơn nhé!"
            )
        return (
            f"Xin lỗi, tôi không tìm thấy thông tin liên quan đến '{query}' trong cơ sở dữ liệu. "
            "Vui lòng thử lại với từ khóa khác hoặc liên hệ trực tiếp với Công an Thừa Thiên Huế để được tư vấn."
        )
    
    # Fallback to template-based generation
    if content_type == 'procedure':
        return _generate_procedure_answer(query, documents)
    elif content_type == 'fine':
        return _generate_fine_answer(query, documents)
    elif content_type == 'office':
        return _generate_office_answer(query, documents)
    elif content_type == 'advisory':
        return _generate_advisory_answer(query, documents)
    elif content_type == 'legal':
        return _generate_legal_answer(query, documents)
    else:
        return _generate_general_answer(query, documents)


def _generate_procedure_answer(query: str, documents: List[Procedure]) -> str:
    """Generate answer for procedure queries."""
    count = len(documents)
    answer = f"Tôi tìm thấy {count} thủ tục liên quan đến '{query}':\n\n"
    
    for i, doc in enumerate(documents[:5], 1):
        answer += f"{i}. {doc.title}\n"
        if doc.domain:
            answer += f"   Lĩnh vực: {doc.domain}\n"
        if doc.level:
            answer += f"   Cấp: {doc.level}\n"
        if doc.conditions:
            conditions_short = doc.conditions[:100] + "..." if len(doc.conditions) > 100 else doc.conditions
            answer += f"   Điều kiện: {conditions_short}\n"
        answer += "\n"
    
    if count > 5:
        answer += f"... và {count - 5} thủ tục khác.\n"
    
    return answer


def _generate_fine_answer(query: str, documents: List[Fine]) -> str:
    """Generate answer for fine queries."""
    count = len(documents)
    answer = f"Tôi tìm thấy {count} mức phạt liên quan đến '{query}':\n\n"
    
    # Highlight best match (first result) if available
    if documents:
        best_match = documents[0]
        answer += "Kết quả chính xác nhất:\n"
        answer += f"• {best_match.name}\n"
        if best_match.code:
            answer += f"  Mã vi phạm: {best_match.code}\n"
        
        # Format fine amount using helper function
        fine_amount = format_fine_amount(
            float(best_match.min_fine) if best_match.min_fine else None,
            float(best_match.max_fine) if best_match.max_fine else None
        )
        if fine_amount:
            answer += f"  Mức phạt: {fine_amount}\n"
        
        if best_match.article:
            answer += f"  Điều luật: {best_match.article}\n"
        answer += "\n"
        
        # Add other results if available
        if count > 1:
            answer += "Các mức phạt khác:\n"
            for i, doc in enumerate(documents[1:5], 2):
                answer += f"{i}. {doc.name}\n"
                if doc.code:
                    answer += f"   Mã vi phạm: {doc.code}\n"
                
                # Format fine amount
                fine_amount = format_fine_amount(
                    float(doc.min_fine) if doc.min_fine else None,
                    float(doc.max_fine) if doc.max_fine else None
                )
                if fine_amount:
                    answer += f"   Mức phạt: {fine_amount}\n"
                
                if doc.article:
                    answer += f"   Điều luật: {doc.article}\n"
                answer += "\n"
    else:
        # Fallback if no documents
        for i, doc in enumerate(documents[:5], 1):
            answer += f"{i}. {doc.name}\n"
            if doc.code:
                answer += f"   Mã vi phạm: {doc.code}\n"
            
            # Format fine amount
            fine_amount = format_fine_amount(
                float(doc.min_fine) if doc.min_fine else None,
                float(doc.max_fine) if doc.max_fine else None
            )
            if fine_amount:
                answer += f"   Mức phạt: {fine_amount}\n"
            
            if doc.article:
                answer += f"   Điều luật: {doc.article}\n"
            answer += "\n"
    
    if count > 5:
        answer += f"... và {count - 5} mức phạt khác.\n"
    
    return answer


def _generate_office_answer(query: str, documents: List[Office]) -> str:
    """Generate answer for office queries."""
    count = len(documents)
    answer = f"Tôi tìm thấy {count} đơn vị liên quan đến '{query}':\n\n"
    
    for i, doc in enumerate(documents[:5], 1):
        answer += f"{i}. {doc.unit_name}\n"
        if doc.address:
            answer += f"   Địa chỉ: {doc.address}\n"
        if doc.district:
            answer += f"   Quận/Huyện: {doc.district}\n"
        if doc.phone:
            answer += f"   Điện thoại: {doc.phone}\n"
        if doc.working_hours:
            answer += f"   Giờ làm việc: {doc.working_hours}\n"
        answer += "\n"
    
    if count > 5:
        answer += f"... và {count - 5} đơn vị khác.\n"
    
    return answer


def _generate_advisory_answer(query: str, documents: List[Advisory]) -> str:
    """Generate answer for advisory queries."""
    count = len(documents)
    answer = f"Tôi tìm thấy {count} cảnh báo liên quan đến '{query}':\n\n"
    
    for i, doc in enumerate(documents[:5], 1):
        answer += f"{i}. {doc.title}\n"
        if doc.summary:
            summary_short = doc.summary[:150] + "..." if len(doc.summary) > 150 else doc.summary
            answer += f"   {summary_short}\n"
        answer += "\n"
    
    if count > 5:
        answer += f"... và {count - 5} cảnh báo khác.\n"
    
    return answer


def _clean_text(value: str) -> str:
    """Normalize whitespace and strip noise for legal snippets."""
    if not value:
        return ""
    compressed = re.sub(r"\s+", " ", value)
    return compressed.strip()


def _summarize_section(
    section: LegalSection,
    max_sentences: int = 3,
    max_chars: int = 600
) -> str:
    """
    Produce a concise Vietnamese summary directly from the stored content.
    
    This is used as the Vietnamese prefill before calling the LLM so we avoid
    English drift and keep the answer grounded.
    """
    content = _clean_text(section.content)
    if not content:
        return ""

    # Split by sentence boundaries; fall back to chunks if delimiters missing.
    sentences = re.split(r"(?<=[.!?])\s+", content)
    if not sentences:
        sentences = [content]

    summary_parts = []
    for sentence in sentences:
        if not sentence:
            continue
        summary_parts.append(sentence)
        joined = " ".join(summary_parts)
        if len(summary_parts) >= max_sentences or len(joined) >= max_chars:
            break

    summary = " ".join(summary_parts)
    if len(summary) > max_chars:
        summary = summary[:max_chars].rsplit(" ", 1)[0] + "..."
    return summary.strip()


def _format_citation(section: LegalSection) -> str:
    citation = section.document.title
    if section.section_code:
        citation = f"{citation} – {section.section_code}"
    page = ""
    if section.page_start:
        page = f" (trang {section.page_start}"
        if section.page_end and section.page_end != section.page_start:
            page += f"-{section.page_end}"
        page += ")"
    return f"{citation}{page}".strip()


def _build_legal_prefill(documents: List[LegalSection]) -> str:
    """
    Build a compact Vietnamese summary block that will be injected into the
    Guardrails prompt. The goal is to bias the model toward Vietnamese output.
    """
    if not documents:
        return ""

    lines = ["Bản tóm tắt tiếng Việt từ cơ sở dữ liệu:"]
    for idx, section in enumerate(documents[:3], start=1):
        summary = _summarize_section(section, max_sentences=2, max_chars=400)
        citation = _format_citation(section)
        if not summary:
            continue
        lines.append(f"{idx}. {summary} (Nguồn: {citation})")

    return "\n".join(lines)


def _generate_legal_citation_block(documents: List[LegalSection]) -> str:
    """Return formatted citation block reused by multiple answer modes."""
    if not documents:
        return ""

    lines: List[str] = []
    for idx, section in enumerate(documents[:5], start=1):
        summary = _summarize_section(section)
        snippet = _clean_text(section.content)[:350]
        if snippet and len(snippet) == 350:
            snippet = snippet.rsplit(" ", 1)[0] + "..."
        citation = _format_citation(section)

        lines.append(f"{idx}. {section.section_title or 'Nội dung'} – {citation}")
        if summary:
            lines.append(f"   - Tóm tắt: {summary}")
        if snippet:
            lines.append(f"   - Trích dẫn: \"{snippet}\"")
        lines.append("")

    if len(documents) > 5:
        lines.append(f"... và {len(documents) - 5} trích đoạn khác trong cùng nguồn dữ liệu.")

    return "\n".join(lines).strip()


def _generate_legal_answer(query: str, documents: List[LegalSection]) -> str:
    count = len(documents)
    if count == 0:
        return (
            f"Tôi chưa tìm thấy trích dẫn pháp lý nào cho '{query}'. "
            "Bạn có thể cung cấp thêm ngữ cảnh để tôi tiếp tục hỗ trợ."
        )

    header = (
        f"Tôi đã tổng hợp {count} trích đoạn pháp lý liên quan đến '{query}'. "
        "Đây là bản tóm tắt tiếng Việt kèm trích dẫn:"
    )
    citation_block = _generate_legal_citation_block(documents)
    return f"{header}\n\n{citation_block}".strip()


def _generate_general_answer(query: str, documents: List[Any]) -> str:
    """Generate general answer."""
    count = len(documents)
    return f"Tôi tìm thấy {count} kết quả liên quan đến '{query}'. Vui lòng xem chi tiết bên dưới."


def _strip_accents(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFD", value)
        if unicodedata.category(char) != "Mn"
    )


def _contains_markers(
    text_with_accents: str,
    text_without_accents: str,
    markers: List[str]
) -> bool:
    for marker in markers:
        marker_lower = marker.lower()
        marker_no_accents = _strip_accents(marker_lower)
        if marker_lower in text_with_accents or marker_no_accents in text_without_accents:
            return True
    return False


def _is_valid_legal_answer(answer: str, documents: List[LegalSection]) -> bool:
    """
    Validate that the LLM answer for legal intent references actual legal content.
    
    Criteria:
        - Must not contain denial phrases (already handled earlier) or "xin lỗi".
        - Must not introduce obvious monetary values (legal documents không có số tiền phạt).
        - Must have tối thiểu 40 ký tự để tránh câu trả lời quá ngắn.
    """
    if not answer:
        return False
    
    normalized_answer = answer.lower()
    normalized_answer_no_accents = _strip_accents(normalized_answer)
    
    denial_markers = [
        "xin lỗi",
        "thông tin trong cơ sở dữ liệu chưa đủ",
        "không thể giúp",
        "không tìm thấy thông tin",
        "không có dữ liệu",
    ]
    if _contains_markers(normalized_answer, normalized_answer_no_accents, denial_markers):
        return False
    
    money_markers = ["vnđ", "vnd", "đồng", "đ", "dong"]
    if _contains_markers(normalized_answer, normalized_answer_no_accents, money_markers):
        return False
    
    if len(answer.strip()) < 40:
        return False
    
    return True


def rag_pipeline(
    query: str,
    intent: str,
    top_k: int = 5,
    min_confidence: float = 0.3,
    context: Optional[List[Dict[str, Any]]] = None,
    use_llm: bool = True
) -> Dict[str, Any]:
    """
    Complete RAG pipeline: retrieval + answer generation.
    
    Args:
        query: User query.
        intent: Detected intent.
        top_k: Number of documents to retrieve.
        min_confidence: Minimum confidence threshold.
        context: Optional conversation context.
        use_llm: Whether to use LLM for answer generation.
    
    Returns:
        Dictionary with 'answer', 'documents', 'count', 'confidence', 'content_type'.
    """
    # Map intent to content type
    intent_to_type = {
        'search_procedure': 'procedure',
        'search_fine': 'fine',
        'search_office': 'office',
        'search_advisory': 'advisory',
        'search_legal': 'legal',
        'general_query': 'general',
        'greeting': 'general',
    }
    
    content_type = intent_to_type.get(intent, 'procedure')
    
    # Retrieve documents
    documents = retrieve_top_k_documents(query, content_type, top_k=top_k)
    
    # Enable LLM automatically for casual conversation intents
    llm_allowed = use_llm or intent in {"general_query", "greeting"}

    structured_used = False
    answer: Optional[str] = None

    if intent == "search_legal" and documents:
        llm = get_llm_generator()
        if llm:
            prefill_summary = _build_legal_prefill(documents)
            structured = llm.generate_structured_legal_answer(
                query,
                documents,
                prefill_summary=prefill_summary,
            )
            if structured:
                answer = format_structured_legal_answer(structured)
                structured_used = True
                citation_block = _generate_legal_citation_block(documents)
                if citation_block:
                    answer = (
                        f"{answer.rstrip()}\n\nTrích dẫn chi tiết:\n{citation_block}"
                    )

    if answer is None:
        answer = generate_answer_template(
            query,
            documents,
            content_type,
            context=context,
            use_llm=llm_allowed
        )

    # Fallback nếu intent pháp luật nhưng câu LLM không đạt tiêu chí
    if (
        intent == "search_legal"
        and documents
        and isinstance(answer, str)
        and not structured_used
    ):
        if not _is_valid_legal_answer(answer, documents):
            print("[RAG] ⚠️ Fallback: invalid legal answer detected", flush=True)
            answer = _generate_legal_answer(query, documents)
        else:
            citation_block = _generate_legal_answer(query, documents)
            if citation_block.strip():
                answer = f"{answer.rstrip()}\n\nTrích dẫn chi tiết:\n{citation_block}"
    
    # Calculate confidence (simple: based on number of results and scores)
    confidence = min(1.0, len(documents) / top_k)
    if documents and hasattr(documents[0], '_hybrid_score'):
        confidence = max(confidence, documents[0]._hybrid_score)
    
    return {
        'answer': answer,
        'documents': documents,
        'count': len(documents),
        'confidence': confidence,
        'content_type': content_type
    }

