"""
Chatbot with ML-based intent classification for natural language queries.
"""
import re
import unicodedata
from typing import Dict, List, Tuple, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import numpy as np
from .models import Procedure, Fine, Office, Advisory
from .search_ml import search_with_ml, expand_query_with_synonyms


# Training data for intent classification
INTENT_TRAINING_DATA = {
    "search_fine": [
        "mức phạt", "phạt bao nhiêu", "tiền phạt", "vi phạm giao thông",
        "vượt đèn đỏ", "nồng độ cồn", "không đội mũ bảo hiểm",
        "mức phạt là gì", "phạt như thế nào", "hành vi vi phạm",
        "điều luật", "nghị định", "mức xử phạt"
    ],
    "search_procedure": [
        "thủ tục", "làm thủ tục", "hồ sơ", "điều kiện",
        "thủ tục cư trú", "thủ tục ANTT", "thủ tục PCCC",
        "cần giấy tờ gì", "làm như thế nào", "quy trình",
        "thời hạn", "lệ phí", "nơi nộp"
    ],
    "search_office": [
        "địa chỉ", "điểm tiếp dân", "công an", "phòng ban",
        "số điện thoại", "giờ làm việc", "nơi tiếp nhận",
        "đơn vị nào", "ở đâu", "liên hệ"
    ],
    "search_advisory": [
        "cảnh báo", "lừa đảo", "scam", "thủ đoạn",
        "cảnh giác", "an toàn", "bảo mật"
    ],
    "general_query": [
        "xin chào", "giúp tôi", "tư vấn", "hỏi",
        "thông tin", "tra cứu", "tìm kiếm"
    ]
}

# Response templates
RESPONSE_TEMPLATES = {
    "search_fine": "Tôi tìm thấy {count} mức phạt liên quan đến '{query}':",
    "search_procedure": "Tôi tìm thấy {count} thủ tục liên quan đến '{query}':",
    "search_office": "Tôi tìm thấy {count} đơn vị liên quan đến '{query}':",
    "search_advisory": "Tôi tìm thấy {count} cảnh báo liên quan đến '{query}':",
    "general_query": "Tôi có thể giúp bạn tra cứu thông tin về thủ tục, mức phạt, đơn vị hoặc cảnh báo. Bạn muốn tìm gì?",
    "no_results": "Xin lỗi, tôi không tìm thấy thông tin liên quan đến '{query}'. Vui lòng thử lại với từ khóa khác.",
    "greeting": "Xin chào! Tôi có thể giúp bạn tra cứu thông tin về thủ tục hành chính, mức phạt giao thông, danh bạ đơn vị và cảnh báo an ninh. Bạn cần tìm gì?",
}


