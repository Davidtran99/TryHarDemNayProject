"""
Machine Learning-based search utilities using TF-IDF and text similarity.
"""
import re
from typing import List, Tuple, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from django.db import connection
from django.db.models import Q, QuerySet, F
from django.contrib.postgres.search import SearchQuery, SearchRank
from .models import Synonym


def normalize_text(text: str) -> str:
    """Normalize Vietnamese text for search."""
    if not text:
        return ""
    # Lowercase and remove extra spaces
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def expand_query_with_synonyms(query: str) -> List[str]:
    """Expand query using synonyms from database."""
    query_normalized = normalize_text(query)
    expanded = [query_normalized]
    
    try:
        # Get all synonyms
        synonyms = Synonym.objects.all()
        for synonym in synonyms:
            keyword = normalize_text(synonym.keyword)
            alias = normalize_text(synonym.alias)
            
            # If query contains keyword, add alias
            if keyword in query_normalized:
                expanded.append(query_normalized.replace(keyword, alias))
            # If query contains alias, add keyword
            if alias in query_normalized:
                expanded.append(query_normalized.replace(alias, keyword))
    except Exception:
        pass  # If Synonym table doesn't exist yet
    
    return list(set(expanded))  # Remove duplicates


def create_search_vector(text_fields: List[str]) -> str:
    """Create a searchable text vector from multiple fields."""
    return " ".join(str(field) for field in text_fields if field)


def calculate_similarity_scores(
    query: str,
    documents: List[str],
    top_k: int = 20
) -> List[Tuple[int, float]]:
    """
    Calculate cosine similarity scores between query and documents.
    Returns list of (index, score) tuples sorted by score descending.
    """
    if not query or not documents:
        return []
    
    # Expand query with synonyms
    expanded_queries = expand_query_with_synonyms(query)
    
    # Combine all query variations
    all_texts = expanded_queries + documents
    
    try:
        # Create TF-IDF vectorizer
        vectorizer = TfidfVectorizer(
            analyzer='word',
            ngram_range=(1, 2),  # Unigrams and bigrams
            min_df=1,
            max_df=0.95,
            lowercase=True,
            token_pattern=r'\b\w+\b'
        )
        
        # Fit and transform
        tfidf_matrix = vectorizer.fit_transform(all_texts)
        
        # Get query vector (average of expanded queries)
        query_vectors = tfidf_matrix[:len(expanded_queries)]
        query_vector = np.mean(query_vectors.toarray(), axis=0).reshape(1, -1)
        
        # Get document vectors
        doc_vectors = tfidf_matrix[len(expanded_queries):]
        
        # Calculate similarities
        similarities = cosine_similarity(query_vector, doc_vectors)[0]
        
        # Get top k results with scores
        top_indices = np.argsort(similarities)[::-1][:top_k]
        results = [(int(idx), float(similarities[idx])) for idx in top_indices if similarities[idx] > 0.0]
        
        return results
    except Exception as e:
        # Fallback to simple text matching if ML fails
        query_lower = normalize_text(query)
        results = []
        for idx, doc in enumerate(documents):
            doc_lower = normalize_text(doc)
            if query_lower in doc_lower:
                # Simple score based on position and length
                score = 1.0 - (doc_lower.find(query_lower) / max(len(doc_lower), 1))
                results.append((idx, score))
        return sorted(results, key=lambda x: x[1], reverse=True)[:top_k]


