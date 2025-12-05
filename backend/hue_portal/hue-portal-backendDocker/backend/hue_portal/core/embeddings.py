"""
Vector embeddings utilities for semantic search.
"""
import os
import threading
from typing import List, Optional, Union, Dict
import numpy as np
from pathlib import Path

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

# Available embedding models (ordered by preference for Vietnamese)
# Models are ordered from fastest to best quality
AVAILABLE_MODELS = {
    # Fast models (384 dim) - Good for production
    "paraphrase-multilingual": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",  # Fast, 384 dim
    
    # High quality models (768 dim) - Better accuracy
    "multilingual-mpnet": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",  # High quality, 768 dim, recommended
    "vietnamese-sbert": "keepitreal/vietnamese-sbert-v2",  # Vietnamese-specific (may require auth)
    
    # Very high quality models (1024+ dim) - Best accuracy but slower
    "multilingual-e5-large": "intfloat/multilingual-e5-large",  # Very high quality, 1024 dim, large model
    "multilingual-e5-base": "intfloat/multilingual-e5-base",  # High quality, 768 dim, balanced
    
    # Vietnamese-specific models (if available)
    "vietnamese-embedding": "dangvantuan/vietnamese-embedding",  # Vietnamese-specific (if available)
    "vietnamese-bi-encoder": "bkai-foundation-models/vietnamese-bi-encoder",  # Vietnamese bi-encoder (if available)
}

