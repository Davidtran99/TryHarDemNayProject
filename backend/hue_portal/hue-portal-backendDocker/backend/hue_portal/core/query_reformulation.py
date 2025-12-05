"""
Query reformulation strategies for handling difficult queries.
"""
from typing import List, Optional, Dict, Any
import re


def simplify_query(query: str) -> str:
    """
    Simplify query by removing stopwords and keeping only key terms.
    
    Args:
        query: Original query string.
    
    Returns:
        Simplified query string.
    """
    # Vietnamese stopwords
    stopwords = {
        "là", "gì", "bao nhiêu", "như thế nào", "ở đâu", "của", "và", "hoặc",
        "tôi", "bạn", "có", "không", "được", "một", "các", "với", "cho",
        "theo", "thì", "sao", "như", "về", "trong", "nào", "để", "mà"
    }
    
    words = query.lower().split()
    key_words = [w for w in words if w not in stopwords and len(w) > 2]
    
    return " ".join(key_words) if key_words else query


def extract_key_terms(query: str) -> List[str]:
    """
    Extract key terms from query (document codes, numbers, important nouns).
    
    Args:
        query: Original query string.
    
    Returns:
        List of key terms.
    """
    key_terms = []
    
    # Extract document codes
    doc_code_patterns = [
        r'QD[-\s]?69',
        r'QD[-\s]?264',
        r'264[-\s]?QD',
        r'TT[-\s]?02',
        r'QUYET[-\s]?DINH[-\s]?69',
        r'QUYET[-\s]?DINH[-\s]?264',
        r'THONG[-\s]?TU[-\s]?02',
    ]
    
    for pattern in doc_code_patterns:
        matches = re.findall(pattern, query.upper())
        key_terms.extend(matches)
    
    # Extract numbers (likely article numbers)
    numbers = re.findall(r'\d+', query)
    key_terms.extend(numbers)
    
    # Extract important legal terms
    legal_terms = [
        "kỷ luật", "đảng viên", "cán bộ", "xử lý", "hình thức",
        "điều lệnh", "quy định", "quyết định", "thông tư"
    ]
    
    query_lower = query.lower()
    for term in legal_terms:
        if term in query_lower:
            key_terms.append(term)
    
    return list(set(key_terms))


def reformulate_query_multiple_ways(query: str) -> List[str]:
    """
    Generate multiple reformulations of the query.
    
    Args:
        query: Original query string.
    
    Returns:
        List of reformulated queries.
    """
    reformulations = [query]  # Always include original
    
    # 1. Simplified version (remove stopwords)
    simplified = simplify_query(query)
    if simplified != query and len(simplified) > 3:
        reformulations.append(simplified)
    
    # 2. Key terms only
    key_terms = extract_key_terms(query)
    if key_terms:
        key_terms_query = " ".join(key_terms)
        if key_terms_query not in reformulations:
            reformulations.append(key_terms_query)
    
    # 3. Remove question words
    question_words = ["là gì", "như thế nào", "bao nhiêu", "ở đâu", "sao", "thế nào"]
    query_lower = query.lower()
    for qw in question_words:
        if qw in query_lower:
            reformulated = query_lower.replace(qw, "").strip()
            if reformulated and reformulated not in reformulations:
                reformulations.append(reformulated)
    
    # 4. Expand abbreviations
    abbreviations = {
        "qd": "quyết định",
        "tt": "thông tư",
        "cand": "công an nhân dân",
    }
    expanded = query_lower
    for abbr, full in abbreviations.items():
        expanded = expanded.replace(abbr, full)
    if expanded != query_lower and expanded not in reformulations:
        reformulations.append(expanded)
    
    return reformulations


def create_fallback_queries(query: str, intent: str) -> List[str]:
    """
    Create fallback queries for when primary search fails.
    
    Args:
        query: Original query string.
        intent: Detected intent.
    
    Returns:
        List of fallback queries ordered by priority.
    """
    fallbacks = []
    
    # Strategy 1: Extract only document codes and key legal terms
    key_terms = extract_key_terms(query)
    if key_terms:
        fallbacks.append(" ".join(key_terms))
    
    # Strategy 2: Simplified query
    simplified = simplify_query(query)
    if simplified != query:
        fallbacks.append(simplified)
    
    # Strategy 3: Intent-specific keywords
    if intent == "search_legal":
        # Extract document code if present
        doc_codes = []
        if "69" in query or "quyết định 69" in query.lower():
            doc_codes.append("QD-69-TW")
        if "264" in query or "quyết định 264" in query.lower():
            doc_codes.append("264-QD-TW")
        if "thông tư 02" in query.lower() or "tt 02" in query.lower():
            doc_codes.append("TT-02-CAND")
        
        # Add legal keywords
        legal_keywords = []
        if "kỷ luật" in query.lower():
            legal_keywords.append("kỷ luật")
        if "đảng viên" in query.lower():
            legal_keywords.append("đảng viên")
        if "xử lý" in query.lower():
            legal_keywords.append("xử lý")
        
        if doc_codes or legal_keywords:
            fallback = " ".join(doc_codes + legal_keywords)
            if fallback not in fallbacks:
                fallbacks.append(fallback)
    
    return fallbacks


