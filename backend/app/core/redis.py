"""
Redis client and caching utilities
"""
from typing import Optional, Any
import json
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.logging import logger

# Global Redis client
redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Get Redis client instance"""
    global redis_client
    
    if redis_client is None:
        redis_client = await aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
        logger.info("Redis client initialized")
    
    return redis_client


async def close_redis() -> None:
    """Close Redis connection"""
    global redis_client
    
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")


# ===== Caching Utilities =====

async def cache_set(key: str, value: Any, expire: int = 3600) -> bool:
    """
    Set cache value
    
    Args:
        key: Cache key
        value: Value to cache (will be JSON serialized)
        expire: TTL in seconds
    
    Returns:
        True if successful
    """
    try:
        redis = await get_redis()
        serialized = json.dumps(value)
        await redis.setex(key, expire, serialized)
        return True
    except Exception as e:
        logger.error(f"Cache set error: {e}")
        return False


async def cache_get(key: str) -> Optional[Any]:
    """
    Get cache value
    
    Args:
        key: Cache key
    
    Returns:
        Cached value or None
    """
    try:
        redis = await get_redis()
        value = await redis.get(key)
        
        if value:
            return json.loads(value)
        
        return None
    except Exception as e:
        logger.error(f"Cache get error: {e}")
        return None


async def cache_delete(key: str) -> bool:
    """Delete cache key"""
    try:
        redis = await get_redis()
        await redis.delete(key)
        return True
    except Exception as e:
        logger.error(f"Cache delete error: {e}")
        return False


async def cache_delete_pattern(pattern: str) -> int:
    """
    Delete all keys matching pattern
    
    Args:
        pattern: Redis key pattern (e.g., "user:*")
    
    Returns:
        Number of deleted keys
    """
    try:
        redis = await get_redis()
        keys = await redis.keys(pattern)
        
        if keys:
            return await redis.delete(*keys)
        
        return 0
    except Exception as e:
        logger.error(f"Cache delete pattern error: {e}")
        return 0


async def cache_exists(key: str) -> bool:
    """Check if cache key exists"""
    try:
        redis = await get_redis()
        return await redis.exists(key) > 0
    except Exception as e:
        logger.error(f"Cache exists error: {e}")
        return False


# ===== Rate Limiting =====

async def rate_limit_check(key: str, max_requests: int, window_seconds: int) -> bool:
    """
    Check rate limit using sliding window
    
    Args:
        key: Rate limit key (e.g., "ratelimit:webhook:192.168.1.1")
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds
    
    Returns:
        True if request is allowed, False if rate limited
    """
    try:
        redis = await get_redis()
        current = await redis.get(key)
        
        if current is None:
            # First request in window
            await redis.setex(key, window_seconds, "1")
            return True
        
        count = int(current)
        
        if count >= max_requests:
            return False
        
        # Increment counter
        await redis.incr(key)
        return True
        
    except Exception as e:
        logger.error(f"Rate limit check error: {e}")
        # Fail open (allow request on error)
        return True


# ===== Distributed Locks =====

async def acquire_lock(key: str, timeout: int = 10) -> bool:
    """
    Acquire distributed lock
    
    Args:
        key: Lock key
        timeout: Lock timeout in seconds
    
    Returns:
        True if lock acquired
    """
    try:
        redis = await get_redis()
        return await redis.set(f"lock:{key}", "1", nx=True, ex=timeout)
    except Exception as e:
        logger.error(f"Acquire lock error: {e}")
        return False


async def release_lock(key: str) -> bool:
    """Release distributed lock"""
    try:
        redis = await get_redis()
        await redis.delete(f"lock:{key}")
        return True
    except Exception as e:
        logger.error(f"Release lock error: {e}")
        return False
