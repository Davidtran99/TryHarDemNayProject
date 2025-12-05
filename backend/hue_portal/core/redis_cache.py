"""
Redis Cache Layer for Query Rewrite and Prefetch Results.

This module provides Redis caching for:
- Query rewrite results (1000 queries, TTL 1 hour)
- Prefetch results by document_code (TTL 30 minutes)

Supports Upstash and Railway Redis free tier.
"""
import os
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import timedelta

logger = logging.getLogger(__name__)

# Try to import redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("[REDIS] redis package not installed. Install with: pip install redis")


class RedisCache:
    """
    Redis cache manager for query rewrites and prefetch results.
    
    Supports graceful degradation if Redis is unavailable.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL. If None, reads from REDIS_URL env var.
        """
        self.redis_url = redis_url or os.environ.get("REDIS_URL")
        self.client: Optional[redis.Redis] = None
        self._connected = False
        
        if not REDIS_AVAILABLE:
            logger.warning("[REDIS] Redis package not available, caching disabled")
            return
        
        if not self.redis_url:
            logger.warning("[REDIS] REDIS_URL not configured, caching disabled")
            return
        
        self._connect()
    
    def _connect(self) -> None:
        """Connect to Redis server."""
        if not REDIS_AVAILABLE or not self.redis_url:
            return
        
        try:
            # Parse Redis URL
            # Format: redis://[:password@]host[:port][/db]
            # Or: rediss:// for SSL
            self.client = redis.from_url(
                self.redis_url,
                decode_responses=True,  # Auto-decode strings
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            self.client.ping()
            self._connected = True
            logger.info("[REDIS] ✅ Connected to Redis successfully")
        except Exception as e:
            logger.warning(f"[REDIS] Failed to connect to Redis: {e}, caching disabled")
            self.client = None
            self._connected = False
    
    def is_available(self) -> bool:
        """Check if Redis is available and connected."""
        if not self._connected or not self.client:
            return False
        
        try:
            self.client.ping()
            return True
        except Exception:
            self._connected = False
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key.
        
        Returns:
            Cached value or None if not found.
        """
        if not self.is_available():
            return None
        
        try:
            value = self.client.get(key)
            if value is None:
                return None
            
            # Try to parse as JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # Return as string if not JSON
                return value
        except Exception as e:
            logger.warning(f"[REDIS] Error getting key '{key}': {e}")
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key.
            value: Value to cache (will be JSON-encoded if dict/list).
            ttl_seconds: Time to live in seconds. If None, no expiration.
        
        Returns:
            True if successful, False otherwise.
        """
        if not self.is_available():
            return False
        
        try:
            # Serialize value to JSON if it's a dict/list
            if isinstance(value, (dict, list)):
                serialized = json.dumps(value, ensure_ascii=False)
            else:
                serialized = str(value)
            
            if ttl_seconds:
                self.client.setex(key, ttl_seconds, serialized)
            else:
                self.client.set(key, serialized)
            
            return True
        except Exception as e:
            logger.warning(f"[REDIS] Error setting key '{key}': {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key.
        
        Returns:
            True if successful, False otherwise.
        """
        if not self.is_available():
            return False
        
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"[REDIS] Error deleting key '{key}': {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key.
        
        Returns:
            True if key exists, False otherwise.
        """
        if not self.is_available():
            return False
        
        try:
            return self.client.exists(key) > 0
        except Exception:
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern.
        
        Args:
            pattern: Redis key pattern (e.g., "query_rewrite:*").
        
        Returns:
            Number of keys deleted.
        """
        if not self.is_available():
            return 0
        
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"[REDIS] Error clearing pattern '{pattern}': {e}")
            return 0


# Singleton instance
_redis_cache_instance: Optional[RedisCache] = None


def get_redis_cache(redis_url: Optional[str] = None) -> RedisCache:
    """
    Get or create Redis cache instance.
    
    Args:
        redis_url: Optional Redis URL. If None, uses REDIS_URL env var.
    
    Returns:
        RedisCache instance.
    """
    global _redis_cache_instance
    
    if _redis_cache_instance is None:
        _redis_cache_instance = RedisCache(redis_url=redis_url)
    
    return _redis_cache_instance

