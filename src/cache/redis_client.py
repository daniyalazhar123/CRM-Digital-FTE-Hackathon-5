"""
CRM Digital FTE — Redis Cache Client

Provides:
- Connection pooling via redis.asyncio
- REDIS_URL parsing (supports redis:// or rediss:// with auth)
- Graceful reconnect
- Configurable TTL (defaults: KB 1hr, customer 1hr, ticket 30min)
- Cache helpers: cached_kb_search, cached_customer_lookup, cached_ticket_lookup
"""

import os
import json
import logging
from typing import Optional, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
KB_SEARCH_TTL = int(os.getenv("REDIS_KB_TTL", "3600"))       # 1 hour
CUSTOMER_TTL = int(os.getenv("REDIS_CUSTOMER_TTL", "3600"))   # 1 hour
TICKET_TTL = int(os.getenv("REDIS_TICKET_TTL", "1800"))       # 30 min
DEFAULT_TTL = int(os.getenv("REDIS_DEFAULT_TTL", "3600"))     # 1 hour

POOL_SIZE = int(os.getenv("REDIS_POOL_SIZE", "20"))
SOCKET_TIMEOUT = int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))

# ── Client ─────────────────────────────────────────────────────────────────────

class RedisCache:
    """Async Redis cache with auto-reconnect and connection pooling.

    Usage:
        cache = RedisCache()
        await cache.set("key", value, ttl=300)
        val = await cache.get("key")
        ttl = await cache.ttl("key")
        await cache.close()
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._redis = None
            cls._instance._pool = None
        return cls._instance

    def __init__(self):
        pass

    async def _connect(self):
        """Lazy connect — creates connection pool on first use."""
        if self._redis is not None:
            try:
                await self._redis.ping()
                return
            except Exception:
                logger.warning("[REDIS] Connection lost, reconnecting...")
                self._redis = None
                self._pool = None

        try:
            import redis.asyncio as aioredis
            parsed = urlparse(REDIS_URL)

            password = None
            if parsed.password:
                password = parsed.password

            self._pool = aioredis.ConnectionPool.from_url(
                REDIS_URL,
                max_connections=POOL_SIZE,
                decode_responses=True,
                socket_timeout=SOCKET_TIMEOUT,
                socket_connect_timeout=SOCKET_TIMEOUT,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            self._redis = aioredis.Redis(connection_pool=self._pool)
            await self._redis.ping()
            logger.info("[REDIS] Connected to %s@%s/%s",
                        parsed.hostname, parsed.port or 6379, (parsed.path or "/0").lstrip("/"))
        except ImportError:
            logger.warning("[REDIS] redis.asyncio not installed — caching disabled")
        except Exception as e:
            logger.warning("[REDIS] Connection failed: %s", e)
            self._redis = None
            self._pool = None

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache. Returns None if missing."""
        await self._connect()
        if self._redis is None:
            return None
        try:
            val = await self._redis.get(key)
            if val is None:
                return None
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return val
        except Exception as e:
            logger.warning("[REDIS] GET error: %s", e)
            return None

    async def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
        """Set a value in cache with TTL (seconds)."""
        await self._connect()
        if self._redis is None:
            return False
        try:
            if not isinstance(value, str):
                value = json.dumps(value)
            await self._redis.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.warning("[REDIS] SET error: %s", e)
            return False

    async def ttl(self, key: str) -> int:
        """Get remaining TTL for a key. Returns -2 if missing, -1 if no TTL."""
        await self._connect()
        if self._redis is None:
            return -2
        try:
            return await self._redis.ttl(key)
        except Exception:
            return -2

    async def delete(self, key: str) -> bool:
        """Delete a key."""
        await self._connect()
        if self._redis is None:
            return False
        try:
            n = await self._redis.delete(key)
            return n > 0
        except Exception as e:
            logger.warning("[REDIS] DELETE error: %s", e)
            return False

    async def health_check(self) -> bool:
        """Ping Redis. Returns True if connected."""
        try:
            if self._redis is None:
                await self._connect()
            if self._redis is None:
                return False
            return await self._redis.ping()
        except Exception:
            return False

    async def close(self):
        """Close all connections (async)."""
        if self._pool:
            await self._pool.disconnect()
            logger.info("[REDIS] Connections closed")
        self._redis = None
        self._pool = None

    # Synchronous close for backward compatibility
    def close_sync(self):
        """Close all connections (sync wrapper)."""
        try:
            asyncio.run(self.close())
        except RuntimeError:
            # Already in event loop — skip sync close
            pass


# ── Singleton ──────────────────────────────────────────────────────────────────

_cache_instance: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
    return _cache_instance


# ── Helper functions for specific cache types ──────────────────────────────────

async def cached_kb_search(query: str, max_results: int = 5) -> Optional[Any]:
    """Return cached KB search results or None."""
    cache = get_cache()
    key = f"kb:{query[:100].strip().lower()}:{max_results}"
    return await cache.get(key)


async def cache_kb_search(query: str, results: Any, max_results: int = 5) -> bool:
    """Cache KB search results."""
    cache = get_cache()
    key = f"kb:{query[:100].strip().lower()}:{max_results}"
    return await cache.set(key, results, ttl=KB_SEARCH_TTL)


async def cached_customer_lookup(identifier: str) -> Optional[Any]:
    """Return cached customer context or None."""
    cache = get_cache()
    key = f"customer:{identifier}"
    return await cache.get(key)


async def cache_customer_lookup(identifier: str, data: Any) -> bool:
    """Cache customer context."""
    cache = get_cache()
    key = f"customer:{identifier}"
    return await cache.set(key, data, ttl=CUSTOMER_TTL)


async def cached_ticket_lookup(ticket_id: str) -> Optional[Any]:
    """Return cached ticket data or None."""
    cache = get_cache()
    key = f"ticket:{ticket_id}"
    return await cache.get(key)


async def cache_ticket_lookup(ticket_id: str, data: Any) -> bool:
    """Cache ticket data."""
    cache = get_cache()
    key = f"ticket:{ticket_id}"
    return await cache.set(key, data, ttl=TICKET_TTL)


async def invalidate_customer_cache(identifier: str) -> bool:
    """Remove customer from cache (e.g. after data update)."""
    cache = get_cache()
    return await cache.delete(f"customer:{identifier}")


async def invalidate_kb_cache(query: str, max_results: int = 5) -> bool:
    """Remove a specific KB search from cache."""
    cache = get_cache()
    return await cache.delete(f"kb:{query[:100].strip().lower()}:{max_results}")


# ═══════════════════════════════════════════════════════════════════════════════
# Backward-compatible aliases (for existing tests)
# ═══════════════════════════════════════════════════════════════════════════════

RedisClient = RedisCache
get_redis_client = get_cache

# Legacy config constants (parsed from REDIS_URL for compat)
REDIS_AVAILABLE = True  # Always True; graceful degradation handles connection failures
CUSTOMER_LOOKUP_TTL = CUSTOMER_TTL

# Re-export REDIS_HOST / REDIS_PORT / REDIS_PASSWORD / REDIS_DB (parsed from URL)
_parsed_url = urlparse(REDIS_URL)
REDIS_HOST = _parsed_url.hostname or "localhost"
REDIS_PORT = _parsed_url.port or 6379
REDIS_PASSWORD = _parsed_url.password or ""
REDIS_DB = int((_parsed_url.path or "/0").lstrip("/") or 0)


def _make_cache_key(prefix: str, *args, **kwargs) -> str:
    """Legacy cache key generator — kept for backward compatibility."""
    parts = [prefix]
    parts.extend(str(a) for a in args)
    parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return ":".join(parts)