def search_with_ml(
    queryset: QuerySet,
    query: str,
    text_fields: List[str],
    top_k: int = 20,
    min_score: float = 0.1,
    use_hybrid: bool = True
) -> QuerySet:
    """
    Search queryset using ML-based similarity scoring.
    
    Args:
        queryset: Django QuerySet to search
        query: Search query string
        text_fields: List of field names to search in
        top_k: Maximum number of results
        min_score: Minimum similarity score threshold
    
    Returns:
        Filtered and ranked QuerySet
    """
    if not query:
        return queryset[:top_k]

    # Try hybrid search if enabled
    if use_hybrid:
        try:
            from .hybrid_search import search_with_hybrid
            from .config.hybrid_search_config import get_config
            
            # Determine content type from model
            model_name = queryset.model.__name__.lower()
            content_type = None
            if 'procedure' in model_name:
                content_type = 'procedure'
            elif 'fine' in model_name:
                content_type = 'fine'
            elif 'office' in model_name:
                content_type = 'office'
            elif 'advisory' in model_name:
                content_type = 'advisory'
            
            config = get_config(content_type)
            return search_with_hybrid(
                queryset,
                query,
                text_fields,
                top_k=top_k,
                min_score=min_score,
                use_hybrid=True,
                bm25_weight=config.bm25_weight,
                vector_weight=config.vector_weight
            )
        except Exception as e:
            print(f"Hybrid search not available, using BM25/TF-IDF: {e}")

    # Attempt PostgreSQL BM25 ranking first when available
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
            # Fall through to ML-based search if any error occurs (e.g. missing extensions)
            pass
    
    # Get all objects and create search vectors
    all_objects = list(queryset)
    if not all_objects:
        return queryset.none()
    
    # Create search vectors for each object
    documents = []
    for obj in all_objects:
        field_values = [getattr(obj, field, "") for field in text_fields]
        search_vector = create_search_vector(field_values)
        documents.append(search_vector)
    
    # Calculate similarity scores
    try:
        scored_indices = calculate_similarity_scores(query, documents, top_k=top_k)
        
        # Filter by minimum score and get object IDs
        valid_indices = [idx for idx, score in scored_indices if score >= min_score]
        
        # If ML search found results, use them
        if valid_indices:
            result_objects = [all_objects[idx] for idx in valid_indices]
            result_ids = [obj.id for obj in result_objects]
            
            if result_ids:
                # Create a mapping of ID to order for sorting
                id_to_order = {obj_id: idx for idx, obj_id in enumerate(result_ids)}
                
                # Filter by IDs and sort by the order
                filtered = queryset.filter(id__in=result_ids)
                
                # Convert to list, sort by order, then convert back to queryset
                result_list = list(filtered)
                result_list.sort(key=lambda x: id_to_order.get(x.id, 999))
                
                # Return limited results - create a new queryset from IDs in order
                ordered_ids = [obj.id for obj in result_list[:top_k]]
                if ordered_ids:
                    # Use Case/When for ordering in PostgreSQL
                    from django.db.models import Case, When, IntegerField
                    preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(ordered_ids)], output_field=IntegerField())
                    return queryset.filter(id__in=ordered_ids).order_by(preserved)
    except Exception as e:
        # If ML search fails, fall back to simple search
        pass
    
    # Fallback to simple icontains search with exact match prioritization
    query_lower = normalize_text(query)
    query_words = query_lower.split()
    
    # Extract key phrases (2-3 words) for better matching
    key_phrases = []
    for i in range(len(query_words) - 1):
        phrase = " ".join(query_words[i:i+2])
        if len(phrase) > 3:
            key_phrases.append(phrase)
    for i in range(len(query_words) - 2):
        phrase = " ".join(query_words[i:i+3])
        if len(phrase) > 5:
            key_phrases.append(phrase)
    
    # Try to find exact phrase matches first
    exact_matches = []
    primary_field = text_fields[0] if text_fields else None
    if primary_field:
        for phrase in key_phrases:
            filter_kwargs = {f"{primary_field}__icontains": phrase}
            matches = list(queryset.filter(**filter_kwargs)[:top_k])
            exact_matches.extend(matches)
    
    # If we found exact matches, prioritize them
    if exact_matches:
        # Remove duplicates while preserving order
        seen = set()
        unique_matches = []
        for obj in exact_matches:
            if obj.id not in seen:
                seen.add(obj.id)
                unique_matches.append(obj)
        return unique_matches[:top_k]
    
    # Fallback to simple icontains search
    q_objects = Q()
    for field in text_fields:
        q_objects |= Q(**{f"{field}__icontains": query})
    return queryset.filter(q_objects)[:top_k]
    

