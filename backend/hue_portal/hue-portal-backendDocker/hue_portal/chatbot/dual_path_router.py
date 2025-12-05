"""
Dual-Path RAG Router - Routes queries to Fast Path (golden dataset) or Slow Path (full RAG).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple
import numpy as np
from django.db.models import Q

from hue_portal.core.models import GoldenQuery
from hue_portal.core.embeddings import get_embedding_model


@dataclass
class RouteDecision:
    """Decision from Dual-Path Router."""
    path: str  # "fast_path" or "slow_path"
    method: str  # "keyword" or "llm" or "similarity" or "default"
    confidence: float
    matched_golden_query_id: Optional[int] = None
    similarity_score: Optional[float] = None
    intent: Optional[str] = None
    rationale: str = ""


class KeywordRouter:
    """Fast keyword-based router to match queries against golden dataset."""
    
    def __init__(self):
        self._normalize_cache = {}
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for matching (lowercase, remove accents, extra spaces)."""
        if query in self._normalize_cache:
            return self._normalize_cache[query]
        
        normalized = query.lower().strip()
        # Remove accents for accent-insensitive matching
        normalized = unicodedata.normalize("NFD", normalized)
        normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
        # Remove extra spaces
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        self._normalize_cache[query] = normalized
        return normalized
    
    def route(self, query: str, intent: str, confidence: float) -> RouteDecision:
        """
        Try to match query against golden dataset using keyword matching.
        
        Returns:
            RouteDecision with path="fast_path" if match found, else path="slow_path"
        """
        query_normalized = self._normalize_query(query)
        
        # Try exact match first (fastest)
        try:
            golden_query = GoldenQuery.objects.get(
                query_normalized=query_normalized,
                is_active=True
            )
            return RouteDecision(
                path="fast_path",
                method="keyword",
                confidence=1.0,
                matched_golden_query_id=golden_query.id,
                intent=intent,
                rationale="exact_match"
            )
        except (GoldenQuery.DoesNotExist, GoldenQuery.MultipleObjectsReturned):
            pass
        
        # Try fuzzy match: check if query contains golden query or vice versa
        # This handles variations like "mức phạt vượt đèn đỏ" vs "vượt đèn đỏ phạt bao nhiêu"
        try:
            # Find golden queries with same intent
            golden_queries = GoldenQuery.objects.filter(
                intent=intent,
                is_active=True
            )[:50]  # Limit to avoid too many comparisons
            
            for gq in golden_queries:
                gq_normalized = self._normalize_query(gq.query)
                
                # Check if query is substring of golden query or vice versa
                if (query_normalized in gq_normalized or 
                    gq_normalized in query_normalized):
                    # Calculate similarity (simple Jaccard similarity)
                    query_words = set(query_normalized.split())
                    gq_words = set(gq_normalized.split())
                    if query_words and gq_words:
                        similarity = len(query_words & gq_words) / len(query_words | gq_words)
                        if similarity >= 0.7:  # 70% word overlap
                            return RouteDecision(
                                path="fast_path",
                                method="keyword",
                                confidence=similarity,
                                matched_golden_query_id=gq.id,
                                similarity_score=similarity,
                                intent=intent,
                                rationale="fuzzy_match"
                            )
        except Exception:
            pass
        
        # No match found
        return RouteDecision(
            path="slow_path",
            method="keyword",
            confidence=confidence,
            intent=intent,
            rationale="no_keyword_match"
        )


