"""
Pure Semantic Search - 100% vector search with multi-query support.

This module implements pure semantic search (no BM25) which is the recommended
approach when using Query Rewrite Strategy + BGE-M3. All top systems have moved
away from hybrid search (BM25 + Vector) to pure semantic search since Oct 2025.
"""
import logging
from typing import List, Tuple, Optional, Dict, Any, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.db.models import QuerySet

from .embeddings import (
    get_embedding_model,
    generate_embedding,
    cosine_similarity
)
from .embedding_utils import load_embedding

logger = logging.getLogger(__name__)

# Minimum vector score threshold
DEFAULT_MIN_VECTOR_SCORE = 0.1


def get_vector_scores(
    queryset: QuerySet,
    query: str,
    top_k: int = 20
) -> List[Tuple[Any, float]]:
    """
    Get vector similarity scores for queryset.
    
    This is extracted from hybrid_search.py for use in pure semantic search.
    
    Args:
        queryset: Django QuerySet to search.
        query: Search query string.
        top_k: Maximum number of results.
    
    Returns:
        List of (object, vector_score) tuples.
    """
    if not query or not query.strip():
        return []
    
    # Generate query embedding
    model = get_embedding_model()
    if model is None:
        return []
    
    query_embedding = generate_embedding(query, model=model)
    if query_embedding is None:
        return []
    
    # Get all objects with embeddings
    all_objects = list(queryset)
    if not all_objects:
        return []
    
    # Check dimension compatibility first
    query_dim = len(query_embedding)
    dimension_mismatch = False
    
    # Calculate similarities
    scores = []
    for obj in all_objects:
        obj_embedding = load_embedding(obj)
        if obj_embedding is not None:
            obj_dim = len(obj_embedding)
            if obj_dim != query_dim:
                # Dimension mismatch - skip vector search for this object
                if not dimension_mismatch:
                    logger.warning(
                        f"Dimension mismatch: query={query_dim}, stored={obj_dim}. Skipping vector search."
                    )
                    dimension_mismatch = True
                continue
            similarity = cosine_similarity(query_embedding, obj_embedding)
            if similarity >= DEFAULT_MIN_VECTOR_SCORE:
                scores.append((obj, similarity))
    
    # If dimension mismatch detected, return empty
    if dimension_mismatch and not scores:
        return []
    
    # Sort by score descending
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_k * 2]  # Get more for merging with other queries


def calculate_exact_match_boost(obj: Any, query: str, text_fields: List[str]) -> float:
    """
    Calculate boost score for exact keyword matches in title/name fields.
    
    This ensures exact matches are prioritized even in pure semantic search.
    
    Args:
        obj: Django model instance.
        query: Search query string.
        text_fields: List of field names to check (first 2 are usually title/name).
    
    Returns:
        Boost score (0.0 to 1.0).
    """
    if not query or not text_fields:
        return 0.0
    
    query_lower = query.lower().strip()
    # Extract key phrases (2-3 word combinations) from query
    query_words = query_lower.split()
    key_phrases = []
    for i in range(len(query_words) - 1):
        phrase = " ".join(query_words[i:i+2])
        if len(phrase) > 3:
            key_phrases.append(phrase)
    for i in range(len(query_words) - 2):
        phrase = " ".join(query_words[i:i+3])
        if len(phrase) > 5:
            key_phrases.append(phrase)
    
    # Also add individual words (longer than 2 chars)
    query_words_set = set(word for word in query_words if len(word) > 2)
    
    boost = 0.0
    
    # Check primary fields (title, name) for exact matches
    # First 2 fields are usually title/name
    for field in text_fields[:2]:
        if hasattr(obj, field):
            field_value = str(getattr(obj, field, "")).lower()
            if field_value:
                # Check for key phrases first (highest priority)
                for phrase in key_phrases:
                    if phrase in field_value:
                        # Major boost for phrase match
                        boost += 0.5
                        # Extra boost if it's the exact field value
                        if field_value.strip() == phrase.strip():
                            boost += 0.3
                
                # Check for full query match
                if query_lower in field_value:
                    boost += 0.4
                
                # Count matched individual words
                matched_words = sum(1 for word in query_words_set if word in field_value)
                if matched_words > 0:
                    # Moderate boost for word matches
                    boost += 0.1 * min(matched_words, 3)  # Cap at 3 words
    
    return min(boost, 1.0)  # Cap at 1.0 for very strong matches


