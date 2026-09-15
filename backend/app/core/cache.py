"""
Redis caching utilities for frequently accessed data
"""
import json
from typing import Optional, Any, Callable, TypeVar
from functools import wraps
from datetime import timedelta
import hashlib
import logging

from app.core.redis import get_redis

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Cache TTL presets
CACHE_TTL = {
    "plans": 3600,          # 1 hour - plans rarely change
    "servers": 300,         # 5 minutes - server status may change
    "dashboard_stats": 60,  # 1 minute - stats should be relatively fresh
    "user_profile": 300,    # 5 minutes
    "analytics": 600,       # 10 minutes
    "default": 300,         # 5 minutes default
}


async def get_cached(key: str) -> Optional[Any]:
    """Get value from cache"""
    try:
        redis = await get_redis()
        data = await redis.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.warning(f"Cache get failed for {key}: {e}")
        return None


async def set_cached(key: str, value: Any, ttl: int = None) -> bool:
    """Set value in cache"""
    try:
        redis = await get_redis()
        ttl = ttl or CACHE_TTL["default"]
        await redis.setex(key, ttl, json.dumps(value, default=str))
        return True
    except Exception as e:
        logger.warning(f"Cache set failed for {key}: {e}")
        return False


async def delete_cached(key: str) -> bool:
    """Delete value from cache"""
    try:
        redis = await get_redis()
        await redis.delete(key)
        return True
    except Exception as e:
        logger.warning(f"Cache delete failed for {key}: {e}")
        return False


async def invalidate_pattern(pattern: str) -> int:
    """Delete all keys matching pattern"""
    try:
        redis = await get_redis()
        keys = []
        async for key in redis.scan_iter(match=pattern):
            keys.append(key)
        
        if keys:
            await redis.delete(*keys)
        return len(keys)
    except Exception as e:
        logger.warning(f"Cache invalidate failed for {pattern}: {e}")
        return 0


def make_cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments"""
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
    key_str = ":".join(key_parts)
    return hashlib.md5(key_str.encode()).hexdigest()[:16]


def cached(
    prefix: str,
    ttl: int = None,
    key_builder: Callable = None
):
    """
    Decorator for caching function results
    
    Usage:
        @cached("plans", ttl=3600)
        async def get_plans():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = f"{prefix}:{key_builder(*args, **kwargs)}"
            else:
                cache_key = f"{prefix}:{make_cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_value = await get_cached(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value
            
            # Execute function
            logger.debug(f"Cache miss: {cache_key}")
            result = await func(*args, **kwargs)
            
            # Store in cache
            cache_ttl = ttl or CACHE_TTL.get(prefix, CACHE_TTL["default"])
            await set_cached(cache_key, result, cache_ttl)
            
            return result
        return wrapper
    return decorator


# Specific cache functions for common operations

async def cache_plans(plans: list) -> bool:
    """Cache plans list"""
    return await set_cached("plans:all", plans, CACHE_TTL["plans"])


async def get_cached_plans() -> Optional[list]:
    """Get cached plans"""
    return await get_cached("plans:all")


async def invalidate_plans_cache():
    """Invalidate plans cache"""
    await invalidate_pattern("plans:*")


async def cache_servers(servers: list) -> bool:
    """Cache servers list"""
    return await set_cached("servers:all", servers, CACHE_TTL["servers"])


async def get_cached_servers() -> Optional[list]:
    """Get cached servers"""
    return await get_cached("servers:all")


async def invalidate_servers_cache():
    """Invalidate servers cache"""
    await invalidate_pattern("servers:*")


async def cache_dashboard_stats(stats: dict) -> bool:
    """Cache dashboard stats"""
    return await set_cached("dashboard:stats", stats, CACHE_TTL["dashboard_stats"])


async def get_cached_dashboard_stats() -> Optional[dict]:
    """Get cached dashboard stats"""
    return await get_cached("dashboard:stats")


async def cache_user_subscription(user_id: str, subscription: dict) -> bool:
    """Cache user subscription"""
    return await set_cached(f"subscription:{user_id}", subscription, CACHE_TTL["user_profile"])


async def get_cached_user_subscription(user_id: str) -> Optional[dict]:
    """Get cached user subscription"""
    return await get_cached(f"subscription:{user_id}")


async def invalidate_user_subscription(user_id: str):
    """Invalidate user subscription cache"""
    await delete_cached(f"subscription:{user_id}")


# Rate limiting cache functions

async def check_rate_limit(
    key: str,
    max_requests: int,
    window_seconds: int
) -> tuple[bool, int]:
    """
    Check if rate limit is exceeded
    Returns (is_allowed, remaining_requests)
    """
    try:
        redis = await get_redis()
        cache_key = f"ratelimit:{key}"
        
        current = await redis.get(cache_key)
        if current is None:
            await redis.setex(cache_key, window_seconds, 1)
            return True, max_requests - 1
        
        current_count = int(current)
        if current_count >= max_requests:
            return False, 0
        
        await redis.incr(cache_key)
        return True, max_requests - current_count - 1
        
    except Exception as e:
        logger.warning(f"Rate limit check failed: {e}")
        return True, max_requests  # Allow on error


# Cache warming function

async def warm_cache():
    """Warm up frequently used caches on startup"""
    logger.info("Warming up cache...")
    
    # This would be called from app startup
    # to pre-populate caches with commonly accessed data
    
    # Example: pre-fetch and cache plans
    # plans = await fetch_plans_from_db()
    # await cache_plans(plans)
    
    logger.info("Cache warming complete")
