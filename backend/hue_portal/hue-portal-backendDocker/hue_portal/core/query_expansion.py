"""
Query expansion with Vietnamese synonyms for improved search recall.
"""
from typing import List, Set

# Vietnamese synonyms dictionary for legal domain
VIETNAMESE_SYNONYMS = {
    # Discipline/punishment terms
    "kỷ luật": ["xử lý", "xử phạt", "vi phạm", "trừng phạt", "kỷ luật đảng viên"],
    "xử lý": ["kỷ luật", "xử phạt", "trừng phạt"],
    "vi phạm": ["sai phạm", "lỗi", "khuyết điểm"],
    
    # Document types
    "quyết định": ["qd", "nghị quyết", "văn bản", "quyết nghị"],
    "thông tư": ["tt", "văn bản hướng dẫn"],
    "nghị định": ["nđ", "nd", "văn bản pháp luật"],
    "điều lệnh": ["quy định", "quy chế", "nội quy"],
    
    # Organizational terms
    "đảng viên": ["cán bộ đảng", "đảng viên đảng bộ", "đảng viên chi bộ"],
    "cán bộ": ["công chức", "viên chức", "cán bộ công an"],
    "công an": ["cand", "lực lượng công an", "công an nhân dân"],
    
    # Disciplinary forms
    "khiển trách": ["kỷ luật khiển trách", "hình thức khiển trách"],
    "cảnh cáo": ["kỷ luật cảnh cáo", "hình thức cảnh cáo"],
    "cách chức": ["kỷ luật cách chức", "miễn nhiệm"],
    "khai trừ": ["khai trừ đảng", "kỷ luật khai trừ"],
    
    # Procedures
    "thủ tục": ["quy trình", "trình tự", "các bước"],
    "hồ sơ": ["giấy tờ", "tài liệu", "chứng từ"],
    "điều kiện": ["yêu cầu", "tiêu chuẩn", "quy định"],
    
    # Common verbs
    "quy định": ["qui định", "nêu rõ", "chỉ rõ", "ghi rõ"],
    "áp dụng": ["thực hiện", "thi hành", "triển khai"],
    "ban hành": ["công bố", "phát hành", "ra đời"],
}

# Reverse mapping for faster lookup
_REVERSE_SYNONYMS = {}
for key, synonyms in VIETNAMESE_SYNONYMS.items():
    for syn in synonyms:
        if syn not in _REVERSE_SYNONYMS:
            _REVERSE_SYNONYMS[syn] = []
        _REVERSE_SYNONYMS[syn].append(key)
        # Add other synonyms
        _REVERSE_SYNONYMS[syn].extend([s for s in synonyms if s != syn])


def expand_query(query: str, max_expansions: int = 3) -> List[str]:
    """
    Expand query with Vietnamese synonyms.
    
    Args:
        query: Original query string.
        max_expansions: Maximum number of synonym expansions per term.
    
    Returns:
        List of expanded query strings (including original).
    """
    if not query:
        return [query]
    
    query_lower = query.lower()
    expanded_queries = [query]  # Always include original
    
    # Find matching terms
    matched_terms = set()
    for term in VIETNAMESE_SYNONYMS.keys():
        if term in query_lower:
            matched_terms.add(term)
    
    # Also check reverse mapping
    for term in _REVERSE_SYNONYMS.keys():
        if term in query_lower:
            matched_terms.add(term)
    
    # Generate expanded queries
    for term in matched_terms:
        # Get synonyms
        synonyms = VIETNAMESE_SYNONYMS.get(term, [])
        if not synonyms and term in _REVERSE_SYNONYMS:
            synonyms = _REVERSE_SYNONYMS[term]
        
        # Create expanded queries (limit to max_expansions)
        for syn in synonyms[:max_expansions]:
            expanded = query_lower.replace(term, syn)
            if expanded != query_lower and expanded not in expanded_queries:
                expanded_queries.append(expanded)
    
    return expanded_queries


def get_synonyms(term: str) -> Set[str]:
    """
    Get all synonyms for a term.
    
    Args:
        term: Term to find synonyms for.
    
    Returns:
        Set of synonyms (including the term itself).
    """
    term_lower = term.lower()
    synonyms = {term_lower}
    
    # Check direct mapping
    if term_lower in VIETNAMESE_SYNONYMS:
        synonyms.update(VIETNAMESE_SYNONYMS[term_lower])
    
    # Check reverse mapping
    if term_lower in _REVERSE_SYNONYMS:
        synonyms.update(_REVERSE_SYNONYMS[term_lower])
    
    return synonyms


def expand_keywords(keywords: List[str]) -> List[str]:
    """
    Expand a list of keywords with synonyms.
    
    Args:
        keywords: List of keyword strings.
    
    Returns:
        Expanded list of keywords (including originals).
    """
    expanded = set(keywords)  # Keep originals
    
    for keyword in keywords:
        synonyms = get_synonyms(keyword)
        expanded.update(synonyms)
    
    return list(expanded)

