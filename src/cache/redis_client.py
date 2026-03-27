"""
CRM Digital FTE - Redis Client
Feature 4: Redis Caching Layer

Provides connection pooling and caching for:
- Knowledge base search results (1hr TTL)
- Customer lookups (1hr TTL)
- Session data
"""

import os
import json
import logging
from typing import Optional, Any, Dict, List
from datetime import timedelta
import hashlib

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger(__name__)

# Configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')
REDIS_DB = int(os.getenv('REDIS_DB', '0'))

# TTL settings (in seconds)
DEFAULT_TTL = 3600  # 1 hour
KB_SEARCH_TTL = 3600  # 1 hour
CUSTOMER_LOOKUP_TTL = 3600  # 1 hour
SESSION_TTL = 86400  # 24 hours

# Connection pool settings
POOL_MAX_CONNECTIONS = 50
POOL_MIN_IDLE = 5
POOL_TIMEOUT = 5


class RedisClient:
    """
    Redis client with connection pooling.
    
    Usage:
        client = RedisClient()
        await client.set('key', 'value')
        value = await client.get('key')
    """
    
    _instance = None
    _pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisClient, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not REDIS_AVAILABLE:
            logger.warning("Redis library not installed, caching disabled")
            self._client = None
            return
        
        if self._pool is None:
            self._create_pool()
        
        self._client = None
    
    def _create_pool(self):
        """Create Redis connection pool."""
        try:
            self._pool = redis.ConnectionPool(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD if REDIS_PASSWORD else None,
                db=REDIS_DB,
                max_connections=POOL_MAX_CONNECTIONS,
                decode_responses=True,
                socket_timeout=POOL_TIMEOUT,
                socket_connect_timeout=POOL_TIMEOUT,
                retry_on_timeout=True
            )
            logger.info(f"✓ Redis pool created: {REDIS_HOST}:{REDIS_PORT}")
        except Exception as e:
            logger.error(f"✗ Failed to create Redis pool: {e}")
            self._pool = None
    
    def _get_client(self) -> Optional['redis.Redis']:
        """Get Redis client from pool."""
        if not REDIS_AVAILABLE or not self._pool:
            return None
        
        try:
            if self._client is None:
                self._client = redis.Redis(connection_pool=self._pool)
                # Test connection
                self._client.ping()
            return self._client
        except Exception as e:
            logger.error(f"Redis connection error: {e}")
            self._client = None
            return None
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        client = self._get_client()
        if not client:
            return None
        
        try:
            value = client.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
                # Try to parse as JSON
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            logger.debug(f"Cache MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            bool: True if successful
        """
        client = self._get_client()
        if not client:
            return False
        
        try:
            # Serialize to JSON if not string
            if not isinstance(value, str):
                value = json.dumps(value)
            
            success = client.setex(key, ttl, value)
            if success:
                logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return success
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if deleted
        """
        client = self._get_client()
        if not client:
            return False
        
        try:
            return client.delete(key) > 0
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        client = self._get_client()
        if not client:
            return False
        
        try:
            return client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching pattern.
        
        Args:
            pattern: Key pattern (e.g., "kb_search:*")
            
        Returns:
            Number of keys deleted
        """
        client = self._get_client()
        if not client:
            return 0
        
        try:
            keys = client.keys(pattern)
            if keys:
                return client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis invalidate error: {e}")
            return 0
    
    async def health_check(self) -> bool:
        """Check Redis connection health."""
        client = self._get_client()
        if not client:
            return False
        
        try:
            return client.ping()
        except Exception:
            return False
    
    def close(self):
        """Close Redis connections."""
        if self._pool:
            self._pool.disconnect()
            logger.info("✓ Redis connections closed")


# Global client instance
_redis_client = None


def get_redis_client() -> RedisClient:
    """Get or create Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client


# =============================================================================
# CACHING DECORATORS
# =============================================================================

def _make_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate cache key from arguments.
    
    Args:
        prefix: Key prefix
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Cache key string
    """
    # Create hash of arguments
    key_data = f"{args}:{sorted(kwargs.items())}"
    key_hash = hashlib.md5(key_data.encode()).hexdigest()
    return f"{prefix}:{key_hash}"


async def cached_kb_search(query: str, category: Optional[str] = None, 
                           max_results: int = 5) -> Optional[List[Dict]]:
    """
    Get knowledge base search from cache.
    
    Args:
        query: Search query
        category: Optional category filter
        max_results: Max results to return
        
    Returns:
        Cached search results or None
    """
    client = get_redis_client()
    key = _make_cache_key("kb_search", query, category=category, max_results=max_results)
    
    result = await client.get(key)
    if result:
        logger.info(f"Cache HIT for KB search: {query[:50]}...")
        return result
    
    return None


async def cache_kb_search(query: str, results: List[Dict], 
                          category: Optional[str] = None,
                          max_results: int = 5) -> bool:
    """
    Cache knowledge base search results.
    
    Args:
        query: Search query
        results: Search results to cache
        category: Optional category filter
        max_results: Max results
        
    Returns:
        bool: True if cached successfully
    """
    client = get_redis_client()
    key = _make_cache_key("kb_search", query, category=category, max_results=max_results)
    
    return await client.set(key, results, ttl=KB_SEARCH_TTL)


async def cached_customer_lookup(identifier: str, identifier_type: str = 'email') -> Optional[Dict]:
    """
    Get customer lookup from cache.
    
    Args:
        identifier: Email or phone
        identifier_type: 'email' or 'phone'
        
    Returns:
        Cached customer data or None
    """
    client = get_redis_client()
    key = f"customer:{identifier_type}:{identifier}"
    
    result = await client.get(key)
    if result:
        logger.info(f"Cache HIT for customer: {identifier}")
        return result
    
    return None


async def cache_customer_lookup(identifier: str, customer_data: Dict,
                                 identifier_type: str = 'email') -> bool:
    """
    Cache customer lookup results.
    
    Args:
        identifier: Email or phone
        customer_data: Customer data to cache
        identifier_type: 'email' or 'phone'
        
    Returns:
        bool: True if cached successfully
    """
    client = get_redis_client()
    key = f"customer:{identifier_type}:{identifier}"
    
    return await client.set(key, customer_data, ttl=CUSTOMER_LOOKUP_TTL)


async def invalidate_customer_cache(identifier: str, identifier_type: str = 'email') -> bool:
    """
    Invalidate customer cache.
    
    Args:
        identifier: Email or phone
        identifier_type: 'email' or 'phone'
        
    Returns:
        bool: True if invalidated
    """
    client = get_redis_client()
    key = f"customer:{identifier_type}:{identifier}"
    
    return await client.delete(key)


# =============================================================================
# MAIN (TESTING)
# =============================================================================

async def main():
    """Test Redis client."""
    print("="*60)
    print("REDIS CLIENT TEST")
    print("="*60)
    
    client = get_redis_client()
    
    # Test connection
    healthy = await client.health_check()
    print(f"Health check: {'✓ PASS' if healthy else '✗ FAIL'}")
    
    if healthy:
        # Test set/get
        await client.set("test_key", {"test": "value"}, ttl=60)
        value = await client.get("test_key")
        print(f"Set/Get test: {'✓ PASS' if value else '✗ FAIL'}")
        
        # Test delete
        await client.delete("test_key")
        value = await client.get("test_key")
        print(f"Delete test: {'✓ PASS' if not value else '✗ FAIL'}")
        
        # Test caching helpers
        await cache_kb_search("test query", [{"title": "Test"}])
        cached = await cached_kb_search("test query")
        print(f"KB cache test: {'✓ PASS' if cached else '✗ FAIL'}")
        
        await cache_customer_lookup("test@example.com", {"id": "123", "email": "test@example.com"})
        cached = await cached_customer_lookup("test@example.com")
        print(f"Customer cache test: {'✓ PASS' if cached else '✗ FAIL'}")
    
    print("="*60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
