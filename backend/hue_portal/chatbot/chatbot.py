"""
Chatbot with ML-based intent classification for natural language queries.
"""
import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import numpy as np
from hue_portal.core.models import Procedure, Fine, Office, Advisory
from hue_portal.core.search_ml import search_with_ml, expand_query_with_synonyms


def format_fine_amount(min_fine: Optional[float], max_fine: Optional[float]) -> Optional[str]:
    """
    Format fine amount as '200.000 - 400.000 VNĐ'.
    
    Args:
        min_fine: Minimum fine amount.
        max_fine: Maximum fine amount.
    
    Returns:
        Formatted string or None if both are None.
    """
    if min_fine is not None and max_fine is not None:
        # Format with thousand separators (dots for Vietnamese format)
        min_str = f"{min_fine:,.0f}".replace(",", ".")
        max_str = f"{max_fine:,.0f}".replace(",", ".")
        return f"{min_str} - {max_str} VNĐ"
    elif min_fine is not None:
        min_str = f"{min_fine:,.0f}".replace(",", ".")
        return f"{min_str} VNĐ"
    return None


# Training data for intent classification (fallback when chưa có model huấn luyện)
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
        "cảnh giác", "an toàn", "bảo mật",
        "cảnh báo lừa đảo giả danh công an",
        "mạo danh cán bộ công an",
        "lừa đảo mạo danh",
        "cảnh báo an ninh",
        "thủ đoạn lừa đảo",
        "scam giả danh",
        "cảnh giác lừa đảo online",
        "lừa đảo qua điện thoại",
        "cảnh báo bảo mật",
        "mạo danh cán bộ",
        "lừa đảo giả danh",
        "cảnh báo lừa đảo",
        "thủ đoạn scam",
        "cảnh giác an toàn",
        "lừa đảo online",
        "cảnh báo mạo danh"
    ],
    "search_legal": [
        "quyết định", "quy định", "thông tư", "nghị quyết",
        "văn bản pháp luật", "văn bản quy phạm", "điều lệnh",
        "kỷ luật đảng viên", "kỷ luật", "xử lý kỷ luật",
        "quyết định 69", "quyết định 264", "qd 69", "qd 264",
        "thông tư 02", "tt 02", "điều lệnh cand",
        "quy định kỷ luật", "hình thức kỷ luật", "mức kỷ luật",
        "xử lý vi phạm", "kỷ luật đảng", "kỷ luật cán bộ",
        "quy định về", "theo quyết định", "theo thông tư",
        "nội dung quyết định", "nội dung thông tư", "điều khoản"
    ],
    "general_query": [
        "xin chào", "giúp tôi", "tư vấn", "hỏi",
        "thông tin", "tra cứu", "tìm kiếm"
    ]
}

