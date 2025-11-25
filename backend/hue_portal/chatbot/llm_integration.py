"""
LLM integration for natural answer generation.
Supports OpenAI GPT, Anthropic Claude, Ollama, Hugging Face Inference API, Local Hugging Face models, and API mode.
"""
import os
import re
import json
import sys
import traceback
import logging
import time
from typing import List, Dict, Any, Optional
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional

logger = logging.getLogger(__name__)

# Import download progress tracker (optional)
try:
    from .download_progress import get_progress_tracker, DownloadProgress
    PROGRESS_TRACKER_AVAILABLE = True
except ImportError:
    PROGRESS_TRACKER_AVAILABLE = False
    logger.warning("Download progress tracker not available")

# LLM Provider types
LLM_PROVIDER_OPENAI = "openai"
LLM_PROVIDER_ANTHROPIC = "anthropic"
LLM_PROVIDER_OLLAMA = "ollama"
LLM_PROVIDER_HUGGINGFACE = "huggingface"  # Hugging Face Inference API
LLM_PROVIDER_LOCAL = "local"  # Local Hugging Face Transformers model
LLM_PROVIDER_API = "api"  # API mode - call HF Spaces API
LLM_PROVIDER_NONE = "none"

# Get provider from environment (default to local Qwen if none provided)
DEFAULT_LLM_PROVIDER = os.environ.get("DEFAULT_LLM_PROVIDER", LLM_PROVIDER_LOCAL).lower()
env_provider = os.environ.get("LLM_PROVIDER", "").strip().lower()
LLM_PROVIDER = env_provider or DEFAULT_LLM_PROVIDER


