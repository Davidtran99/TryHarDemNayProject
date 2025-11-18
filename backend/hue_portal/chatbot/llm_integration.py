"""
LLM integration for natural answer generation.
Supports OpenAI GPT, Anthropic Claude, and local LLMs (Ollama).
"""
import os
import re
import json
from typing import List, Dict, Any, Optional
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional

# LLM Provider types
LLM_PROVIDER_OPENAI = "openai"
LLM_PROVIDER_ANTHROPIC = "anthropic"
LLM_PROVIDER_OLLAMA = "ollama"
LLM_PROVIDER_NONE = "none"

# Get provider from environment
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", LLM_PROVIDER_NONE).lower()


class LLMGenerator:
    """Generate natural language answers using LLMs."""
    
    def __init__(self, provider: Optional[str] = None):
        """
        Initialize LLM generator.
        
        Args:
            provider: LLM provider ('openai', 'anthropic', 'ollama', or None for auto-detect).
        """
        self.provider = provider or LLM_PROVIDER
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize LLM client based on provider."""
        if self.provider == LLM_PROVIDER_OPENAI:
            try:
                import openai
                api_key = os.environ.get("OPENAI_API_KEY")
                if api_key:
                    self.client = openai.OpenAI(api_key=api_key)
                    print("✅ OpenAI client initialized")
                else:
                    print("⚠️ OPENAI_API_KEY not found, OpenAI disabled")
            except ImportError:
                print("⚠️ openai package not installed, install with: pip install openai")
        
        elif self.provider == LLM_PROVIDER_ANTHROPIC:
            try:
                import anthropic
                api_key = os.environ.get("ANTHROPIC_API_KEY")
                if api_key:
                    self.client = anthropic.Anthropic(api_key=api_key)
                    print("✅ Anthropic client initialized")
                else:
                    print("⚠️ ANTHROPIC_API_KEY not found, Anthropic disabled")
            except ImportError:
                print("⚠️ anthropic package not installed, install with: pip install anthropic")
        
        elif self.provider == LLM_PROVIDER_OLLAMA:
            self.ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            print(f"✅ Ollama configured (base_url: {self.ollama_base_url})")
        
        else:
            print("ℹ️ No LLM provider configured, using template-based generation")
    
    def is_available(self) -> bool:
        """Check if LLM is available."""
        return self.client is not None or self.provider == LLM_PROVIDER_OLLAMA
    
    def generate_answer(
        self,
        query: str,
        context: Optional[List[Dict[str, Any]]] = None,
        documents: Optional[List[Any]] = None
    ) -> Optional[str]:
        """
        Generate natural language answer from documents.
        
        Args:
            query: User query.
            context: Optional conversation context.
            documents: Retrieved documents.
        
        Returns:
            Generated answer or None if LLM not available.
        """
        if not self.is_available():
            return None
        
        # Build prompt
        prompt = self._build_prompt(query, context, documents)
        
        try:
            if self.provider == LLM_PROVIDER_OPENAI:
                return self._generate_openai(prompt)
            elif self.provider == LLM_PROVIDER_ANTHROPIC:
                return self._generate_anthropic(prompt)
            elif self.provider == LLM_PROVIDER_OLLAMA:
                return self._generate_ollama(prompt)
        except Exception as e:
            print(f"Error generating answer with LLM: {e}")
            return None
    
    def _build_prompt(
        self,
        query: str,
        context: Optional[List[Dict[str, Any]]],
        documents: Optional[List[Any]]
    ) -> str:
        """Build prompt for LLM."""
        prompt_parts = [
            "Bạn là chatbot tư vấn của Công an Thừa Thiên Huế.",
            "Nhiệm vụ của bạn là trả lời câu hỏi của người dùng dựa trên thông tin được cung cấp.",
            "",
            f"Câu hỏi: {query}",
            ""
        ]
        
        if context:
            prompt_parts.append("Ngữ cảnh cuộc hội thoại:")
            for msg in context[-3:]:  # Last 3 messages
                role = "Người dùng" if msg.get("role") == "user" else "Bot"
                content = msg.get("content", "")
                prompt_parts.append(f"{role}: {content}")
            prompt_parts.append("")
        
        if documents:
            prompt_parts.append("Thông tin tham khảo:")
            for i, doc in enumerate(documents[:5], 1):
                # Extract relevant fields based on document type
                doc_text = self._format_document(doc)
                prompt_parts.append(f"{i}. {doc_text}")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "Hãy trả lời câu hỏi một cách tự nhiên, chính xác, và hữu ích dựa trên thông tin trên.",
            "Nếu không có thông tin phù hợp, hãy nói rõ và đề xuất cách tìm kiếm khác.",
            "Trả lời bằng tiếng Việt, ngắn gọn và dễ hiểu."
        ])
        
        return "\n".join(prompt_parts)
    
    def _format_document(self, doc: Any) -> str:
        """Format document for prompt."""
        doc_type = type(doc).__name__.lower()
        
        if "fine" in doc_type:
            parts = [f"Mức phạt: {getattr(doc, 'name', '')}"]
            if hasattr(doc, 'code') and doc.code:
                parts.append(f"Mã: {doc.code}")
            if hasattr(doc, 'min_fine') and hasattr(doc, 'max_fine'):
                if doc.min_fine and doc.max_fine:
                    parts.append(f"Số tiền: {doc.min_fine:,.0f} - {doc.max_fine:,.0f} VNĐ")
            return " | ".join(parts)
        
        elif "procedure" in doc_type:
            parts = [f"Thủ tục: {getattr(doc, 'title', '')}"]
            if hasattr(doc, 'dossier') and doc.dossier:
                parts.append(f"Hồ sơ: {doc.dossier}")
            if hasattr(doc, 'fee') and doc.fee:
                parts.append(f"Lệ phí: {doc.fee}")
            return " | ".join(parts)
        
        elif "office" in doc_type:
            parts = [f"Đơn vị: {getattr(doc, 'unit_name', '')}"]
            if hasattr(doc, 'address') and doc.address:
                parts.append(f"Địa chỉ: {doc.address}")
            if hasattr(doc, 'phone') and doc.phone:
                parts.append(f"Điện thoại: {doc.phone}")
            return " | ".join(parts)
        
        elif "advisory" in doc_type:
            parts = [f"Cảnh báo: {getattr(doc, 'title', '')}"]
            if hasattr(doc, 'summary') and doc.summary:
                parts.append(f"Nội dung: {doc.summary[:200]}")
            return " | ".join(parts)
        
        return str(doc)
    
    def _generate_openai(self, prompt: str) -> Optional[str]:
        """Generate answer using OpenAI."""
        if not self.client:
            return None
        
        try:
            response = self.client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
                messages=[
                    {"role": "system", "content": "Bạn là chatbot tư vấn chuyên nghiệp."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return None
    
    def _generate_anthropic(self, prompt: str) -> Optional[str]:
        """Generate answer using Anthropic Claude."""
        if not self.client:
            return None
        
        try:
            message = self.client.messages.create(
                model=os.environ.get("ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            print(f"Anthropic API error: {e}")
            return None
    
    def _generate_ollama(self, prompt: str) -> Optional[str]:
        """Generate answer using Ollama (local LLM)."""
        try:
            import requests
            model = os.environ.get("OLLAMA_MODEL", "llama2")
            
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("response")
            return None
        except Exception as e:
            print(f"Ollama API error: {e}")
            return None
    
    def summarize_context(self, messages: List[Dict[str, Any]], max_length: int = 200) -> str:
        """
        Summarize conversation context.
        
        Args:
            messages: List of conversation messages.
            max_length: Maximum summary length.
        
        Returns:
            Summary string.
        """
        if not messages:
            return ""
        
        # Simple summarization: extract key entities and intents
        intents = []
        entities = set()
        
        for msg in messages:
            if msg.get("intent"):
                intents.append(msg["intent"])
            if msg.get("entities"):
                for key, value in msg["entities"].items():
                    if isinstance(value, str):
                        entities.add(value)
                    elif isinstance(value, list):
                        entities.update(value)
        
        summary_parts = []
        if intents:
            unique_intents = list(set(intents))
            summary_parts.append(f"Chủ đề: {', '.join(unique_intents)}")
        if entities:
            summary_parts.append(f"Thông tin: {', '.join(list(entities)[:5])}")
        
        summary = ". ".join(summary_parts)
        return summary[:max_length] if len(summary) > max_length else summary
    
    def extract_entities_llm(self, query: str) -> Dict[str, Any]:
        """
        Extract entities using LLM.
        
        Args:
            query: User query.
        
        Returns:
            Dictionary of extracted entities.
        """
        if not self.is_available():
            return {}
        
        prompt = f"""
        Trích xuất các thực thể từ câu hỏi sau:
        "{query}"
        
        Các loại thực thể cần tìm:
        - fine_code: Mã vi phạm (V001, V002, ...)
        - fine_name: Tên vi phạm
        - procedure_name: Tên thủ tục
        - office_name: Tên đơn vị
        
        Trả lời dưới dạng JSON: {{"fine_code": "...", "fine_name": "...", ...}}
        Nếu không có, trả về {{}}.
        """
        
        try:
            if self.provider == LLM_PROVIDER_OPENAI:
                response = self._generate_openai(prompt)
            elif self.provider == LLM_PROVIDER_ANTHROPIC:
                response = self._generate_anthropic(prompt)
            elif self.provider == LLM_PROVIDER_OLLAMA:
                response = self._generate_ollama(prompt)
            else:
                return {}
            
            if response:
                # Try to extract JSON from response
                json_match = re.search(r'\{[^}]+\}', response)
                if json_match:
                    return json.loads(json_match.group())
        except Exception as e:
            print(f"Error extracting entities with LLM: {e}")
        
        return {}


# Global LLM generator instance
_llm_generator: Optional[LLMGenerator] = None

def get_llm_generator() -> Optional[LLMGenerator]:
    """Get or create LLM generator instance."""
    global _llm_generator
    if _llm_generator is None:
        _llm_generator = LLMGenerator()
    return _llm_generator if _llm_generator.is_available() else None

