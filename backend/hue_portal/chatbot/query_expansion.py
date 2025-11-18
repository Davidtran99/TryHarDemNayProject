"""
Query expansion and paraphrasing utilities for improving search recall.
"""
import re
import unicodedata
from typing import List, Dict, Any, Optional, Set
from hue_portal.core.models import Synonym
from hue_portal.core.search_ml import expand_query_with_synonyms


def normalize_vietnamese_query(query: str) -> str:
    """
    Normalize Vietnamese text by handling diacritics variants.
    
    Args:
        query: Input query string.
    
    Returns:
        Normalized query string.
    """
    if not query:
        return ""
    
    # Remove extra spaces
    query = re.sub(r'\s+', ' ', query.strip())
    
    # Lowercase
    query = query.lower()
    
    return query


def extract_key_phrases(query: str) -> List[str]:
    """
    Extract key phrases from query.
    
    Args:
        query: Input query string.
    
    Returns:
        List of key phrases.
    """
    if not query:
        return []
    
    # Remove common stopwords
    stopwords = {
        "là", "gì", "bao nhiêu", "như thế nào", "ở đâu", "của", "và", "hoặc",
        "tôi", "bạn", "có", "không", "được", "một", "các", "với", "cho"
    }
    
    # Split into words
    words = re.findall(r'\b\w+\b', query.lower())
    
    # Filter stopwords and short words
    key_words = [w for w in words if w not in stopwords and len(w) > 2]
    
    # Extract bigrams (2-word phrases)
    phrases = []
    for i in range(len(key_words) - 1):
        phrase = f"{key_words[i]} {key_words[i+1]}"
        phrases.append(phrase)
    
    # Combine single words and phrases
    all_phrases = key_words + phrases
    
    return all_phrases


def expand_query_semantically(query: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    Expand query with synonyms and related terms.
    
    Args:
        query: Original query string.
        context: Optional context dictionary with entities, intents, etc.
    
    Returns:
        List of expanded query variations.
    """
    expanded = [query]
    
    # Use existing synonym expansion
    synonym_expanded = expand_query_with_synonyms(query)
    expanded.extend(synonym_expanded)
    
    # Add context-based expansions
    if context:
        entities = context.get("entities", {})
        
        # If fine_code in context, add fine name variations
        if "fine_code" in entities:
            fine_code = entities["fine_code"]
            # Could look up fine name from database and add variations
            expanded.append(f"{query} {fine_code}")
        
        # If procedure_name in context, add procedure variations
        if "procedure_name" in entities:
            procedure_name = entities["procedure_name"]
            expanded.append(f"{query} {procedure_name}")
    
    # Add common Vietnamese variations
    variations = _get_vietnamese_variations(query)
    expanded.extend(variations)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_expanded = []
    for q in expanded:
        q_normalized = normalize_vietnamese_query(q)
        if q_normalized not in seen:
            seen.add(q_normalized)
            unique_expanded.append(q)
    
    return unique_expanded


def _get_vietnamese_variations(query: str) -> List[str]:
    """
    Get common Vietnamese query variations.
    
    Args:
        query: Input query.
    
    Returns:
        List of variations.
    """
    variations = []
    query_lower = query.lower()
    
    # Common synonym mappings
    synonym_map = {
        "mức phạt": ["tiền phạt", "phạt", "xử phạt"],
        "thủ tục": ["hồ sơ", "giấy tờ", "quy trình"],
        "địa chỉ": ["nơi", "chỗ", "điểm"],
        "số điện thoại": ["điện thoại", "số liên hệ", "hotline"],
        "giờ làm việc": ["thời gian", "giờ", "lịch làm việc"],
        "cảnh báo": ["thông báo", "lưu ý", "chú ý"],
        "lừa đảo": ["scam", "gian lận", "lừa"],
    }
    
    for key, synonyms in synonym_map.items():
        if key in query_lower:
            for synonym in synonyms:
                variation = query_lower.replace(key, synonym)
                if variation != query_lower:
                    variations.append(variation)
    
    return variations


def paraphrase_query(query: str) -> List[str]:
    """
    Generate paraphrases of the query to increase recall.
    
    Args:
        query: Original query string.
    
    Returns:
        List of paraphrased queries.
    """
    paraphrases = [query]
    query_lower = query.lower()
    
    # Common paraphrasing patterns for Vietnamese
    patterns = [
        # Question variations
        (r"mức phạt (.+) là bao nhiêu", r"phạt \1 bao nhiêu tiền"),
        (r"thủ tục (.+) cần gì", r"làm thủ tục \1 cần giấy tờ gì"),
        (r"địa chỉ (.+) ở đâu", r"\1 ở đâu"),
        (r"(.+) như thế nào", r"cách \1"),
    ]
    
    for pattern, replacement in patterns:
        if re.search(pattern, query_lower):
            paraphrase = re.sub(pattern, replacement, query_lower)
            if paraphrase != query_lower:
                paraphrases.append(paraphrase)
    
    # Add question word variations
    if "bao nhiêu" in query_lower:
        paraphrases.append(query_lower.replace("bao nhiêu", "mức"))
        paraphrases.append(query_lower.replace("bao nhiêu", "giá"))
    
    if "như thế nào" in query_lower:
        paraphrases.append(query_lower.replace("như thế nào", "cách"))
        paraphrases.append(query_lower.replace("như thế nào", "quy trình"))
    
    # Remove duplicates
    return list(dict.fromkeys(paraphrases))


def enhance_query_with_context(query: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Enhance query with context information.
    
    Args:
        query: Original query string.
        context: Optional context dictionary.
    
    Returns:
        Enhanced query string.
    """
    if not context:
        return query
    
    enhanced_parts = [query]
    
    # Add entities from context
    entities = context.get("entities", {})
    if "fine_code" in entities:
        enhanced_parts.append(entities["fine_code"])
    if "procedure_name" in entities:
        enhanced_parts.append(entities["procedure_name"])
    if "office_name" in entities:
        enhanced_parts.append(entities["office_name"])
    
    # Add intent-based keywords
    intent = context.get("intent", "")
    if intent == "search_fine":
        enhanced_parts.append("mức phạt vi phạm")
    elif intent == "search_procedure":
        enhanced_parts.append("thủ tục hành chính")
    elif intent == "search_office":
        enhanced_parts.append("đơn vị công an")
    
    return " ".join(enhanced_parts)

