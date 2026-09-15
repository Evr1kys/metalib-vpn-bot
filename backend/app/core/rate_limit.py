"""
Advanced Rate Limiting Configuration

Provides multiple rate limit strategies:
- Per-IP for public endpoints
- Per-user for authenticated endpoints
- Per-endpoint for sensitive operations
"""
from typing import Optional, Callable
from fastapi import Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from functools import wraps

from app.core.config import settings
from app.core.logging import logger


def get_user_identifier(request: Request) -> str:
    """
    Extract user identifier for rate limiting.
    
    Priority:
    1. Authenticated user ID (from JWT)
    2. Bot token (X-Bot-Token header)
    3. Client IP address
    
    This ensures authenticated users share limits across IPs,
    while unauthenticated users are limited per IP.
    """
    # Check for authenticated user
    if hasattr(request.state, 'user_id') and request.state.user_id:
        return f"user:{request.state.user_id}"
    
    # Check for bot token
    bot_token = request.headers.get("X-Bot-Token")
    if bot_token:
        # Use first 16 chars of token hash for identification
        import hashlib
        token_hash = hashlib.sha256(bot_token.encode()).hexdigest()[:16]
        return f"bot:{token_hash}"
    
    # Fallback to IP
    return f"ip:{get_remote_address(request)}"


def get_telegram_user_id(request: Request) -> str:
    """
    Extract Telegram user ID for bot-specific rate limiting.
    Useful for preventing abuse via the bot interface.
    """
    # Check for X-Telegram-User-ID header (set by bot)
    tg_user_id = request.headers.get("X-Telegram-User-ID")
    if tg_user_id:
        return f"tg:{tg_user_id}"
    
    return get_user_identifier(request)


# Main rate limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/hour", "100/minute"],  # Global defaults
    storage_uri=settings.redis_url,
    strategy="fixed-window",  # Standard fixed window strategy
)


# ===== Rate Limit Decorators =====

class RateLimitConfig:
    """
    Centralized rate limit configuration for different endpoint types.
    
    Limits are defined as: "X per Y" where Y is second/minute/hour/day
    Multiple limits can be combined: ["10/minute", "100/hour"]
    """
    
    # Authentication endpoints - strict limits to prevent brute force
    AUTH_LOGIN = ["5/minute", "20/hour"]  # 5 attempts per minute, 20 per hour
    AUTH_2FA = ["10/minute", "50/hour"]   # 2FA verification
    AUTH_REFRESH = ["30/minute"]           # Token refresh
    
    # VPN Key endpoints - moderate limits
    VPN_KEY_ACCESS = ["60/minute", "500/hour"]  # Key access (QR, page)
    VPN_PROVISION = ["10/minute", "50/hour"]    # VPN provisioning (expensive operation)
    
    # Subscription operations
    SUBSCRIPTION_CREATE = ["5/minute", "30/hour"]   # Creating subscriptions
    SUBSCRIPTION_READ = ["100/minute"]              # Reading subscription info
    
    # Payment operations - strict limits
    PAYMENT_CREATE = ["5/minute", "20/hour"]       # Creating payments
    PAYMENT_WEBHOOK = ["1000/minute"]              # Webhook callbacks (from payment provider)
    
    # Admin operations
    ADMIN_READ = ["200/minute"]                    # Reading data
    ADMIN_WRITE = ["30/minute", "200/hour"]        # Writing/updating data
    
    # Referral system
    REFERRAL_CREATE = ["10/minute", "100/hour"]   # Creating referral links
    REFERRAL_APPLY = ["5/minute", "20/hour"]      # Applying referral codes
    
    # Support tickets
    SUPPORT_CREATE = ["5/minute", "30/hour"]      # Creating tickets
    SUPPORT_MESSAGE = ["20/minute", "200/hour"]   # Sending messages
    
    # Public API
    PUBLIC_READ = ["100/minute", "1000/hour"]     # Public info endpoints
    
    # Bot internal API
    BOT_INTERNAL = ["500/minute"]                  # High limit for bot operations


# Rate limit exceeded response
def rate_limit_exceeded_response(request: Request, exc) -> Response:
    """
    Custom response for rate limit exceeded.
    Includes Retry-After header for proper client handling.
    """
    from fastapi.responses import JSONResponse
    
    retry_after = getattr(exc, 'retry_after', 60)
    
    logger.warning(
        f"Rate limit exceeded: {request.url.path} "
        f"from {get_remote_address(request)} "
        f"(identifier: {get_user_identifier(request)})"
    )
    
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "detail": "Слишком много запросов. Пожалуйста, подождите.",
            "retry_after": retry_after
        },
        headers={
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": str(getattr(exc, 'limit', 'unknown')),
        }
    )


# ===== Utility Functions =====

def apply_rate_limits(limiter: Limiter, limits: list[str], key_func: Optional[Callable] = None):
    """
    Decorator factory for applying multiple rate limits to an endpoint.
    
    Usage:
        @apply_rate_limits(limiter, RateLimitConfig.AUTH_LOGIN)
        async def login(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        # Apply each limit
        for limit in limits:
            wrapper = limiter.limit(
                limit,
                key_func=key_func or get_user_identifier
            )(wrapper)
        
        return wrapper
    return decorator


# ===== IP Whitelist for Internal Services =====

WHITELISTED_IPS = {
    "127.0.0.1",
    "172.16.0.0/12",  # Docker internal
    "10.0.0.0/8",     # Internal network
}


def is_whitelisted(request: Request) -> bool:
    """Check if request IP is whitelisted (bypasses rate limits)"""
    import ipaddress
    
    client_ip = get_remote_address(request)
    if not client_ip:
        return False
    
    try:
        ip = ipaddress.ip_address(client_ip)
        
        for network in WHITELISTED_IPS:
            if "/" in network:
                if ip in ipaddress.ip_network(network, strict=False):
                    return True
            elif client_ip == network:
                return True
                
    except ValueError:
        pass
    
    return False


def conditional_rate_limit(limits: list[str], key_func: Optional[Callable] = None):
    """
    Rate limit decorator that skips whitelisted IPs.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if is_whitelisted(request):
                return await func(request, *args, **kwargs)
            
            # Apply rate limiting
            return await func(request, *args, **kwargs)
        
        # Apply limits
        for limit in limits:
            wrapper = limiter.limit(
                limit,
                key_func=key_func or get_user_identifier,
                exempt_when=is_whitelisted
            )(wrapper)
        
        return wrapper
    return decorator
