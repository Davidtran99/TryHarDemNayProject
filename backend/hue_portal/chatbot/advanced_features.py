"""
Advanced features for chatbot: follow-up suggestions, ambiguity detection, explanations.
"""
from typing import List, Dict, Any, Optional
from hue_portal.core.models import Fine, Procedure, Office, Advisory


def suggest_follow_up_questions(query: str, results: List[Any], intent: str) -> List[str]:
    """
    Suggest follow-up questions based on query and results.
    
    Args:
        query: Original query.
        results: Retrieved results.
        intent: Detected intent.
    
    Returns:
        List of suggested follow-up questions.
    """
    suggestions = []
    
    if intent == "search_fine":
        if results:
            # Suggest questions about related fines
            suggestions.append("Còn mức phạt nào khác không?")
            suggestions.append("Điều luật liên quan là gì?")
            suggestions.append("Biện pháp khắc phục như thế nào?")
        else:
            suggestions.append("Bạn có thể cho biết cụ thể loại vi phạm không?")
    
    elif intent == "search_procedure":
        if results:
            suggestions.append("Hồ sơ cần chuẩn bị gì?")
            suggestions.append("Lệ phí là bao nhiêu?")
            suggestions.append("Thời hạn xử lý là bao lâu?")
            suggestions.append("Nộp hồ sơ ở đâu?")
        else:
            suggestions.append("Bạn muốn tìm thủ tục nào cụ thể?")
    
    elif intent == "search_office":
        if results:
            suggestions.append("Số điện thoại liên hệ?")
            suggestions.append("Giờ làm việc như thế nào?")
            suggestions.append("Địa chỉ cụ thể ở đâu?")
        else:
            suggestions.append("Bạn muốn tìm đơn vị nào?")
    
    elif intent == "search_advisory":
        if results:
            suggestions.append("Còn cảnh báo nào khác không?")
            suggestions.append("Cách phòng tránh như thế nào?")
        else:
            suggestions.append("Bạn muốn tìm cảnh báo về chủ đề gì?")
    
    return suggestions[:3]  # Return top 3 suggestions


def detect_ambiguity(query: str, results_count: int, confidence: float) -> Tuple[bool, Optional[str]]:
    """
    Detect if query is ambiguous.
    
    Args:
        query: User query.
        results_count: Number of results found.
        confidence: Confidence score.
    
    Returns:
        Tuple of (is_ambiguous, ambiguity_reason).
    """
    query_lower = query.lower()
    query_words = query.split()
    
    # Very short queries are often ambiguous
    if len(query_words) <= 2:
        return (True, "Câu hỏi quá ngắn, cần thêm thông tin")
    
    # Low confidence and many results suggests ambiguity
    if results_count > 10 and confidence < 0.5:
        return (True, "Kết quả quá nhiều, cần cụ thể hơn")
    
    # Very generic queries
    generic_queries = ["thông tin", "tìm kiếm", "hỏi", "giúp"]
    if any(gq in query_lower for gq in generic_queries) and len(query_words) <= 3:
        return (True, "Câu hỏi chung chung, cần cụ thể hơn")
    
    return (False, None)


def generate_explanation(result: Any, query: str, score: Optional[float] = None) -> str:
    """
    Generate explanation for why a result is relevant.
    
    Args:
        result: Result object.
        result_type: Type of result.
        query: Original query.
        score: Relevance score.
    
    Returns:
        Explanation string.
    """
    result_type = type(result).__name__.lower()
    explanation_parts = []
    
    if "fine" in result_type:
        name = getattr(result, "name", "")
        code = getattr(result, "code", "")
        explanation_parts.append(f"Kết quả này phù hợp vì:")
        if code:
            explanation_parts.append(f"- Mã vi phạm: {code}")
        if name:
            explanation_parts.append(f"- Tên vi phạm: {name}")
        if score:
            explanation_parts.append(f"- Độ phù hợp: {score:.0%}")
    
    elif "procedure" in result_type:
        title = getattr(result, "title", "")
        explanation_parts.append(f"Kết quả này phù hợp vì:")
        if title:
            explanation_parts.append(f"- Tên thủ tục: {title}")
        if score:
            explanation_parts.append(f"- Độ phù hợp: {score:.0%}")
    
    elif "office" in result_type:
        unit_name = getattr(result, "unit_name", "")
        explanation_parts.append(f"Kết quả này phù hợp vì:")
        if unit_name:
            explanation_parts.append(f"- Tên đơn vị: {unit_name}")
        if score:
            explanation_parts.append(f"- Độ phù hợp: {score:.0%}")
    
    elif "advisory" in result_type:
        title = getattr(result, "title", "")
        explanation_parts.append(f"Kết quả này phù hợp vì:")
        if title:
            explanation_parts.append(f"- Tiêu đề: {title}")
        if score:
            explanation_parts.append(f"- Độ phù hợp: {score:.0%}")
    
    return "\n".join(explanation_parts) if explanation_parts else "Kết quả này phù hợp với câu hỏi của bạn."


def compare_results(results: List[Any], result_type: str) -> str:
    """
    Compare multiple results and highlight differences.
    
    Args:
        results: List of result objects.
        result_type: Type of results.
    
    Returns:
        Comparison summary string.
    """
    if len(results) < 2:
        return ""
    
    comparison_parts = ["So sánh các kết quả:"]
    
    if result_type == "fine":
        # Compare fine amounts
        fine_amounts = []
        for result in results[:3]:
            if hasattr(result, "min_fine") and hasattr(result, "max_fine"):
                if result.min_fine and result.max_fine:
                    fine_amounts.append(f"{result.name}: {result.min_fine:,.0f} - {result.max_fine:,.0f} VNĐ")
        
        if fine_amounts:
            comparison_parts.extend(fine_amounts)
    
    elif result_type == "procedure":
        # Compare procedures by domain/level
        for result in results[:3]:
            title = getattr(result, "title", "")
            domain = getattr(result, "domain", "")
            level = getattr(result, "level", "")
            if title:
                comp = f"- {title}"
                if domain:
                    comp += f" ({domain})"
                if level:
                    comp += f" - Cấp {level}"
                comparison_parts.append(comp)
    
    return "\n".join(comparison_parts)

