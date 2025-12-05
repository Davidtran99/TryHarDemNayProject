"""
Caching utilities for chatbot responses and search results.
"""
from functools import lru_cache
from django.core.cache import cache
import hashlib
import time
from typing import Optional, Dict, Any


class ChatbotCache:
    """Multi-level caching for chatbot responses."""
    
    CACHE_TIMEOUT = 3600  # 1 hour
    CACHE_PREFIX = "chatbot"
    SEARCH_CACHE_PREFIX = "search"
    
    # Cache statistics
    cache_hits = 0
    cache_misses = 0
    
    @staticmethod
    def get_cache_key(query: str, intent: str, session_id: Optional[str] = None) -> str:
        """
        Generate cache key for chatbot response.
        
        Args:
            query: User query string.
            intent: Detected intent.
            session_id: Optional session ID.
        
        Returns:
            Cache key string.
        """
        key_parts = [query.lower().strip(), intent]
        if session_id:
            key_parts.append(session_id)
        key_str = "|".join(key_parts)
        key_hash = hashlib.md5(key_str.encode('utf-8')).hexdigest()
        return f"{ChatbotCache.CACHE_PREFIX}:{key_hash}"
    
    @staticmethod
    def get_cached_response(query: str, intent: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get cached chatbot response.
        
        Args:
            query: User query string.
            intent: Detected intent.
            session_id: Optional session ID.
        
        Returns:
            Cached response dict or None.
        """
        cache_key = ChatbotCache.get_cache_key(query, intent, session_id)
        cached = cache.get(cache_key)
        
        if cached:
            ChatbotCache.cache_hits += 1
            return cached
        
        ChatbotCache.cache_misses += 1
        return None
    
    @staticmethod
    def set_cached_response(
        query: str, 
        intent: str, 
        response: Dict[str, Any], 
        session_id: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> None:
        """
        Cache chatbot response.
        
        Args:
            query: User query string.
            intent: Detected intent.
            response: Response dict to cache.
            session_id: Optional session ID.
            timeout: Cache timeout in seconds (default: CACHE_TIMEOUT).
        """
        cache_key = ChatbotCache.get_cache_key(query, intent, session_id)
        timeout = timeout or ChatbotCache.CACHE_TIMEOUT
        
        # Add timestamp for cache validation
        cached_data = {
            **response,
            '_cached_at': time.time()
        }
        
        cache.set(cache_key, cached_data, timeout)
    
    @staticmethod
    def get_cached_search_results(query: str, model_name: str, text_fields: tuple) -> Optional[list]:
        """
        Get cached search results.
        
        Args:
            query: Search query.
            model_name: Model name.
            text_fields: Tuple of text fields searched.
        
        Returns:
            Cached results list or None.
        """
        key_str = f"{query}|{model_name}|{':'.join(text_fields)}"
        key_hash = hashlib.md5(key_str.encode('utf-8')).hexdigest()
        cache_key = f"{ChatbotCache.SEARCH_CACHE_PREFIX}:{key_hash}"
        
        cached = cache.get(cache_key)
        if cached:
            ChatbotCache.cache_hits += 1
            return cached
        
        ChatbotCache.cache_misses += 1
        return None
    
    @staticmethod
    def set_cached_search_results(
        query: str, 
        model_name: str, 
        text_fields: tuple, 
        results: list,
        timeout: Optional[int] = None
    ) -> None:
        """
        Cache search results.
        
        Args:
            query: Search query.
            model_name: Model name.
            text_fields: Tuple of text fields searched.
            results: Results list to cache.
            timeout: Cache timeout in seconds (default: CACHE_TIMEOUT).
        """
        key_str = f"{query}|{model_name}|{':'.join(text_fields)}"
        key_hash = hashlib.md5(key_str.encode('utf-8')).hexdigest()
        cache_key = f"{ChatbotCache.SEARCH_CACHE_PREFIX}:{key_hash}"
        timeout = timeout or ChatbotCache.CACHE_TIMEOUT
        
        cache.set(cache_key, results, timeout)
    
    @staticmethod
    def invalidate_cache(query: Optional[str] = None, intent: Optional[str] = None) -> None:
        """
        Invalidate cache entries.
        
        Args:
            query: Optional query to invalidate (if None, invalidate all).
            intent: Optional intent to invalidate.
        """
        if query and intent:
            cache_key = ChatbotCache.get_cache_key(query, intent)
            cache.delete(cache_key)
        else:
            # Invalidate all chatbot cache (use cache.clear() with caution)
            # For production, use cache versioning instead
            pass
    
    @staticmethod
    def get_cache_stats() -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache hit rate and counts.
        """
        total = ChatbotCache.cache_hits + ChatbotCache.cache_misses
        if total == 0:
            return {
                "hit_rate": 0.0,
                "hits": 0,
                "misses": 0,
                "total": 0
            }
        
        return {
            "hit_rate": ChatbotCache.cache_hits / total,
            "hits": ChatbotCache.cache_hits,
            "misses": ChatbotCache.cache_misses,
            "total": total
        }
    
    @staticmethod
    def reset_stats() -> None:
        """Reset cache statistics."""
        ChatbotCache.cache_hits = 0
        ChatbotCache.cache_misses = 0


@lru_cache(maxsize=1)
def get_all_synonyms():
    """
    Get all synonyms from database (cached).
    
    Returns:
        List of Synonym objects.
    """
    from .models import Synonym
    try:
        return list(Synonym.objects.all())
    except Exception:
        return []