class LLMGenerator:
    """Generate natural language answers using LLMs."""
    
    def __init__(self, provider: Optional[str] = None):
        """
        Initialize LLM generator.
        
        Args:
            provider: LLM provider ('openai', 'anthropic', 'ollama', 'local', 'huggingface', 'api', or None for auto-detect).
        """
        self.provider = provider or LLM_PROVIDER
        self.client = None
        self.local_model = None
        self.local_tokenizer = None
        self.api_base_url = None
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
            self.ollama_model = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
            print(f"✅ Ollama configured (base_url: {self.ollama_base_url}, model: {self.ollama_model})")
        
        elif self.provider == LLM_PROVIDER_HUGGINGFACE:
            self.hf_api_key = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY")
            self.hf_model = os.environ.get("HF_MODEL", "Qwen/Qwen2.5-7B-Instruct")
            if self.hf_api_key:
                print(f"✅ Hugging Face API configured (model: {self.hf_model})")
            else:
                print("⚠️ HF_TOKEN not found, Hugging Face may have rate limits")
        
        elif self.provider == LLM_PROVIDER_API:
            # API mode - call HF Spaces API
            self.api_base_url = os.environ.get(
                "HF_API_BASE_URL", 
                "https://davidtran999-hue-portal-backend.hf.space/api"
            )
            print(f"✅ API mode configured (base_url: {self.api_base_url})")
        
        elif self.provider == LLM_PROVIDER_LOCAL:
            self._initialize_local_model()
        
        else:
            print("ℹ️ No LLM provider configured, using template-based generation")
    
    def _initialize_local_model(self):
        """Initialize local Hugging Face Transformers model."""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            
            # Default to Qwen 2.5 7B with 8-bit quantization (fits in GPU RAM)
            model_path = os.environ.get("LOCAL_MODEL_PATH", "Qwen/Qwen2.5-7B-Instruct")
            device = os.environ.get("LOCAL_MODEL_DEVICE", "auto")  # auto, cpu, cuda
            
            print(f"[LLM] Loading local model: {model_path}", flush=True)
            logger.info(f"[LLM] Loading local model: {model_path}")
            
            # Determine device
            if device == "auto":
                device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # Start cache monitoring for download progress (optional)
            try:
                from .cache_monitor import get_cache_monitor
                monitor = get_cache_monitor()
                monitor.start_monitoring(model_path, interval=2.0)
                print(f"[LLM] 📊 Started cache monitoring for {model_path}", flush=True)
                logger.info(f"[LLM] 📊 Started cache monitoring for {model_path}")
            except Exception as e:
                logger.warning(f"Could not start cache monitoring: {e}")
            
            # Load tokenizer
            print("[LLM] Loading tokenizer...", flush=True)
            logger.info("[LLM] Loading tokenizer...")
            try:
                self.local_tokenizer = AutoTokenizer.from_pretrained(
                    model_path,
                    trust_remote_code=True
                )
                print("[LLM] ✅ Tokenizer loaded successfully", flush=True)
                logger.info("[LLM] ✅ Tokenizer loaded successfully")
            except Exception as tokenizer_err:
                error_trace = traceback.format_exc()
                print(f"[LLM] ❌ Tokenizer load error: {tokenizer_err}", flush=True)
                print(f"[LLM] ❌ Tokenizer trace: {error_trace}", flush=True)
                logger.error(f"[LLM] ❌ Tokenizer load error: {tokenizer_err}\n{error_trace}")
                print(f"[LLM] ❌ ERROR: {type(tokenizer_err).__name__}: {str(tokenizer_err)}", file=sys.stderr, flush=True)
                traceback.print_exc(file=sys.stderr)
                raise
            
            # Load model with optional quantization and fallback mechanism
            print(f"[LLM] Loading model to {device}...", flush=True)
            logger.info(f"[LLM] Loading model to {device}...")
            
            # Check for quantization config
            # Default to 8-bit for 7B (better thinking), 4-bit for larger models
            default_8bit = "7b" in model_path.lower() or "7B" in model_path
            default_4bit = ("32b" in model_path.lower() or "32B" in model_path or "14b" in model_path.lower() or "14B" in model_path) and not default_8bit
            
            # Check environment variable for explicit quantization preference
            quantization_pref = os.environ.get("LOCAL_MODEL_QUANTIZATION", "").lower()
            if quantization_pref == "4bit":
                use_8bit = False
                use_4bit = True
            elif quantization_pref == "8bit":
                use_8bit = True
                use_4bit = False
            elif quantization_pref == "none":
                use_8bit = False
                use_4bit = False
            else:
                # Use defaults based on model size
                use_8bit = os.environ.get("LOCAL_MODEL_8BIT", "true" if default_8bit else "false").lower() == "true"
                use_4bit = os.environ.get("LOCAL_MODEL_4BIT", "true" if default_4bit else "false").lower() == "true"
            
            # Try loading with fallback: 8-bit → 4-bit → float16
            model_loaded = False
            quantization_attempts = []
            
            if device == "cuda":
                # Attempt 1: Try 8-bit quantization (if requested)
                if use_8bit:
                    quantization_attempts.append(("8-bit", True, False))
                
                # Attempt 2: Try 4-bit quantization (if 8-bit fails or not requested)
                if use_4bit or (use_8bit and not model_loaded):
                    quantization_attempts.append(("4-bit", False, True))
                
                # Attempt 3: Fallback to float16 (no quantization)
                quantization_attempts.append(("float16", False, False))
            else:
                # CPU: only float32
                quantization_attempts.append(("float32", False, False))
            
            last_error = None
            for attempt_name, try_8bit, try_4bit in quantization_attempts:
                if model_loaded:
                    break
                
                try:
                    load_kwargs = {
                        "trust_remote_code": True,
                        "low_cpu_mem_usage": True,
                    }
                    
                    if device == "cuda":
                        load_kwargs["device_map"] = "auto"
                        
                        if try_4bit:
                            # Check if bitsandbytes is available
                            try:
                                import bitsandbytes as bnb
                                from transformers import BitsAndBytesConfig
                                load_kwargs["quantization_config"] = BitsAndBytesConfig(
                                    load_in_4bit=True,
                                    bnb_4bit_compute_dtype=torch.float16
                                )
                                print(f"[LLM] Attempting to load with 4-bit quantization (~4-5GB VRAM for 7B)", flush=True)
                            except ImportError:
                                print(f"[LLM] ⚠️ bitsandbytes not available, skipping 4-bit quantization", flush=True)
                                raise ImportError("bitsandbytes not available")
                        elif try_8bit:
                            from transformers import BitsAndBytesConfig
                            # Fixed: Remove CPU offload to avoid Int8Params compatibility issue
                            load_kwargs["quantization_config"] = BitsAndBytesConfig(
                                load_in_8bit=True,
                                llm_int8_threshold=6.0
                                # Removed: llm_int8_enable_fp32_cpu_offload=True (causes compatibility issues)
                            )
                            # Removed: max_memory override - let accelerate handle it automatically
                            print(f"[LLM] Attempting to load with 8-bit quantization (~7GB VRAM for 7B)", flush=True)
                        else:
                            load_kwargs["torch_dtype"] = torch.float16
                            print(f"[LLM] Attempting to load with float16 (no quantization)", flush=True)
                    else:
                        load_kwargs["torch_dtype"] = torch.float32
                        print(f"[LLM] Attempting to load with float32 (CPU)", flush=True)
                    
                    # Load model
                    self.local_model = AutoModelForCausalLM.from_pretrained(
                        model_path,
                        **load_kwargs
                    )
                    
                    # Stop cache monitoring (download complete)
                    try:
                        from .cache_monitor import get_cache_monitor
                        monitor = get_cache_monitor()
                        monitor.stop_monitoring(model_path)
                        print(f"[LLM] ✅ Model download complete, stopped monitoring", flush=True)
                    except:
                        pass
                    
                    print(f"[LLM] ✅ Model loaded successfully with {attempt_name} quantization", flush=True)
                    logger.info(f"[LLM] ✅ Model loaded successfully with {attempt_name} quantization")
                    
                    # Optional: Compile model for faster inference (PyTorch 2.0+)
                    try:
                        if hasattr(torch, "compile") and device == "cuda":
                            print(f"[LLM] ⚡ Compiling model for faster inference...", flush=True)
                            self.local_model = torch.compile(self.local_model, mode="reduce-overhead")
                            print(f"[LLM] ✅ Model compiled successfully", flush=True)
                            logger.info(f"[LLM] ✅ Model compiled for faster inference")
                    except Exception as compile_err:
                        print(f"[LLM] ⚠️ Model compilation skipped: {compile_err}", flush=True)
                        # Continue without compilation
                    
                    model_loaded = True
                    
                except Exception as model_load_err:
                    last_error = model_load_err
                    error_trace = traceback.format_exc()
                    print(f"[LLM] ⚠️ Failed to load with {attempt_name}: {model_load_err}", flush=True)
                    logger.warning(f"[LLM] ⚠️ Failed to load with {attempt_name}: {model_load_err}")
                    
                    # If this was the last attempt, raise the error
                    if attempt_name == quantization_attempts[-1][0]:
                        print(f"[LLM] ❌ All quantization attempts failed. Last error: {model_load_err}", flush=True)
                        print(f"[LLM] ❌ Model load trace: {error_trace}", flush=True)
                        logger.error(f"[LLM] ❌ Model load error: {model_load_err}\n{error_trace}")
                        print(f"[LLM] ❌ ERROR: {type(model_load_err).__name__}: {str(model_load_err)}", file=sys.stderr, flush=True)
                        traceback.print_exc(file=sys.stderr)
                        raise
                    else:
                        # Try next quantization method
                        print(f"[LLM] 🔄 Falling back to next quantization method...", flush=True)
                        continue
            
            if not model_loaded:
                raise RuntimeError("Failed to load model with any quantization method")
            
            if device == "cpu":
                try:
                    self.local_model = self.local_model.to(device)
                    print(f"[LLM] ✅ Model moved to {device}", flush=True)
                    logger.info(f"[LLM] ✅ Model moved to {device}")
                except Exception as move_err:
                    error_trace = traceback.format_exc()
                    print(f"[LLM] ❌ Model move error: {move_err}", flush=True)
                    logger.error(f"[LLM] ❌ Model move error: {move_err}\n{error_trace}")
                    print(f"[LLM] ❌ ERROR: {type(move_err).__name__}: {str(move_err)}", file=sys.stderr, flush=True)
                    traceback.print_exc(file=sys.stderr)
            
            self.local_model.eval()  # Set to evaluation mode
            print(f"[LLM] ✅ Local model loaded successfully on {device}", flush=True)
            logger.info(f"[LLM] ✅ Local model loaded successfully on {device}")
            
        except ImportError as import_err:
            error_msg = "transformers package not installed, install with: pip install transformers torch"
            print(f"[LLM] ⚠️ {error_msg}", flush=True)
            logger.warning(f"[LLM] ⚠️ {error_msg}")
            print(f"[LLM] ❌ ImportError: {import_err}", file=sys.stderr, flush=True)
            self.local_model = None
            self.local_tokenizer = None
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"[LLM] ❌ Error loading local model: {e}", flush=True)
            print(f"[LLM] ❌ Full trace: {error_trace}", flush=True)
            logger.error(f"[LLM] ❌ Error loading local model: {e}\n{error_trace}")
            print(f"[LLM] ❌ ERROR: {type(e).__name__}: {str(e)}", file=sys.stderr, flush=True)
            traceback.print_exc(file=sys.stderr)
            print("[LLM] 💡 Tip: Use smaller models like Qwen/Qwen2.5-1.5B-Instruct or Qwen/Qwen2.5-0.5B-Instruct", flush=True)
            self.local_model = None
            self.local_tokenizer = None
    
    def is_available(self) -> bool:
        """Check if LLM is available."""
        return (
            self.client is not None or 
            self.provider == LLM_PROVIDER_OLLAMA or
            self.provider == LLM_PROVIDER_HUGGINGFACE or
            self.provider == LLM_PROVIDER_API or
            (self.provider == LLM_PROVIDER_LOCAL and self.local_model is not None)
        )
    
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
            print(f"[LLM] Generating answer with provider: {self.provider}", flush=True)
            logger.info(f"[LLM] Generating answer with provider: {self.provider}")
            
            if self.provider == LLM_PROVIDER_OPENAI:
                result = self._generate_openai(prompt)
            elif self.provider == LLM_PROVIDER_ANTHROPIC:
                result = self._generate_anthropic(prompt)
            elif self.provider == LLM_PROVIDER_OLLAMA:
                result = self._generate_ollama(prompt)
            elif self.provider == LLM_PROVIDER_HUGGINGFACE:
                result = self._generate_huggingface(prompt)
            elif self.provider == LLM_PROVIDER_LOCAL:
                result = self._generate_local(prompt)
            elif self.provider == LLM_PROVIDER_API:
                # For API mode, send the full prompt (with documents) as the message
                # This ensures HF Spaces receives all context from retrieved documents
                result = self._generate_api(prompt, context)
            else:
                result = None
            
            if result:
                print(f"[LLM] ✅ Answer generated successfully (length: {len(result)})", flush=True)
                logger.info(f"[LLM] ✅ Answer generated successfully (length: {len(result)})")
            else:
                print(f"[LLM] ⚠️ No answer generated", flush=True)
                logger.warning("[LLM] ⚠️ No answer generated")
            
            return result
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"[LLM] ❌ Error generating answer: {e}", flush=True)
            print(f"[LLM] ❌ Full trace: {error_trace}", flush=True)
            logger.error(f"[LLM] ❌ Error generating answer: {e}\n{error_trace}")
            print(f"[LLM] ❌ ERROR: {type(e).__name__}: {str(e)}", file=sys.stderr, flush=True)
            traceback.print_exc(file=sys.stderr)
            return None
    
    def _build_prompt(
        self,
        query: str,
        context: Optional[List[Dict[str, Any]]],
        documents: Optional[List[Any]]
    ) -> str:
        """Build prompt for LLM."""
        prompt_parts = [
            "Bạn là chatbot tư vấn pháp lý của Công an Thừa Thiên Huế.",
            "Nhiệm vụ: Trả lời câu hỏi của người dùng dựa trên các văn bản pháp luật và quy định được cung cấp.",
            "",
            f"Câu hỏi của người dùng: {query}",
            ""
        ]
        
        if context:
            prompt_parts.append("Ngữ cảnh cuộc hội thoại trước đó:")
            for msg in context[-3:]:  # Last 3 messages
                role = "Người dùng" if msg.get("role") == "user" else "Bot"
                content = msg.get("content", "")
                prompt_parts.append(f"{role}: {content}")
            prompt_parts.append("")
        
        if documents:
            prompt_parts.append("Các văn bản/quy định liên quan:")
            for i, doc in enumerate(documents[:5], 1):
                # Extract relevant fields based on document type
                doc_text = self._format_document(doc)
                prompt_parts.append(f"{i}. {doc_text}")
            prompt_parts.append("")
            # If documents exist, require strict adherence
            prompt_parts.extend([
                "Yêu cầu QUAN TRỌNG:",
                "- CHỈ trả lời dựa trên thông tin trong 'Các văn bản/quy định liên quan' ở trên",
                "- KHÔNG được tự tạo hoặc suy đoán thông tin không có trong tài liệu",
                "- Nếu thông tin không đủ để trả lời, hãy nói rõ: 'Thông tin trong cơ sở dữ liệu chưa đủ để trả lời câu hỏi này'",
                "- Nếu có mức phạt, phải ghi rõ số tiền (ví dụ: 200.000 - 400.000 VNĐ)",
                "- Nếu có điều khoản, ghi rõ mã điều (ví dụ: Điều 5, Điều 10)",
                "- Nếu có thủ tục, ghi rõ hồ sơ, lệ phí, thời hạn",
                "- Trả lời bằng tiếng Việt, ngắn gọn, dễ hiểu",
                "",
                "Trả lời:"
            ])
        else:
            # No documents - allow general conversation
            prompt_parts.extend([
                "Yêu cầu:",
                "- Trả lời câu hỏi một cách tự nhiên và hữu ích như một chatbot AI thông thường",
                "- Nếu câu hỏi liên quan đến pháp luật, thủ tục, mức phạt nhưng không có thông tin trong cơ sở dữ liệu, hãy nói: 'Tôi không tìm thấy thông tin này trong cơ sở dữ liệu. Bạn có thể liên hệ trực tiếp với Công an Thừa Thiên Huế để được tư vấn chi tiết hơn.'",
                "- Trả lời bằng tiếng Việt, thân thiện, ngắn gọn, dễ hiểu",
                "",
                "Trả lời:"
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
        
        elif "legalsection" in doc_type or "legal" in doc_type:
            parts = []
            if hasattr(doc, 'section_code') and doc.section_code:
                parts.append(f"Điều khoản: {doc.section_code}")
            if hasattr(doc, 'section_title') and doc.section_title:
                parts.append(f"Tiêu đề: {doc.section_title}")
            if hasattr(doc, 'document') and doc.document:
                doc_obj = doc.document
                if hasattr(doc_obj, 'title'):
                    parts.append(f"Văn bản: {doc_obj.title}")
                if hasattr(doc_obj, 'code'):
                    parts.append(f"Mã văn bản: {doc_obj.code}")
            if hasattr(doc, 'content') and doc.content:
                # Truncate content to 300 chars for prompt
                content_short = doc.content[:300] + "..." if len(doc.content) > 300 else doc.content
                parts.append(f"Nội dung: {content_short}")
            return " | ".join(parts) if parts else str(doc)
        
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
                model=os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
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
            model = getattr(self, 'ollama_model', os.environ.get("OLLAMA_MODEL", "qwen2.5:7b"))
            
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 500
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json().get("response")
            return None
        except Exception as e:
            print(f"Ollama API error: {e}")
            return None
    
    def _generate_huggingface(self, prompt: str) -> Optional[str]:
        """Generate answer using Hugging Face Inference API."""
        try:
            import requests
            
            api_url = f"https://api-inference.huggingface.co/models/{self.hf_model}"
            headers = {}
            if hasattr(self, 'hf_api_key') and self.hf_api_key:
                headers["Authorization"] = f"Bearer {self.hf_api_key}"
            
            response = requests.post(
                api_url,
                headers=headers,
                json={
                    "inputs": prompt,
                    "parameters": {
                        "temperature": 0.7,
                        "max_new_tokens": 500,
                        "return_full_text": False
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get("generated_text", "")
                elif isinstance(result, dict):
                    return result.get("generated_text", "")
            elif response.status_code == 503:
                # Model is loading, wait and retry
                print("⚠️ Model is loading, please wait...")
                return None
            else:
                print(f"Hugging Face API error: {response.status_code} - {response.text}")
            return None
        except Exception as e:
            print(f"Hugging Face API error: {e}")
            return None
    
    def _generate_local(self, prompt: str) -> Optional[str]:
        """Generate answer using local Hugging Face Transformers model."""
        if self.local_model is None or self.local_tokenizer is None:
            return None
        
        try:
            import torch
            
            # Format prompt for Qwen models
            messages = [
                {"role": "system", "content": "Bạn là chatbot tư vấn chuyên nghiệp."},
                {"role": "user", "content": prompt}
            ]
            
            # Apply chat template if available
            if hasattr(self.local_tokenizer, "apply_chat_template"):
                text = self.local_tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True
                )
            else:
                text = prompt
            
            # Tokenize
            inputs = self.local_tokenizer(text, return_tensors="pt")
            
            # Move to device
            device = next(self.local_model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}
            
            # Generate with optimized parameters for faster inference
            with torch.no_grad():
                # Use greedy decoding for faster generation (can switch to sampling if needed)
                outputs = self.local_model.generate(
                    **inputs,
                    max_new_tokens=150,  # Reduced from 500 for faster generation
                    temperature=0.6,  # Lower temperature for faster, more deterministic output
                    top_p=0.85,  # Slightly lower top_p
                    do_sample=True,
                    use_cache=True,  # Enable KV cache for faster generation
                    pad_token_id=self.local_tokenizer.eos_token_id,
                    repetition_penalty=1.1,  # Prevent repetition
                    early_stopping=True  # Stop early if EOS token is generated
                )
            
            # Decode
            generated_text = self.local_tokenizer.decode(
                outputs[0][inputs["input_ids"].shape[1]:],
                skip_special_tokens=True
            )
            
            return generated_text.strip()
            
        except TypeError as e:
            # Check for Int8Params compatibility error
            if "_is_hf_initialized" in str(e) or "Int8Params" in str(e):
                error_msg = (
                    f"[LLM] ❌ Int8Params compatibility error: {e}\n"
                    f"[LLM] 💡 This error occurs when using 8-bit quantization with incompatible library versions.\n"
                    f"[LLM] 💡 Solutions:\n"
                    f"[LLM]   1. Set LOCAL_MODEL_QUANTIZATION=4bit to use 4-bit quantization instead\n"
                    f"[LLM]   2. Set LOCAL_MODEL_QUANTIZATION=none to disable quantization\n"
                    f"[LLM]   3. Use API mode (LLM_PROVIDER=api) to avoid local model issues\n"
                    f"[LLM]   4. Use a smaller model like Qwen/Qwen2.5-1.5B-Instruct"
                )
                print(error_msg, flush=True)
                logger.error(f"[LLM] ❌ Int8Params compatibility error: {e}")
                print(f"[LLM] ❌ ERROR: {type(e).__name__}: {str(e)}", file=sys.stderr, flush=True)
                return None
            else:
                # Other TypeError, re-raise to be caught by general handler
                raise
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"[LLM] ❌ Local model generation error: {e}", flush=True)
            print(f"[LLM] ❌ Full trace: {error_trace}", flush=True)
            logger.error(f"[LLM] ❌ Local model generation error: {e}\n{error_trace}")
            print(f"[LLM] ❌ ERROR: {type(e).__name__}: {str(e)}", file=sys.stderr, flush=True)
            traceback.print_exc(file=sys.stderr)
            return None
    
    def _generate_api(self, prompt: str, context: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
        """Generate answer by calling HF Spaces API.
        
        Args:
            prompt: Full prompt including query and documents context.
            context: Optional conversation context (not used in API mode, handled by HF Spaces).
        """
        if not self.api_base_url:
            return None
        
        try:
            import requests
            
            # Prepare request payload
            # Send the full prompt (with documents) as the message to HF Spaces
            # This ensures HF Spaces receives all context from retrieved documents
            payload = {
                "message": prompt,
                "reset_session": False
            }
            
            # Only add session_id if we have a valid session context
            # For now, we'll omit it and let the API generate a new one
            
            # Add context if available (API may support this in future)
            # For now, context is handled by the API internally
            
            # Call API endpoint
            api_url = f"{self.api_base_url}/chatbot/chat/"
            print(f"[LLM] 🔗 Calling API: {api_url}", flush=True)
            print(f"[LLM] 📤 Payload: {payload}", flush=True)
            
            response = requests.post(
                api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            
            print(f"[LLM] 📥 Response status: {response.status_code}", flush=True)
            print(f"[LLM] 📥 Response headers: {dict(response.headers)}", flush=True)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"[LLM] 📥 Response JSON: {result}", flush=True)
                    # Extract message from response
                    if isinstance(result, dict):
                        message = result.get("message", None)
                        if message:
                            print(f"[LLM] ✅ Got message from API (length: {len(message)})", flush=True)
                        return message
                    else:
                        print(f"[LLM] ⚠️ Response is not a dict: {type(result)}", flush=True)
                        return None
                except ValueError as e:
                    print(f"[LLM] ❌ JSON decode error: {e}", flush=True)
                    print(f"[LLM] ❌ Response text: {response.text[:500]}", flush=True)
                    return None
            elif response.status_code == 503:
                # Service unavailable - model might be loading
                print("[LLM] ⚠️ API service is loading, please wait...", flush=True)
                return None
            else:
                print(f"[LLM] ❌ API error: {response.status_code} - {response.text[:500]}", flush=True)
                return None
        except requests.exceptions.Timeout:
            print("[LLM] ❌ API request timeout")
            return None
        except requests.exceptions.ConnectionError as e:
            print(f"[LLM] ❌ API connection error: {e}")
            return None
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"[LLM] ❌ API mode error: {e}", flush=True)
            print(f"[LLM] ❌ Full trace: {error_trace}", flush=True)
            logger.error(f"[LLM] ❌ API mode error: {e}\n{error_trace}")
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
            elif self.provider == LLM_PROVIDER_HUGGINGFACE:
                response = self._generate_huggingface(prompt)
            elif self.provider == LLM_PROVIDER_LOCAL:
                response = self._generate_local(prompt)
            elif self.provider == LLM_PROVIDER_API:
                # For API mode, we can't extract entities directly
                # Return empty dict
                return {}
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
_last_provider: Optional[str] = None

def get_llm_generator() -> Optional[LLMGenerator]:
    """Get or create LLM generator instance.
    
    Recreates instance if provider changed (e.g., from local to api).
    """
    global _llm_generator, _last_provider
    
    # Get current provider from env
    current_provider = os.environ.get("LLM_PROVIDER", LLM_PROVIDER_NONE).lower()
    
    # Recreate if provider changed or instance doesn't exist
    if _llm_generator is None or _last_provider != current_provider:
        _llm_generator = LLMGenerator()
        _last_provider = current_provider
        print(f"[LLM] 🔄 Recreated LLM generator with provider: {current_provider}", flush=True)
    
    return _llm_generator if _llm_generator.is_available() else None