def reformulate_with_llm(query: str, intent: str, llm_generator=None) -> List[str]:
    """
    Use LLM to reformulate complex queries into simpler, more searchable forms.
    
    Args:
        query: Original query string.
        intent: Detected intent.
        llm_generator: Optional LLM generator instance.
    
    Returns:
        List of reformulated queries.
    """
    if not llm_generator:
        return []
    
    try:
        # Create prompt for query reformulation
        reformulation_prompt = f"""Bạn là trợ lý tìm kiếm văn bản pháp luật. Nhiệm vụ của bạn là chuyển đổi câu hỏi phức tạp thành các câu hỏi đơn giản hơn, dễ tìm kiếm hơn.

Câu hỏi gốc: "{query}"

Hãy tạo 3-5 phiên bản đơn giản hóa của câu hỏi này, tập trung vào:
1. Mã văn bản (nếu có): QD-69-TW, 264-QD-TW, TT-02-CAND, TT-02-BIEN-SOAN
2. Từ khóa chính: kỷ luật, đảng viên, xử lý, hình thức, quy định
3. Số điều/khoản (nếu có)

Trả về mỗi câu hỏi trên một dòng, không đánh số, không giải thích thêm.
Chỉ trả về các câu hỏi, không có tiêu đề hay format khác."""

        response = llm_generator.generate_answer(
            reformulation_prompt,
            context=None,
            documents=[]
        )
        
        if response:
            # Parse response into list of queries
            reformulated = [
                line.strip() 
                for line in response.split('\n') 
                if line.strip() and not line.strip().startswith(('#', '-', '*', '1.', '2.', '3.'))
            ]
            # Filter out queries that are too similar to original or too short
            reformulated = [
                q for q in reformulated 
                if len(q) > 5 and q.lower() != query.lower()
            ]
            return reformulated[:5]  # Limit to 5 reformulations
    except Exception as e:
        print(f"[Query Reformulation] ⚠️ LLM reformulation failed: {e}", flush=True)
    
    return []


def suggest_query_improvements(query: str, intent: str, found_documents: int = 0) -> str:
    """
    Generate helpful suggestions for users when query is too difficult.
    
    Args:
        query: Original query string.
        intent: Detected intent.
        found_documents: Number of documents found.
    
    Returns:
        Suggestion message for user.
    """
    suggestions = []
    
    if intent == "search_legal":
        if found_documents == 0:
            suggestions.append("• Thử sử dụng mã văn bản cụ thể (ví dụ: QD-69-TW, 264-QD-TW)")
            suggestions.append("• Nhắc đến số điều/khoản nếu bạn biết (ví dụ: Điều 5, Khoản 2)")
            suggestions.append("• Sử dụng từ khóa chính: kỷ luật, đảng viên, xử lý, hình thức")
        
        # Check if query has document code
        has_code = any(code in query.upper() for code in ["QD-69", "264-QD", "TT-02", "QUYET DINH 69", "QUYET DINH 264"])
        if not has_code:
            suggestions.append("• Thêm mã văn bản vào câu hỏi để tìm kiếm chính xác hơn")
    
    elif intent == "search_fine":
        if found_documents == 0:
            suggestions.append("• Mô tả rõ loại vi phạm (ví dụ: vượt đèn đỏ, không đội mũ bảo hiểm)")
            suggestions.append("• Sử dụng từ khóa: mức phạt, vi phạm, xử phạt")
    
    elif intent == "search_procedure":
        if found_documents == 0:
            suggestions.append("• Nêu rõ tên thủ tục hành chính bạn cần")
            suggestions.append("• Sử dụng từ khóa: thủ tục, hồ sơ, giấy tờ")
    
    if suggestions:
        return "\n".join(suggestions)
    
    return "• Thử diễn đạt câu hỏi theo cách khác\n• Sử dụng từ khóa cụ thể hơn"