class Chatbot:
    def __init__(self):
        self.intent_classifier = None
        self.vectorizer = None
        self._train_classifier()
    
    def _train_classifier(self):
        """Train intent classification model."""
        try:
            # Prepare training data
            texts = []
            labels = []
            
            for intent, examples in INTENT_TRAINING_DATA.items():
                for example in examples:
                    texts.append(self._preprocess_text(example))
                    labels.append(intent)
            
            if not texts:
                return
            
            # Create and train pipeline
            self.intent_classifier = Pipeline([
                ('tfidf', TfidfVectorizer(
                    analyzer='word',
                    ngram_range=(1, 2),
                    min_df=1,
                    lowercase=True,
                    token_pattern=r'\b\w+\b'
                )),
                ('clf', MultinomialNB())
            ])
            
            self.intent_classifier.fit(texts, labels)
        except Exception as e:
            print(f"Error training classifier: {e}")
            self.intent_classifier = None
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for classification - keep Vietnamese characters."""
        if not text:
            return ""
        text = text.lower().strip()
        # Only remove punctuation marks, keep all letters (including Vietnamese) and numbers
        # Remove: !"#$%&'()*+,-./:;<=>?@[\]^_`{|}~
        text = re.sub(r'[!"#$%&\'()*+,\-./:;<=>?@\[\\\]^_`{|}~]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _remove_accents(self, text: str) -> str:
        """Remove diacritics for accent-insensitive matching."""
        if not text:
            return ""
        normalized = unicodedata.normalize("NFD", text)
        return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")

    def _keyword_in(self, query_lower: str, query_ascii: str, keyword: str) -> bool:
        """Check keyword presence in either original or accent-free text."""
        kw_lower = keyword.lower()
        if kw_lower in query_lower:
            return True
        kw_ascii = self._remove_accents(kw_lower)
        return kw_ascii in query_ascii
    
    def classify_intent(self, query: str) -> Tuple[str, float]:
        """
        Classify user intent from query.
        Returns (intent, confidence_score)
        """
        # Use keyword-based classification first (more reliable for Vietnamese)
        keyword_intent, keyword_confidence = self._keyword_based_intent(query)
        
        # ALWAYS use keyword-based for now (more reliable for Vietnamese)
        # Special handling for greeting - only if really simple
        if keyword_intent == "greeting":
            query_lower = query.lower().strip()
            query_ascii = self._remove_accents(query_lower)
            query_words = query_lower.split()
            # Double-check: if query has fine keywords, it's NOT a greeting
            fine_indicators = ["phạt", "mức", "vuot", "vượt", "đèn", "den", "vi phạm", "vi pham"]
            if any(self._keyword_in(query_lower, query_ascii, indicator) for indicator in fine_indicators):
                # Re-check with fine keywords
                for kw in ["mức phạt", "vi phạm", "đèn đỏ", "vượt đèn", "muc phat", "vuot den", "phat", "vuot", "den", "muc"]:
                    if self._keyword_in(query_lower, query_ascii, kw):
                        return ("search_fine", 0.9)
            # Only return greeting if query is very short (<= 3 words)
            if len(query_words) > 3:
                # If long query classified as greeting, it's probably wrong - use general
                return ("general_query", 0.5)
        
        # For all other intents, use keyword-based result
        return (keyword_intent, max(keyword_confidence, 0.8))
    
    def _keyword_based_intent(self, query: str) -> Tuple[str, float]:
        """Fallback keyword-based intent classification."""
        # Use original query (lowercase) to preserve Vietnamese characters
        query_lower = query.lower().strip()
        query_ascii = self._remove_accents(query_lower)
        query_words = query_lower.split()
        
        # Check for keywords - prioritize fine-related queries FIRST
        # Check on original query to preserve Vietnamese characters
        # Check longer phrases first, then single words
        fine_keywords = ["mức phạt", "vi phạm", "đèn đỏ", "nồng độ cồn", "mũ bảo hiểm", "tốc độ", "bằng lái", "vượt đèn", "mức phạt vượt"]
        fine_keywords_ascii = [self._remove_accents(kw) for kw in fine_keywords]
        fine_single_words = ["phạt", "vượt", "đèn", "mức", "phat", "vuot", "den"]
        
        # Check multi-word keywords first
        has_fine_keywords = False
        for kw, kw_ascii in zip(fine_keywords, fine_keywords_ascii):
            if self._keyword_in(query_lower, query_ascii, kw) or kw_ascii in query_ascii:
                return ("search_fine", 0.95)  # Very high confidence
        # Then check single words - check ALL of them, not just first match
        for kw in fine_single_words:
            if self._keyword_in(query_lower, query_ascii, kw):
                has_fine_keywords = True
                # Return immediately if found
                return ("search_fine", 0.9)
        
        has_procedure_keywords = any(
            self._keyword_in(query_lower, query_ascii, kw) for kw in
            ["thủ tục", "hồ sơ", "điều kiện", "cư trú", "antt", "pccc", "thu tuc", "ho so", "dieu kien", "cu tru"]
        )
        if has_procedure_keywords:
            return ("search_procedure", 0.8)
        
        has_office_keywords = any(
            self._keyword_in(query_lower, query_ascii, kw) for kw in
            ["địa chỉ", "điểm tiếp dân", "công an", "số điện thoại", "giờ làm việc", "dia chi", "diem tiep dan", "cong an", "so dien thoai", "gio lam viec"]
        )
        if has_office_keywords:
            return ("search_office", 0.8)
        
        has_advisory_keywords = any(
            self._keyword_in(query_lower, query_ascii, kw) for kw in
            ["cảnh báo", "lừa đảo", "scam", "canh bao", "lua dao"]
        )
        if has_advisory_keywords:
            return ("search_advisory", 0.8)
        
        # Only treat as greeting if it's VERY short (<= 3 words) and ONLY contains greeting words
        # AND does NOT contain any other keywords
        has_any_keyword = (has_fine_keywords or has_procedure_keywords or 
                          has_office_keywords or has_advisory_keywords)
        
        if (len(query_words) <= 3 and 
            any(self._keyword_in(query_lower, query_ascii, kw) for kw in ["xin chào", "chào", "hello", "hi", "xin chao", "chao"]) and
            not has_any_keyword):
            return ("greeting", 0.9)
        
        return ("general_query", 0.5)
    
    def extract_keywords(self, query: str) -> List[str]:
        """Extract keywords from query for search."""
        # Remove common stopwords
        stopwords = {"là", "gì", "bao nhiêu", "như thế nào", "ở đâu", "của", "và", "hoặc", "tôi", "bạn"}
        
        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        
        return keywords
    
    def search_by_intent(self, intent: str, query: str, limit: int = 5) -> Dict[str, Any]:
        """Search based on classified intent."""
        # Use original query for better matching, especially for Vietnamese text
        keywords = query.strip()
        # Also try with extracted keywords as fallback
        extracted = " ".join(self.extract_keywords(query))
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
        
        return {
            "intent": intent,
            "query": query,
            "keywords": keywords,
            "results": results,
            "count": len(results)
        }
    
    def generate_response(self, query: str) -> Dict[str, Any]:
        """
        Generate chatbot response for user query.
        Returns dict with message, intent, and results.
        """
        query = query.strip()
        
        # Classify intent FIRST
        intent, confidence = self.classify_intent(query)
        
        # Only handle greetings if it's REALLY a simple greeting (very short, no other keywords)
        query_lower = query.lower().strip()
        query_words = query_lower.split()
        
        # Check if it contains keywords that indicate it's NOT a greeting
        has_fine_keywords = any(kw in query_lower for kw in ["phạt", "mức phạt", "vi phạm", "đèn đỏ", "nồng độ cồn", "mũ bảo hiểm", "tốc độ", "vượt"])
        has_procedure_keywords = any(kw in query_lower for kw in ["thủ tục", "hồ sơ", "điều kiện", "cư trú", "antt", "pccc"])
        has_office_keywords = any(kw in query_lower for kw in ["địa chỉ", "công an", "số điện thoại", "giờ làm việc"])
        has_advisory_keywords = any(kw in query_lower for kw in ["cảnh báo", "lừa đảo", "scam"])
        
        # Only treat as greeting if it's very short AND has no other keywords AND classified as greeting
        is_simple_greeting = (len(query_words) <= 3 and 
                             any(greeting in query_lower for greeting in ["xin chào", "chào", "hello", "hi"]) and
                             not (has_fine_keywords or has_procedure_keywords or has_office_keywords or has_advisory_keywords))
        
        if is_simple_greeting and intent == "greeting":
            return {
                "message": RESPONSE_TEMPLATES["greeting"],
                "intent": "greeting",
                "results": [],
                "count": 0
            }
        
        # Search based on intent
        search_result = self.search_by_intent(intent, query, limit=5)
        
        # Generate response message
        if search_result["count"] > 0:
            template = RESPONSE_TEMPLATES.get(intent, RESPONSE_TEMPLATES["general_query"])
            message = template.format(
                count=search_result["count"],
                query=query
            )
        else:
            message = RESPONSE_TEMPLATES["no_results"].format(query=query)
        
        return {
            "message": message,
            "intent": intent,
            "confidence": confidence,
            "results": search_result["results"],
            "count": search_result["count"]
        }


# Global chatbot instance
_chatbot_instance = None

def get_chatbot() -> Chatbot:
    """Get or create chatbot instance."""
    global _chatbot_instance
    if _chatbot_instance is None:
        _chatbot_instance = Chatbot()
    return _chatbot_instance

