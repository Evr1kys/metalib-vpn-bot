"""
Servers endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.models import Server, ServerStatus, ManagementType
from app.services.server_orchestrator import ServerOrchestrator
from app.api.deps import get_current_admin, AdminUser
from app.core.security import encrypt_data

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class ServerCreateRequest(BaseModel):
    """Server creation request"""
    name: str
    location: str  # for frontend compatibility
    host: str  # IP address - for frontend compatibility
    port: int = 443
    vpn_type: str = "xray"
    max_users: int = 100
    priority: int = 0
    is_active: bool = True
    api_url: Optional[str] = None
    api_key: Optional[str] = None


class ServerUpdateRequest(BaseModel):
    """Server update request"""
    name: Optional[str] = None
    location: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    vpn_type: Optional[str] = None
    max_users: Optional[int] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    api_url: Optional[str] = None
    api_key: Optional[str] = None


class ServerResponse(BaseModel):
    """Server response"""
    id: str
    name: str
    location: str  # region renamed to location for frontend
    host: str  # ip_address renamed to host for frontend
    port: int
    vpn_type: str
    status: str
    current_load: int  # current_users renamed for frontend
    max_users: int
    priority: int
    is_active: bool
    total_bandwidth: int = 0  # all-time total bandwidth in bytes
    current_bandwidth: int = 0  # current period bandwidth in bytes
    last_health_check: Optional[str] = None
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[ServerResponse])
@limiter.limit("30/minute")
async def list_servers(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """List all servers"""
    stmt = select(Server)
    result = await db.execute(stmt)
    all_servers = result.scalars().all()
    
    return [
        ServerResponse(
            id=str(server.id),
            name=server.name,
            location=server.region,
            host=str(server.ip_address),
            port=443,  # default
            vpn_type=server.server_metadata.get("vpn_type", "xray") if server.server_metadata else "xray",
            status=server.status.value,
            current_load=server.current_users,
            max_users=server.max_users,
            priority=server.server_metadata.get("priority", 0) if server.server_metadata else 0,
            is_active=server.is_active,
            total_bandwidth=server.total_bandwidth or 0,
            current_bandwidth=server.current_bandwidth or 0,
            last_health_check=server.last_health_check.isoformat() if server.last_health_check else None,
        )
        for server in all_servers
    ]


@router.post("/", response_model=ServerResponse)
@limiter.limit("10/minute")
async def create_server(
    request: Request,
    server_data: ServerCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Create new server"""
    # Encrypt API key if provided
    api_key_encrypted = encrypt_data(server_data.api_key) if server_data.api_key else None
    
    server = Server(
        name=server_data.name,
        region=server_data.location,
        ip_address=server_data.host,
        management_type=ManagementType.AGENT,
        agent_url=server_data.api_url,
        agent_token=api_key_encrypted,
        max_users=server_data.max_users,
        status=ServerStatus.HEALTHY,
        is_active=server_data.is_active,
        server_metadata={
            "vpn_type": server_data.vpn_type,
            "priority": server_data.priority,
            "port": server_data.port,
        }
    )
    
    db.add(server)
    await db.commit()
    await db.refresh(server)
    
    return ServerResponse(
        id=str(server.id),
        name=server.name,
        location=server.region,
        host=str(server.ip_address),
        port=server_data.port,
        vpn_type=server_data.vpn_type,
        status=server.status.value,
        current_load=0,
        max_users=server.max_users,
        priority=server_data.priority,
        is_active=server.is_active,
        last_health_check=None,
    )


@router.put("/{server_id}", response_model=ServerResponse)
async def update_server(
    server_id: str,
    server_data: ServerUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Update server"""
    stmt = select(Server).where(Server.id == server_id)
    result = await db.execute(stmt)
    server = result.scalar_one_or_none()
    
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    # Update fields
    if server_data.name is not None:
        server.name = server_data.name
    if server_data.location is not None:
        server.region = server_data.location
    if server_data.host is not None:
        server.ip_address = server_data.host
    if server_data.max_users is not None:
        server.max_users = server_data.max_users
    if server_data.is_active is not None:
        server.is_active = server_data.is_active
    if server_data.api_url is not None:
        server.agent_url = server_data.api_url
    if server_data.api_key is not None:
        server.agent_token = encrypt_data(server_data.api_key)
    
    # Update metadata
    metadata = server.server_metadata or {}
    if server_data.vpn_type is not None:
        metadata["vpn_type"] = server_data.vpn_type
    if server_data.priority is not None:
        metadata["priority"] = server_data.priority
    if server_data.port is not None:
        metadata["port"] = server_data.port
    server.server_metadata = metadata
    
    await db.commit()
    await db.refresh(server)
    
    return ServerResponse(
        id=str(server.id),
        name=server.name,
        location=server.region,
        host=str(server.ip_address),
        port=metadata.get("port", 443),
        vpn_type=metadata.get("vpn_type", "xray"),
        status=server.status.value,
        current_load=server.current_users,
        max_users=server.max_users,
        priority=metadata.get("priority", 0),
        is_active=server.is_active,
        last_health_check=server.last_health_check.isoformat() if server.last_health_check else None,
    )


@router.delete("/{server_id}")
async def delete_server(
    server_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Delete server"""
    stmt = select(Server).where(Server.id == server_id)
    result = await db.execute(stmt)
    server = result.scalar_one_or_none()
    
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    await db.delete(server)
    await db.commit()
    
    return {"status": "ok", "message": "Server deleted"}


@router.post("/{server_id}/health-check")
async def perform_health_check(
    server_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Perform manual health check"""
    orchestrator = ServerOrchestrator(db)
    
    is_healthy = await orchestrator.health_check(server_id)
    
    return {
        "server_id": server_id,
        "is_healthy": is_healthy,
    }


@router.post("/{server_id}/drain")
async def drain_server(
    server_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Put server in drain mode"""
    orchestrator = ServerOrchestrator(db)
    await orchestrator.drain_server(server_id)
    
    return {"status": "ok", "message": "Server set to drain mode"}


@router.post("/{server_id}/activate")
async def activate_server(
    server_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Activate server"""
    orchestrator = ServerOrchestrator(db)
    await orchestrator.activate_server(server_id)
    
    return {"status": "ok", "message": "Server activated"}
