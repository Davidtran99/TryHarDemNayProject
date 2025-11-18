"""
Vector embeddings utilities for semantic search.
"""
import os
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
AVAILABLE_MODELS = {
    "vietnamese-sbert": "keepitreal/vietnamese-sbert-v2",  # Vietnamese-specific, good quality
    "multilingual-e5": "intfloat/multilingual-e5-large",  # Large, high quality, multilingual
    "paraphrase-multilingual": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",  # Fast, good quality
    "multilingual-mpnet": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",  # High quality, slower
}

# Default embedding model for Vietnamese (can be overridden via env var)
DEFAULT_MODEL_NAME = os.environ.get(
    "EMBEDDING_MODEL",
    AVAILABLE_MODELS.get("vietnamese-sbert", "keepitreal/vietnamese-sbert-v2")
)
FALLBACK_MODEL_NAME = AVAILABLE_MODELS.get("paraphrase-multilingual", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# Cache for model instance
_model_cache: Optional[SentenceTransformer] = None
_cached_model_name: Optional[str] = None


def get_embedding_model(model_name: Optional[str] = None, force_reload: bool = False) -> Optional[SentenceTransformer]:
    """
    Get or load embedding model instance.
    
    Args:
        model_name: Name of the model to load. Can be:
            - Full model name (e.g., "keepitreal/vietnamese-sbert-v2")
            - Short name (e.g., "vietnamese-sbert")
            - None (uses DEFAULT_MODEL_NAME from env or default)
        force_reload: Force reload model even if cached.
    
    Returns:
        SentenceTransformer instance or None if not available.
    """
    global _model_cache, _cached_model_name
    
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        print("Warning: sentence-transformers not installed. Install with: pip install sentence-transformers")
        return None
    
    # Resolve model name (check if it's a short name)
    resolved_model_name = model_name or DEFAULT_MODEL_NAME
    if resolved_model_name in AVAILABLE_MODELS:
        resolved_model_name = AVAILABLE_MODELS[resolved_model_name]
    
    # Return cached model if same model and not forcing reload
    if _model_cache is not None and _cached_model_name == resolved_model_name and not force_reload:
        return _model_cache
    
    # Load new model
    try:
        print(f"Loading embedding model: {resolved_model_name}")
        _model_cache = SentenceTransformer(resolved_model_name)
        _cached_model_name = resolved_model_name
        print(f"✅ Successfully loaded model: {resolved_model_name}")
        return _model_cache
    except Exception as e:
        print(f"❌ Error loading model {resolved_model_name}: {e}")
        if resolved_model_name != FALLBACK_MODEL_NAME:
            print(f"Trying fallback model: {FALLBACK_MODEL_NAME}")
            try:
                _model_cache = SentenceTransformer(FALLBACK_MODEL_NAME)
                _cached_model_name = FALLBACK_MODEL_NAME
                print(f"✅ Successfully loaded fallback model: {FALLBACK_MODEL_NAME}")
                return _model_cache
            except Exception as e2:
                print(f"❌ Error loading fallback model: {e2}")
        return None


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

