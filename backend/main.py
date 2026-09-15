"""
FastAPI Main Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
import sentry_sdk
import uuid
import re

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.core.database import init_db, close_db
from app.core.redis import get_redis, close_redis
from app.core.prometheus import setup_prometheus
from app.api.v1 import api_router
from app.middleware import add_bot_access_middleware
from app.middleware.request_context import RequestContextMiddleware


# Setup logging
setup_logging()

# Setup Sentry (if configured)
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
    )


# Rate limiter
limiter = Limiter(key_func=get_remote_address)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add comprehensive security headers to all responses"""
    async def dispatch(self, request: Request, call_next):
        # Add request ID for tracing
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        response = await call_next(request)
        
        # Request ID for tracing
        response.headers["X-Request-ID"] = request_id
        
        # Core security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Content Security Policy for API responses
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        
        # HSTS for production (2 years + preload ready)
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        
        # Remove sensitive headers
        for header in ["Server", "X-Powered-By"]:
            if header in response.headers:
                del response.headers[header]
        
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan"""
    # Startup
    logger.info("Starting MetaLib VPN Bot API...")
    
    # Initialize Redis
    await get_redis()
    logger.info("Redis connected")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    logger.info(f"API started on {settings.api_host}:{settings.api_port}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    
    # Close HTTP clients
    try:
        from app.integrations.platega import platega_client
        await platega_client.close()
        logger.info("Platega client closed")
    except Exception as e:
        logger.warning(f"Error closing Platega client: {e}")
    
    await close_redis()
    await close_db()
    logger.info("Shutdown complete")


# Create FastAPI app
is_dev = settings.environment == "development" or settings.debug

app = FastAPI(
    title="MetaLib VPN Bot API",
    description="API for VPN subscription bot with multi-server infrastructure",
    version="1.0.0",
    docs_url="/docs" if is_dev else None,
    redoc_url="/redoc" if is_dev else None,
    openapi_url="/openapi.json" if is_dev else None,
    lifespan=lifespan,
)

# Add security headers middleware (first in chain)
app.add_middleware(SecurityHeadersMiddleware)

# Add request context middleware for logging
app.add_middleware(RequestContextMiddleware)

# Trusted Host middleware (prevents host header attacks)
if settings.environment == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["metalib.xyz", "*.metalib.xyz", "vpn.metalib.xyz", "localhost", "backend", "127.0.0.1"]
    )

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware with strict origins
allowed_origins = settings.api_cors_origins if settings.api_cors_origins else [
    "https://metalib.xyz",
    "https://vpn.metalib.xyz",
    "https://admin.metalib.xyz"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Bot-Token", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
    max_age=600,  # Cache preflight for 10 minutes
)

# Bot access control middleware
add_bot_access_middleware(app)

# Setup Prometheus metrics
setup_prometheus(app)


# Health check endpoint
@app.get("/health")
@app.get("/api/v1/health")
async def health_check():
    """Health check"""
    return {
        "status": "ok",
        "environment": settings.environment,
        "version": "1.0.0"
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MetaLib VPN Bot API",
        "version": "1.0.0",
        "docs": "/docs" if settings.debug else None,
    }


# Include API router
app.include_router(api_router, prefix="/api/v1")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Never expose internal errors in production
    is_development = settings.environment == "development" or settings.debug
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if is_development else "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
