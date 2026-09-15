"""
API Access Control Middleware

Restricts bot-related endpoints to authorized clients only.
Admin and auth endpoints remain public.
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Set
from app.core.config import settings
from app.core.logging import logger


# Bot endpoints that require bot token authentication
BOT_ENDPOINTS_PREFIX = [
    "/api/v1/users",
    "/api/v1/subscriptions",
    "/api/v1/payments",
    "/api/v1/devices",
    "/api/v1/referrals",
    "/api/v1/notifications",
]

# Public endpoints (no authentication required)
PUBLIC_ENDPOINTS = [
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    "/api/v1/health",
    "/api/v1/webhooks/",  # Webhooks have their own signature verification
    "/api/v1/web/",  # Web public endpoints (auth, etc.)
    "/api/v1/plans",  # Plans are public for website pricing
]

# Admin-only endpoints (require admin JWT, no bot token)
ADMIN_ONLY_ENDPOINTS = [
    "/api/v1/admin",
    "/api/v1/auth",
    "/api/v1/servers",
    "/api/v1/vpn",
    "/api/v1/stats",
    "/api/v1/broadcast",
    "/api/v1/promocodes",
]


class BotAccessMiddleware(BaseHTTPMiddleware):
    """
    Middleware to restrict bot-related API endpoints to authorized clients.
    
    Authentication methods:
    1. Bot Token: X-Bot-Token header with settings.bot_api_token (bot only)
    2. Admin JWT: Bearer token in Authorization header (admin panel only)
    
    Public endpoints (no auth):
    - /docs, /redoc, /openapi.json
    - /health
    - /webhooks/* (have signature verification)
    
    Admin-only endpoints (JWT required, no bot token):
    - /api/v1/admin/*
    - /api/v1/auth/*
    - /api/v1/servers/*
    - /api/v1/vpn/*
    - /api/v1/stats
    - /api/v1/broadcast
    - /api/v1/promocodes
    
    Bot endpoints (Bot Token required OR Admin JWT):
    - /api/v1/users
    - /api/v1/plans
    - /api/v1/subscriptions
    - /api/v1/payments
    - /api/v1/devices
    - /api/v1/referrals
    """
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path.rstrip('/')  # Normalize path
        
        # Allow public endpoints
        for endpoint in PUBLIC_ENDPOINTS:
            endpoint_normalized = endpoint.rstrip('/')
            if path == endpoint_normalized or path.startswith(endpoint_normalized + '/'):
                return await call_next(request)
        
        # Admin-only endpoints - require JWT, reject bot token
        if any(path.startswith(endpoint) for endpoint in ADMIN_ONLY_ENDPOINTS):
            auth_header = request.headers.get("Authorization")
            bot_token = request.headers.get("X-Bot-Token")
            
            # Reject bot token attempts
            if bot_token and not auth_header:
                logger.warning(f"Bot token used on admin endpoint: {path} from {request.client.host}")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Admin authentication required"}
                )
            
            # Require JWT (will be validated by endpoint dependencies)
            if not auth_header or not auth_header.startswith("Bearer "):
                logger.warning(f"Unauthorized admin endpoint access: {path} from {request.client.host}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Admin JWT token required"}
                )
            
            logger.debug(f"Admin access granted: {path}")
            return await call_next(request)
        
        # Bot endpoints - require bot token OR admin JWT
        if any(path.startswith(endpoint) for endpoint in BOT_ENDPOINTS_PREFIX):
            # Check for bot token
            bot_token = request.headers.get("X-Bot-Token")
            auth_header = request.headers.get("Authorization")
            
            # Allow if bot token matches
            if bot_token and bot_token == settings.bot_api_token:
                logger.debug(f"Bot access granted: {path}")
                return await call_next(request)
            
            # Allow if JWT bearer token present (will be validated by endpoint dependencies)
            if auth_header and auth_header.startswith("Bearer "):
                logger.debug(f"Admin access to bot endpoint: {path}")
                return await call_next(request)
            
            # No valid authentication
            logger.warning(f"Unauthorized bot endpoint access attempt: {path} from {request.client.host}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Bot token or admin JWT required"}
            )
        
        # All other endpoints - deny by default
        logger.warning(f"Access denied to unknown endpoint: {path} from {request.client.host}")
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "Access denied"}
        )


def add_bot_access_middleware(app):
    """Add bot access middleware to FastAPI app"""
    app.add_middleware(BotAccessMiddleware)
    logger.info("Bot access control middleware enabled")
