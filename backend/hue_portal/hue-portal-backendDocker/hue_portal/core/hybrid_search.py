"""
Hybrid search combining BM25 and vector similarity.
"""
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
from django.db import connection
from django.db.models import QuerySet, F
from django.contrib.postgres.search import SearchQuery, SearchRank

from .embeddings import (
    get_embedding_model,
    generate_embedding,
    cosine_similarity
)
from .embedding_utils import load_embedding
from .search_ml import expand_query_with_synonyms


# Default weights for hybrid search
DEFAULT_BM25_WEIGHT = 0.4
DEFAULT_VECTOR_WEIGHT = 0.6

# Minimum scores
DEFAULT_MIN_BM25_SCORE = 0.0
DEFAULT_MIN_VECTOR_SCORE = 0.1


def calculate_exact_match_boost(obj: Any, query: str, text_fields: List[str]) -> float:
    """
    Calculate boost score for exact keyword matches in title/name fields.
    
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


def get_bm25_scores(
    queryset: QuerySet,
    query: str,
    top_k: int = 20
) -> List[Tuple[Any, float]]:
    """
    Get BM25 scores for queryset.
    
    Args:
        queryset: Django QuerySet to search.
        query: Search query string.
        top_k: Maximum number of results.
    
    Returns:
        List of (object, bm25_score) tuples.
    """
    if not query or connection.vendor != "postgresql":
        return []
    
    if not hasattr(queryset.model, "tsv_body"):
        return []
    
    try:
        expanded_queries = expand_query_with_synonyms(query)
        combined_query = None
        for q_variant in expanded_queries:
            variant_query = SearchQuery(q_variant, config="simple")
            combined_query = variant_query if combined_query is None else combined_query | variant_query

        if combined_query is not None:
            ranked_qs = (
                queryset
                .annotate(rank=SearchRank(F("tsv_body"), combined_query))
                .filter(rank__gt=DEFAULT_MIN_BM25_SCORE)
                .order_by("-rank")
            )
            results = list(ranked_qs[:top_k * 2])  # Get more for hybrid ranking
            return [(obj, float(getattr(obj, "rank", 0.0))) for obj in results]
    except Exception as e:
        print(f"Error in BM25 search: {e}")
    
    return []


def get_vector_scores(
    queryset: QuerySet,
    query: str,
    top_k: int = 20
) -> List[Tuple[Any, float]]:
    """
    Get vector similarity scores for queryset.
    
    Args:
        queryset: Django QuerySet to search.
        query: Search query string.
        top_k: Maximum number of results.
    
    Returns:
        List of (object, vector_score) tuples.
    """
    if not query:
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
                    print(f"⚠️ Dimension mismatch: query={query_dim}, stored={obj_dim}. Skipping vector search.")
                    dimension_mismatch = True
                continue
            similarity = cosine_similarity(query_embedding, obj_embedding)
            if similarity >= DEFAULT_MIN_VECTOR_SCORE:
                scores.append((obj, similarity))
    
    # If dimension mismatch detected, return empty to fall back to BM25 + exact match
    if dimension_mismatch and not scores:
        return []
    
    # Sort by score descending
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_k * 2]  # Get more for hybrid ranking


def normalize_scores(scores: List[Tuple[Any, float]]) -> Dict[Any, float]:
    """
    Normalize scores to 0-1 range.
    
    Args:
        scores: List of (object, score) tuples.
    
    Returns:
        Dictionary mapping object to normalized score.
    """
    if not scores:
        return {}
    
    max_score = max(score for _, score in scores) if scores else 1.0
    min_score = min(score for _, score in scores) if scores else 0.0
    
    if max_score == min_score:
        # All scores are the same, return uniform distribution
        return {obj: 1.0 for obj, _ in scores}
    
    # Normalize to 0-1
    normalized = {}
    for obj, score in scores:
        normalized[obj] = (score - min_score) / (max_score - min_score)
    
    return normalized


def hybrid_search(
    queryset: QuerySet,
    query: str,
    top_k: int = 20,
    bm25_weight: float = DEFAULT_BM25_WEIGHT,
    vector_weight: float = DEFAULT_VECTOR_WEIGHT,
    min_hybrid_score: float = 0.1,
    text_fields: Optional[List[str]] = None
) -> List[Any]:
    """
    Perform hybrid search combining BM25 and vector similarity.
    
    Args:
        queryset: Django QuerySet to search.
        query: Search query string.
        top_k: Maximum number of results.
        bm25_weight: Weight for BM25 score (0-1).
        vector_weight: Weight for vector score (0-1).
        min_hybrid_score: Minimum combined score threshold.
        text_fields: List of field names for exact match boost (optional).
    
    Returns:
        List of objects sorted by hybrid score.
    """
    if not query:
        return list(queryset[:top_k])
    
    # Normalize weights
    total_weight = bm25_weight + vector_weight
    if total_weight > 0:
        bm25_weight = bm25_weight / total_weight
        vector_weight = vector_weight / total_weight
    else:
        bm25_weight = 0.5
        vector_weight = 0.5
    
    # Get BM25 scores
    bm25_results = get_bm25_scores(queryset, query, top_k=top_k)
    bm25_scores = normalize_scores(bm25_results)
    
    # Get vector scores
    vector_results = get_vector_scores(queryset, query, top_k=top_k)
    vector_scores = normalize_scores(vector_results)
    
    # Combine scores
    combined_scores = {}
    all_objects = set()
    
    # Add BM25 objects
    for obj, _ in bm25_results:
        all_objects.add(obj)
        combined_scores[obj] = bm25_scores.get(obj, 0.0) * bm25_weight
    
    # Add vector objects
    for obj, _ in vector_results:
        all_objects.add(obj)
        if obj in combined_scores:
            combined_scores[obj] += vector_scores.get(obj, 0.0) * vector_weight
        else:
            combined_scores[obj] = vector_scores.get(obj, 0.0) * vector_weight
    
    # CRITICAL: Find exact matches FIRST using icontains, then apply boost
    # This ensures exact matches are always found and prioritized
    if text_fields:
        query_lower = query.lower()
        # Extract key phrases (2-word and 3-word) from query
        query_words = query_lower.split()
        key_phrases = []
        # 2-word phrases
        for i in range(len(query_words) - 1):
            phrase = " ".join(query_words[i:i+2])
            if len(phrase) > 3:
                key_phrases.append(phrase)
        # 3-word phrases  
        for i in range(len(query_words) - 2):
            phrase = " ".join(query_words[i:i+3])
            if len(phrase) > 5:
                key_phrases.append(phrase)
        
        # Find potential exact matches using icontains on name/title field
        # This ensures we don't miss exact matches even if BM25/vector don't find them
        exact_match_candidates = set()
        primary_field = text_fields[0] if text_fields else "name"
        if hasattr(queryset.model, primary_field):
            # Search for key phrases in the primary field
            for phrase in key_phrases:
                filter_kwargs = {f"{primary_field}__icontains": phrase}
                candidates = queryset.filter(**filter_kwargs)[:top_k * 2]
                exact_match_candidates.update(candidates)
        
        # Apply exact match boost to all candidates
        for obj in exact_match_candidates:
            if obj not in all_objects:
                all_objects.add(obj)
                combined_scores[obj] = 0.0
            
            # Apply exact match boost (this should dominate)
            boost = calculate_exact_match_boost(obj, query, text_fields)
            if boost > 0:
                # Exact match boost should dominate - set it high
                combined_scores[obj] = max(combined_scores.get(obj, 0.0), boost)
        
        # Also check objects already in results for exact matches
        for obj in list(all_objects):
            boost = calculate_exact_match_boost(obj, query, text_fields)
            if boost > 0:
                # Boost existing scores
                combined_scores[obj] = max(combined_scores.get(obj, 0.0), boost)
    
    # Filter by minimum score and sort
    filtered_scores = [
        (obj, score) for obj, score in combined_scores.items()
        if score >= min_hybrid_score
    ]
    filtered_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Return top k
    results = [obj for obj, _ in filtered_scores[:top_k]]
    
    # Store hybrid score on objects for reference
    for obj, score in filtered_scores[:top_k]:
        obj._hybrid_score = score
        obj._bm25_score = bm25_scores.get(obj, 0.0)
        obj._vector_score = vector_scores.get(obj, 0.0)
        # Store exact match boost if applied
        if text_fields:
            obj._exact_match_boost = calculate_exact_match_boost(obj, query, text_fields)
        else:
            obj._exact_match_boost = 0.0
    
    return results


def semantic_query_expansion(query: str, top_n: int = 3) -> List[str]:
    """
    Expand query with semantically similar terms using embeddings.
    
    Args:
        query: Original query string.
        top_n: Number of similar terms to add.
    
    Returns:
        List of expanded query variations.
    """
    try:
        from hue_portal.chatbot.query_expansion import expand_query_semantically
        return expand_query_semantically(query, context=None)
    except Exception:
        # Fallback to basic synonym expansion
        return expand_query_with_synonyms(query)


def rerank_results(query: str, results: List[Any], text_fields: List[str], top_k: int = 5) -> List[Any]:
    """
    Rerank results using cross-encoder approach (recalculate similarity with query).
    
    Args:
        query: Search query.
        results: List of result objects.
        text_fields: List of field names to use for reranking.
        top_k: Number of top results to return.
    
    Returns:
        Reranked list of results.
    """
    if not results or not query:
        return results[:top_k]
    
    try:
        # Generate query embedding
        model = get_embedding_model()
        if model is None:
            return results[:top_k]
        
        query_embedding = generate_embedding(query, model=model)
        if query_embedding is None:
            return results[:top_k]
        
        # Calculate similarity for each result
        scored_results = []
        for obj in results:
            # Create text representation from text_fields
            text_parts = []
            for field in text_fields:
                if hasattr(obj, field):
                    value = getattr(obj, field, "")
                    if value:
                        text_parts.append(str(value))
            
            if not text_parts:
                continue
            
            obj_text = " ".join(text_parts)
            obj_embedding = generate_embedding(obj_text, model=model)
            
            if obj_embedding is not None:
                similarity = cosine_similarity(query_embedding, obj_embedding)
                scored_results.append((obj, similarity))
        
        # Sort by similarity and return top_k
        scored_results.sort(key=lambda x: x[1], reverse=True)
        return [obj for obj, _ in scored_results[:top_k]]
    except Exception as e:
        print(f"Error in reranking: {e}")
        return results[:top_k]


def diversify_results(results: List[Any], top_k: int = 5, similarity_threshold: float = 0.8) -> List[Any]:
    """
    Ensure diversity in results by removing very similar items.
    
    Args:
        results: List of result objects.
        top_k: Number of results to return.
        similarity_threshold: Maximum similarity allowed between results.
    
    Returns:
        Diversified list of results.
    """
    if len(results) <= top_k:
        return results
    
    try:
        model = get_embedding_model()
        if model is None:
            return results[:top_k]
        
        # Generate embeddings for all results
        result_embeddings = []
        valid_results = []
        
        for obj in results:
            # Try to get embedding from object
            obj_embedding = load_embedding(obj)
            if obj_embedding is not None:
                result_embeddings.append(obj_embedding)
                valid_results.append(obj)
        
        if len(valid_results) <= top_k:
            return valid_results
        
        # Select diverse results using Maximal Marginal Relevance (MMR)
        selected = [valid_results[0]]  # Always include first (highest score)
        selected_indices = {0}
        selected_embeddings = [result_embeddings[0]]
        
        for _ in range(min(top_k - 1, len(valid_results) - 1)):
            best_score = -1
            best_idx = -1
            
            for i, (obj, emb) in enumerate(zip(valid_results, result_embeddings)):
                if i in selected_indices:
                    continue
                
                # Calculate max similarity to already selected results
                max_sim = 0.0
                for sel_emb in selected_embeddings:
                    sim = cosine_similarity(emb, sel_emb)
                    max_sim = max(max_sim, sim)
                
                # Score: prefer results with lower similarity to selected ones
                score = 1.0 - max_sim
                
                if score > best_score:
                    best_score = score
                    best_idx = i
            
            if best_idx >= 0:
                selected.append(valid_results[best_idx])
                selected_indices.add(best_idx)
                selected_embeddings.append(result_embeddings[best_idx])
        
        return selected
    except Exception as e:
        print(f"Error in diversifying results: {e}")
        return results[:top_k]


def search_with_hybrid(
    queryset: QuerySet,
    query: str,
    text_fields: List[str],
    top_k: int = 20,
    min_score: float = 0.1,
    use_hybrid: bool = True,
    bm25_weight: float = DEFAULT_BM25_WEIGHT,
    vector_weight: float = DEFAULT_VECTOR_WEIGHT,
    use_reranking: bool = False,
    use_diversification: bool = False
) -> QuerySet:
    """
    Search with hybrid BM25 + vector, with fallback to BM25-only or TF-IDF.
    
    Args:
        queryset: Django QuerySet to search.
        query: Search query string.
        text_fields: List of field names (for fallback).
        top_k: Maximum number of results.
        min_score: Minimum score threshold.
        use_hybrid: Whether to use hybrid search.
        bm25_weight: Weight for BM25 in hybrid search.
        vector_weight: Weight for vector in hybrid search.
    
    Returns:
        Filtered and ranked QuerySet.
    """
    if not query:
        return queryset[:top_k]
    
    # Try hybrid search if enabled
    if use_hybrid:
        try:
            hybrid_results = hybrid_search(
                queryset,
                query,
                top_k=top_k,
                bm25_weight=bm25_weight,
                vector_weight=vector_weight,
                min_hybrid_score=min_score,
                text_fields=text_fields
            )
            
            if hybrid_results:
                # Apply reranking if enabled
                if use_reranking and len(hybrid_results) > top_k:
                    hybrid_results = rerank_results(query, hybrid_results, text_fields, top_k=top_k * 2)
                
                # Apply diversification if enabled
                if use_diversification:
                    hybrid_results = diversify_results(hybrid_results, top_k=top_k)
                
                # Convert to QuerySet with preserved order
                result_ids = [obj.id for obj in hybrid_results[:top_k]]
                if result_ids:
                    from django.db.models import Case, When, IntegerField
                    preserved = Case(
                        *[When(pk=pk, then=pos) for pos, pk in enumerate(result_ids)],
                        output_field=IntegerField()
                    )
                    return queryset.filter(id__in=result_ids).order_by(preserved)
        except Exception as e:
            print(f"Hybrid search failed, falling back: {e}")
    
    # Fallback to BM25-only
    if connection.vendor == "postgresql" and hasattr(queryset.model, "tsv_body"):
        try:
            expanded_queries = expand_query_with_synonyms(query)
            combined_query = None
            for q_variant in expanded_queries:
                variant_query = SearchQuery(q_variant, config="simple")
                combined_query = variant_query if combined_query is None else combined_query | variant_query

            if combined_query is not None:
                ranked_qs = (
                    queryset
                    .annotate(rank=SearchRank(F("tsv_body"), combined_query))
                    .filter(rank__gt=0)
                    .order_by("-rank")
                )
                results = list(ranked_qs[:top_k])
                if results:
                    for obj in results:
                        obj._ml_score = getattr(obj, "rank", 0.0)
                    return results
        except Exception:
            pass
    
    # Final fallback: import and use original search_with_ml
    from .search_ml import search_with_ml
    return search_with_ml(queryset, query, text_fields, top_k=top_k, min_score=min_score)