# Default embedding model for Vietnamese (can be overridden via env var)
# Use multilingual-e5-base as default for HF Space - good balance of quality and speed
# 768 dimensions, faster than e5-large (1024 dim), better quality than MiniLM (384 dim)
# Can be set via EMBEDDING_MODEL env var (supports both short names and full model paths)
# Examples:
#   - EMBEDDING_MODEL=multilingual-e5-base (uses short name)
#   - EMBEDDING_MODEL=intfloat/multilingual-e5-base (full path)
#   - EMBEDDING_MODEL=/path/to/local/model (local model path)
#   - EMBEDDING_MODEL=username/private-model (private HF model, requires HF_TOKEN)
DEFAULT_MODEL_NAME = os.environ.get(
    "EMBEDDING_MODEL",
    AVAILABLE_MODELS.get("multilingual-e5-base", "intfloat/multilingual-e5-base")
)
FALLBACK_MODEL_NAME = AVAILABLE_MODELS.get("paraphrase-multilingual", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# Thread-safe singleton for model caching
class EmbeddingModelManager:
    """Thread-safe singleton manager for embedding models."""

    _instance: Optional["EmbeddingModelManager"] = None
    _lock = threading.Lock()
    _model: Optional[SentenceTransformer] = None
    _model_name: Optional[str] = None
    _model_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_model(
        self,
        model_name: Optional[str] = None,
        force_reload: bool = False,
    ) -> Optional[SentenceTransformer]:
        """
        Get or load embedding model instance with thread-safe caching.
        
        Args:
            model_name: Name of the model to load.
            force_reload: Force reload model even if cached.
        
        Returns:
            SentenceTransformer instance or None if not available.
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            print(
                "Warning: sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
            return None
        
        resolved_model_name = model_name or DEFAULT_MODEL_NAME
        if resolved_model_name in AVAILABLE_MODELS:
            resolved_model_name = AVAILABLE_MODELS[resolved_model_name]
        
        if (
            not force_reload
            and self._model is not None
            and self._model_name == resolved_model_name
        ):
            return self._model
        
        with self._model_lock:
            if (
                not force_reload
                and self._model is not None
                and self._model_name == resolved_model_name
            ):
                return self._model
            
            return self._load_model(resolved_model_name)
    
    def _load_model(self, resolved_model_name: str) -> Optional[SentenceTransformer]:
        """Internal method to load model (must be called with lock held)."""
        try:
            print(f"Loading embedding model: {resolved_model_name}")
            
            model_path = Path(resolved_model_name)
            if model_path.exists() and model_path.is_dir():
                print(f"Loading local model from: {resolved_model_name}")
                self._model = SentenceTransformer(str(model_path))
            else:
                hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
                model_kwargs = {}
                if hf_token:
                    print(f"Using Hugging Face token for model: {resolved_model_name}")
                    model_kwargs["token"] = hf_token
                self._model = SentenceTransformer(resolved_model_name, **model_kwargs)
            
            self._model_name = resolved_model_name
            
            try:
                test_embedding = self._model.encode("test", show_progress_bar=False)
                dim = len(test_embedding)
                print(f"✅ Successfully loaded model: {resolved_model_name} (dimension: {dim})")
            except Exception:
                print(f"✅ Successfully loaded model: {resolved_model_name}")
            
            return self._model
        except Exception as exc:
            print(f"❌ Error loading model {resolved_model_name}: {exc}")
            if resolved_model_name != FALLBACK_MODEL_NAME:
                print(f"Trying fallback model: {FALLBACK_MODEL_NAME}")
                try:
                    self._model = SentenceTransformer(FALLBACK_MODEL_NAME)
                    self._model_name = FALLBACK_MODEL_NAME
                    test_embedding = self._model.encode("test", show_progress_bar=False)
                    dim = len(test_embedding)
                    print(
                        f"✅ Successfully loaded fallback model: {FALLBACK_MODEL_NAME} "
                        f"(dimension: {dim})"
                    )
                    return self._model
                except Exception as fallback_exc:
                    print(f"❌ Error loading fallback model: {fallback_exc}")
        return None


# Global manager instance
_embedding_manager = EmbeddingModelManager()


def get_embedding_model(model_name: Optional[str] = None, force_reload: bool = False) -> Optional[SentenceTransformer]:
    """
    Get or load embedding model instance with thread-safe caching.
    
    Args:
        model_name: Name of the model to load. Can be:
            - Full model name (e.g., "keepitreal/vietnamese-sbert-v2")
            - Short name (e.g., "vietnamese-sbert")
            - None (uses DEFAULT_MODEL_NAME from env or default)
        force_reload: Force reload model even if cached.
    
    Returns:
        SentenceTransformer instance or None if not available.
    """
    return _embedding_manager.get_model(model_name, force_reload)


def list_available_models() -> Dict[str, str]:
    """
    List all available embedding models.
    
    Returns:
        Dictionary mapping short names to full model names.
    """
    return AVAILABLE_MODELS.copy()


def compare_models(texts: List[str], model_names: Optional[List[str]] = None) -> Dict[str, Dict[str, float]]:
    """
    Compare different embedding models on sample texts.
    
    Args:
        texts: List of sample texts to test.
        model_names: List of model names to compare. If None, compares all available models.
    
    Returns:
        Dictionary with comparison results including:
        - dimension: Embedding dimension
        - encoding_time: Time to encode texts (seconds)
        - avg_similarity: Average similarity between texts
    """
    import time
    
    if model_names is None:
        model_names = list(AVAILABLE_MODELS.keys())
    
    results = {}
    
    for model_key in model_names:
        if model_key not in AVAILABLE_MODELS:
            continue
        
        model_name = AVAILABLE_MODELS[model_key]
        try:
            model = get_embedding_model(model_name, force_reload=True)
            if model is None:
                continue
            
            # Get dimension
            dim = get_embedding_dimension(model_name)
            
            # Measure encoding time
            start_time = time.time()
            embeddings = generate_embeddings_batch(texts, model=model)
            encoding_time = time.time() - start_time
            
            # Calculate average similarity
            similarities = []
            for i in range(len(embeddings)):
                for j in range(i + 1, len(embeddings)):
                    if embeddings[i] is not None and embeddings[j] is not None:
                        sim = cosine_similarity(embeddings[i], embeddings[j])
                        similarities.append(sim)
            
            avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
            
            results[model_key] = {
                "model_name": model_name,
                "dimension": dim,
                "encoding_time": encoding_time,
                "avg_similarity": avg_similarity
            }
        except Exception as e:
            print(f"Error comparing model {model_key}: {e}")
            results[model_key] = {"error": str(e)}
    
    return results


def generate_embedding(text: str, model: Optional[SentenceTransformer] = None) -> Optional[np.ndarray]:
    """
    Generate embedding vector for a single text.
    
    Args:
        text: Input text to embed.
        model: SentenceTransformer instance. If None, uses default model.
    
    Returns:
        Numpy array of embedding vector or None if error.
    """
    if not text or not text.strip():
        return None
    
    if model is None:
        model = get_embedding_model()
    
    if model is None:
        return None
    
    try:
        embedding = model.encode(text, normalize_embeddings=True, show_progress_bar=False)
        return embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None


def generate_embeddings_batch(texts: List[str], model: Optional[SentenceTransformer] = None, batch_size: int = 32) -> List[Optional[np.ndarray]]:
    """
    Generate embeddings for a batch of texts.
    
    Args:
        texts: List of input texts.
        model: SentenceTransformer instance. If None, uses default model.
        batch_size: Batch size for processing.
    
    Returns:
        List of numpy arrays (embeddings) or None for failed texts.
    """
    if not texts:
        return []
    
    if model is None:
        model = get_embedding_model()
    
    if model is None:
        return [None] * len(texts)
    
    try:
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        return [emb for emb in embeddings]
    except Exception as e:
        print(f"Error generating batch embeddings: {e}")
        return [None] * len(texts)


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vec1: First vector.
        vec2: Second vector.
    
    Returns:
        Cosine similarity score (0-1).
    """
    if vec1 is None or vec2 is None:
        return 0.0
    
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


def get_embedding_dimension(model_name: Optional[str] = None) -> int:
    """
    Get embedding dimension for a model.
    
    Args:
        model_name: Model name. If None, uses default.
    
    Returns:
        Embedding dimension or 0 if unknown.
    """
    model = get_embedding_model(model_name)
    if model is None:
        return 0
    
    # Get dimension by encoding a dummy text
    try:
        dummy_embedding = model.encode("test", show_progress_bar=False)
        return len(dummy_embedding)
    except Exception:
        return 0

