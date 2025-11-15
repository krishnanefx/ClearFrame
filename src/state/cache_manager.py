"""Cache manager for storing and retrieving frequently accessed data."""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


class CacheEntry:
    """A single cache entry with expiration support."""
    
    def __init__(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Initialize cache entry.
        
        Args:
            key: Cache key
            value: Cached value
            ttl: Time-to-live in seconds (None for no expiration)
        """
        self.key = key
        self.value = value
        self.created_at = datetime.now()
        self.ttl = ttl
        self.access_count = 0
        self.last_accessed = self.created_at
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl is None:
            return False
        
        expiration_time = self.created_at + timedelta(seconds=self.ttl)
        return datetime.now() > expiration_time
    
    def access(self) -> Any:
        """Access the cached value and update metrics."""
        self.access_count += 1
        self.last_accessed = datetime.now()
        return self.value


class CacheManager:
    """
    Manages caching for agent responses, tool results, and other data.
    Supports TTL, LRU eviction, and cache statistics.
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: Optional[int] = 3600):
        """
        Initialize cache manager.
        
        Args:
            max_size: Maximum number of cache entries
            default_ttl: Default time-to-live in seconds (None for no expiration)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0
        }
        logger.info(f"CacheManager initialized with max_size={max_size}, default_ttl={default_ttl}")
    
    def _generate_key(self, data: Any) -> str:
        """Generate a cache key from data."""
        if isinstance(data, str):
            return hashlib.sha256(data.encode()).hexdigest()
        
        # For other types, convert to JSON first
        json_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return
        
        # Find least recently accessed entry
        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_accessed
        )
        
        del self._cache[lru_key]
        self._stats["evictions"] += 1
        logger.debug(f"Evicted LRU entry: {lru_key}")
    
    def _cleanup_expired(self) -> None:
        """Remove all expired entries."""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
            self._stats["expirations"] += 1
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired entries")
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional time-to-live in seconds (overrides default)
        """
        # Clean up expired entries periodically
        if len(self._cache) % 100 == 0:
            self._cleanup_expired()
        
        # Evict if at max size
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._evict_lru()
        
        # Use provided TTL or default
        entry_ttl = ttl if ttl is not None else self.default_ttl
        
        self._cache[key] = CacheEntry(key, value, entry_ttl)
        logger.debug(f"Cached entry: {key} (ttl={entry_ttl})")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if key not in self._cache:
            self._stats["misses"] += 1
            return None
        
        entry = self._cache[key]
        
        # Check if expired
        if entry.is_expired():
            del self._cache[key]
            self._stats["expirations"] += 1
            self._stats["misses"] += 1
            return None
        
        self._stats["hits"] += 1
        return entry.access()
    
    def cache_tool_result(self, tool_name: str, args: Dict[str, Any], result: Any, ttl: Optional[int] = None) -> str:
        """
        Cache a tool execution result.
        
        Args:
            tool_name: Name of the tool
            args: Tool arguments
            result: Tool result to cache
            ttl: Optional TTL
            
        Returns:
            Generated cache key
        """
        cache_data = {
            "tool": tool_name,
            "args": args
        }
        key = self._generate_key(cache_data)
        self.set(key, result, ttl)
        return key
    
    def get_tool_result(self, tool_name: str, args: Dict[str, Any]) -> Optional[Any]:
        """
        Retrieve a cached tool result.
        
        Args:
            tool_name: Name of the tool
            args: Tool arguments
            
        Returns:
            Cached result or None
        """
        cache_data = {
            "tool": tool_name,
            "args": args
        }
        key = self._generate_key(cache_data)
        return self.get(key)
    
    def delete(self, key: str) -> bool:
        """
        Delete a cache entry.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": hit_rate,
            "evictions": self._stats["evictions"],
            "expirations": self._stats["expirations"]
        }
    
    def get_entry_info(self, key: str) -> Optional[Dict[str, Any]]:
        """Get information about a cache entry."""
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        return {
            "key": key,
            "created_at": entry.created_at.isoformat(),
            "last_accessed": entry.last_accessed.isoformat(),
            "access_count": entry.access_count,
            "ttl": entry.ttl,
            "is_expired": entry.is_expired()
        }
