"""
Caching Service for Phase 4
In-memory and optional Redis caching for dashboard metrics and frequently accessed data
"""

import time
import json
from typing import Dict, Any, Optional
from functools import wraps


class CacheEntry:
    """Represents a cached value with TTL"""
    def __init__(self, value: Any, ttl: int = 300):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl

    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return time.time() - self.created_at > self.ttl

    def __repr__(self):
        return f"CacheEntry(value={self.value}, expired={self.is_expired()})"


class InMemoryCache:
    """Simple in-memory cache implementation"""
    def __init__(self):
        self.cache: Dict[str, CacheEntry] = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key not in self.cache:
            self.misses += 1
            return None

        entry = self.cache[key]
        if entry.is_expired():
            del self.cache[key]
            self.misses += 1
            return None

        self.hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: int = 300):
        """Set value in cache with TTL"""
        self.cache[key] = CacheEntry(value, ttl)

    def delete(self, key: str):
        """Delete value from cache"""
        if key in self.cache:
            del self.cache[key]

    def clear(self):
        """Clear entire cache"""
        self.cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            'hits': self.hits,
            'misses': self.misses,
            'total': total,
            'hit_rate': round(hit_rate, 2),
            'size': len(self.cache)
        }

    def __repr__(self):
        return f"InMemoryCache(size={len(self.cache)}, {self.get_stats()})"


# Global cache instance
_cache = InMemoryCache()


def get_cache() -> InMemoryCache:
    """Get the global cache instance"""
    return _cache


def cache_key(prefix: str, *args) -> str:
    """Generate a cache key from prefix and args"""
    key_parts = [prefix] + [str(arg) for arg in args]
    return ':'.join(key_parts)


def cached(ttl: int = 300, key_fn=None):
    """
    Decorator to cache function results
    ttl: time to live in seconds
    key_fn: optional function to generate custom cache key
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_fn:
                cache_key_value = key_fn(*args, **kwargs)
            else:
                cache_key_value = cache_key(func.__name__, *args)

            # Check cache
            cached_value = _cache.get(cache_key_value)
            if cached_value is not None:
                return cached_value

            # Execute function
            result = func(*args, **kwargs)

            # Store in cache
            if result is not None:
                _cache.set(cache_key_value, result, ttl)

            return result

        return wrapper
    return decorator


# Cache keys for common operations
DASHBOARD_METRICS_CACHE_KEY = "dashboard:metrics:{site}"
USER_PREFERENCES_CACHE_KEY = "user:preferences:{user_id}"
ALERT_RULES_CACHE_KEY = "alerts:rules:{user_id}"
FILTER_PRESETS_CACHE_KEY = "filters:presets:{user_id}"


def cache_metrics(site: str, metrics: Dict[str, Any], ttl: int = 300):
    """Cache dashboard metrics"""
    key = DASHBOARD_METRICS_CACHE_KEY.format(site=site)
    _cache.set(key, metrics, ttl)


def get_cached_metrics(site: str) -> Optional[Dict[str, Any]]:
    """Get cached dashboard metrics"""
    key = DASHBOARD_METRICS_CACHE_KEY.format(site=site)
    return _cache.get(key)


def invalidate_metrics(site: str = None):
    """Invalidate metrics cache for a site or all sites"""
    if site:
        key = DASHBOARD_METRICS_CACHE_KEY.format(site=site)
        _cache.delete(key)
    else:
        # Clear all metric keys
        _cache.clear()


def cache_user_preferences(user_id: str, prefs: Dict[str, Any], ttl: int = 3600):
    """Cache user preferences"""
    key = USER_PREFERENCES_CACHE_KEY.format(user_id=user_id)
    _cache.set(key, prefs, ttl)


def get_cached_preferences(user_id: str) -> Optional[Dict[str, Any]]:
    """Get cached user preferences"""
    key = USER_PREFERENCES_CACHE_KEY.format(user_id=user_id)
    return _cache.get(key)


def invalidate_user_cache(user_id: str):
    """Invalidate all caches for a user"""
    _cache.delete(USER_PREFERENCES_CACHE_KEY.format(user_id=user_id))
    _cache.delete(ALERT_RULES_CACHE_KEY.format(user_id=user_id))
    _cache.delete(FILTER_PRESETS_CACHE_KEY.format(user_id=user_id))


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    return _cache.get_stats()
