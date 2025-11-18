"""
RAG (Retrieval-Augmented Generation) pipeline for answer generation.
"""
from typing import List, Dict, Any, Optional
from .hybrid_search import hybrid_search
from .models import Procedure, Fine, Office, Advisory
from hue_portal.chatbot.chatbot import format_fine_amount


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
    if not documents:
        return f"Xin lỗi, tôi không tìm thấy thông tin liên quan đến '{query}'. Vui lòng thử lại với từ khóa khác."
    
    # Try LLM generation first if enabled
    if use_llm:
        try:
            from hue_portal.chatbot.llm_integration import get_llm_generator
            llm = get_llm_generator()
            if llm:
                llm_answer = llm.generate_answer(query, context=context, documents=documents)
                if llm_answer:
                    return llm_answer
        except Exception as e:
            print(f"LLM generation failed, using template: {e}")
    
    # Fallback to template-based generation
    if content_type == 'procedure':
        return _generate_procedure_answer(query, documents)
    elif content_type == 'fine':
        return _generate_fine_answer(query, documents)
    elif content_type == 'office':
        return _generate_office_answer(query, documents)
    elif content_type == 'advisory':
        return _generate_advisory_answer(query, documents)
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


def _generate_general_answer(query: str, documents: List[Any]) -> str:
    """Generate general answer."""
    count = len(documents)
    return f"Tôi tìm thấy {count} kết quả liên quan đến '{query}'. Vui lòng xem chi tiết bên dưới."


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
    }
    
    content_type = intent_to_type.get(intent, 'procedure')
    
    # Retrieve documents
    documents = retrieve_top_k_documents(query, content_type, top_k=top_k)
    
    if not documents:
        return {
            'answer': f"Xin lỗi, tôi không tìm thấy thông tin liên quan đến '{query}'.",
            'documents': [],
            'count': 0,
            'confidence': 0.0,
            'content_type': content_type
        }
    
    # Generate answer (with LLM if available)
    answer = generate_answer_template(query, documents, content_type, context=context, use_llm=use_llm)
    
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

