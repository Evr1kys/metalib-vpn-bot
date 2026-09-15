"""
VPN Agent Main Application
"""
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.config import settings
from app.api import router
from loguru import logger

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | <level>{message}</level>"
)

# Create FastAPI app
app = FastAPI(
    title="VPN Agent API",
    description="VPN server management agent",
    version="1.0.0"
)

# Add CORS middleware (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict to backend IP
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    """Startup event"""
    logger.info("VPN Agent started")
    logger.info(f"WireGuard enabled: {settings.wireguard_enabled}")
    logger.info(f"OpenVPN enabled: {settings.openvpn_enabled}")
    logger.info(f"Amnezia enabled: {settings.amnezia_enabled}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event"""
    logger.info("VPN Agent stopped")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.agent_host,
        port=settings.agent_port,
        reload=False,
        log_level=settings.log_level.lower()
    )
