"""
IP Whitelist middleware for admin access control
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Set, Optional
import ipaddress
import logging

from app.core.config import settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

# Admin endpoints that require IP whitelist
ADMIN_PROTECTED_PATHS = [
    "/api/v1/admin",
    "/api/v1/auth/admin",
    "/api/v1/servers",
    "/api/v1/analytics",
    "/api/v1/audit-logs",
    "/api/v1/broadcast",
]


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    Middleware to restrict admin endpoints to whitelisted IPs
    
    Whitelist can be configured via:
    1. Environment variable: ADMIN_IP_WHITELIST (comma-separated)
    2. Redis key: admin:ip_whitelist (JSON array)
    3. Database (for dynamic updates)
    """
    
    def __init__(self, app, whitelist: Set[str] = None, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled
        self.static_whitelist = whitelist or set()
        
        # Parse whitelist from settings
        if settings.admin_ip_whitelist:
            for ip in settings.admin_ip_whitelist.split(","):
                ip = ip.strip()
                if ip:
                    self.static_whitelist.add(ip)
        
        # Always allow localhost
        self.static_whitelist.add("127.0.0.1")
        self.static_whitelist.add("::1")
        self.static_whitelist.add("localhost")
        
        logger.info(f"IP Whitelist middleware initialized with {len(self.static_whitelist)} IPs")
    
    async def dispatch(self, request: Request, call_next):
        # Skip if disabled
        if not self.enabled:
            return await call_next(request)
        
        # Check if path requires protection
        path = request.url.path
        requires_protection = any(
            path.startswith(protected) for protected in ADMIN_PROTECTED_PATHS
        )
        
        if not requires_protection:
            return await call_next(request)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Check whitelist
        if not await self._is_ip_allowed(client_ip):
            logger.warning(
                f"IP whitelist blocked: {client_ip} tried to access {path}"
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "Access denied. Your IP is not in the whitelist.",
                    "ip": client_ip
                }
            )
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract real client IP from request"""
        # Check X-Forwarded-For header (from reverse proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take first IP in chain (client IP)
            return forwarded.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct connection IP
        if request.client:
            return request.client.host
        
        return "unknown"
    
    async def _is_ip_allowed(self, ip: str) -> bool:
        """Check if IP is in whitelist"""
        # Check static whitelist
        if ip in self.static_whitelist:
            return True
        
        # Check CIDR ranges in static whitelist
        try:
            client_ip = ipaddress.ip_address(ip)
            for allowed in self.static_whitelist:
                try:
                    if "/" in allowed:
                        network = ipaddress.ip_network(allowed, strict=False)
                        if client_ip in network:
                            return True
                except ValueError:
                    continue
        except ValueError:
            pass
        
        # Check dynamic whitelist from Redis
        try:
            redis = await get_redis()
            dynamic_list = await redis.smembers("admin:ip_whitelist")
            if ip in dynamic_list:
                return True
            
            # Check CIDR in dynamic list
            try:
                client_ip = ipaddress.ip_address(ip)
                for allowed in dynamic_list:
                    if "/" in allowed:
                        try:
                            network = ipaddress.ip_network(allowed, strict=False)
                            if client_ip in network:
                                return True
                        except ValueError:
                            continue
            except ValueError:
                pass
                
        except Exception as e:
            logger.warning(f"Failed to check Redis whitelist: {e}")
        
        return False


# API functions for managing whitelist

async def add_to_whitelist(ip: str) -> bool:
    """Add IP to dynamic whitelist"""
    try:
        redis = await get_redis()
        await redis.sadd("admin:ip_whitelist", ip)
        logger.info(f"Added {ip} to IP whitelist")
        return True
    except Exception as e:
        logger.error(f"Failed to add IP to whitelist: {e}")
        return False


async def remove_from_whitelist(ip: str) -> bool:
    """Remove IP from dynamic whitelist"""
    try:
        redis = await get_redis()
        await redis.srem("admin:ip_whitelist", ip)
        logger.info(f"Removed {ip} from IP whitelist")
        return True
    except Exception as e:
        logger.error(f"Failed to remove IP from whitelist: {e}")
        return False


async def get_whitelist() -> Set[str]:
    """Get current dynamic whitelist"""
    try:
        redis = await get_redis()
        return await redis.smembers("admin:ip_whitelist")
    except Exception as e:
        logger.error(f"Failed to get IP whitelist: {e}")
        return set()


async def clear_whitelist() -> bool:
    """Clear dynamic whitelist"""
    try:
        redis = await get_redis()
        await redis.delete("admin:ip_whitelist")
        logger.info("Cleared IP whitelist")
        return True
    except Exception as e:
        logger.error(f"Failed to clear IP whitelist: {e}")
        return False


def add_ip_whitelist_middleware(app, enabled: bool = True):
    """Add IP whitelist middleware to FastAPI app"""
    # Only enable in production or when explicitly configured
    should_enable = enabled and settings.environment == "production"
    
    app.add_middleware(
        IPWhitelistMiddleware,
        enabled=should_enable
    )
    
    if should_enable:
        logger.info("IP whitelist middleware enabled for admin endpoints")
    else:
        logger.info("IP whitelist middleware disabled")
