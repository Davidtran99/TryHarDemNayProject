"""
Reranker module using BGE Reranker v2 M3 for improved document ranking.
Reduces top-8 results to top-3 most relevant chunks, cutting prompt size by ~40%.
"""
import logging
from typing import List, Any, Optional
import os

logger = logging.getLogger(__name__)

# Global reranker instance (lazy loaded)
_reranker = None
_reranker_model_name = None


def get_reranker(model_name: Optional[str] = None):
    """
    Get or initialize BGE Reranker model.
    
    Args:
        model_name: Model name (default: BAAI/bge-reranker-v2-m3)
    
    Returns:
        Reranker model instance or None if unavailable.
    """
    global _reranker, _reranker_model_name
    
    model_name = model_name or os.environ.get(
        "RERANKER_MODEL",
        "BAAI/bge-reranker-v2-m3"
    )
    
    # Return cached model if already loaded
    if _reranker is not None and _reranker_model_name == model_name:
        return _reranker
    
    # Try FlagEmbedding first (best performance)
    try:
        from FlagEmbedding import FlagReranker
        
        print(f"[RERANKER] Loading FlagEmbedding model: {model_name}", flush=True)
        logger.info("[RERANKER] Loading FlagEmbedding model: %s", model_name)
        
        _reranker = FlagReranker(model_name, use_fp16=False)  # Use FP32 for CPU compatibility
        _reranker_model_name = model_name
        
        print(f"[RERANKER] ✅ FlagEmbedding model loaded successfully", flush=True)
        logger.info("[RERANKER] ✅ FlagEmbedding model loaded successfully")
        
        return _reranker
    except ImportError:
        print("[RERANKER] ⚠️ FlagEmbedding not available, trying sentence-transformers CrossEncoder...", flush=True)
        logger.warning("[RERANKER] FlagEmbedding not available, trying CrossEncoder")
    except Exception as e:
        print(f"[RERANKER] ⚠️ FlagEmbedding failed: {e}, trying CrossEncoder...", flush=True)
        logger.warning("[RERANKER] FlagEmbedding failed: %s, trying CrossEncoder", e)
    
    # Fallback: Use sentence-transformers CrossEncoder (compatible with transformers 4.44.2)
    try:
        from sentence_transformers import CrossEncoder
        
        # Use a lightweight cross-encoder model compatible with transformers 4.44.2
        fallback_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        print(f"[RERANKER] Loading CrossEncoder fallback: {fallback_model}", flush=True)
        logger.info("[RERANKER] Loading CrossEncoder fallback: %s", fallback_model)
        
        # Set timeout for model download (30 seconds)
        import os
        os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "30")
        
        _reranker = CrossEncoder(fallback_model, max_length=512)
        _reranker_model_name = fallback_model
        
        print(f"[RERANKER] ✅ CrossEncoder loaded successfully", flush=True)
        logger.info("[RERANKER] ✅ CrossEncoder loaded successfully")
        
        return _reranker
    except ImportError:
        print(f"[RERANKER] ❌ sentence-transformers not installed. Install with: pip install sentence-transformers", flush=True)
        logger.error("[RERANKER] sentence-transformers not installed")
        return None
    except Exception as e:
        print(f"[RERANKER] ❌ Failed to load CrossEncoder fallback: {e}", flush=True)
        logger.error("[RERANKER] Failed to load CrossEncoder fallback: %s", e)
        return None


def rerank_documents(
    query: str,
    documents: List[Any],
    top_k: int = 3,
    model_name: Optional[str] = None
) -> List[Any]:
    """
    Rerank documents using BGE Reranker v2 M3.
    
    Args:
        query: Search query.
        documents: List of document objects (must have 'data' attribute with content).
        top_k: Number of top results to return (default: 3).
        model_name: Optional model name override.
    
    Returns:
        Top-k reranked documents.
    """
    if not documents or not query:
        return documents[:top_k]
    
    if len(documents) <= top_k:
        # No need to rerank if we already have <= top_k results
        return documents
    
    reranker = get_reranker(model_name)
    if reranker is None:
        # Fallback: return top-k by original score
        return documents[:top_k]
    
    try:
        # Prepare pairs for reranking: (query, document_text)
        pairs = []
        doc_objects = []
        
        for doc in documents:
            # Extract text from document
            doc_data = getattr(doc, "data", doc) if hasattr(doc, "data") else doc
            
            # Build text representation
            text_parts = []
            if hasattr(doc_data, "content"):
                text_parts.append(str(doc_data.content))
            if hasattr(doc_data, "section_title"):
                text_parts.append(str(doc_data.section_title))
            if hasattr(doc_data, "section_code"):
                text_parts.append(str(doc_data.section_code))
            
            # Fallback: try to get text from dict
            if not text_parts and isinstance(doc_data, dict):
                text_parts.append(str(doc_data.get("content", "")))
                text_parts.append(str(doc_data.get("section_title", "")))
            
            doc_text = " ".join(text_parts).strip()
            if doc_text:
                pairs.append((query, doc_text))
                doc_objects.append(doc)
        
        if not pairs:
            return documents[:top_k]
        
        # Rerank using cross-encoder
        print(f"[RERANKER] Reranking {len(pairs)} documents...", flush=True)
        logger.debug("[RERANKER] Reranking %d documents", len(pairs))
        
        # Handle different reranker types
        from FlagEmbedding import FlagReranker
        from sentence_transformers import CrossEncoder
        
        if isinstance(reranker, FlagReranker):
            # FlagReranker.compute_score returns list of scores for multiple pairs
            scores = reranker.compute_score(pairs, normalize=True)
            
            # Handle both single score (float) and list of scores
            if isinstance(scores, (int, float)):
                scored_docs = [(doc_objects[0], float(scores))]
            elif isinstance(scores, list):
                scored_docs = list(zip(doc_objects, scores))
            else:
                logger.warning("[RERANKER] Unexpected score type: %s", type(scores))
                return documents[:top_k]
        elif isinstance(reranker, CrossEncoder):
            # CrossEncoder.predict returns numpy array
            scores = reranker.predict(pairs)
            if hasattr(scores, 'tolist'):
                scores = scores.tolist()
            elif not isinstance(scores, list):
                scores = [float(scores)] if len(pairs) == 1 else list(scores)
            scored_docs = list(zip(doc_objects, scores))
        else:
            logger.warning("[RERANKER] Unknown reranker type: %s", type(reranker))
            return documents[:top_k]
        
        # Sort by score (descending)
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Return top-k
        reranked = [doc for doc, score in scored_docs[:top_k]]
        
        print(f"[RERANKER] ✅ Reranked to top-{top_k} (scores: {[f'{s:.3f}' for _, s in scored_docs[:top_k]]})", flush=True)
        logger.debug(
            "[RERANKER] ✅ Reranked to top-%d (scores: %s)",
            top_k,
            [f"{s:.3f}" for _, s in scored_docs[:top_k]]
        )
        
        return reranked
    
    except Exception as e:
        print(f"[RERANKER] ❌ Reranking failed: {e}, falling back to original order", flush=True)
        logger.error("[RERANKER] Reranking failed: %s", e, exc_info=True)
        return documents[:top_k]

