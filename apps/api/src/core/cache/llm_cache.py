import hashlib
import json
import logging
from typing import Dict, List, Optional
from cachetools import TTLCache

logger = logging.getLogger(__name__)

class LLMCache:
    """In-memory cache for LLM responses."""
    
    def __init__(self, maxsize: int = 1000, ttl: int = 3600):
        """
        Initialize cache.
        
        Args:
            maxsize: Maximum number of cached responses
            ttl: Time-to-live in seconds (default: 1 hour)
        """
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._hits = 0
        self._misses = 0
    
    def _make_key(self, messages: List[Dict[str, str]], model: str) -> str:
        """Create cache key from messages and model."""
        content = json.dumps({"messages": messages, "model": model}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get(self, messages: List[Dict[str, str]], model: str) -> Optional[str]:
        """Get cached response if available."""
        key = self._make_key(messages, model)
        result = self._cache.get(key)
        if result:
            self._hits += 1
            logger.debug(f"Cache hit: {key[:8]}...")
        else:
            self._misses += 1
        return result
    
    def set(self, messages: List[Dict[str, str]], model: str, response: str):
        """Cache a response."""
        key = self._make_key(messages, model)
        self._cache[key] = response
        logger.debug(f"Cached response: {key[:8]}...")
    
    def stats(self) -> Dict[str, float]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "size": len(self._cache),
            "hit_rate": round(hit_rate, 2)
        }
    
    def clear(self):
        """Clear the cache."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0


# Global cache instance
_llm_cache: Optional[LLMCache] = None

def get_llm_cache() -> LLMCache:
    """Get or create global LLM cache."""
    global _llm_cache
    if _llm_cache is None:
        _llm_cache = LLMCache()
    return _llm_cache
