# CRM Digital FTE - Cache Layer
"""
Redis caching layer for performance optimization.
"""

from .redis_client import RedisClient, get_redis_client, cached_kb_search, cached_customer_lookup

__all__ = [
    'RedisClient',
    'get_redis_client',
    'cached_kb_search',
    'cached_customer_lookup'
]