# Đường dẫn artefact model
TRAINING_DIR = Path(__file__).resolve().parent / "training"
ARTIFACT_MODEL = TRAINING_DIR / "artifacts" / "intent_model.joblib"
ARTIFACT_METRICS = TRAINING_DIR / "artifacts" / "metrics.json"

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
        self.intent_metrics: Optional[Dict[str, Any]] = None
        self._load_classifier()
    
    def _load_classifier(self):
        """Load pretrained classifier nếu có, fallback tự huấn luyện seed data."""
        if ARTIFACT_MODEL.exists():
            try:
                self.intent_classifier = joblib.load(ARTIFACT_MODEL)
                if ARTIFACT_METRICS.exists():
                    self.intent_metrics = json.loads(ARTIFACT_METRICS.read_text(encoding="utf-8"))
                return
            except Exception as exc:
                print(f"Warning: không thể load intent_model.joblib ({exc}). Sẽ huấn luyện tạm thời.")
                self.intent_classifier = None
                self.intent_metrics = None
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
    
    def classify_intent(self, query: str, context: Optional[Dict[str, Any]] = None) -> Tuple[str, float]:
        """
        Classify user intent from query with optional context.
        
        Args:
            query: User query string.
            context: Optional context dictionary with recent_messages, entities, etc.
        
        Returns:
            Tuple of (intent, confidence_score)
        """
        # Use context to improve classification if available
        if context:
            # Check recent intents in context
            recent_messages = context.get("recent_messages", [])
            if recent_messages:
                # Get most recent intent
                for msg in reversed(recent_messages):
                    if msg.get("intent") and msg.get("intent") != "greeting":
                        recent_intent = msg.get("intent")
                        # Boost confidence if query is short and recent intent is relevant
                        if len(query.split()) <= 5:
                            # Likely a follow-up question
                            return (recent_intent, 0.85)
        
        model_intent, model_confidence = self._model_based_intent(query)
        keyword_intent, keyword_confidence = self._keyword_based_intent(query)
        
        # CRITICAL: If keyword-based detects search_legal, NEVER let model override it
        # Legal queries are very specific and keyword matching is more reliable than model
        if keyword_intent == "search_legal" and keyword_confidence >= 0.85:
            return (keyword_intent, keyword_confidence)
        
        chosen_intent = keyword_intent
        confidence = keyword_confidence

        # Nếu model tự tin và không mâu thuẫn với keyword, ưu tiên model
        # BUT: Never override search_legal
        if model_intent and model_confidence >= 0.65:
            if keyword_intent in {model_intent, "general_query", "greeting"}:
                # Only override if keyword is not search_legal
                if keyword_intent != "search_legal":
                    chosen_intent = model_intent
                    confidence = max(confidence, model_confidence)
        
        # Ensemble: combine model and keyword predictions
        if model_intent and keyword_intent:
            if model_intent == keyword_intent:
                # Both agree - boost confidence
                confidence = min(1.0, (model_confidence + keyword_confidence) / 2 + 0.1)
            elif model_confidence > 0.7 and keyword_confidence < 0.6:
                # Model is more confident - use model
                # BUT: Never override search_legal
                if keyword_intent != "search_legal":
                    chosen_intent = model_intent
                    confidence = model_confidence * 0.9  # Slight penalty for disagreement

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
        
        # Confidence calibration: adjust confidence based on query characteristics
        confidence = self._calibrate_confidence(chosen_intent, confidence, query)
        
        return (chosen_intent, confidence)
    
    def _calibrate_confidence(self, intent: str, base_confidence: float, query: str) -> float:
        """
        Calibrate confidence score based on query characteristics.
        
        Args:
            intent: Classified intent.
            base_confidence: Base confidence score.
            query: Original query.
        
        Returns:
            Calibrated confidence score.
        """
        confidence = base_confidence
        query_lower = query.lower()
        query_words = query.split()
        
        # Boost confidence for longer, more specific queries
        if len(query_words) >= 5:
            confidence = min(1.0, confidence + 0.05)
        
        # Reduce confidence for very short queries
        if len(query_words) <= 2:
            confidence = max(0.3, confidence - 0.1)
        
        # Boost confidence if query contains intent-specific keywords
        intent_keywords = {
            "search_fine": ["phạt", "mức phạt", "vi phạm"],
            "search_procedure": ["thủ tục", "hồ sơ", "giấy tờ"],
            "search_office": ["địa chỉ", "công an", "đơn vị"],
            "search_advisory": ["cảnh báo", "lừa đảo", "scam"],
        }
        
        if intent in intent_keywords:
            keywords = intent_keywords[intent]
            if any(kw in query_lower for kw in keywords):
                confidence = min(1.0, confidence + 0.05)
        
        return confidence
    
    def _personalize_query(
        self,
        query: str,
        intent: str,
        context: Optional[Dict[str, Any]],
        session_id: Optional[str]
    ) -> str:
        """
        Personalize query based on user history and session context.
        
        Args:
            query: Original query.
            intent: Detected intent.
            context: Conversation context.
            session_id: Session ID.
        
        Returns:
            Personalized query.
        """
        if not context or not session_id:
            return query
        
        # Get user preferences from context
        entities = context.get("entities", {})
        intents = context.get("intents", [])
        
        # If user frequently asks about same intent, boost related terms
        if intents and len(intents) >= 2:
            most_common_intent = max(set(intents), key=intents.count)
            if most_common_intent == intent:
                # User prefers this intent - query is already personalized
                pass
        
        # Add context entities to query if missing
        enhanced_parts = [query]
        
        if intent == "search_fine" and "fine_code" in entities:
            fine_code = entities["fine_code"]
            if fine_code not in query.lower():
                enhanced_parts.append(fine_code)
        
        return " ".join(enhanced_parts)
    
    def _model_based_intent(self, query: str) -> Tuple[Optional[str], float]:
        """Phân loại ý định bằng model đã huấn luyện nếu có."""
        if not self.intent_classifier:
            return (None, 0.0)
        try:
            predicted_proba = getattr(self.intent_classifier, "predict_proba", None)
            if not predicted_proba:
                return (None, 0.0)
            probs = predicted_proba([query])[0]
            classes = self._intent_classes()
            if not classes:
                return (None, 0.0)
            max_idx = int(np.argmax(probs))
            return (classes[max_idx], float(probs[max_idx]))
        except Exception:
            return (None, 0.0)

    def _intent_classes(self) -> Optional[List[str]]:
        if not self.intent_classifier:
            return None
        if hasattr(self.intent_classifier, "classes_"):
            return list(self.intent_classifier.classes_)
        named_steps = getattr(self.intent_classifier, "named_steps", {})
        clf = named_steps.get("clf") if isinstance(named_steps, dict) else None
        if clf and hasattr(clf, "classes_"):
            return list(clf.classes_)
        return None
    
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
        
        # Check advisory keywords first to avoid conflict with "công an" in office keywords
        has_advisory_keywords = any(
            self._keyword_in(query_lower, query_ascii, kw) for kw in
            ["cảnh báo", "lừa đảo", "scam", "mạo danh", "thủ đoạn", "cảnh giác", "canh bao", "lua dao", "mao danh", "thu doan", "canh giac"]
        )
        if has_advisory_keywords:
            return ("search_advisory", 0.8)
        
        has_office_keywords = any(
            self._keyword_in(query_lower, query_ascii, kw) for kw in
            ["địa chỉ", "điểm tiếp dân", "công an", "số điện thoại", "giờ làm việc", "dia chi", "diem tiep dan", "cong an", "so dien thoai", "gio lam viec"]
        )
        if has_office_keywords:
            return ("search_office", 0.8)
        
        # Check legal keywords (check BEFORE advisory to avoid "công an" conflict)
        has_legal_keywords = any(
            self._keyword_in(query_lower, query_ascii, kw) for kw in
            ["quyết định", "quy định", "thông tư", "nghị quyết", "văn bản pháp luật", "văn bản quy phạm", "điều lệnh",
             "kỷ luật đảng viên", "kỷ luật", "xử lý kỷ luật", "hình thức kỷ luật", "mức kỷ luật",
             "quyết định 69", "quyết định 264", "qd 69", "qd 264", "thông tư 02", "tt 02",
             "quy định kỷ luật", "kỷ luật đảng", "kỷ luật cán bộ", "xử lý vi phạm",
             "quyet dinh", "quy dinh", "thong tu", "nghi quyet", "van ban phap luat", "van ban quy pham", "dieu lenh",
             "ky luat dang vien", "ky luat", "xu ly ky luat", "hinh thuc ky luat", "muc ky luat",
             "quyet dinh 69", "quyet dinh 264", "qd 69", "qd 264", "thong tu 02", "tt 02",
             "quy dinh ky luat", "ky luat dang", "ky luat can bo", "xu ly vi pham"]
        )
        if has_legal_keywords:
            return ("search_legal", 0.85)
        
        # Only treat as greeting if it's VERY short (<= 3 words) and ONLY contains greeting words
        # AND does NOT contain any other keywords
        has_any_keyword = (has_fine_keywords or has_procedure_keywords or 
                          has_office_keywords or has_advisory_keywords or has_legal_keywords)
        
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
                "fine_amount_formatted": format_fine_amount(
                    float(f.min_fine) if f.min_fine else None,
                    float(f.max_fine) if f.max_fine else None
                ),
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
    
    def _serialize_document(self, doc: Any, content_type: str) -> Dict[str, Any]:
        """Convert Django model instance to JSON-serializable dict."""
        base = {"id": getattr(doc, "id", None)}
        content_type = (content_type or "").lower()
        
        def _to_iso(value):
            if value is None:
                return None
            if hasattr(value, "isoformat"):
                return value.isoformat()
            return value
        
        if content_type == "procedure":
            base.update({
                "title": getattr(doc, "title", ""),
                "domain": getattr(doc, "domain", ""),
                "level": getattr(doc, "level", ""),
                "conditions": getattr(doc, "conditions", ""),
                "dossier": getattr(doc, "dossier", ""),
                "fee": getattr(doc, "fee", ""),
                "duration": getattr(doc, "duration", ""),
                "authority": getattr(doc, "authority", ""),
                "source_url": getattr(doc, "source_url", ""),
            })
        elif content_type == "fine":
            min_fine = float(doc.min_fine) if getattr(doc, "min_fine", None) is not None else None
            max_fine = float(doc.max_fine) if getattr(doc, "max_fine", None) is not None else None
            base.update({
                "name": getattr(doc, "name", ""),
                "code": getattr(doc, "code", ""),
                "min_fine": min_fine,
                "max_fine": max_fine,
                "fine_amount_formatted": format_fine_amount(min_fine, max_fine),
                "article": getattr(doc, "article", ""),
                "decree": getattr(doc, "decree", ""),
            })
        elif content_type == "office":
            base.update({
                "unit_name": getattr(doc, "unit_name", ""),
                "address": getattr(doc, "address", ""),
                "district": getattr(doc, "district", ""),
                "phone": getattr(doc, "phone", ""),
                "working_hours": getattr(doc, "working_hours", ""),
            })
        elif content_type == "advisory":
            base.update({
                "title": getattr(doc, "title", ""),
                "summary": getattr(doc, "summary", ""),
                "source_url": getattr(doc, "source_url", ""),
                "published_at": _to_iso(getattr(doc, "published_at", None)),
            })
        else:
            # Fallback: include common attributes but skip non-serializable ones
            safe_attrs = [
                "title", "summary", "description", "domain", "level", "conditions",
                "dossier", "fee", "duration", "authority", "unit_name", "address",
                "district", "phone", "working_hours", "source_url", "published_at"
            ]
            for attr in safe_attrs:
                if hasattr(doc, attr):
                    value = getattr(doc, attr)
                    if attr == "published_at":
                        base[attr] = _to_iso(value)
                    elif isinstance(value, (str, int, float, type(None))):
                        base[attr] = value
        
        return base
    
    def generate_response(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate chatbot response for user query with context awareness.
        
        Args:
            query: User query string.
            session_id: Optional session ID for context management.
        
        Returns:
            Dict with message, intent, results, and session_id.
        """
        query = query.strip()
        original_query = query
        
        # Get context if session_id provided
        context_messages = []
        context_dict = None
        if session_id:
            try:
                from hue_portal.chatbot.context_manager import ConversationContext
                from hue_portal.chatbot.entity_extraction import resolve_pronouns, extract_all_entities
                
                # Get recent messages
                recent_messages = ConversationContext.get_recent_messages(session_id, limit=10)
                context_messages = [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "intent": msg.intent,
                        "entities": msg.entities
                    }
                    for msg in recent_messages
                ]
                
                # Build context dictionary for intent classification
                context_dict = ConversationContext.get_context_summary(session_id, max_messages=5)
                
                # Resolve pronouns in query
                if context_messages:
                    query = resolve_pronouns(query, context_messages)
                    if query != original_query:
                        print(f"Query enhanced with context: '{original_query}' -> '{query}'")
            except Exception as e:
                print(f"Error loading context: {e}")
        
        # Classify intent FIRST (use enhanced query and context)
        intent, confidence = self.classify_intent(query, context=context_dict)
        
        # Personalize response based on context and user history
        personalized_query = self._personalize_query(query, intent, context_dict, session_id)
        if personalized_query != query:
            query = personalized_query
        
        # Only handle greetings if it's REALLY a simple greeting (very short, no other keywords)
        query_lower = query.lower().strip()
        query_words = query_lower.split()
        
        # Check if it contains keywords that indicate it's NOT a greeting
        has_fine_keywords = any(kw in query_lower for kw in ["phạt", "mức phạt", "vi phạm", "đèn đỏ", "nồng độ cồn", "mũ bảo hiểm", "tốc độ", "vượt"])
        has_procedure_keywords = any(kw in query_lower for kw in ["thủ tục", "hồ sơ", "điều kiện", "cư trú", "antt", "pccc"])
        # Check advisory keywords first to avoid conflict with "công an" in office keywords
        has_advisory_keywords = any(kw in query_lower for kw in ["cảnh báo", "lừa đảo", "scam", "mạo danh", "thủ đoạn", "cảnh giác"])
        has_office_keywords = any(kw in query_lower for kw in ["địa chỉ", "công an", "số điện thoại", "giờ làm việc"])
        has_legal_keywords = any(kw in query_lower for kw in ["quyết định", "quy định", "thông tư", "kỷ luật đảng viên", "kỷ luật", "qd 69", "qd 264", "thông tư 02", "điều lệnh", "văn bản pháp luật"])
        
        # Only treat as greeting if it's very short AND has no other keywords AND classified as greeting
        is_simple_greeting = (len(query_words) <= 3 and 
                             any(greeting in query_lower for greeting in ["xin chào", "chào", "hello", "hi"]) and
                             not (has_fine_keywords or has_procedure_keywords or has_office_keywords or has_advisory_keywords or has_legal_keywords))
        
        if is_simple_greeting and intent == "greeting":
            response = {
                "message": RESPONSE_TEMPLATES["greeting"],
                "intent": "greeting",
                "results": [],
                "count": 0,
                "session_id": session_id
            }
            
            # Save conversation if session_id provided
            if session_id:
                try:
                    from hue_portal.chatbot.context_manager import ConversationContext
                    from hue_portal.chatbot.entity_extraction import extract_all_entities
                    
                    # Save user message
                    entities = extract_all_entities(original_query)
                    ConversationContext.add_message(
                        session_id=session_id,
                        role="user",
                        content=original_query,
                        intent=intent,
                        entities=entities
                    )
                    
                    # Save bot response
                    ConversationContext.add_message(
                        session_id=session_id,
                        role="bot",
                        content=RESPONSE_TEMPLATES["greeting"],
                        intent=intent
                    )
                except Exception as e:
                    print(f"Error saving conversation: {e}")
            
            return response
        
        # Try RAG pipeline first (if embeddings available)
        use_rag = True
        try:
            from hue_portal.core.rag import rag_pipeline
            # Build context list for RAG
            rag_context = None
            if context_messages:
                rag_context = context_messages
            rag_result = rag_pipeline(query, intent, top_k=5, min_confidence=confidence, context=rag_context, use_llm=True)
            
            # Use RAG answer if available (even with count=0 for general conversation)
            if rag_result.get("answer") and (rag_result["count"] > 0 or rag_result.get("answer", "").strip()):
                # Use RAG-generated answer
                documents = rag_result["documents"][:5]
                results = [
                    {
                        "type": rag_result["content_type"],
                        "data": self._serialize_document(doc, rag_result["content_type"])
                    } for doc in documents
                ]
                
                # Add best_match flag and relevance_scores
                best_match_index = 0 if documents else None
                relevance_scores = []
                for i, doc in enumerate(documents):
                    score = getattr(doc, "_hybrid_score", getattr(doc, "_ml_score", 0.0))
                    relevance_scores.append({
                        "index": i,
                        "score": float(score) if score else 0.0,
                        "is_best_match": i == 0
                    })
                
                response = {
                    "message": rag_result["answer"],
                    "intent": intent,
                    "confidence": rag_result["confidence"],
                    "results": results,
                    "count": rag_result["count"],
                    "best_match": best_match_index,
                    "relevance_scores": relevance_scores,
                    "session_id": session_id
                }
                
                # Save conversation if session_id provided
                if session_id:
                    try:
                        from hue_portal.chatbot.context_manager import ConversationContext
                        from hue_portal.chatbot.entity_extraction import extract_all_entities
                        
                        # Save user message
                        entities = extract_all_entities(original_query)
                        ConversationContext.add_message(
                            session_id=session_id,
                            role="user",
                            content=original_query,
                            intent=intent,
                            entities=entities
                        )
                        
                        # Save bot response
                        ConversationContext.add_message(
                            session_id=session_id,
                            role="bot",
                            content=rag_result["answer"],
                            intent=intent
                        )
                    except Exception as e:
                        print(f"Error saving conversation: {e}")
                
                return response
        except Exception as e:
            # Fallback to original search if RAG fails
            print(f"RAG pipeline not available, using original search: {e}")
            use_rag = False
        
        # Search based on intent (original method)
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
        
        # Add best_match flag and relevance_scores for search results
        best_match_index = 0 if search_result["count"] > 0 else None
        relevance_scores = []
        for i, result in enumerate(search_result["results"][:5]):
            # Try to get score from result data if available
            score = 0.0
            if isinstance(result, dict) and "data" in result:
                # Score might be in the data or we can infer from position
                score = 1.0 - (i * 0.1)  # Decreasing score for lower positions
            relevance_scores.append({
                "index": i,
                "score": score,
                "is_best_match": i == 0
            })
        
        response = {
            "message": message,
            "intent": intent,
            "confidence": confidence,
            "results": search_result["results"],
            "count": search_result["count"],
            "best_match": best_match_index,
            "relevance_scores": relevance_scores,
            "session_id": session_id
        }
        
        # Save conversation if session_id provided
        if session_id:
            try:
                from hue_portal.chatbot.context_manager import ConversationContext
                from hue_portal.chatbot.entity_extraction import extract_all_entities
                
                # Save user message
                entities = extract_all_entities(original_query)
                ConversationContext.add_message(
                    session_id=session_id,
                    role="user",
                    content=original_query,
                    intent=intent,
                    entities=entities
                )
                
                # Save bot response
                ConversationContext.add_message(
                    session_id=session_id,
                    role="bot",
                    content=message,
                    intent=intent
                )
            except Exception as e:
                print(f"Error saving conversation: {e}")
        
        return response


# Global chatbot instance
_chatbot_instance = None

def get_chatbot() -> Chatbot:
    """Get or create chatbot instance."""
    global _chatbot_instance
    if _chatbot_instance is None:
        _chatbot_instance = Chatbot()
    return _chatbot_instance
