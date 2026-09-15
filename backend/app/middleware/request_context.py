"""
Request context middleware - adds request_id and context to all requests
"""
import uuid
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.audit import (
    request_id_ctx, 
    user_id_ctx, 
    admin_id_ctx, 
    ip_address_ctx,
    logger
)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds request context for logging and tracing
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        
        # Get client IP (considering proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip_address = forwarded_for.split(",")[0].strip()
        else:
            ip_address = request.client.host if request.client else "unknown"
        
        # Set context variables
        request_id_token = request_id_ctx.set(request_id)
        ip_address_token = ip_address_ctx.set(ip_address)
        
        # Add request_id to request state
        request.state.request_id = request_id
        request.state.ip_address = ip_address
        
        # Track request timing
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.4f}"
            
            # Log request
            logger.bind(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration=f"{process_time:.4f}s",
                ip=ip_address,
            ).info(f"{request.method} {request.url.path} - {response.status_code}")
            
            return response
            
        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            logger.bind(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                duration=f"{process_time:.4f}s",
                ip=ip_address,
                error=str(e),
            ).error(f"{request.method} {request.url.path} - ERROR: {e}")
            raise
            
        finally:
            # Reset context variables
            request_id_ctx.reset(request_id_token)
            ip_address_ctx.reset(ip_address_token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all responses
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS for production
        if not request.url.hostname in ["localhost", "127.0.0.1"]:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class ContentSecurityPolicyMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds Content-Security-Policy header
    """
    
    CSP_POLICY = "; ".join([
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' https://telegram.org",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: https:",
        "font-src 'self' data:",
        "connect-src 'self' https://api.metalib.xyz wss://api.metalib.xyz",
        "frame-ancestors 'self' https://telegram.org https://web.telegram.org",
        "base-uri 'self'",
        "form-action 'self'",
    ])
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Only add CSP for HTML responses
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            response.headers["Content-Security-Policy"] = self.CSP_POLICY
        
        return response