def parallel_vector_search(
    queries: List[str],
    queryset: QuerySet,
    top_k_per_query: int = 5,
    final_top_k: int = 7,
    text_fields: Optional[List[str]] = None
) -> List[Tuple[Any, float]]:
    """
    Search with multiple queries in parallel, then merge results.
    
    This is the core of Query Rewrite Strategy - run multiple vector searches
    in parallel and merge results to get the best documents.
    
    Args:
        queries: List of rewritten queries (3-5 queries from Query Rewrite).
        queryset: Django QuerySet to search.
        top_k_per_query: Top K results per query (default: 5).
        final_top_k: Final top K results after merging (default: 7).
        text_fields: Optional list of field names for exact match boost.
    
    Returns:
        List of (object, combined_score) tuples, sorted by score descending.
    
    Example:
        queries = [
            "nội dung điều 12",
            "quy định điều 12",
            "điều 12 quy định về"
        ]
        results = parallel_vector_search(queries, LegalSection.objects.all())
        # Returns top 7 sections with highest combined scores
    """
    if not queries or not queries[0].strip():
        return []
    
    if len(queries) == 1:
        # Single query - use direct vector search
        return _single_query_search(queries[0], queryset, top_k=final_top_k, text_fields=text_fields)
    
    # Multiple queries - run in parallel
    all_results: Dict[Any, float] = {}  # object -> max_score
    
    # Use ThreadPoolExecutor for parallel searches
    with ThreadPoolExecutor(max_workers=min(len(queries), 5)) as executor:
        # Submit all searches
        future_to_query = {
            executor.submit(get_vector_scores, queryset, query, top_k=top_k_per_query): query
            for query in queries
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_query):
            query = future_to_query[future]
            try:
                results = future.result()
                # Merge results: use max score for each object
                for obj, score in results:
                    if obj in all_results:
                        # Keep the maximum score from all queries
                        all_results[obj] = max(all_results[obj], score)
                    else:
                        all_results[obj] = score
            except Exception as e:
                logger.warning(f"[PARALLEL_SEARCH] Error searching with query '{query}': {e}")
    
    # Apply exact match boost if text_fields provided
    if text_fields:
        boosted_results = []
        for obj, score in all_results.items():
            boost = calculate_exact_match_boost(obj, queries[0], text_fields)  # Use first query for boost
            # Combine vector score with exact match boost (weighted)
            combined_score = score * 0.8 + boost * 0.2  # 80% vector, 20% exact match
            boosted_results.append((obj, combined_score))
        all_results_list = boosted_results
    else:
        all_results_list = list(all_results.items())
    
    # Sort by score descending
    all_results_list.sort(key=lambda x: x[1], reverse=True)
    
    return all_results_list[:final_top_k]


def _single_query_search(
    query: str,
    queryset: QuerySet,
    top_k: int = 20,
    text_fields: Optional[List[str]] = None
) -> List[Tuple[Any, float]]:
    """
    Single query vector search with exact match boost.
    
    Args:
        query: Search query string.
        queryset: Django QuerySet to search.
        top_k: Maximum number of results.
        text_fields: Optional list of field names for exact match boost.
    
    Returns:
        List of (object, score) tuples, sorted by score descending.
    """
    # Get vector scores
    vector_results = get_vector_scores(queryset, query, top_k=top_k)
    
    if not text_fields:
        return vector_results[:top_k]
    
    # Apply exact match boost
    boosted_results = []
    for obj, score in vector_results:
        boost = calculate_exact_match_boost(obj, query, text_fields)
        # Combine vector score with exact match boost (weighted)
        combined_score = score * 0.8 + boost * 0.2  # 80% vector, 20% exact match
        boosted_results.append((obj, combined_score))
    
    # Sort by combined score
    boosted_results.sort(key=lambda x: x[1], reverse=True)
    return boosted_results[:top_k]


def pure_semantic_search(
    queries: List[str],
    queryset: QuerySet,
    top_k: int = 20,
    text_fields: Optional[List[str]] = None
) -> List[Any]:
    """
    Pure semantic search (100% vector, no BM25).
    
    This is the recommended search strategy when using Query Rewrite + BGE-M3.
    All top systems have moved away from hybrid search to pure semantic since Oct 2025.
    
    Args:
        queries: List of queries (1 query or 3-5 queries from Query Rewrite).
        queryset: Django QuerySet to search.
        top_k: Maximum number of results.
        text_fields: Optional list of field names for exact match boost.
    
    Returns:
        List of objects sorted by score (highest first).
    
    Usage:
        # Single query
        results = pure_semantic_search(["mức phạt vi phạm"], queryset, top_k=20)
        
        # Multiple queries (from Query Rewrite)
        rewritten_queries = query_rewriter.rewrite_query("mức phạt vi phạm")
        results = pure_semantic_search(rewritten_queries, queryset, top_k=20)
    """
    if not queries:
        return []
    
    if len(queries) == 1:
        # Single query - direct search
        results = _single_query_search(queries[0], queryset, top_k=top_k, text_fields=text_fields)
    else:
        # Multiple queries - parallel search
        results = parallel_vector_search(
            queries,
            queryset,
            top_k_per_query=max(5, top_k // len(queries)),
            final_top_k=top_k,
            text_fields=text_fields
        )
    
    # Return just the objects (without scores)
    return [obj for obj, _ in results]

