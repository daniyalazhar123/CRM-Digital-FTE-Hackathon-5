# CRM Digital FTE - Cache Layer
"""
Redis caching layer for performance optimization.

Provides:
- RedisCache: async Redis client with connection pooling
- cached_kb_search / cache_kb_search
- cached_customer_lookup / cache_customer_lookup
- cached_ticket_lookup / cache_ticket_lookup
"""

from .redis_client import (
    RedisCache,
    get_cache,
    cached_kb_search,
    cache_kb_search,
    cached_customer_lookup,
    cache_customer_lookup,
    cached_ticket_lookup,
    cache_ticket_lookup,
    invalidate_customer_cache,
    invalidate_kb_cache,
)

# Backward-compat aliases
RedisClient = RedisCache
get_redis_client = get_cache

__all__ = [
    "RedisCache",
    "RedisClient",
    "get_cache",
    "get_redis_client",
    "cached_kb_search",
    "cache_kb_search",
    "cached_customer_lookup",
    "cache_customer_lookup",
    "cached_ticket_lookup",
    "cache_ticket_lookup",
    "invalidate_customer_cache",
    "invalidate_kb_cache",
]