class DualPathRouter:
    """Main router that decides Fast Path vs Slow Path using hybrid approach."""
    
    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize Dual-Path Router.
        
        Args:
            similarity_threshold: Minimum similarity score for semantic matching (default: 0.85)
        """
        self.keyword_router = KeywordRouter()
        self.llm_router = None  # Lazy load if needed
        self.similarity_threshold = similarity_threshold
        self._embedding_model = None
    
    def route(self, query: str, intent: str, confidence: float) -> RouteDecision:
        """
        Route query to Fast Path or Slow Path.
        
        Args:
            query: User query string.
            intent: Detected intent.
            confidence: Intent classification confidence.
        
        Returns:
            RouteDecision with path, method, and matched golden query ID if applicable.
        """
        # Step 1: Keyword-based routing (fastest, ~1-5ms)
        keyword_decision = self.keyword_router.route(query, intent, confidence)
        if keyword_decision.path == "fast_path":
            return keyword_decision
        
        # Step 2: Semantic similarity search in golden dataset (~50-100ms)
        similarity_match = self._find_similar_golden_query(query, intent)
        if similarity_match and similarity_match['score'] >= self.similarity_threshold:
            return RouteDecision(
                path="fast_path",
                method="similarity",
                confidence=similarity_match['score'],
                matched_golden_query_id=similarity_match['id'],
                similarity_score=similarity_match['score'],
                intent=intent,
                rationale="semantic_similarity"
            )
        
        # Step 3: LLM router fallback (for edge cases, ~100-200ms)
        # Only use if confidence is low (uncertain intent)
        if confidence < 0.7:
            llm_decision = self._llm_route(query, intent)
            if llm_decision and llm_decision.path == "fast_path":
                return llm_decision
        
        # Default: Slow Path (full RAG pipeline)
        return RouteDecision(
            path="slow_path",
            method="default",
            confidence=confidence,
            intent=intent,
            rationale="no_fast_path_match"
        )
    
    def _find_similar_golden_query(self, query: str, intent: str) -> Optional[Dict]:
        """
        Find similar query in golden dataset using semantic search.
        
        Args:
            query: User query.
            intent: Detected intent.
        
        Returns:
            Dict with 'id' and 'score' if match found, None otherwise.
        """
        try:
            # Get active golden queries with same intent
            golden_queries = list(
                GoldenQuery.objects.filter(
                    intent=intent,
                    is_active=True,
                    query_embedding__isnull=False
                )[:100]  # Limit for performance
            )
            
            if not golden_queries:
                return None
            
            # Get embedding model
            embedding_model = self._get_embedding_model()
            if not embedding_model:
                return None
            
            # Generate query embedding
            query_embedding = embedding_model.encode(query, convert_to_numpy=True)
            query_embedding = query_embedding / np.linalg.norm(query_embedding)  # Normalize
            
            # Calculate similarities
            best_match = None
            best_score = 0.0
            
            for gq in golden_queries:
                if not gq.query_embedding:
                    continue
                
                # Load golden query embedding
                gq_embedding = np.array(gq.query_embedding)
                if len(gq_embedding) == 0:
                    continue
                
                # Normalize
                gq_embedding = gq_embedding / np.linalg.norm(gq_embedding)
                
                # Calculate cosine similarity
                similarity = float(np.dot(query_embedding, gq_embedding))
                
                if similarity > best_score:
                    best_score = similarity
                    best_match = gq.id
            
            if best_match and best_score >= self.similarity_threshold:
                return {
                    'id': best_match,
                    'score': best_score
                }
            
            return None
            
        except Exception as e:
            # Log error but don't fail
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error in semantic similarity search: {e}")
            return None
    
    def _get_embedding_model(self):
        """Lazy load embedding model."""
        if self._embedding_model is None:
            self._embedding_model = get_embedding_model()
        return self._embedding_model
    
    def _llm_route(self, query: str, intent: str) -> Optional[RouteDecision]:
        """
        Use LLM to decide routing (optional, for edge cases).
        
        This is a fallback for low-confidence queries where keyword and similarity
        didn't find a match, but LLM might recognize it as a common query.
        
        Args:
            query: User query.
            intent: Detected intent.
        
        Returns:
            RouteDecision if LLM finds a match, None otherwise.
        """
        # For now, return None (LLM routing can be implemented later if needed)
        # This would require a small LLM (7B) to classify if query matches golden dataset
        return None

